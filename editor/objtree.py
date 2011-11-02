#!/usr/bin/env python

#primitive kind
#transform
# rotate axis,angle
# scale x,y,z
# move x,y,z
#identity
#repeat n

import array
import d3d
import string
import math
import parser
import re
import types
import struct
import copy
from ctypes import create_string_buffer,windll

code = 0
def next():
    global code
    code = code+1
    return code

OP_FANOUT         = next()
OP_SAVETRANS      = next()
OP_REPEAT         = next()
OP_PRIM           = next()
OP_DYNPRIM        = next()
OP_LIGHT          = next()
OP_CAMERA         = next()
OP_ASSIGN         = next()
OP_LOCALASSIGN    = next()
OP_CONDITIONAL    = next()
OP_NOPLEAF        = next()
OP_ROTATE         = next()
OP_ROTATELOCAL    = next()
OP_SCALE          = next()
OP_SCALELOCAL     = next()
OP_TRANSLATE      = next()
OP_TRANSLATELOCAL = next()
OP_LABEL = 0xff
OP_END = 0xfe


predefined_variables = []

def update_predefined_variables():
    global predefined_variables
    buf = create_string_buffer(1000)
    nparams = windll.RenderDLL.getparams(buf)
    predefined_variables = buf.raw.split("/", nparams)[0:nparams]

def float32(f):
    return struct.unpack('f', struct.pack('f', f))[0]

def float2string(f):
    nd = 0
    s = "0"
    f = float32(f)
    while float32(float(s)) != f:
        s = ("%."+str(nd)+"f") % f
        nd += 1
    return s

def makeMatrix(*data):
    return array.array("f", data)


class DefValue(object):
    def __init__(self, exp):
        self.setExp(exp)

    def setExp(self, exp):
        if isinstance(exp, types.FloatType):
            self.exp = float2string(exp)
        else:
            self.exp = str(exp)

    def export(self, node, exporter):
        try:
            exporter.node = node
            exporter.exportexp(self.exp)
        except Exception, e:
            raise ExportException(node, e.message)


class ObjectNode(object):
    def __init__(self):
        self.children = [] # ObjectNode
        self.definitions = [] # DefValue

    def getParameters(self):
        return []

    def getOptions(self):
        return []

    def getName(self):
        return "default"

    def paramName(self, param):
        return param

    def setDefaultValues(self):
        for p in self.getParameters():
            self.definitions.append(DefValue(self.getDefault()))

    def export_nchildren(self):
        return 1

    def exportDefinitions(self, exporter):
        for d in reversed(self.definitions):
            d.export(self, exporter)

    def setParamName(self, p_index, p_name):
        pass

    def clone(self):
        cloned = copy.copy(self)
        cloned.children = []
        cloned.definitions = [DefValue(d.exp) for d in self.definitions]
        return cloned

    def export(self, exporter):
        return self.children


class SaveTransform(ObjectNode):
    def getName(self):
        return "Fix"

    def brickColor(self):
        return 0xc060a0

    def export_nchildren(self):
        return 1

    def export(self, exporter):
        if len(self.children) == 0:
            raise ExportException(self, "Fix node with no children")
        if len(self.children) == 1:
            exporter.out += [OP_SAVETRANS]
            return self.children
        savechildren = []
        for c in self.children:
            save = SaveTransform()
            save.children = [c]
            savechildren.append(save)
        return savechildren


class LabeledNode(ObjectNode):
    def __init__(self):
        ObjectNode.__init__(self)
        self.label = ""

    def getOptions(self):
        return ["label"]

    def getName(self):
        return self.label

    def option(self, op, value):
        if value is not None:
            self.label = value
        return self.label


class Identity(LabeledNode):
    def __init__(self, field):
        LabeledNode.__init__(self)
        self.field = field

    def brickColor(self):
        if self.label not in self.field.labelbricks or not any(b.node == self for b in self.field.labelbricks[self.label]):
            # button
            return 0x808080
        if self.label in self.field.linkbricks:
            if self.label in self.field.labelbricks and len(self.field.labelbricks[self.label]) > 1:
                # more than one linked label
                return 0xb0a0a0
            # linked label
            return 0xb0b0b0
        # unlinked label
        return 0x808080

    def export(self, exporter):
        return self.children


