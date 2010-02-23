#!/usr/bin/env python

from gui import *
from guicomps import *
from music import *
import d3d
import d3dc
import objtree as ot
import math
import tkSimpleDialog
import tkMessageBox
import time
import pickle
from ctypes import *
import struct
import types

CAMERA_NEAR_Z = 0.125
CAMERA_FAR_Z = 1024.0
CAMERA_ZOOM = 1.5

#frame = 0

def float2int(val):
    return struct.unpack('I', struct.pack('f', val))[0]

def int2float(val):
    return struct.unpack('f', struct.pack('I', val))[0]

def roundtoprec(val,prec):
    intrepr = float2int(val)
    intrepr = (intrepr + ((1 << (32-prec)) >> 1)) & (-1 << (32-prec))
    return int2float(intrepr)

    #if val==0: return 0
    #(m,e) = math.frexp(math.fabs(val))
    #m = (int(m*(2**prec)+.5))/(2.**prec)
    #return math.ldexp(m, e) * val/math.fabs(val)

def getprec(val,minp=0,maxp=32):
    if(minp==maxp):
        return minp
    if val==roundtoprec(val,(minp+maxp-1)/2):
        return getprec(val,minp,(minp+maxp+1)/2-1)
    return getprec(val,(minp+maxp+1)/2,maxp)

def evalSpline(x0, dx0, x1, dx1, x):
    a = 2*x0 - 2*x1 + dx0 + dx1
    b = 3*x1 - 3*x0 - 2*dx0 - dx1
    c = dx0
    d = x0
    return ((a*x + b)*x + c)*x + d


class MeshDisplay(Component):
    def __init__(self):
        Component.__init__(self)
        self.tree = None
        FloatBuf = c_float * 1000
        self.exported_program = create_string_buffer(10000)
        self.exported_constants = create_string_buffer(1024)
        self.basematrix = ot.makeMatrix (
            1,0,0,0,
            0,1,0,0,
            0,0,1,0,
            0,0,0,1)
        self.eyedist = 10.0
        self.constmap = {}
        self.badnode = None
        self.timebar = None
        # self.reftime = 0
        self.project = None

    def setTree(self, tree):
        windll.RenderDLL.init(c_void_p(d3d.getDevice()), self.project.engine_id, self.project.effect_file)

        ot.update_predefined_variables()

        self.tree = tree
        self.exportTree()
        if tree is None:
            self.playbutton.passivate()
        #    print constants
        #    sys.stdout.flush()

    def exportTree(self):
        try:
            if self.tree is not None:
                program, constants, self.constmap = ot.export(self.tree)
                for i,p in enumerate(program):
                    self.exported_program[i] = chr(p)
                for i,c in enumerate(constants):
                    struct.pack_into('f', self.exported_constants, i*4, c)
            self.badnode = None
            self.getRoot().window.setError(None)
        except ot.ExportException, e:
            self.badnode = e.node
            self.getRoot().window.setError(e.message)

    def setBinding(self, name, value):
        self.bindings[name] = value
        struct.pack_into('f', self.exported_constants, self.constmap[name]*4, value)

    def setProject(self, project):
        self.project = project
        windll.RenderDLL.reinit(self.project.engine_id, self.project.effect_file)
        ot.update_predefined_variables()
        initMusic(self.project.music_file)

    def render(self, info):
        global frame
        if self.tree and self.timebar and not self.badnode:
            if self.timebar.draggable.status != Draggable.DRAGGING and self.playbutton.active:
                self.timebar.area_pos = max(0,min(getMusicLength(),getMusicPos()))*1000

            d3d.setView((0,0,0),(0,0,1),CAMERA_FAR_Z)
            d3d.setState(d3dc.RS.ALPHABLENDENABLE, False)
            d3d.setState(d3dc.RS.ZENABLE, True)
            d3d.setState(d3dc.RS.CULLMODE, d3dc.RS.CULL.CCW)

            self.bindings = {}
            self.setBinding("time", max(0,self.timebar.area_pos/1000.) * (self.project.bpm / 60.0))
            
            oldrect = info.addScissorRect(self.pos + self.size)
            windll.RenderDLL.renderobj(self.exported_program, self.exported_constants)
            info.setScissorRect(oldrect)

            d3d.setState(d3dc.RS.CULLMODE, d3dc.RS.CULL.NONE)

    def handleMouseEvent(self, event, manager):
        if event.button == BUTTON_WHEELUP:
            self.eyedist /= 1.2
        elif event.button == BUTTON_WHEELDOWN:
            self.eyedist *= 1.2
        return event


