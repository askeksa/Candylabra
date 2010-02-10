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
import os

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
        tkMessageBox.showinfo("Saved (no error)", "File saved: "+filename)        
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
    if field.active:
        try:
            tree = field.active.buildTree(set())
            exporter = ot.Exporter(tree)
            instructions,constants,constmap = exporter.optimized_export()
            #print instructions
            #print constants
            node_to_brick = {}
            for b in field.children:
                node_to_brick[b.node] = b

            conststring = {}
            for c,nodes in exporter.constnodes.iteritems():
                if isinstance(c,types.FloatType):
                    intrep = struct.unpack('I', struct.pack('f', c))[0]
                    conststring[c] = ("%f (%08X): " % (c, intrep)) + str([n.getName() + (" (%d,%d)" % node_to_brick[n].gridpos) for n in nodes])

            print
            print
            print
            for c in sorted(conststring.keys(), (lambda a,b : cmp(abs(a), abs(b)))):
                print conststring[c]
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
                #last_exp = 0
                for c in constants:
                    frep = struct.pack('f', c)
                    #this_exp = ord(frep[3])
                    #frep = frep[0:3] + chr(this_exp-last_exp)
                    #last_exp = this_exp
                    consts_file.write(frep)
                consts_file.close()
            except IOError:
                tkMessageBox.showerror("File error", "Could not write files")

        except ot.ExportException, e:
            traceback.print_exc()
            sys.stderr.flush()
            tkMessageBox.showerror(title = "Export error", message = e.message)


def get_engines():
    buf = create_string_buffer(1000)
    n_eng = windll.RenderDLL.getengines(buf)
    return buf.raw.split("|", n_eng)[0:n_eng]

def set_engine(engine_id):
    field.project.engine_id = engine_id
    field.display.setProject(field.project)

def make_filename_relative(filename):
    filename = os.path.abspath(filename)
    cwd = os.path.abspath(os.getcwd())
    tooldir = os.path.dirname(cwd)
    for basedir,prefix in [(tooldir,".."), (os.path.dirname(tooldir),".."+os.sep+"..")]:
        if os.path.normcase(filename).startswith(os.path.normcase(basedir)):
            return prefix + filename[len(basedir):]
    return filename

def set_effect():
    chosen_name = tkFileDialog.askopenfilename(initialfile = field.project.effect_file)
    if chosen_name:
        field.project.effect_file = make_filename_relative(chosen_name)
        field.display.setProject(field.project)

def set_music():
    chosen_name = tkFileDialog.askopenfilename(initialfile = field.project.music_file)
    if chosen_name:
        field.project.music_file = make_filename_relative(chosen_name)
        field.display.setProject(field.project)

def set_bpm():
    bpm = tkSimpleDialog.askfloat("Enter value",
                                  "Beats per minute",
                                  initialvalue=field.project.bpm)
    field.project.bpm = bpm
    field.display.setProject(field.project)