class Link(LabeledNode):
    def __init__(self, field):
        LabeledNode.__init__(self)
        self.field = field

    def brickColor(self):
        if self.label not in self.field.linkbricks or not any(b.node == self for b in self.field.linkbricks[self.label]):
            # button
            return 0xf0f0f0
        if self.label in self.field.labelbricks:
            if len(self.field.labelbricks[self.label]) > 1:
                # more than one matching label
                return 0xf0e0e0
            # one matching label
            return 0xf0f0f0
        # no matching labels
        return 0x505050

    def export(self, exporter):
        if self.label not in self.field.labelbricks:
            raise ExportException(self, "No matching label")
        if len(self.field.labelbricks[self.label]) > 1:
            raise ExportException(self, "More than one matching label")
        return self.children


class Transform(ObjectNode):
    def __init__(self, isglobal):
        ObjectNode.__init__(self)
        self.isglobal = isglobal

class Move(Transform):
    def __init__(self, isglobal=False):
        Transform.__init__(self, isglobal)

    def getParameters(self):
        return ["x","y","z"]

    def getDefault(self):
        return 0.0

    def getName(self):
        name = "%s %s %s" % tuple(d.exp for d in self.definitions)
        if len(name) > 14:
            name = name[0:14]
        return name

    def brickColor(self):
        if self.isglobal:
            return 0x404080
        return 0x4040c0

    def export(self, exporter):
        exporter.out += [OP_TRANSLATE if self.isglobal else OP_TRANSLATELOCAL]
        self.exportDefinitions(exporter)
        return self.children

class Scale(Transform):
    def __init__(self, isglobal=False):
        Transform.__init__(self, isglobal)

    def getParameters(self):
        return ["x","y","z"]

    def getDefault(self):
        return 1.0

    def getName(self):
        name = "%s %s %s" % tuple(d.exp for d in self.definitions)
        if len(name) > 14:
            name = name[0:14]
        return name

    def brickColor(self):
        if self.isglobal:
            return 0x408080
        return 0x4080c0

    def export(self, exporter):
        exporter.out += [OP_SCALE if self.isglobal else OP_SCALELOCAL]
        self.exportDefinitions(exporter)
        return self.children

class Rotate(Transform):
    AXIS_X = 0
    AXIS_Y = 1
    AXIS_Z = 2

    def __init__(self, axis, isglobal=False):
        Transform.__init__(self, isglobal)
        self.axis = axis

    def getParameters(self):
        return ["angle"]

    def getOptions(self):
        return ["axis"]

    def getDefault(self):
        return 0.0

    def getName(self):
        name = "%s: %s" % ("XYZ"[self.axis], self.definitions[0].exp)
        if len(name) > 14:
            name = name[0:14]
        return name
    
    def option(self, op, value):
        if value:
            if value.upper() == "X": self.axis = Rotate.AXIS_X
            if value.upper() == "Y": self.axis = Rotate.AXIS_Y
            if value.upper() == "Z": self.axis = Rotate.AXIS_Z
        return "XYZ"[self.axis]

    def setAxis(self, axis):
        self.axis = axis

    def brickColor(self):
        if self.isglobal:
            return 0x804080
        return 0x8040c0

    def export(self, exporter):
        return self.export_helper(exporter, 3)

    def export_helper(self, exporter, index):
        axis_index = [1,2,0][self.axis]
        zero = exporter.getConstIndex(0.0, self)
        if axis_index < index:
            # New node
            exporter.out += [zero] * (3 - index)
            exporter.out += [OP_ROTATE if self.isglobal else OP_ROTATELOCAL]
            index = 0
        exporter.out += [zero] * (axis_index - index)
        self.exportDefinitions(exporter)
        if len(self.children) == 1 and isinstance(self.children[0], Rotate) and False: # illegal
            return self.children[0].export_helper(exporter, axis_index+1)
        else:
            exporter.out += [zero] * (2 - axis_index)
            return self.children


class Repeat(ObjectNode):
    def __init__(self, n):
        ObjectNode.__init__(self)
        self.n = n

    def getOptions(self):
        return ["n"]

    def getName(self):
        return "repeat %d" % self.n

    def option(self, op, value):
        if value:
            try:
                intval = int(value)
                if intval >= 0:
                    self.n = intval
            except ValueError:
                pass
        return self.n

    def brickColor(self):
        return 0x40c040

    def export_nchildren(self):
        return 0

    def export(self, exporter):
        if len(self.children) == 1:
            n = self.children[0]
        else:
            n = ObjectNode()
            n.children = list(self.children)
        exporter.todo.append((n, len(exporter.out)+1))
        n_rep = self.n+1
        if (n_rep % 256) == 255 or (n_rep / 256) > 254:
            raise ExportException(self, "Illegal repeat count")
        exporter.out += [OP_REPEAT, 0, (n_rep % 256), (n_rep / 256)]
        return []


