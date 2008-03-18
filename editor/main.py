#!/usr/bin/env python

from gui import *
from guicomps import *
from display import *
from music import *
import d3d
import d3dc
import objtree as ot
import math
import sys
import struct
import traceback
import types

import tkFileDialog
import tkSimpleDialog
import tkMessageBox
import Tkinter

filename = None
field = None
window = None

def setfilename(n):
    global filename
    filename = n
    window.setTitle(unicode(n))

def save():
    if filename is not None:
        field.save(filename)
    else:
        saveas()

def saveas():
    global filename
    chosen_name = tkFileDialog.asksaveasfilename()
    if chosen_name:
        setfilename(chosen_name)
        field.save(filename)

def load():
    global filename
    chosen_name = tkFileDialog.askopenfilename()
    if chosen_name:
        setfilename(chosen_name)
        field.load(filename)

def insert():
    chosen_name = tkFileDialog.askopenfilename()
    if chosen_name:
        field.insert(chosen_name)

def export():
    def varcompare(a,b):
        if isinstance(a,types.FloatType):
            if isinstance(b,types.FloatType):
                return cmp(a,b)
            return 1 
        if isinstance(b,types.FloatType):
            return -1
        return 0

    if field.active:
        try:
            tree = field.active.buildTree(field.children, set())
            instructions,constants,constmap = ot.export(tree)

            constvars = range(len(constmap))
            for v,i in constmap.iteritems():
                constvars[i] = v
            constvars.sort(varcompare)
            constmap = {}
            for i,v in enumerate(constvars):
                constmap[v] = i
            instructions,constants,constmap = ot.export(tree, constmap)

            print instructions
            print constants
            sys.stdout.flush()

            tree_name = tkFileDialog.asksaveasfilename(initialfile = "tree.dat")
            if not tree_name:
                return
            consts_name = tkFileDialog.asksaveasfilename(initialfile = "constantpool.dat")
            if not consts_name:
                return
            try:
                tree_file = open(tree_name, 'wb')
                tree_file.write(''.join([chr(b) for b in instructions]))
                tree_file.close()
                consts_file = open(consts_name, 'wb')
                for c in constants:
                    frep = struct.pack('f', c)
                    #frep = chr(0)*2 + frep[2:4]
                    consts_file.write(frep)
                consts_file.close()
            except IOError:
                tkMessageBox.showerror("File error", "Could not write files")

        except ot.ExportException, e:
            tkMessageBox.showerror(title = "Export error", message = e.message)

class TimeSlider(Scrollbar):
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
        display.playbutton.repeatAction()
        
class PlayButton(Button):
    active = False
    display = None
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
        playMusic(self.display.timebar.area_pos/1000.)
        
    def passivate(self):
        self.active = False
        self.text = "Play"
        self.color = 0x808080
        stopMusic()    

    def __init__(self, display):
        self.display = display
        Button.__init__(self, self.action, "Play", 0x808080)

