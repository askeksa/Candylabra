#!/usr/bin/env python

from gui import *
from guicomps import *
from music import *
import d3d
import d3dc
import objtree as ot
import math
import Tkinter
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

tkroot = Tkinter.Tk()
tkroot.withdraw()

def float2int(val):
    return struct.unpack('I', struct.pack('f', val))[0]

def int2float(val):
    return struct.unpack('f', struct.pack('I', val))[0]

def roundtoprec(val,prec):
    if prec <= 32:
        intrepr = float2int(val)
        intrepr = (intrepr + ((1 << (32-prec)) >> 1)) & (-1 << (32-prec))
        return int2float(intrepr)
    else:
        return val

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
        windll.RenderDLL.init(c_void_p(d3d.getDevice()), self.project.engine_id, self.project.effect_file, self.project.sync_file, self.project.data_file)

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
        windll.RenderDLL.reinit(self.project.engine_id, self.project.effect_file, self.project.sync_file, self.project.data_file)
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
            render_return = windll.RenderDLL.renderobj(self.exported_program, self.exported_constants)
            info.setScissorRect(oldrect)

            d3d.setState(d3dc.RS.CULLMODE, d3dc.RS.CULL.NONE)

            timer0 = render_return & 0xffff
            timer1 = (render_return >> 16) & 0xffff
            timers = []
            if timer0 != 0:
                timers.append(timer0)
            if timer1 != 0:
                timers.append(timer1)
            info.window.setTimers(timers)

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
        self.node.children = []
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
            if isinstance(self.node, ot.Loop):
                child_bricks = [self] + child_bricks

            self.node.children = [b.buildTree(visited) for b in child_bricks]
        return self.node


class Project:
    def __init__(self, field):
        self.bricks = field.children
        self.engine_id = 0
        self.effect_file = "../objects/default.fx"
        self.music_file = "../objects/Silence.ogg"
        self.bpm = 120.0
        self.sync_file = "../objects/dummy.sync"
        self.data_file = "../objects/dummy.dat"

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
        self.hidden = False
        self.addHotkey(d3dc.VK.TAB, (lambda event, manager : self.switchHidden()))

    def __getstate__(self):
        raise Exception("Internal error: Attempt to serialize the BrickField!")

    def switchHidden(self):
        self.hidden = not self.hidden

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
        if self.hidden:
            return

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

            for op in node.getOptions():
                vbutton = OptionAdjuster(op, self)
                self.valuebar.addChild(vbutton)
                any_va = True

            for param in node.getParameters():
                vbutton = ParamAdjuster(param, node, self)
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

    def bottomBrickPos(self):
        return max(b.gridpos[1] for b in self.children) * Brick.HEIGHT

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
        for b in self.project.bricks:
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
                dummy = Project(self)
                for pf in ["sync_file", "data_file"]:
                    if pf not in project.__dict__:
                        project.__dict__[pf] = dummy.__dict__[pf]
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
                if isinstance(c.node, ot.Transform) and "scope" not in c.node.__dict__:
                    if "isglobal" in c.node.__dict__:
                        c.node.scope = 1 if c.node.isglobal else 0
                        del c.node.isglobal
                    else:
                        c.node.scope = 0
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
    def __init__(self, field):
        TextBevel.__init__(self, fontname = u"Courier New", fontsize = 15)
        Draggable.__init__(self, ORIENTATION_HORIZONTAL)
        self.field = field
        self.minsize = Brick.SIZE
        self.editor = None

    def handleMouseEvent(self, event, manager):
        self.double = event.double

        event = Draggable.handleMouseEvent(self, event, manager)

        if self.status == Draggable.HOVER:
            self.handleHover(event, True)
        elif self.status == Draggable.IDLE:
            self.handleHover(event, False)

        if self.status == Draggable.HOVER and event.buttonDown(BUTTON_RIGHT):
            cursor, mark = self.getTextEditRange(event.x)
            length_before = len(self.text)
            self.text = self.getValue()
            prefix_length = length_before - len(self.text)
            cursor = max(0, cursor - prefix_length)
            mark = max(0, mark - prefix_length)

            self.editor = ValueAdjusterEditor(self, cursor, mark, manager)
            manager.addMouseListener(self.editor)
            manager.addKeyListener(self.editor)
            return None

        return event

    def acceptEditedText(self, text):
        self.setValue(text)
        self.field.updateValueBar(self.field.active)
        self.field.updateDisplay()

    def detachEditor(self, manager):
        manager.removeMouseListener(self.editor)
        manager.removeKeyListener(self.editor)
        self.editor = None

    def initDragging(self):
        self.doubleclicked = self.double
        self.orig_value = self.initDragValue()
        self.drag_value = self.orig_value
        if self.doubleclicked:
            self.orig_precision = getprec(self.orig_value)

    def updateDragging(self, delta, other=0):
        if self.orig_value is not None:
            if self.doubleclicked:
                self.setDragValue(roundtoprec(self.orig_value,self.orig_precision+delta/10))
            else:
                value_delta = delta * math.exp(-8-0.01*other)
                self.setDragValue(self.orig_value + value_delta)

    def render(self, info):
        if self.editor:
            block_range = (self.editor.rangeStart(), self.editor.rangeEnd(), 0xff808080)
            cursor_range = (self.editor.cursor, self.editor.cursor, 0xffffffff)
            self.setColorRanges([block_range, cursor_range])
        TextBevel.render(self, info)

    def getTextEditRange(self, x):
        i,lx,rx = self.getCharAt(x)
        if x > (lx + rx)/2:
            i += 1
        if i < 0:
            i = 0
        if i > len(self.text):
            i = len(self.text)
        return i,i