def calcBrickPos(fieldpos, gridpos):
    return tuple(fieldpos[i] + gridpos[i] * Brick.SIZE[i] for i in range(2))

def tadd(p1,p2):
    return (p1[0]+p2[0], p1[1]+p2[1])

def tsub(p1,p2):
    return (p1[0]-p2[0], p1[1]-p2[1])

SPLINELENGTH = 10

def drawSpline(x0,y0, x1,y1, color):
    xl = [evalSpline(x0, 0, x1, 0, i/float(SPLINELENGTH)) for i in range(SPLINELENGTH+1)]
    yl = [evalSpline(y0, 42, y1, 42, i/float(SPLINELENGTH)) for i in range(SPLINELENGTH+1)]
    linelist = [(xl[i],yl[i],xl[i+1],yl[i+1],color) for i in range(SPLINELENGTH)]
    d3d.drawLines(linelist, 2.0)


class Brick(TextBevel):
    WIDTH = 80
    HEIGHT = 20
    SIZE = (WIDTH, HEIGHT)

    def __init__(self, node, field, gridpos, enc = None):
        TextBevel.__init__(self)
        self.node = node
        self.field = field
        self.gridpos = gridpos
        self.size = Brick.SIZE
        if enc is not None:
            self.extra_node_children = enc
        else:
            self.extra_node_children = []

    def getColor(self):
        if self.field.display.badnode == self.node:
            return 0xff0000
        return self.node.brickColor()

    def __getstate__(self):
        return (self.node, self.gridpos, self.extra_node_children)

    def __setstate__(self, state):
        if isinstance(state, types.TupleType):
            self.node, self.gridpos, self.extra_node_children = state
        else:
            self.__dict__ = state

    def render(self, info):
        self.text = self.node.getName()
        self.pos = calcBrickPos(self.field.pos, self.gridpos)
        self.lit = (self.field.status in (BrickField.IDLE,BrickField.CONNECTING) and
                    self.field.current_pos and
                    self.field.getGridPos(self.field.current_pos) == self.gridpos)
        self.pressed = (self == self.field.active or self in self.field.selected)
        TextBevel.render(self, info)

    def below(self, other):
        return (self.gridpos[0] == other.gridpos[0] and 
                self.gridpos[1] == other.gridpos[1]+1)

    def childBricks(self):
        child_bricks = [b for b in self.field.children if b.below(self)] + self.extra_node_children
        child_bricks.sort(lambda a,b : cmp(a.gridpos, b.gridpos))
        return child_bricks

    def buildTree(self, visited):
        if self.node not in visited:
            visited.add(self.node)

            child_bricks = self.childBricks()
            if isinstance(self.node, ot.Link) and self.node.label in self.field.labelbricks:
                child_bricks = self.field.labelbricks[self.node.label] + child_bricks

            self.node.children = [b.buildTree(visited) for b in child_bricks]
        return self.node


class Project:
    def __init__(self, field):
        self.bricks = field.children
        self.engine_id = 0
        self.effect_file = "../objects/default.fx"
        self.music_file = "../objects/Silence.ogg"
        self.bpm = 120.0