class Conditional(ObjectNode):
    def __init__(self):
        ObjectNode.__init__(self)

    def getParameters(self):
        return ["condition"]

    def getDefault(self):
        return 0.0

    def getName(self):
        return self.definitions[0].exp

    def brickColor(self):
        return 0x20a080

    def export_nchildren(self):
        return 0

    def export(self, exporter):
        if len(self.children) != 2:
            raise ExportException(self, "Conditional must have two children")
        exporter.out += [OP_CONDITIONAL]
        self.exportDefinitions(exporter)
        exporter.todo.append((self.children[0], len(exporter.out)))
        exporter.todo.append((self.children[1], len(exporter.out)+1))
        exporter.out += [0,0]
        return []


class DefinitionNode(ObjectNode):
    def __init__(self, var):
        self.var = var
        ObjectNode.__init__(self)

    def getParameters(self):
        return [self.var]

    def getDefault(self):
        return 0.0

    def getName(self):
        name = "%s = %s" % (self.var, self.definitions[0].exp)
        if len(name) > 14:
            name = name[0:14]
        return name

    def setParamName(self, p_index, p_name):
        if p_name.isalnum() and p_name[0].isalpha():
            self.var = p_name


class GlobalDefinition(DefinitionNode):
    def brickColor(self):
        if self.var in predefined_variables:
            return 0xe0e090
        else:
            return 0xa0a080

    def export(self, exporter):
        var_index = exporter.getConstIndex(self.var, self)
        exporter.out += [OP_ASSIGN]
        self.exportDefinitions(exporter)
        exporter.out += [var_index]
        return self.children


class LocalDefinition(DefinitionNode):
    def brickColor(self):
        if self.var in predefined_variables:
            return 0xf0d090
        else:
            return 0xc09080

    def export(self, exporter):
        var_index = exporter.getConstIndex(self.var, self)
        exporter.out += [OP_LOCALASSIGN]
        self.exportDefinitions(exporter)
        exporter.out += [var_index]
        return self.children


class PrimitiveNode(ObjectNode):
    def __init__(self, index, max_index):
        ObjectNode.__init__(self)
        self.index = index
        self.max_index = max_index

    def getParameters(self):
        return ["r","g","b","a"]

    def getOptions(self):
        return ["index"]

    def getDefault(self):
        return 0.5

    def option(self, op, value):
        if value:
            intval = int(value)
            if intval >= 0 and intval <= self.max_index:
                self.index = intval
        return self.index

    def brickColor(self):
        return 0xe0e020

    def export_nchildren(self):
        return 0


class Item(PrimitiveNode):
    MAX_INDEX = 100

    def __init__(self, index):
        PrimitiveNode.__init__(self, index, Text.MAX_INDEX)

    def getName(self):
        return "Object %d" % (self.index)

    def export(self, exporter):
        exporter.out += [OP_PRIM]
        exporter.out += [self.index]
        self.exportDefinitions(exporter)
        return self.children


class Primitive(Item):
    pass


class Text(Item):
    pass


class DynamicItem(PrimitiveNode):
    MAX_INDEX = 100

    def __init__(self, index):
        PrimitiveNode.__init__(self, index, Text.MAX_INDEX)

    def getParameters(self):
        return ["i", "r","g","b","a"]

    def getOptions(self):
        return []

    def getName(self):
        name = "%s" % (self.definitions[0].exp)
        if len(name) > 14:
            name = name[0:14]
        return name

    def setDefaultValues(self):
        PrimitiveNode.setDefaultValues(self)
        self.definitions[0] = DefValue(str(self.index))

    def export(self, exporter):
        exporter.out += [OP_DYNPRIM]
        self.exportDefinitions(exporter)
        #self.definitions[0].export(self, exporter)
        return self.children


class Light(PrimitiveNode):
    MAX_INDEX = 1

    def __init__(self, index):
        PrimitiveNode.__init__(self, index, Light.MAX_INDEX)

    def getName(self):
        return "Light %d" % (self.index)

    def export(self, exporter):
        exporter.out += [OP_LIGHT]
        exporter.out += [self.index]
        self.exportDefinitions(exporter)
        return self.children


