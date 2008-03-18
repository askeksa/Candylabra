#!/usr/bin/env python

import sys
import d3d
import time
from d3dc import WM,CREATE,RS

ORIENTATION_HORIZONTAL = 0
ORIENTATION_VERTICAL = 1

KEY_DOWN = 0
KEY_UP = 1

BUTTON_NONE = 0
BUTTON_LEFT = 1
BUTTON_RIGHT = 2
BUTTON_MIDDLE = 3
BUTTON_WHEELUP = 4
BUTTON_WHEELDOWN = 5

BUTTON_DOWN = 0
BUTTON_UP = 1

WINDOW_SIZEMOVE = 0
WINDOW_FOCUSGAINED = 1
WINDOW_FOCUSLOST = 2
WINDOW_MINIMIZED = 3
WINDOW_UNMINIMIZED = 4
WINDOW_QUIT = 5


class KeyEvent(object):
    def __init__(self, direction, code, char):
        self.direction = direction
        self.code = code
        self.char = char


class MouseEvent(object):
    def __init__(self, button, direction, double, x, y):
        self.button = button
        self.direction = direction
        self.double = double
        self.x = x
        self.y = y

    def buttonDown(self, button):
        return self.button == button and self.direction == BUTTON_DOWN

    def buttonUp(self, button):
        return self.button == button and self.direction == BUTTON_UP


class WindowEvent(object):
    def __init__(self, kind):
        self.kind = kind