class BrickField(Container):
    IDLE = 0
    CREATING = 1
    MOVING = 2
    CONNECTING = 3
    SELECTING = 4

    def __init__(self, display, valuebar, scrollbar):
        Container.__init__(self)
        self.display = display
        self.valuebar = valuebar
        self.scrollbar = scrollbar
        self.status = BrickField.IDLE
        self.copying = False
        self.scrollstep = 4 * Brick.HEIGHT
        self.selected = set()
        self.base_selected = set()
        self.setActive(None)
        self.root = None
        self.frames = []
        self.current_pos = None
        self.addHotkey(d3dc.VK.DELETE, (lambda event, manager : self.delete(self.selected)))
        self.project = Project(self)
        self.display.setProject(self.project)
        self.labelbricks = dict()
        self.linkbricks = dict()

    def __getstate__(self):
        raise Exception("Internal error: Attempt to serialize the BrickField!")

    def delete(self, bricks):
        if self.root in bricks:
            self.setRoot(None)
        for b in bricks:
            self.removeChild(b)
            for c in self.children:
                if b in c.extra_node_children:
                    c.extra_node_children.remove(b)
        self.selected = set()
        self.base_selected = set()
        self.setActive(None)
        self.updateDisplay()

    def drawBrickFrame(self, gridpos):
        pos = calcBrickPos(self.pos, gridpos)
        drawBox(pos, Brick.SIZE, [0xa0ff8080,0x00000000,0xa0ff8080])

    def getConnectionPos(self, p, voffset):
        if isinstance(p,Brick):
            return tadd(calcBrickPos(self.pos, p.gridpos), (Brick.WIDTH/2, voffset))
        else:
            return p

    def drawConnection(self, a,b, color):
        aposx,aposy = self.getConnectionPos(a, Brick.HEIGHT)
        bposx,bposy = self.getConnectionPos(b, 0)
        drawSpline(aposx,aposy, bposx,bposy, color)

    def render(self, info):
        oldrect = info.addScissorRect(self.pos + self.size)

        for b in self.children:
            for c in b.extra_node_children:
                if not (b in self.selected or c in self.selected):
                    self.drawConnection(b,c, 0xff8080c0)

        Container.render(self, info)

        for b in self.children:
            targets = b.extra_node_children
            if isinstance(b.node, ot.Link) and b.node.label in self.labelbricks:
                targets = targets + self.labelbricks[b.node.label]
            for c in targets:
                if b in self.selected or c in self.selected:
                    self.drawConnection(b,c, 0xffffffff)

        if self.status == BrickField.CONNECTING:
            csource = self.origin_brick
            b = self.brickAt(self.getGridPos(self.current_pos))
            if not b == self.origin_brick:
                if b:
                    ctarget = b
                else:
                    ctarget = self.current_pos
                self.drawConnection(csource, ctarget, 0xffffffff)

        if self.root:
            for border in [2,4,6]:
                tborder = (border, border)
                col = 0xffffff + ((8-border) << 28)
                drawBox(tsub(self.root.pos, (border, border)), tadd(Brick.SIZE, (border*2, border*2)),
                        [col, 0, col])

        for f in self.frames:
            self.drawBrickFrame(f)

        if self.status == BrickField.SELECTING:
            drawBox(self.origin_pos, tsub(self.current_pos, self.origin_pos), [0xc0000000, 0x80000000, 0xc0000000])

        info.setScissorRect(oldrect)

        self.getRoot().window.pos = self.getGridPos(self.current_pos)

    def getGridPos(self, pos):
        if pos is None:
            return None
        return tuple((pos[i]-self.pos[i])/Brick.SIZE[i] for i in range(2))

    def setRoot(self, root):
        self.root = root
        self.updateDisplay()

    def setActive(self, active):
        self.active = active
        self.updateValueBar(active)

    def makeBrickMap(self, typ, bmap):
        bmap.clear()
        for b in self.children:
            if isinstance(b.node, typ):
                if b.node.label not in bmap:
                    bmap[b.node.label] = []
                bmap[b.node.label].append(b)

    def updateDisplay(self):
        self.makeBrickMap(ot.Identity, self.labelbricks)
        self.makeBrickMap(ot.Link, self.linkbricks)
                    
        if self.root:
            self.display.setTree(self.root.buildTree(set()))
        else:
            self.display.setTree(None)

    def updateValueBar(self, brick):
        for va in list(self.valuebar.children):
            self.valuebar.removeChild(va, update=False)
        any_va = False
        if brick:
            node = brick.node

            def valuefunc(param, value):
                if param in node.getOptions():
                    return node.option(param, value)
                p_index = node.getParameters().index(param)
                if value is not None:
                    valuestr = str(value)
                    eq_pos = valuestr.find("=")
                    if eq_pos != -1:
                        p_name = valuestr[0:eq_pos].strip()
                        value = valuestr[eq_pos+1:]
                        node.setParamName(p_index, p_name)
                    try:
                        node.definitions[p_index].setExp(value)
                    except SyntaxError:
                        pass
                return node.definitions[p_index].exp
                
            for op in node.getOptions() + node.getParameters():
                vbutton = ValueAdjuster(op, valuefunc, self)
                self.valuebar.addChild(vbutton)
                any_va = True

        if not any_va:
            self.valuebar.addChild(Component())

    def brickAt(self, gridpos):
        for b in self.children:
            if b.gridpos == gridpos:
                return b
        return None

    def selectionRect(self):
        x1,y1 = self.current_pos
        x2,y2 = self.origin_pos
        x1,x2 = min(x1,x2),max(x1,x2)
        y1,y2 = min(y1,y2),max(y1,y2)
        return (x1,y1,x2-x1,y2-y1)

    def setCreating(self, creator):
        self.creator = creator
        self.status = BrickField.CREATING

    def legalBrickPos(self, gridpos, ignoreselected):
        if not (gridpos[0] >= 0 and gridpos[1] >= 0):
            return False
        return all(b.gridpos != gridpos
                   for b in self.children
                   if not ignoreselected or not b in self.selected)

