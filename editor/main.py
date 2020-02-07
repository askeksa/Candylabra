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
import time

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

def export(exportfun, swap_endian = False, truncate = False):
    if field.active:
        try:
            tree = field.active.buildTree(set())
            exporter = ot.Exporter(tree)
            instructions,constants,constmap = exportfun(exporter)
            if isinstance(instructions, types.TupleType):
                nodes, exps = instructions
                instructions = None
                #print nodes
            #print instructions
            #print constants
            node_to_brick = {}
            for b in field.children:
                node_to_brick[b.node] = b

            conststring = {}
            for c,cnodes in exporter.constnodes.iteritems():
                if isinstance(c,types.FloatType):
                    intrep = struct.unpack('I', struct.pack('f', c))[0]
                    if truncate:
                        fhex = "%08X -> %08X" % (intrep, intrep & 0xffff0000)
                    else:
                        fhex = "%08X" % (intrep)
                    conststring[c] = ("%f (%s): " % (c, fhex)) + str([n.getName() + (" (%d,%d)" % node_to_brick[n].gridpos) for n in cnodes])

            print
            print
            print constmap
            print
            for c in sorted(conststring.keys(), (lambda a,b : cmp(abs(a), abs(b)))):
                print conststring[c]
            sys.stdout.flush()

            consts_name = tkFileDialog.asksaveasfilename(initialfile = "constantpool.dat")
            if not consts_name:
                return
            if instructions:
                tree_name = consts_name.replace("constantpool.dat", "tree.dat")
            else:
                nodes_name = consts_name.replace("constantpool.dat", "nodes.dat")
                exps_name = consts_name.replace("constantpool.dat", "exps.dat")
            try:
                def writebytes(filename, data):
                    f = open(filename, 'wb')
                    f.write(''.join([chr(b) for b in data]))
                    f.close()
                if instructions:
                    writebytes(tree_name, instructions)
                else:
                    writebytes(nodes_name, nodes)
                    writebytes(exps_name, exps)
                consts_file = open(consts_name, 'wb')
                #last_exp = 0
                for c in constants:
                    frep = struct.pack('f', c)
                    #this_exp = ord(frep[3])
                    #frep = frep[0:3] + chr(this_exp-last_exp)
                    #last_exp = this_exp
                    if truncate:
                        frep = chr(0)+chr(0)+frep[2:4]
                    if swap_endian:
                        frep = frep[3]+frep[2]+frep[1]+frep[0]
                    consts_file.write(frep)
                consts_file.close()
            except IOError:
                tkMessageBox.showerror("File error", "Could not write files")

        except Exception, e:
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

def set_project_file(field_name):
    filename = field.project.__dict__[field_name]
    chosen_name = tkFileDialog.askopenfilename(initialfile = filename)
    if chosen_name:
        field.project.__dict__[field_name] = make_filename_relative(chosen_name)
        field.display.setProject(field.project)

def set_effect():
    set_project_file("effect_file")

def set_music():
    set_project_file("music_file")

def set_sync():
    set_project_file("sync_file")

def set_data():
    set_project_file("data_file")