class ValueAdjusterEditor:
    def __init__(self, adjuster, initial_cursor, initial_mark, manager):
        self.adjuster = adjuster
        self.cursor = initial_cursor
        self.mark = initial_mark
        self.manager = manager
        self.original_text = adjuster.text
        self.undo_stack = []
        self.redo_stack = []

    def rangeStart(self):
        return min(self.cursor, self.mark)

    def rangeEnd(self):
        return max(self.cursor, self.mark)

    def hasRange(self):
        return self.cursor != self.mark

    def handleMouseEvent(self, event, manager):
        return None

    def handleKeyEvent(self, event, manager):
        if not event.direction == KEY_DOWN:
            return None

        text = self.adjuster.text
        old_state = text, self.cursor, self.mark

        # Commands
        if event.keyHeld(d3dc.VK.CONTROL):
            if event.code == ord('A'):
                # Select all
                self.cursor = len(text)
                self.mark = 0
            elif event.code == ord('C'):
                # Copy
                if self.hasRange():
                    cliptext = text[self.rangeStart():self.rangeEnd()]
                else:
                    cliptext = text
                tkroot.clipboard_clear()
                tkroot.clipboard_append(cliptext)
            elif event.code == ord('V'):
                # Paste
                cliptext = tkroot.selection_get(selection = "CLIPBOARD")
                text = text[:self.rangeStart()] + cliptext + text[self.rangeEnd():]
                self.cursor = self.rangeStart() + len(cliptext)
                self.mark = self.cursor
            elif event.code == ord('X'):
                # Cut
                if self.hasRange():
                    cliptext = text[self.rangeStart():self.rangeEnd()]
                    text = text[:self.rangeStart()] + text[self.rangeEnd():]
                    self.cursor = self.rangeStart()
                    self.mark = self.cursor
                else:
                    cliptext = text
                    text = ""
                    self.cursor = 0
                    self.mark = self.cursor
                tkroot.clipboard_clear()
                tkroot.clipboard_append(cliptext)
            elif event.code == ord('Y'):
                # Redo
                if len(self.redo_stack) > 0:
                    self.undo_stack.append((text, self.cursor, self.mark))
                    text, self.cursor, self.mark = self.redo_stack.pop()
                    self.adjuster.text = text
            elif event.code == ord('Z'):
                # Undo
                if len(self.undo_stack) > 0:
                    self.redo_stack.append((text, self.cursor, self.mark))
                    text, self.cursor, self.mark = self.undo_stack.pop()
                    self.adjuster.text = text

        # Editor terminators
        elif event.code == d3dc.VK.RETURN:
            self.adjuster.acceptEditedText(text)
            if not event.keyHeld(d3dc.VK.SHIFT):
                self.adjuster.detachEditor(manager)
            return None
        elif event.code == d3dc.VK.ESCAPE:
            self.adjuster.acceptEditedText(self.original_text)
            if not event.keyHeld(d3dc.VK.SHIFT):
                self.adjuster.detachEditor(manager)
            return None

        # Navigation
        elif event.code == d3dc.VK.LEFT:
            if event.keyHeld(d3dc.VK.SHIFT):
                self.cursor = max(0, self.cursor - 1)
            else:
                if self.hasRange():
                    self.cursor = self.rangeStart()
                else:
                    self.cursor = max(0, self.cursor - 1)
                self.mark = self.cursor
        elif event.code == d3dc.VK.RIGHT:
            if event.keyHeld(d3dc.VK.SHIFT):
                self.cursor = min(self.cursor + 1, len(text))
            else:
                if self.hasRange():
                    self.cursor = self.rangeEnd()
                else:
                    self.cursor = min(self.cursor + 1, len(text))
                self.mark = self.cursor
        elif event.code == d3dc.VK.HOME:
            self.cursor = 0
            if not event.keyHeld(d3dc.VK.SHIFT):
                self.mark = self.cursor
        elif event.code == d3dc.VK.END:
            self.cursor = len(text)
            if not event.keyHeld(d3dc.VK.SHIFT):
                self.mark = self.cursor

        # Deletion
        elif event.code == d3dc.VK.BACK:
            if self.hasRange():
                text = text[:self.rangeStart()] + text[self.rangeEnd():]
                self.cursor = self.rangeStart()
                self.mark = self.cursor
            elif self.cursor > 0:
                text = text[:self.cursor-1] + text[self.cursor:]
                self.cursor -= 1
                self.mark = self.cursor
        elif event.code == d3dc.VK.DELETE:
            if self.hasRange():
                text = text[:self.rangeStart()] + text[self.rangeEnd():]
                self.cursor = self.rangeStart()
                self.mark = self.cursor
            elif self.cursor < len(text):
                text = text[:self.cursor] + text[self.cursor+1:]

        # Text input
        elif event.char >= ord(' ') and event.char <= ord('~'):
            text = text[:self.rangeStart()] + chr(event.char) + text[self.rangeEnd():]
            self.cursor = self.rangeStart() + 1
            self.mark = self.cursor

        if text != self.adjuster.text:
            self.undo_stack.append(old_state)
            self.redo_stack = []
            self.adjuster.text = text
        return None


