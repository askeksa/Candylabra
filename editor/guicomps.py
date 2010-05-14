#!/usr/bin/env python

import sys
from gui import *
import d3d
from d3dc import *


def weighColor(color, weight):
    masks = [0xff0000, 0x00ff00, 0x0000ff]
    return sum(int(min((color & mask) * weight, mask)) & mask for mask in masks)

def addTuple(tup, n):
    t1,t2 = tup
    return (t1+n,t2+n)

def drawBox(pos, size, colors):
    x1,y1 = pos
    w,h = size
    x2,y2 = x1+w,y1+h

    coords = [
        (x1,y1), (x1+2,y1+2),
        (x2,y1), (x2-2,y1+2),
        (x2,y2), (x2-2,y2-2),
        (x1,y2), (x1+2,y2-2)]

    indices = [
        [(0,2,1),(1,2,3),(0,1,6),(6,1,7)],
        [(1,3,7),(7,3,5)],
        [(2,4,3),(3,4,5),(6,7,4),(4,7,5)]]

    vertices = [
        (float(x),float(y),1.0,1.0,colors[c])
        for c,tril in enumerate(indices)
        for tri in tril
        for i in tri
        for x,y in [coords[i]]]

    d3d.setState(RS.FVF, FVF.XYZRHW | FVF.DIFFUSE)
    d3d.setTransform()
    d3d.setState(RS.ZENABLE, False)
    d3d.setState(RS.ALPHABLENDENABLE, True)
    d3d.setState(RS.SRCBLEND, RS.BLEND.SRCALPHA)
    d3d.setState(RS.DESTBLEND, RS.BLEND.INVSRCALPHA)
    d3d.drawVertices(TYPE.TRIANGLELIST, vertices)


class Bevel(Component):
    DEFAULT_COLOR = 0x808080

    def __init__(self):
        Component.__init__(self)
        self.lit = False
        self.pressed = False
        self.minsize = (6,6)
        self.maxsize = (Component.MAXSIZE,Component.MAXSIZE)

    def getColor(self):
        return Bevel.DEFAULT_COLOR

    def render(self, info):
        color = self.getColor()
        if self.lit:
            color = weighColor(color, 0.75) + weighColor(0xffffff, 0.25)
        lcolor = weighColor(color, 0.5) + weighColor(0xffffff, 0.5)
        dcolor = weighColor(color, 0.5)
        if self.pressed:
            lcolor,dcolor = dcolor,lcolor
        colors = [c | 0xff000000 for c in [lcolor, color, dcolor]]
        
        drawBox(self.pos, self.size, colors)


class TextBevel(Bevel):
    DEFAULT_FONTNAME = u"Arial"
    DEFAULT_FONTSIZE = 11

    def __init__(self, text = "", fontname = None, fontsize = None):
        Bevel.__init__(self)
        self.text = text
        self.fontname = fontname
        self.fontsize = fontsize
        self.font = None

    def render(self, info):
        Bevel.render(self, info)
        if not self.font:
            fontname = self.fontname
            fontsize = self.fontsize
            if fontname is None:
                fontname = TextBevel.DEFAULT_FONTNAME
            if fontsize is None:
                fontsize = TextBevel.DEFAULT_FONTSIZE
            self.font = d3d.Font(fontname, fontsize)
        text = (unicode(self.text),) + self.pos + self.size + (0xff000000, FONT.CENTER | FONT.VCENTER)
        d3d.drawTexts(self.font, [text])


class Button(TextBevel):
    IDLE = 0
    HOVER = 1
    PRESSED = 2

    def __init__(self, action, text = "", color = Bevel.DEFAULT_COLOR):
        TextBevel.__init__(self, text)
        self.action = action
        self.color = color
        self.minsize = (80,20)
        self.maxsize = (80,20)
        self.status = Button.IDLE

    def getColor(self):
        return self.color

    def setIdle(self, event, manager):
        self.status = Button.IDLE
        self.lit = False
        self.pressed = False
        manager.removeMouseListener(self)

    def handleMouseEvent(self, event, manager):
        if self.status == Button.IDLE:
            self.status = Button.HOVER
            self.lit = True
            manager.addMouseListener(self)
        if self.status == Button.HOVER:
            if not self.hit(event.x, event.y):
                self.setIdle(event, manager)
                return event
            if event.buttonDown(BUTTON_LEFT):
                self.status = Button.PRESSED
                self.pressed = True

                return None
            return event
        else: # PRESSED
            if not self.hit(event.x, event.y):
                self.setIdle(event, manager)
                return event
            if event.buttonUp(BUTTON_LEFT):
                self.setIdle(event, manager)
                self.action()
            return None