def set_bpm():
    bpm = tkSimpleDialog.askfloat("Enter value",
                                  "Beats per minute",
                                  initialvalue=field.project.bpm)
    if bpm is not None:
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
    scrollbarh = Scrollbar(ORIENTATION_HORIZONTAL)
    valuebar = ValueBar()
    valuebar.addChild(Component())
    field = BrickField(display, valuebar, scrollbarv)
    field.setPosAndSize((0,0),(2000,3000))
    #field.addChild(Brick(ot.Rotate(ot.AXIS_X), field, (1,1)))
    #field.addChild(Brick(ot.Identity(), field, (2,1)))
    scrollfield = Scrollable([scrollbarh,scrollbarv])
    scrollfield.addChild(field)
    scrollfield.weight = 2.0
    adjuster = Adjuster()

    scrollfield.addHotkey(d3dc.VK.NEXT, (lambda e,m : scrollbarh.jump(1) if e.keyHeld(d3dc.VK.SHIFT)
        else scrollbarv.jump(1)))
    scrollfield.addHotkey(d3dc.VK.PRIOR, (lambda e,m : scrollbarh.jump(-1) if e.keyHeld(d3dc.VK.SHIFT)
        else scrollbarv.jump(-1)))
    scrollfield.addHotkey(d3dc.VK.END, (lambda e,m : scrollbarh.jump(99) if e.keyHeld(d3dc.VK.SHIFT)
        else scrollbarv.setAreaPos(field.bottomBrickPos()+20-scrollfield.size[1])))
    scrollfield.addHotkey(d3dc.VK.HOME, (lambda e,m : scrollbarh.jump(-99) if e.keyHeld(d3dc.VK.SHIFT)
        else scrollbarv.jump(-99)))

    filler = Component()
    filler.weight = 1000000

    buttonpanes = Sequence(ORIENTATION_HORIZONTAL)
    buttonpane1 = Sequence(ORIENTATION_VERTICAL)
    buttonpane2 = Sequence(ORIENTATION_VERTICAL)
    filepane = Sequence(ORIENTATION_VERTICAL)
    parampane = Sequence(ORIENTATION_VERTICAL)
    enginepane = Sequence(ORIENTATION_VERTICAL)
    buttonpanes.addChild(filler)
    buttonpanes.addChild(buttonpane1)
    buttonpanes.addChild(buttonpane2)
    buttonpanes.addChild(filepane)
    buttonpanes.addChild(parampane)
    buttonpanes.addChild(enginepane)

    button_item = CreateButton("Object", (lambda : ot.Item(0)), field, 'O')
    button_dynitem = CreateButton("Dyn object", (lambda : ot.DynamicItem()), field, 'D')
    #for o in range(0,10):
    #    button_item.addHotkey(ord('0')+o, (lambda e,m : field.setCreating(lambda : ot.DynamicItem(o))))
    button_light = CreateButton("ligHt", (lambda : ot.Light(0)), field, 'H')
    button_camera = CreateButton("camEra", (lambda : ot.Camera()), field, 'E')
    button_identity = CreateButton("lAbel", (lambda : ot.Identity(field)), field, 'A')
    button_link = CreateButton("linK", (lambda : ot.Link(field)), field, 'K')
    button_fix = CreateButton("Fix", ot.SaveTransform, field, 'F')
    button_move = CreateButton("Move", ot.Move, field, 'M')
    button_scale = CreateButton("Scale", ot.Scale, field, 'S')
    button_rotx = CreateButton("rotate X", (lambda : ot.Rotate(ot.Rotate.AXIS_X)), field, 'X')
    button_roty = CreateButton("rotate Y", (lambda : ot.Rotate(ot.Rotate.AXIS_Y)), field, 'Y')
    button_rotz = CreateButton("rotate Z", (lambda : ot.Rotate(ot.Rotate.AXIS_Z)), field, 'Z')
    #button_gmove = CreateButton("G move", (lambda : ot.Move(isglobal=True)), field)
    #button_gscale = CreateButton("G scale", (lambda : ot.Scale(isglobal=True)), field)
    #button_grotx = CreateButton("G rotate x", (lambda : ot.Rotate(ot.Rotate.AXIS_X, isglobal=True)), field)
    #button_groty = CreateButton("G rotate y", (lambda : ot.Rotate(ot.Rotate.AXIS_Y, isglobal=True)), field)
    #button_grotz = CreateButton("G rotate z", (lambda : ot.Rotate(ot.Rotate.AXIS_Z, isglobal=True)), field)
    button_repeat = CreateButton("Repeat", (lambda : ot.Repeat(4)), field, 'R')
    button_loop = CreateButton("looP", (lambda : ot.Loop(4)), field, 'P')
    button_cond = CreateButton("Conditional", (lambda : ot.Conditional()), field, 'C')
    button_if = CreateButton("If", (lambda : ot.If()), field, 'I')
    button_globaldef = CreateButton("Globaldef", (lambda : ot.GlobalDefinition("v")), field, 'G')
    button_localdef = CreateButton("Localdef", (lambda : ot.LocalDefinition("v")), field, 'L')

    buttonpane1.addChild(button_item)
    buttonpane1.addChild(button_dynitem)
    buttonpane1.addChild(button_light)
    buttonpane1.addChild(button_camera)
    buttonpane1.addChild(button_fix)
    buttonpane1.addChild(button_move)
    buttonpane1.addChild(button_scale)
    buttonpane1.addChild(button_rotx)
    buttonpane1.addChild(button_roty)
    buttonpane1.addChild(button_rotz)
    #buttonpane.addChild(button_gmove)
    #buttonpane.addChild(button_gscale)
    #buttonpane.addChild(button_grotx)
    #buttonpane.addChild(button_groty)
    #buttonpane.addChild(button_grotz)
    buttonpane2.addChild(button_identity)
    buttonpane2.addChild(button_link)
    buttonpane2.addChild(button_repeat)
    buttonpane2.addChild(button_loop)
    buttonpane2.addChild(button_cond)
    buttonpane2.addChild(button_if)
    buttonpane2.addChild(button_globaldef)
    buttonpane2.addChild(button_localdef)

    ENGCOL = 0x609090
    enginepane.weight = 0.001
    for id, name in enumerate(get_engines()):
        engine_button = Button((lambda eid : (lambda : set_engine(eid)))(id), name, color = ENGCOL)
        enginepane.addChild(engine_button)

    FBCOL = 0x806060
    button_load = Button(load, "load", color = FBCOL)
    button_insert = Button(insert, "insert", color = FBCOL)
    button_save = Button(save, "save", color = FBCOL)
    button_saveas = Button(saveas, "save as", color = FBCOL)
    button_export = Button((lambda : export(lambda exporter : exporter.optimized_export())), "export", color = FBCOL)
    button_export_compiler = Button((lambda : export(lambda exporter : exporter.export_for_compiler())), "export comp", color = FBCOL)
    button_export_amiga = Button((lambda : export(lambda exporter : exporter.export_amiga(), swap_endian = True)), "export amiga", color = FBCOL)

    PARCOL = 0x807070
    button_effect = Button(set_effect, "effect", color = PARCOL)
    button_music = Button(set_music, "music", color = PARCOL)
    button_bpm = Button(set_bpm, "BPM", color = PARCOL)
    button_sync = Button(set_sync, "sync", color = PARCOL)
    button_data = Button(set_data, "data", color = PARCOL)

    filepane.addChild(button_load)
    filepane.addChild(button_insert)
    filepane.addChild(button_save)
    filepane.addChild(button_saveas)
    filepane.addChild(button_export)
    filepane.addChild(button_export_compiler)
    filepane.addChild(button_export_amiga)

    parampane.addChild(button_effect)
    parampane.addChild(button_music)
    parampane.addChild(button_bpm)
    parampane.addChild(button_sync)
    parampane.addChild(button_data)

    hscroll = Sequence(ORIENTATION_VERTICAL)
    hscroll.addChild(scrollfield)
    hscroll.addChild(scrollbarh)
    vscroll = Sequence(ORIENTATION_HORIZONTAL)
    vscroll.addChild(hscroll)
    vscroll.addChild(scrollbarv)

    display_and_buttons = Sequence(ORIENTATION_VERTICAL)
    display_and_buttons.weight = 0.01

    def layout_with_editor():
        filler = Component()
        filler.weight = 0.01
        buttonpanes.weight = 0.01

        display_and_buttons.addChild(display)
        display_and_buttons.addChild(filler)
        display_and_buttons.addChild(buttonpanes)

        hseq = Sequence(ORIENTATION_HORIZONTAL)
        hseq.addChild(vscroll)
        hseq.addChild(adjuster)
        hseq.addChild(display_and_buttons)

        vseq = Sequence(ORIENTATION_VERTICAL)
        vseq.addChild(hseq)
        vseq.addChild(valuebar)
        vseq.addChild(timepane)

        return vseq

    def layout_fullscreen_effect():
        display_and_buttons.clearChildren(update=False)

        vseq = Sequence(ORIENTATION_VERTICAL)
        vseq.addChild(display)
        vseq.addChild(valuebar)
        vseq.addChild(timepane)

        return vseq

    root = EditorRoot([layout_with_editor, layout_fullscreen_effect])

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

    field.save(time.strftime("../autosave/autosave_%Y-%m-%d_%H.%M.%S.ob"))