if __name__ == "__main__":
    Tkinter.Tk().withdraw()

    display = MeshDisplay()
    display.weight = 2.0
    timepane = Sequence(ORIENTATION_HORIZONTAL)
    timebar = TimeSlider(ORIENTATION_HORIZONTAL, display)
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
    field = BrickField(display, valuebar, scrollbarv)
    field.setPosAndSize((0,0),(2000,3000))
    #field.addChild(Brick(ot.Rotate(ot.AXIS_X), field, (1,1)))
    #field.addChild(Brick(ot.Identity(), field, (2,1)))
    scrollfield = Scrollable(scrollbarv)
    scrollfield.addChild(field)
    scrollfield.weight = 2.0
    adjuster = Adjuster()

    buttonpane = Sequence(ORIENTATION_VERTICAL)
    buttonpane.weight = 0.001

    button_item = CreateButton("object", (lambda : ot.Item(0)), field)
    button_dynitem = CreateButton("dyn object", (lambda : ot.DynamicItem(0)), field)
    #for o in range(0,10):
    #    button_item.addHotkey(ord('0')+o, (lambda e,m : field.setCreating(lambda : ot.DynamicItem(o))))
    button_light = CreateButton("light", (lambda : ot.Light(0)), field)
    button_camera = CreateButton("camera", (lambda : ot.Camera()), field)
    button_identity = CreateButton("lAbel", (lambda : ot.Identity(field)), field, 'A')
    button_link = CreateButton("linK", (lambda : ot.Link(field)), field, 'K')
    button_fix = CreateButton("Fix", ot.SaveTransform, field, 'F')
    button_move = CreateButton("Move", ot.Move, field, 'M')
    button_scale = CreateButton("Scale", ot.Scale, field, 'S')
    button_rotx = CreateButton("rotate X", (lambda : ot.Rotate(ot.Rotate.AXIS_X)), field, 'X')
    button_roty = CreateButton("rotate Y", (lambda : ot.Rotate(ot.Rotate.AXIS_Y)), field, 'Y')
    button_rotz = CreateButton("rotate Z", (lambda : ot.Rotate(ot.Rotate.AXIS_Z)), field, 'Z')
    button_repeat = CreateButton("Repeat", (lambda : ot.Repeat(4)), field, 'R')
    button_cond = CreateButton("Conditional", (lambda : ot.Conditional()), field, 'C')
    button_globaldef = CreateButton("Globaldef", (lambda : ot.GlobalDefinition("v")), field, 'G')
    button_localdef = CreateButton("Localdef", (lambda : ot.LocalDefinition("v")), field, 'L')

    filler = Component()
    filler.weight = 1000000

    buttonpane.addChild(button_item)
    buttonpane.addChild(button_dynitem)
    buttonpane.addChild(button_light)
    buttonpane.addChild(button_camera)
    buttonpane.addChild(button_identity)
    buttonpane.addChild(button_link)
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

    bottombuttons = Sequence(ORIENTATION_HORIZONTAL)
    bottombuttons.weight = 0.001

    FBCOL = 0x806060
    button_load = Button(load, "load", color = FBCOL)
    button_insert = Button(insert, "insert", color = FBCOL)
    button_save = Button(save, "save", color = FBCOL)
    button_saveas = Button(saveas, "save as", color = FBCOL)
    button_export = Button(export, "export", color = FBCOL)

    filler = Component()
    filler.weight = 1000000

    ENGCOL = 0x609090
    engine_buttons = [Button((lambda : set_engine(id)), name, color = ENGCOL) for (id, name) in enumerate(get_engines())]
    PARCOL = 0x807070
    button_effect = Button(set_effect, "effect", color = PARCOL)
    button_music = Button(set_music, "music", color = PARCOL)
    button_bpm = Button(set_bpm, "BPM", color = PARCOL)

    bottombuttons.addChild(button_load)
    bottombuttons.addChild(button_insert)
    bottombuttons.addChild(button_save)
    bottombuttons.addChild(button_saveas)
    bottombuttons.addChild(button_export)
    bottombuttons.addChild(filler)
    for b in engine_buttons:
        bottombuttons.addChild(b)
    bottombuttons.addChild(button_effect)
    bottombuttons.addChild(button_music)
    bottombuttons.addChild(button_bpm)


    #buttonscroll = Scrollbar(ORIENTATION_VERTICAL)
    #buttonfield = Scrollable(buttonscroll)
    #buttonfield.addChild(buttonpane)

    hseq = Sequence(ORIENTATION_HORIZONTAL)
    vseq = Sequence(ORIENTATION_VERTICAL)
    hseq.addChild(buttonpane)
    hseq.addChild(scrollfield)
    hseq.addChild(scrollbarv)
    edit_seq = Sequence(ORIENTATION_VERTICAL)
    #edit_seq.addChild(timepane)
    edit_seq.addChild(hseq)

    disp_seq = Sequence(ORIENTATION_VERTICAL)
    disp_seq.addChild(display)
    disp_seq.addChild(timepane)
    
    vseq.addChild(disp_seq)
    vseq.addChild(adjuster)
    vseq.addChild(edit_seq)
    vseq.addChild(valuebar)
    vseq.addChild(bottombuttons)

    root = EditorRoot(disp_seq)
    root.addChild(vseq)

    window = Window(u"ObjectEditTool", root)
    window.maximize()

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        setfilename(filename)
        field.load(filename)

    quit = 10
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