class BevelFrame(Container):
    THICKNESS = 6

    def __init__(self, thickness = None):
        Container.__init__(self)
        self.addChild(Bevel())
        self.addChild(Bevel())
        self.children[1].pressed = True
        self.thickness = thickness if thickness is not None else BevelFrame.THICKNESS

    def updateMinMax(self):
        if len(self.children) >= 3:
            self.minsize = addTuple(self.children[2].minsize, self.thickness*2)
            self.maxsize = addTuple(self.children[2].maxsize, self.thickness*2)
        else:
            self.minsize = (0,0)
            self.maxsize = (Component.MAXSIZE,Component.MAXSIZE)

    def setPosAndSize(self, pos, size):
        Container.setPosAndSize(self, pos, size)
        self.children[0].setPosAndSize(pos, size)
        self.children[1].setPosAndSize(addTuple(pos, self.thickness-2),
                                       addTuple(size, -(self.thickness-2)*2))
        if len(self.children) >= 3:
            self.children[2].setPosAndSize(addTuple(pos, self.thickness),
                                           addTuple(size, -self.thickness*2))


class Draggable(Bevel):
    IDLE = 0
    HOVER = 1
    DRAGGING = 2

    def __init__(self, orientation, delegate=None):
        Bevel.__init__(self)
        self.orientation = orientation
        self.status = Draggable.IDLE
        if delegate:
            self.delegate = delegate
        else:
            self.delegate = self
    
    def setIdle(self, event, manager):
        self.status = Draggable.IDLE
        self.lit = self.hit(event.x, event.y)
        self.pressed = False
        manager.removeMouseListener(self)

    def handleMouseEvent(self, event, manager):
        pos = (event.x, event.y)[self.orientation]
        if self.status == Draggable.IDLE:
            self.status = Draggable.HOVER
            self.lit = True
            manager.addMouseListener(self)
        if self.status == Draggable.HOVER:
            if not self.hit(event.x, event.y):
                self.setIdle(event, manager)
                return event
            if event.buttonDown(BUTTON_LEFT):
                self.drag_origin = pos
                self.delegate.initDragging()
                self.status = Draggable.DRAGGING
                self.pressed = True
                return None
            return event
        else: # DRAGGING
            if event.buttonDown(BUTTON_RIGHT):
                self.delegate.updateDragging(0)
                self.delegate.stopDragging()
                self.setIdle(event, manager)
                return None
            self.delegate.updateDragging(pos - self.drag_origin)
            if event.buttonUp(BUTTON_LEFT):
                self.delegate.stopDragging()
                self.setIdle(event, manager)
            return None


class Adjuster(Draggable):
    THICKNESS = 8

    def __init__(self, orientation=None):
        Draggable.__init__(self, orientation)
        self.weight = 0.000001

    def updateMinMax(self):
        if self.orientation is None:
            self.orientation = self.parent.orientation
        o = self.orientation
        self.minsize = (Adjuster.THICKNESS,Adjuster.THICKNESS)
        maxsize = list(self.minsize)
        maxsize[1-o] = Component.MAXSIZE
        self.maxsize = tuple(maxsize)

    def initDragging(self):
        o = self.orientation
        self_index = self.parent.children.index(self)
        self.pred = self.parent.children[self_index-1]
        self.succ = self.parent.children[self_index+1]
        self.old_weights = (self.pred.weight, self.succ.weight)
        self.old_sizes = (self.pred.size[o], self.succ.size[o])

    def updateDragging(self, delta):
        o = self.orientation
        pred_size = self.pred.size[o]
        succ_size = self.succ.size[o]
        pred_size = self.old_sizes[0] + delta
        succ_size = self.old_sizes[1] - delta
        clamp_adjust = 0
        if pred_size < self.pred.minsize[o]:
            clamp_adjust = self.pred.minsize[o]-pred_size
        if pred_size > self.pred.maxsize[o]:
            clamp_adjust = self.pred.maxsize[o]-pred_size
        if succ_size < self.succ.minsize[o]:
            clamp_adjust = succ_size-self.succ.minsize[o]
        if succ_size > self.succ.maxsize[o]:
            clamp_adjust = succ_size-self.succ.maxsize[o]
        pred_size += clamp_adjust
        succ_size -= clamp_adjust

        self.pred.weight = pred_size * sum(self.old_weights) / (pred_size + succ_size)
        self.succ.weight = succ_size * sum(self.old_weights) / (pred_size + succ_size)

        self.parent.setPosAndSize(self.parent.pos, self.parent.size)

    def stopDragging(self):
        pass