if __name__ == "__main__":
    Tkinter.Tk().withdraw()

    initMusic()
    display = MeshDisplay()
    display.weight = 2.0
    timepane = Sequence(ORIENTATION_HORIZONTAL)
    timebar = TimeSlider(ORIENTATION_HORIZONTAL)
    timebar.area_shown = 10000
    timebar.area_total = 1000*getMusicLength()+timebar.area_shown
    timebar.area_pos = 0
    timebar.weight = 100000
    playbutton = PlayButton(display)
    timepane.addChild(playbutton)
    timepane.addChild(timebar)
    timepane.weight = 0.001
    
    display.timebar = timebar
    display.playbutton = playbutton
    scrollbarv = Scrollbar(ORIENTATION_VERTICAL)
    valuebar = ValueBar()
    valuebar.addChild(Component())
    field = BrickField(display, valuebar)
    field.setPosAndSize((0,0),(2000,2000))
    #field.addChild(Brick(ot.Rotate(ot.AXIS_X), field, (1,1)))
    #field.addChild(Brick(ot.Identity(), field, (2,1)))
    scrollfield = Scrollable(scrollbarv)
    scrollfield.addChild(field)
    scrollfield.weight = 2.0
    adjuster = Adjuster()
    buttonpane = Sequence(ORIENTATION_VERTICAL)
    buttonpane.weight = 0.001

    button_box = CreateButton("Box", (lambda : ot.Primitive(0)), field, 'B')
    button_sphere = CreateButton("Sphere", (lambda : ot.Primitive(1)), field, 'S')
    button_cylinder = CreateButton("Cylinder", (lambda : ot.Primitive(2)), field, 'C')
    button_smoothbox = CreateButton("smOothbox", (lambda : ot.Primitive(3)), field, 'O')
    button_identity = CreateButton("", ot.Identity, field, 'I')
    button_fix = CreateButton("Fix", ot.SaveTransform, field, 'F')
    button_move = CreateButton("Move", ot.Move, field, 'M')
    button_scale = CreateButton("scAle", ot.Scale, field, 'A')
    button_rotx = CreateButton("rotate X", (lambda : ot.Rotate(ot.Rotate.AXIS_X)), field, 'X')
    button_roty = CreateButton("rotate Y", (lambda : ot.Rotate(ot.Rotate.AXIS_Y)), field, 'Y')
    button_rotz = CreateButton("rotate Z", (lambda : ot.Rotate(ot.Rotate.AXIS_Z)), field, 'Z')
    button_repeat = CreateButton("Repeat", (lambda : ot.Repeat(4)), field, 'R')
    button_cond = CreateButton("conditionaL", (lambda : ot.Conditional()), field, 'L')
    button_globaldef = CreateButton("Globaldef", (lambda : ot.GlobalDefinition("v")), field, 'G')
    button_localdef = CreateButton("localDef", (lambda : ot.LocalDefinition("v")), field, 'D')

    filler = Component()
    filler.weight = 1000000

    FBCOL = 0x806060
    button_load = Button(load, "load", color = FBCOL)
    button_insert = Button(insert, "insert", color = FBCOL)
    button_save = Button(save, "save", color = FBCOL)
    button_saveas = Button(saveas, "save as", color = FBCOL)
    button_export = Button(export, "export", color = FBCOL)

    buttonpane.addChild(button_box)
    buttonpane.addChild(button_sphere)
    buttonpane.addChild(button_cylinder)
    buttonpane.addChild(button_smoothbox)
    buttonpane.addChild(button_identity)
    buttonpane.addChild(button_fix)
    buttonpane.addChild(button_move)
    buttonpane.addChild(button_scale)
    buttonpane.addChild(button_rotx)
    buttonpane.addChild(button_roty)
    buttonpane.addChild(button_rotz)
    buttonpane.addChild(button_repeat)
    buttonpane.addChild(button_cond)
    buttonpane.addChild(button_globaldef)
    buttonpane.addChild(button_localdef)
    buttonpane.addChild(filler)
    buttonpane.addChild(button_load)
    buttonpane.addChild(button_insert)
    buttonpane.addChild(button_save)
    buttonpane.addChild(button_saveas)
    buttonpane.addChild(button_export)

    hseq = Sequence(ORIENTATION_HORIZONTAL)
    vseq = Sequence(ORIENTATION_VERTICAL)
    hseq.addChild(buttonpane)
    hseq.addChild(scrollfield)
    hseq.addChild(scrollbarv)
    edit_seq = Sequence(ORIENTATION_VERTICAL)
    edit_seq.addChild(timepane)
    edit_seq.addChild(hseq)
    vseq.addChild(display)
    vseq.addChild(adjuster)
    vseq.addChild(edit_seq)
    vseq.addChild(valuebar)

    root = EditorRoot(display)
    root.addChild(vseq)

    window = Window(u"ObjectEditTool", root)
    quit = 100
    while quit > 0:
        try:
            window.mainloop()
            quit = 0
        except Exception, e:
            traceback.print_exc()
            sys.stderr.flush()
            tkMessageBox.showerror("Internal error", e.message)

            field.selected = set()
            field.setActive(None)
            field.setRoot(None)

            quit -= 1