class InputManager(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.keylisteners = []
        self.mouselisteners = []
        self.windowlisteners = []
        
    def addKeyListener(self, listener):
        self.keylisteners.insert(0, listener)

    def addMouseListener(self, listener):
        self.mouselisteners.insert(0, listener)

    def addWindowListener(self, listener):
        self.windowlisteners.insert(0, listener)

    def removeKeyListener(self, listener):
        if listener in self.keylisteners:
            self.keylisteners.remove(listener)

    def removeMouseListener(self, listener):
        if listener in self.mouselisteners:
            self.mouselisteners.remove(listener)

    def removeWindowListener(self, listener):
        if listener in self.windowlisteners:
            self.windowlisteners.remove(listener)

    def peekMsgKind(self, d3d_events, kind):
        return d3d_events and d3d_events[0][0] == kind

    def manageInputEvents(self, d3d_events):
        while d3d_events:
            e = d3d_events.pop(0)

            # Key events
            if e[0] in (WM.KEYDOWN, WM.KEYUP):
                if e[0] == WM.KEYDOWN:
                    direction = KEY_DOWN
                else:
                    direction = KEY_UP
                code = e[1]
                if self.peekMsgKind(d3d_events, WM.KEY):
                    d3d_events.pop(0)
                if self.peekMsgKind(d3d_events, WM.CHAR):
                    charmsg = d3d_events.pop(0)
                    char = charmsg[1]
                else:
                    char = None

                event = KeyEvent(direction, code, char)

                for l in self.keylisteners:
                    event = l.handleKeyEvent(event, self)
                    if event is None:
                        break

            # Mouse events
            elif e[0] in (WM.MOUSEWHEEL, WM.MOUSEMOVE,
                          WM.MOUSELDOWN, WM.MOUSELUP, WM.MOUSELDOUBLE,
                          WM.MOUSEMDOWN, WM.MOUSEMUP, WM.MOUSEMDOUBLE,
                          WM.MOUSERDOWN, WM.MOUSERUP, WM.MOUSERDOUBLE):
                if e[0] == WM.MOUSEMOVE:
                    button = BUTTON_NONE
                    direction = BUTTON_UP
                    double = False
                elif e[0] == WM.MOUSEWHEEL:
                    if e[3] == 1:
                        button = BUTTON_WHEELUP
                    else:
                        button = BUTTON_WHEELDOWN
                    direction = BUTTON_DOWN
                    double = False
                else:
                    if e[0] in (WM.MOUSELDOWN, WM.MOUSELUP, WM.MOUSELDOUBLE):
                        button = BUTTON_LEFT
                    elif e[0] in (WM.MOUSERDOWN, WM.MOUSERUP, WM.MOUSERDOUBLE):
                        button = BUTTON_RIGHT
                    elif e[0] in (WM.MOUSEMDOWN, WM.MOUSEMUP, WM.MOUSEMDOUBLE):
                        button = BUTTON_MIDDLE
                    if e[0] in (WM.MOUSELUP, WM.MOUSERUP, WM.MOUSEMUP):
                        direction = BUTTON_UP
                    else:
                        direction = BUTTON_DOWN
                    double = e[0] in (WM.MOUSELDOUBLE, WM.MOUSERDOUBLE, WM.MOUSEMDOUBLE)

                event = MouseEvent(button, direction, double, e[1], e[2])

                for l in self.mouselisteners:
                    event = l.handleMouseEvent(event, self)
                    if event is None:
                        break

            # Window events
            elif e[0] in (WM.SIZEMOVE, WM.FOCUS, WM.MINMAX, WM.QUIT):
                if e[0] == WM.SIZEMOVE:
                    kind = WINDOW_SIZEMOVE
                elif e[0] == WM.FOCUS:
                    if e[1]:
                        kind = WINDOW_FOCUSGAINED
                    else:
                        kind = WINDOW_FOCUSLOST
                elif e[0] == WM.MINMAX:
                    if e[1]:
                        kind = WINDOW_MINIMIZED
                    else:
                        kind = WINDOW_UNMINIMIZED
                else:
                    kind = WINDOW_QUIT

                event = WindowEvent(kind)
                
                for l in self.windowlisteners:
                    event = l.handleWindowEvent(event, self)
                    if event is None:
                        break

            # Other events
            else:
                pass


def intersectRect(r1, r2):
    x1 = max(r1[0], r2[0])
    y1 = max(r1[1], r2[1])
    x2 = min(r1[0]+r1[2], r2[0]+r2[2])
    y2 = min(r1[1]+r1[3], r2[1]+r2[3])
    if x2 <= x1 or y2 <= y1:
        return (0,0,0,0)
    return (x1,y1,x2-x1,y2-y1)


class RenderInfo(object):
    def __init__(self):
        self.scissor = None

    def addScissorRect(self, rect):
        oldrect = self.scissor
        if self.scissor:
            newrect = intersectRect(rect, self.scissor)
        else:
            newrect = rect
        self.setScissorRect(newrect)
        return oldrect

    def setScissorRect(self, rect):
        self.scissor = rect
        if rect:
            d3d.setScissorRect(*rect)
            d3d.setState(RS.SCISSORTESTENABLE, True)
        else:
            d3d.setState(RS.SCISSORTESTENABLE, False)


class Component(object):
    MAXSIZE = 1000000
    
    def __init__(self):
        self.pos = (0,0)
        self.size = (0,0)
        self.parent = None
        self.minsize = (1,1)
        self.maxsize = (Component.MAXSIZE,Component.MAXSIZE)
        self.weight = 1.0
        self.hotkeys = {}

    # From already calculated children sizes
    def updateMinMax(self):
        pass

    # Recursively down
    def calculateMinMax(self):
        self.updateMinMax()

    def render(self, info):
        pass

    def prerender(self, info):
        pass

    def remove(self):
        if self.parent:
            self.parent.removeChild(self)

    def setPosAndSize(self, pos, size):
        self.pos = pos
        self.size = size

    def attachManager(self, manager):
        if self.hotkeys:
            manager.addKeyListener(self)

    def handleKeyEvent(self, event, manager):
        if event.direction == KEY_DOWN and event.code in self.hotkeys:
            self.hotkeys[event.code](event, manager)
            return None
        else:
            return event

    def handleMouseEvent(self, event, manager):
        return event

    def addHotkey(self, code, function):
        self.hotkeys[code] = function

    def hit(self, x, y):
        return (x >= self.pos[0] and x < self.pos[0]+self.size[0] and
                y >= self.pos[1] and y < self.pos[1]+self.size[1])

    def hitRect(self, rect):
        selfrect = self.pos + self.size
        inter = intersectRect(selfrect, rect)
        return inter != (0,0,0,0)

    def rootsize(self):
        return self.getRoot().size

    def getRoot(self):
        return self.parent.getRoot()


class Container(Component):
    def __init__(self):
        Component.__init__(self)
        self.children = []

    def render(self, info):
        for c in self.children:
            c.render(info)

    def prerender(self, info):
        for c in self.children:
            c.prerender(info)

    def calculateMinMax(self):
        for c in self.children:
            c.calculateMinMax()
        self.updateMinMax()

    def addChildAt(self, child, pos, update=True):
        if child.parent:
            if child.parent == self and pos > self.children.index(child):
                pos -= 1
            child.parent.removeChild(child, update=(child.parent != self))
        self.children[pos:pos] = [child]
        child.parent = self
        if update:
            self._update()

    def addChild(self, child, update=True):
        self.addChildAt(child, len(self.children), update)

    def addChildAfter(self, new_child, old_child, update=True):
        if old_child in self.children:
            pos = self.children.index(old_child)+1
        else:
            pos = len(self.children)
        self.addChildAt(new_child, pos, update)

    def addChildBefore(self, new_child, old_child, update=True):
        if old_child in self.children:
            pos = self.children.index(old_child)
        else:
            pos = 0
        self.addChildAt(new_child, pos, update)

    def removeChild(self, child, update=True):
        if child in self.children:
            self.children.remove(child)
            child.parent = None
        if update:
            self._update()

    def _update(self):
        self.updateMinMax()
        if self.parent:
            self.parent._update()

    def attachManager(self, manager):
        for c in self.children:
            c.attachManager(manager)
        Component.attachManager(self, manager)

    def handleMouseEvent(self, event, manager):
        for c in self.children:
            if c.hit(event.x, event.y):
                event = c.handleMouseEvent(event, manager)
                if event is None:
                    return None
        return event


class Sequence(Container):
    def __init__(self, orientation, spacing=0):
        Container.__init__(self)
        self.orientation = orientation
        self.spacing = spacing
        
    def updateMinMax(self):
        o = self.orientation
        totspace = (len(self.children)-1) * self.spacing
        totmin = [0,0]
        totmax = [Component.MAXSIZE,Component.MAXSIZE]
        totmin[o] = totspace
        totmax[o] = totspace
        for c in self.children:
            totmin[o] = totmin[o] + c.minsize[o]
            totmax[o] = totmax[o] + c.maxsize[o]
            totmin[1-o] = max(totmin[1-o], c.minsize[1-o])
            totmax[1-o] = min(totmax[1-o], c.maxsize[1-o])
        totmax[1-o] = max(totmin[1-o],totmax[1-o])
        self.minsize = tuple(totmin)
        self.maxsize = tuple(totmax)

    def calculateFactor(self, size):
        o = self.orientation
        n = len(self.children)
        minfactor = [c.minsize[o]/c.weight for c in self.children]
        maxfactor = [c.maxsize[o]/c.weight for c in self.children]
        minmax = sorted(zip(minfactor, range(n)) + zip (maxfactor, range(n)))
        minsize = self.minsize[o]
        rubber = 0.0
        for factor, index in minmax:
            if minsize + rubber * factor >= size:
                break
            c = self.children[index]
            if factor == minfactor[index]:
                # Unlock min bound
                rubber += c.weight
                minsize -= c.minsize[o]
            else:
                # Lock max bound
                rubber -= c.weight
                minsize += c.maxsize[o]
        else:
            return minmax[-1][0]
        if rubber == 0:
            return 0.0
        return (size - minsize)/rubber

    def setPosAndSize(self, pos, size):
        self.pos = pos
        self.size = size

        if len(self.children) == 0: return

        o = self.orientation
        children_size = size[o]
        factor = self.calculateFactor(children_size)
        positions = []
        pos = 0
        fpos = 0.0
        for c in self.children:
            positions.append(pos)
            fsize = c.weight * factor
            fsize = max(c.minsize[o], min(c.maxsize[o], fsize))
            fpos += fsize + self.spacing
            pos = int(round(fpos))
        positions.append(pos)

        for i,c in enumerate(self.children):
            cpos = list(self.pos)
            cpos[o] += positions[i]
            csize = list(c.maxsize)
            csize[o] = positions[i+1] - positions[i] - self.spacing
            csize[1-o] = min(csize[1-o], size[1-o])
            c.setPosAndSize(tuple(cpos), tuple(csize))


# Root of GUI tree, attached to window
# Should have just one child
class Root(Container):
    def __init__(self):
        Container.__init__(self)
        self.window = None

    def setPosAndSize(self, pos, size):
        self.pos = pos
        self.size = size

        if self.children:
            self.children[0].setPosAndSize(pos, size)

    def updateMinMax(self):
        if self.children:
            self.minsize = self.children[0].minsize
            self.maxsize = self.children[0].maxsize
        else:
            self.minsize = (0,0)
            self.maxsize = (Component.MAXSIZE,Component.MAXSIZE)

    def _update(self):
        Container._update(self)
        self.setPosAndSize(self.pos, self.size)
        if self.window:
            self.window.resetManager()

    def handleWindowEvent(self, event, manager):
        if event.kind == WINDOW_SIZEMOVE:
            dims,(w,h),desktop,style,handle = d3d.getWindow()
            self.setPosAndSize(self.pos, (w,h))
        return event

    def getRoot(self):
        return self


class Window(object):
    def __init__(self, title, root, size = (400,300)):
        self.title = title
        self.root = root
        self.quit = False
        self.manager = InputManager()
        self.error = None

        root.window = self
        root.calculateMinMax()
        size = tuple(max(root.minsize[i], min(root.maxsize[i], size[i])) for i in range(2))
        root.setPosAndSize((0,0), size)

        self.resetManager()

        d3d.createDevice(title, u"", size[0], size[1], False, CREATE.HARDWARE)

    def resetManager(self):
        self.manager.reset()
        self.root.attachManager(self.manager)
        self.manager.addMouseListener(self.root)
        self.manager.addWindowListener(self.root)
        self.manager.addWindowListener(self)

    def mainloop(self):
        last_time = time.clock()
        while True:
            events = d3d.getMessages()
            self.manager.manageInputEvents(events)
            if self.quit:
                break

            info = RenderInfo()
            info.setScissorRect(None)
            self.root.prerender(info)
            d3d.clear()
            d3d.beginScene()
            info.setScissorRect((0,0) + self.root.size)
            try:
                self.root.render(info)
            finally:
                d3d.endScene()
                d3d.present()

            now = time.clock()
            fps = 1.0 / (now - last_time)
            last_time = now
            self.updateTitle(fps)

    def handleWindowEvent(self, event, manager):
        if event.kind == WINDOW_QUIT:
            self.quit = True
        return event

    def setTitle(self, title):
        self.title = title

    def setError(self, error):
        self.error = error

    def updateTitle(self, fps):
        (x,y,w,h),c,d,s,wnd = d3d.getWindow()
        if self.error:
            titlestring = "Error: " + self.error
        else:
            titlestring = "%s - %.1f fps" % (self.title, fps)
        d3d.setWindow(x,y,w,h, unicode(titlestring))