class ScrollbarContainer(Container):
    def __init__(self, orientation):
        Container.__init__(self)
        self.orientation = orientation

    def updateMinMax(self):
        o = self.orientation
        minsize = [0,0]
        maxsize = [Component.MAXSIZE,Component.MAXSIZE]
        minsize[o] = Scrollbar.MINLENGTH
        minsize[1-o] = Scrollbar.THICKNESS
        maxsize[1-o] = Scrollbar.THICKNESS
        self.minsize = tuple(minsize)
        self.maxsize = tuple(maxsize)

class Scrollbar(Container):
    THICKNESS = 12
    MINLENGTH = 8

    def __init__(self, orientation):
        Container.__init__(self)
        self.orientation = orientation
        self.area_total = 10000
        self.area_shown = 1000
        self.area_pos = 0

        bf = BevelFrame()
        sbc = ScrollbarContainer(orientation)
        sbd = Draggable(orientation, self)

        self.frame = bf
        self.container = sbc
        self.draggable = sbd

        sbc.addChild(sbd)
        bf.addChild(sbc)
        self.addChild(bf)

        self.weight = 0.000001

    def updateMinMax(self):
        self.minsize = self.frame.minsize
        self.maxsize = self.frame.maxsize

    def setPosAndSize(self, pos, size):
        Container.setPosAndSize(self, pos, size)
        self.frame.setPosAndSize(pos, size)

    def initDragging(self):
        self.orig_area_pos = self.area_pos

    def getAreaPos(self):
        return self.area_pos

    def setAreaPos(self, pos):
        self.area_pos = max(0, min(self.area_total-self.area_shown, pos))

    def updateDragging(self, delta):
        o = self.orientation
        area_pos = int(round(self.orig_area_pos + delta * self.area_total / float(self.container.size[o])))
        self.setAreaPos(area_pos)

    def stopDragging(self):
        pass

    def updateDraggableSizeAndPos(self):
        o = self.orientation
        size = [0,0]
        pos = list(self.container.pos)
        size[o] = self.container.size[o] * self.area_shown / self.area_total
        size[o] = max(Scrollbar.MINLENGTH, size[o])
        size[1-o] = Scrollbar.THICKNESS

        offset = int(round(self.area_pos *
                           (self.container.size[o]-size[o]) /
                           (self.area_total-self.area_shown)))
        pos[o] += offset
        self.draggable.setPosAndSize(tuple(pos), tuple(size))

    def render(self, info):
        self.updateDraggableSizeAndPos()
        Container.render(self, info)

class Scrollable(Container):
    def __init__(self, scrollbar):
        Container.__init__(self)
        self.scrollbar = scrollbar

    def setPosAndSize(self, pos, size):
        Container.setPosAndSize(self, pos, size)
        self.scrollbar.area_total = self.children[0].size[self.scrollbar.orientation]
        self.scrollbar.area_shown = size[self.scrollbar.orientation]
        
    def render(self, info):
        self.children[0].setPosAndSize((self.pos[0], self.pos[1]-self.scrollbar.area_pos), self.children[0].size)
        #self.children[0].setPosAndSize((self.pos[0], self.pos[1]), self.children[0].size)
        oldrect = info.addScissorRect(self.pos+self.size)
        Container.render(self, info)
        info.setScissorRect(oldrect)