#    def handleKeyEvent(self, event, manager):
#        if event.direction == KEY_DOWN:
#            tkMessageBox.showerror("Key", "%d" % event.code)

    def handleMouseEvent(self, event, manager):
        self.current_pos = (event.x, event.y)
        gridpos = self.getGridPos(self.current_pos)
        self.frames = []
        old_status = self.status

        if event.buttonDown(BUTTON_WHEELDOWN):
            self.scrollbar.setAreaPos(self.scrollbar.getAreaPos()+self.scrollstep)
        if event.buttonDown(BUTTON_WHEELUP):
            self.scrollbar.setAreaPos(self.scrollbar.getAreaPos()-self.scrollstep)
        
        if self.status == BrickField.IDLE:
            if event.buttonDown(BUTTON_LEFT):
                b = self.brickAt(gridpos)
                if b:
                    # Brick clicked
                    if event.keyHeld(VK.SHIFT):
                        # Toggle selection
                        if b in self.selected:
                            self.selected.remove(b)
                        else:
                            self.selected.add(b)
                    else:
                        if (not self.active and not self.selected) or b not in self.selected:
                            # Activate
                            self.setActive(b)
                            self.selected = set([b])
                        if event.double:
                            if self.root == b:
                                self.display.setProject(self.project)
                            self.setRoot(b)
                            #self.display.reftime = time.clock()
                            #playMusic(0)
                        else:
                            self.status = BrickField.MOVING
                            self.origin_brick = b
                            self.copying = event.keyHeld(VK.CONTROL)
                else:
                    # Empty space clicked
                    if event.keyHeld(VK.SHIFT):
                        self.base_selected = self.selected
                    else:
                        self.base_selected = set()
                        self.selected = set()
                    self.setActive(None)
                    self.status = BrickField.SELECTING
                    self.origin_pos = self.current_pos
                    if event.double:
                        self.setRoot(None)
            if event.buttonDown(BUTTON_RIGHT):
                b = self.brickAt(gridpos)
                if b:
                    # Brick right-clicked
                    self.status = BrickField.CONNECTING
                    self.origin_brick = b

        if self.status == BrickField.MOVING:
            # Moving or copying
            diffpos = tsub(gridpos,self.origin_brick.gridpos)
            if event.buttonDown(BUTTON_RIGHT):
                # Abort move
                self.status = BrickField.IDLE
            elif event.buttonUp(BUTTON_LEFT):
                # Button released - move bricks
                if all(self.legalBrickPos(tadd(sb.gridpos, diffpos), not self.copying) for sb in self.selected):
                    # No conflicts
                    if self.copying:
                        # Copy bricks
                        copymap = dict()
                        for sb in self.selected:
                            nodecopy = sb.node.clone()
                            brickcopy = Brick(nodecopy, self, tadd(sb.gridpos, diffpos))
                            copymap[sb] = brickcopy
                            self.addChild(brickcopy)
                        for sb in self.selected:
                            for sbc in sb.extra_node_children:
                                if sbc in self.selected:
                                    copymap[sb].extra_node_children.append(copymap[sbc])
                                else:
                                    copymap[sb].extra_node_children.append(sbc)
                        self.selected = set(copymap.values())
                        self.copying = False
                    else:
                        # Move bricks
                        for sb in self.selected:
                            sb.gridpos = tadd(sb.gridpos, diffpos)
                    self.updateDisplay()
                self.status = BrickField.IDLE
            else:
                self.frames = [
                    tadd(c.gridpos, diffpos)
                    for c in self.children
                    if c in self.selected
                ]

        if self.status == BrickField.SELECTING:
            self.selected = set([
                b for b in self.children
                if b.hitRect(self.selectionRect())
            ])
            self.selected.update(self.base_selected)

            if event.buttonDown(BUTTON_RIGHT):
                # Abort select
                self.setActive(None)
                self.selected = self.base_selected
                self.status = BrickField.IDLE
            elif event.buttonUp(BUTTON_LEFT):
                # Button released - end select
                self.status = BrickField.IDLE
        
        if self.status == BrickField.CONNECTING:
            b = self.brickAt(gridpos)
            if event.buttonUp(BUTTON_RIGHT):
                if b and not b == self.origin_brick:
                    if b in self.origin_brick.extra_node_children:
                        self.origin_brick.extra_node_children.remove(b)
                    else:
                        self.origin_brick.extra_node_children.append(b)
                    self.updateDisplay()
                self.status = BrickField.IDLE