class Camera(ObjectNode):
    def __init__(self):
        ObjectNode.__init__(self)

    def getName(self):
        return "Camera"

    def brickColor(self):
        return 0xe0e020

    def export_nchildren(self):
        return 0

    def export(self, exporter):
        exporter.out += [OP_CAMERA]
        return self.children


class ExportException(Exception):
    def __init__(self, node, message):
        Exception.__init__(self, message)
        self.node = node


class Exporter(object):
    def __init__(self, tree):
        self.tree = tree
        self.constmap = {}
        for (i,var) in enumerate(predefined_variables):
            self.constmap[var] = i
        self.constnodes = {}
        self.out = None
        self.labeled = None
        self.labelmap = None
        self.seenlabels = None
        self.todo = None
        self.node = None

    def getConstIndex(self, value, node):
        if value not in self.constnodes:
            self.constnodes[value] = set()
        self.constnodes[value].add(node)
        try:
            fval = float(value)
            frep = struct.pack('f', fval)
            #frep = chr(0)*2 + frep[2:4]
            value = struct.unpack('f', frep)[0]
        except ValueError:
            pass
        
        if value in self.constmap:
            return self.constmap[value]
        next_index = len(self.constmap)
        self.constmap[value] = next_index
        return next_index

    def newLabel(self, node):
        next_label = len(self.labelmap)
        self.labelmap[node] = next_label
        return next_label

    def exportexp(self, exp):
        id_regexp = re.compile('[a-zA-Z_][0-9a-zA-Z_]*')
        tokens_regexp = re.compile(
            '\s+|({|}|\*|\/|%|#|\+|-|\^|\||\(|\)|\@)' # delimiters
            )
        operators = {'mat': [0xF1], 'sin': [0xF2], 'clamp':[0xF3], 'round':[0xF4], 'abs': [0xF5], '^': [0xF6], '+': [0xF7], '-': [0xF8], '*': [0xF9], '/': [0xFA], '%': [0xFB], '@': [0xFC], '|': [0xFD], '#': [0xFE]}

        def is_id(s):
            return id_regexp.match(s) != None
    
        def gettoken():
            if tokens:
                return tokens.pop(0)
            else:
                return None
    
        def lookahead():
            if tokens:
                return tokens[0]
            else:
                return None
    
        def prim():
            tok = gettoken()
            if tok == '(':
                instructions = expression()
                assert gettoken() == ')'
                return instructions     #parenthesized expression
            else:
                tmp = lookahead()
                if tok == '-':
                    #try:
                    #    float(tmp)
                    #    #hack to allow negative constants
                    #    tok = '-' + gettoken()
                    #    tmp = lookahead()
                    #except ValueError:

                    #negation modelled as 0-
                    return operators['-'] + [self.getConstIndex(0.0, self.node)] + prim()
        
                if tmp == '(':          #function invokation
                    assert gettoken() == '('
                    e = expression()
                    assert gettoken() == ')'
                    return operators[tok] + e
                else:
                    #variable reference or float constant
                    if not is_id(tok):
                        if tok[0] == '.':
                            tok = '0'+tok
                        tok = float(tok)
                    elif tok == 'rand':
                        return [0xF0]
                    return [self.getConstIndex(tok, self.node)]
    
        def factor():
            instructions = prim()
            tmp = lookahead()
            while (tmp in ['^', '@', '|', '#']):
                gettoken()
                right = prim()
                instructions = operators[tmp] + right + instructions
                tmp = lookahead()
        
            return instructions
            
        def term():
            instructions = factor()
            tmp = lookahead()
            while (tmp in ['*', '/', '%']):
                gettoken()
                right = factor()
                if tmp == '%':
                    instructions = operators[tmp] + right + instructions
                else:
                    instructions = operators[tmp] + instructions + right
                tmp = lookahead()
        
            return instructions
                
        def expression():
            instructions = term()
            tmp = lookahead()
            while(tmp in ['+', '-']):
                gettoken()
                right = term()
                instructions = operators[tmp] + instructions + right
                tmp = lookahead()
        
            return instructions
    
        tokens = filter(None, tokens_regexp.split(exp))
        instructions = expression()
        if tokens:
            raise Exception("syntax error in expression")
        self.out += instructions

    def marklabels(self, node):
        if node in self.visited:
            self.labeled.add(node)
        else:
            self.visited.add(node)
            for c in node.children:
                self.marklabels(c)
    
    def exportnode(self, node):
        outpos = len(self.out)
        visitchildren = node.export(self)
        for o in self.out[outpos:]:
            if o < 0 or o > 255:
                raise ExportException(node, "Illegal value in export array: %d" % o)
        if len(visitchildren) != node.export_nchildren():
            if len(visitchildren) == 0:
                self.out += [OP_NOPLEAF]
            if node.export_nchildren() == 0:
                raise ExportException(node, "Primitive node with children")
            if len(visitchildren) > 1:
                self.out += [OP_FANOUT]
        for c in visitchildren:
            if c in self.labeled:
                self.todo.append((c, len(self.out)+1))
                self.out += [OP_REPEAT, 0, 0, 0]
            else:
                self.exportnode(c)
        if len(visitchildren) > 1:
            self.out += [0]
        if node in self.seenlabels:
            self.seenlabels.remove(node)
    
    # return list of byte values and list of constants
    def export(self):
        self.out = []
        self.visited = set()
        self.labeled = set()
        self.marklabels(self.tree)
        self.todo = []
        self.labelmap = {}

        self.seenlabels = set()
        self.exportnode(self.tree)
    
        while self.todo:
            n,ref_index = self.todo.pop()
            if n not in self.labelmap:
                self.labeled.add(n)
                label = self.newLabel(n)
                self.out += [OP_LABEL]
                self.seenlabels = set()
                self.exportnode(n)

            self.out[ref_index] = self.labelmap[n]
            
        self.out += [OP_LABEL, OP_END]
    
        constants = [0.0] * len(self.constmap)
        for val,index in self.constmap.iteritems():
            if isinstance(val, types.FloatType):
                constants[index] = val
    
        return self.out, constants, self.constmap
    
    def optimized_export(self):
        def varcompare(a,b):
            if isinstance(a,types.FloatType):
                if isinstance(b,types.FloatType):
                    if a >= 0.0 and b < 0.0:
                        return -1
                    if a < 0.0 and b >= 0.0:
                        return 1
                    if a < 0.0 and b < 0.0:
                        return cmp(b,a)
                    return cmp(a,b)
                return 1 
            if isinstance(b,types.FloatType):
                return -1
            return 0
    
        instructions,constants,constmap = self.export()
    
        constvars = range(len(constmap))
        for v,i in constmap.iteritems():
            constvars[i] = v
        constvars.sort(varcompare)
        self.constmap = {}
        for i,v in enumerate(constvars):
            self.constmap[v] = i
        instructions,constants,constmap = self.export()
    
        return instructions,constants,constmap

    def export_for_compiler(self):
        instructions,constants,constmap = self.optimized_export()

        def skipexp(i):
            inst = instructions[i]
            i += 1
            if inst > 0xF0:
                i = skipexp(i)
            if inst > 0xF5:
                i = skipexp(i)
            return i

        nodeformat = { # (bytes before exps, exps, bytes after exps)
            0: (0,0,0), # fanout terminator
            OP_FANOUT: (0,0,0),
            OP_SAVETRANS: (0,0,0),
            OP_REPEAT: (0,0,3),
            OP_PRIM: (1,4,0),
            OP_DYNPRIM: (0,5,0),
            OP_LIGHT: None,
            OP_CAMERA: None,
            OP_ASSIGN: (0,1,1),
            OP_LOCALASSIGN: (0,1,1),
            OP_CONDITIONAL: (0,1,2),
            OP_NOPLEAF: (0,0,0),
            OP_ROTATE: (0,3,0),
            OP_ROTATELOCAL: (0,3,0),
            OP_SCALE: (0,3,0),
            OP_SCALELOCAL: (0,3,0),
            OP_TRANSLATE: (0,3,0),
            OP_TRANSLATELOCAL: (0,3,0),
            OP_LABEL: None
        }

        nodes = []
        exps = []

        i = 0
        while i < len(instructions):
            inst = instructions[i]
            i += 1

            if inst == OP_END:
                nodes += [0]
                break

            if inst == OP_LABEL:
                continue

            nodes += [inst]

            b,e,a = nodeformat[inst]
            nodes += instructions[i:i+b]
            i += b

            before_exps = i
            for x in range(e):
                i = skipexp(i)
            exps += instructions[before_exps:i]

            nodes += instructions[i:i+a]
            i += a

        return (nodes,exps),constants,constmap

    def export_amiga(self):
        bytecount_n = [0] * 256
        bytecount_e = [0] * 256

        nodemap = {
            0: 0, # fanout terminator
            OP_FANOUT: 0xF5,
            OP_SAVETRANS: 0xF7,
            OP_REPEAT: 0xF8,
            OP_PRIM: 0xFE,
            OP_DYNPRIM: None,
            OP_LIGHT: None,
            OP_CAMERA: None,
            OP_ASSIGN: 0xFA,
            OP_LOCALASSIGN: None,
            OP_CONDITIONAL: 0xF9,
            OP_NOPLEAF: 0xF6,
            OP_ROTATELOCAL: 0xFD,
            OP_SCALELOCAL: 0xFB,
            OP_TRANSLATELOCAL: 0xFC,
            OP_LABEL: 0xFF
        }

        expmap = {
            0xF0: 0xF7, # random
            0xF2: 0xFE, # sin
            0xF3: 0xFD, # clamp
            0xF4: 0xFC, # round
            0xF7: 0xF9, # +
            0xF8: 0xFA, # -
            0xF9: 0xFB, # *
#            0xF9: 0xFA, # /
#            0xFA: 0xFB, # %
            0xFC: 0xF8  # @
        }

        instructions,constants,constmap = self.optimized_export()

        def traverse_exp(i, out_insts):
            op = instructions[i]
            i = i+1
            if op < 128:
                out_insts.append(op)
            elif op in [0xF0]: # Random
                out_insts.append(expmap[op])
                bytecount_e[expmap[op]] += 1
            elif op in [0xF2, 0xF3, 0xF4]: # Unary op: sin, clamp, round
                out_insts.append(expmap[op])
                bytecount_e[expmap[op]] += 1
                i = traverse_exp(i, out_insts)
            elif op in [0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC]: # Binary op: +, -, *, /, %, @
                out_insts.append(expmap[op])
                bytecount_e[expmap[op]] += 1
                i = traverse_exp(i, out_insts)
                i = traverse_exp(i, out_insts)
            else:
                raise Exception("Unsupported operation: %x" % op)
            return i


        out_insts = []
        i = 0
        while i < len(instructions) and instructions[i] != OP_END:
            inst = instructions[i]
            out_insts.append(nodemap[inst])
            bytecount_n[nodemap[inst]] += 1
            i = i+1
            if inst in [0, OP_FANOUT, OP_SAVETRANS, OP_NOPLEAF, OP_LABEL]:
                pass
            elif inst in [OP_REPEAT]:
                out_insts.append(instructions[i]) # label
                #out_insts.append(instructions[i+2]) # count high byte
                out_insts.append(instructions[i+1]) # count low byte
                i = i+3
            elif inst in [OP_PRIM]:
                i = i+1
                i = traverse_exp(i, []) # a
                i = traverse_exp(i, []) # b
                i = traverse_exp(i, out_insts) # g
                i = traverse_exp(i, out_insts) # r
            elif inst in [OP_ASSIGN, OP_LOCALASSIGN]:
                i = traverse_exp(i, out_insts)
                out_insts.append(instructions[i]) # variable
                i = i+1
            elif inst in [OP_CONDITIONAL]:
                i = traverse_exp(i, out_insts)
                out_insts.append(instructions[i]) # positive label
                out_insts.append(instructions[i+1]) # negative label
                i = i+2
            elif inst in [OP_ROTATELOCAL]:
                i = traverse_exp(i, out_insts) # z
                i = traverse_exp(i, []) # x
                i = traverse_exp(i, []) # y
            elif inst in [OP_SCALELOCAL, OP_TRANSLATELOCAL]:
                i = traverse_exp(i, []) # z
                i = traverse_exp(i, out_insts) # y
                i = traverse_exp(i, out_insts) # x
            else:
                raise Exception("Unexpected node ID: %d" % inst)

        for bc in [bytecount_n, bytecount_e]:
            stat = ""
            for i,c in enumerate(bc):
                if c > 0:
                    stat += "%02X: %d  " % (i,c)
            print stat

        return out_insts,constants,constmap


def export(tree):
    exporter = Exporter(tree)
    return exporter.export()

def optimized_export(tree):
    exporter = Exporter(tree)
    return exporter.optimized_export()