class OptionAdjuster(ValueAdjuster):
    def __init__(self, option, field):
        ValueAdjuster.__init__(self, field)
        self.option = option
        self.updateValue()

    def getName(self):
        return self.option.getName()

    def getValue(self):
        return self.option.getString()

    def setValue(self, value):
        if value is not None:
            self.option.setString(value)
        self.updateValue()

    def updateValue(self):
        self.text = self.option.getName() + " = " + self.option.getString()
        self.field.display.exportTree()

    def handleHover(self, event, hover):
        pass

    def verifyDrag(self, event, manager):
        return self.option.getFloat() is not None

    def initDragValue(self):
        return self.option.getFloat()

    def setDragValue(self, value):
        self.drag_value = value
        self.option.setFloat(value)
        self.updateValue()

    def stopDragging(self):
        self.orig_value = None

    def getTextEditRange(self, x):
        return len(self.text),0


class ParamAdjuster(ValueAdjuster):
    def __init__(self, param, node, field):
        ValueAdjuster.__init__(self, field)
        self.param = param
        self.node = node
        self.setValue(None)
        self.hilight = None

    def getName(self):
        return self.param

    def getValue(self):
        return self.value

    def setValue(self, value):
        p_index = self.node.getParameters().index(self.param)
        if value is not None:
            valuestr = str(value)
            eq_pos = valuestr.find("=")
            if eq_pos != -1:
                p_name = valuestr[0:eq_pos].strip()
                value = valuestr[eq_pos+1:].strip()
                self.node.setParamName(p_index, p_name)
            try:
                self.node.definitions[p_index].setExp(value)
            except SyntaxError:
                pass
        self.value = self.node.definitions[p_index].exp
        self.text = self.makeName()
        self.field.display.exportTree()

    def paramPrefix(self):
        return str(self.param) + " = "

    def makeName(self):
        return self.paramPrefix() + str(self.value)

    def expandTextRange(self, i, charfuns):
        maxmatch = 0
        for cf,vf in charfuns:
            if i != -1 and cf(self.text[i]):
                left_i = i
                right_i = i
                while left_i > 0 and cf(self.text[left_i-1]):
                    left_i -= 1
                while right_i < len(self.text)-1 and cf(self.text[right_i+1]):
                    right_i += 1
                left_i,right_i = vf(left_i,right_i)
                if left_i is not None and right_i is not None:
                    match = right_i - left_i + 1
                    if match > maxmatch:
                        maxmatch = match
                        left = left_i
                        right = right_i
        if maxmatch > 0:
            return (left,right,self.text[left:right+1])
        else:
            return None

    def expandTextToken(self, i, floatflag, idflag):
        def floatchar(c):
            return c.isdigit() or c == "."
        def floatverify(left,right):
            if left > 0 and self.text[left-1] == '-':
                if left == 1 or not (self.text[left-2].isalnum() or self.text[left-2] == ')'):
                    left -= 1
            return left,right
                
        def idchar(c):
            return c.isalnum() or c == "_"
        def idverify(left,right):
            if right < len(self.text)-1 and self.text[right+1] == '(':
                return None,None
            return left,right
        
        charfuns = []
        if floatflag:
            charfuns += [(floatchar,floatverify)]
        if idflag:
            charfuns += [(idchar,idverify)]

        return self.expandTextRange(i, charfuns)

    def verifyDrag(self, event, manager):
        return self.hilight is not None

    def handleHover(self, event, hover):
        if hover:
            i,lx,rx = self.getCharAt(event.x)
            if i >= len(self.paramPrefix()) and i < len(self.text):
                self.hilight = self.expandTextToken(i, floatflag = True, idflag = True)
                return
            else:
                token = self.expandTextToken(len(self.text)-1, floatflag = True, idflag = False)
                if token is not None:
                    l,r,t = token
                    if l == len(self.paramPrefix()):
                        self.hilight = l,r,t
                        return
        self.hilight = None

    def getTextEditRange(self, x):
        if self.hilight:
            l,r,t = self.hilight
            return r+1,l
        else:
            return ValueAdjuster.getTextEditRange(self, x)

    def initDragValue(self):
        l,r,t = self.hilight
        p = len(self.paramPrefix())
        try:
            self.orig_value = float(str(self.value)[l-p:r-p+1])
            left,right = l,r
        except ValueError:
            # Find or create factor on variable
            factor_found = False
            if r < len(self.text)-1 and self.text[r+1] == '*':
                i = r+2
                if i < len(self.text) and self.text[i] == '-':
                    i += 1
                if i < len(self.text):
                    left,right,tt = self.expandTextToken(i, floatflag = True, idflag = False)
                    if left is not None and right is not None:
                        if not (right < len(self.text)-1 and self.text[right+1] in ['^', '@', '|', '#']):
                            left = r+2
                            factor_found = True
            if not factor_found:
                # Create factor on variable
                self.setValue(self.value[:l-p] + "(" + self.value[l-p:r-p+1] + "*1)" + self.value[r-p+1:])
                left = r+3
                right = left
        self.hilight = (left,right,self.text[left:right+1])
        return float(str(self.value)[left-p:right-p+1])

    def setDragValue(self, value):
        self.drag_value = value
        l,r,t = self.hilight
        p = len(self.paramPrefix())
        value = ot.float2string(value)
        old_value = str(self.value)
        self.setValue(old_value[:l-p] + value + old_value[r-p+1:])
        r = l + len(value)-1
        t = value
        self.hilight = l,r,t

    def stopDragging(self):
        l,r,t = self.hilight
        p = len(self.paramPrefix())
        if self.drag_value == 1.0 and l > 0 and self.text[l-1] == '*':
            if not (r < len(self.text)-1 and self.text[r+1] in ['^', '@', '|', '#']):
                # Remove factor
                self.setValue(self.value[:l-p-1] + self.value[r-p+1:])
                # If parenthesized id is left, remove parentheses
                token = self.expandTextToken(l-2, floatflag = False, idflag = True)
                if token is not None:
                    l,r,t = token
                    if l > 0 and self.text[l-1] == '(' and r < len(self.text)-1 and self.text[r+1] == ')':
                        self.setValue(self.value[:l-p-1] + t + self.value[r-p+2:])
        
        self.orig_value = None

    def render(self, info):
        if self.hilight:
            l,r,t = self.hilight
            self.setColorRanges([(l,r+1,0xffe0e0e0)])
        else:
            self.setColorRanges([])
        ValueAdjuster.render(self, info)


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

    def updateDragging(self, delta, other):
        Scrollbar.updateDragging(self, delta, other)

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
        self.addHotkey(ord(' '), (lambda event, manager : self.action()))

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
    def __init__(self, child_funs):
        Root.__init__(self)
        self.child_funs = child_funs
        self.child_index = 0
        self.addChild(child_funs[0]())
        self.addHotkey(d3dc.VK.ESCAPE, (lambda event, manager : self.switch()))

    def switch(self):
        self.child_index = (self.child_index + 1) % len(self.child_funs)
        self.children[0].remove()
        self.addChild(self.child_funs[self.child_index]())
            