#            elif event.buttonDown(BUTTON_RIGHT) and event.double:
#                if b in self.selected:
#                    self.delete(self.selected)
#                else:
#                    self.delete([b])
#                self.status = BrickField.IDLE

        if self.status == BrickField.CREATING:
            if event.buttonDown(BUTTON_RIGHT):
                # Abort creation
                self.status = BrickField.IDLE
            elif event.buttonDown(BUTTON_LEFT):
                if not self.brickAt(gridpos):
                    node = self.creator()
                    node.setDefaultValues()
                    b = Brick(node, self, gridpos)
                    self.addChild(b)
                    self.updateDisplay()
                self.status = BrickField.IDLE
            else:
                self.frames = [gridpos]

        sticky_states = [BrickField.MOVING, BrickField.CONNECTING, BrickField.SELECTING]
        if old_status not in sticky_states and self.status in sticky_states:
            manager.addMouseListener(self)
        elif old_status in sticky_states and self.status not in sticky_states:
            manager.removeMouseListener(self)

    def save(self, filename):
        # Clear field fields
        for b in self.children:
            if "field" in b.node.__dict__:
                b.node.field = None
        try:
            f = open(filename, 'w')
            pickle.dump(self.project, f)
            f.close()
        except IOError:
            tkMessageBox.showerror("File error", "Could not write to file")
        # Restore field fields
        for b in self.children:
            if "field" in b.node.__dict__:
                b.node.field = self

    def _load(self, filename, offset):
        try:
            f = open(filename, 'r')
            project = pickle.load(f)
            f.close()

            if isinstance(project, Project):
                self.project = project
                newbricks = project.bricks
                project.bricks = self.children
            else:
                self.project = Project(self)
                newbricks = project
            self.display.setProject(self.project)

            for c in newbricks:
                c.__init__(c.node, self, tadd(c.gridpos, offset), c.extra_node_children)

                # HACKs to improve loading compatibility
                if isinstance(c.node, ot.Identity) and "label" not in c.node.__dict__:
                    c.node.label = ""
                if isinstance(c.node, ot.DefinitionNode) and not isinstance(c.node, ot.LocalDefinition):
                    globaldef = ot.GlobalDefinition(c.node.var)
                    globaldef.definitions = c.node.definitions
                    c.node = globaldef
                if isinstance(c.node, ot.Text):
                    item = ot.Item(c.node.index)
                    item.definitions = c.node.definitions
                    c.node = item
                for i,d in enumerate(c.node.definitions):
                    if isinstance(d, types.TupleType):
                        c.node.definitions[i] = d[1]

                # Restore field field
                if isinstance(c.node, ot.Identity) or isinstance(c.node, ot.Link):
                    c.node.field = self
                self.addChild(c)
        except IOError:
            tkMessageBox.showerror("File error", "Could not read file")

    def load(self, filename):
        self.selected = set()
        self.setActive(None)
        self.status = BrickField.IDLE
        self.current_pos = None
        self.setRoot(None)
        for c in list(self.children):
            self.removeChild(c, update = False)
        self._load(filename, (0,0))

    def insert(self, filename):
        lowest = -1
        for c in self.children:
            lowest = max(lowest, c.gridpos[1])
        self._load(filename, (0,lowest+1))

    def set_effect_file(self, filename):
        self.effect_file = filename

    def set_music_file(self, filename):
        self.music_file = filename

    def set_bpm(self, bpm):
        self.bpm = bpm



class CreateButton(TextBevel):
    def __init__(self, label, creator, field, hotkey = None):
        TextBevel.__init__(self, label)
        self.creator = creator
        self.field = field
        self.hover = False
        self.color = creator().brickColor()
        if hotkey:
            self.addHotkey(ord(hotkey), (lambda event, manager : self.click()))

    def getColor(self):
        return self.color

    def updateMinMax(self):
        self.minsize = Brick.SIZE
        self.maxsize = Brick.SIZE

    def click(self):
        self.field.setCreating(self.creator)
        
    def handleMouseEvent(self, event, manager):
        if not self.hover:
            self.hover = True
            manager.addMouseListener(self)

        if self.hit(event.x, event.y):
            if event.buttonDown(BUTTON_LEFT):
                self.click()
        else:
            self.hover = False
            manager.removeMouseListener(self)

        return event

    def render(self, info):
        self.lit = self.hover
        self.pressed = self.field.status == BrickField.CREATING and self.field.creator == self.creator
        TextBevel.render(self, info)


class ValueAdjuster(TextBevel, Draggable):
    def __init__(self, param, valuefunc, field):
        TextBevel.__init__(self)
        Draggable.__init__(self, ORIENTATION_HORIZONTAL)
        self.param = param
        self.valuefunc = valuefunc
        self.field = field
        self.setValue(None)
        self.minsize = Brick.SIZE

    def setValue(self, newvalue):
        self.value = self.valuefunc(self.param, newvalue)
        self.text = self.makeName()
        self.field.display.exportTree()

    def makeName(self):
        return "%s = %s" % (self.param, self.value)

    def handleMouseEvent(self, event, manager):
        self.double = event.double
        event = Draggable.handleMouseEvent(self, event, manager)
        if self.status == Draggable.HOVER and event.buttonDown(BUTTON_RIGHT):
            self.setIdle(event, manager)
            newvalue = tkSimpleDialog.askstring("Enter value",
                                                self.param,
                                                initialvalue=self.value)
            self.setValue(newvalue)
            self.field.updateValueBar(self.field.active)
            self.field.updateDisplay()
            return None
        return event

    def initDragging(self):
        self.doubleclicked = self.double
        try:
            self.orig_value = float(self.value)
        except ValueError:
            self.orig_value = None
        if self.doubleclicked:
            self.orig_precision = getprec(self.orig_value)

    def updateDragging(self, delta):
        if self.orig_value is not None:
            if self.doubleclicked:
                self.setValue(roundtoprec(self.orig_value,self.orig_precision+delta/10))
            else: 
                base = max(abs(self.orig_value), 0.1)
                value_delta = base/100.0 * delta
                self.setValue(self.orig_value + value_delta)

    def stopDragging(self):
        pass

class ValueBar(Sequence):
    def __init__(self):
        Sequence.__init__(self, ORIENTATION_HORIZONTAL, spacing = 10)
        self.weight = 0.001

    def updateMinMax(self):
        Sequence.updateMinMax(self)
        self.minsize = (self.minsize[0],Brick.SIZE[1])


class TimeSlider(Scrollbar):
    def __init__(self, orientation, display):
        self.display = display
        Scrollbar.__init__(self, orientation)

    #music_was_playing = False
    def initDragging(self):
        Scrollbar.initDragging(self)
        #self.music_was_playing = musicIsPlaying()
        stopMusic()

    def updateDragging(self, delta):
        Scrollbar.updateDragging(self, delta)

    def stopDragging(self):
        Scrollbar.stopDragging(self)
        #if self.music_was_playing:
        #    playMusic(self.area_pos/1000.)
        self.display.playbutton.repeatAction()


class PlayButton(Button):
    def __init__(self, display):
        self.display = display
        self.active = False
        Button.__init__(self, self.action, "Play", 0x808080)

    def action(self):
        self.active = not self.active
        self.repeatAction()

    def repeatAction(self):
        if self.active:
            self.activate()
        else:
            self.passivate()
        
    def activate(self):
        self.active = True
        self.color = 0xcc5555
        self.text = "Stop"
        playMusic(self.display.timebar.area_pos/1000.0)
        
    def passivate(self):
        self.active = False
        self.text = "Play"
        self.color = 0x808080
        stopMusic()    


class EditorRoot(Root):
    def __init__(self, alt_child):
        Root.__init__(self)
        self.alt_child = alt_child
        self.alt_active = False
        self.normal_seq = []
        self.addHotkey(ord(' '), (lambda event, manager : self.switch()))

    def switch(self):
        seq = self.children[0]
        if not self.alt_active:
            self.normal_seq = list(seq.children)
            for c in self.normal_seq:
                c.remove()
            seq.addChild(self.alt_child)
            self.alt_active = True
        else:
            self.alt_child.remove()
            for c in self.normal_seq:
                seq.addChild(c)
            self.alt_active = False
            self.normal_seq = []
            
