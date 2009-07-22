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
from ctypes import create_string_buffer,windll

OP_FANOUT = 0x01
OP_SAVETRANS = 0x2
OP_CALL = 0x03
OP_PRIM = 0x04
OP_LIGHT = -1#0x05
OP_CAMERA = -1#0x06
OP_ASSIGN = 0x05
OP_LOCALASSIGN = 0x06
OP_CONDITIONAL = 0x07
OP_NOPLEAF = 0x08
OP_ROTATE = 0x09
OP_SCALE = 0x0a
OP_TRANSLATE = 0x0b
OP_LABEL = 0xff
OP_END = 0xfe


predefined_variables = []

def update_predefined_variables():
    global predefined_variables
    buf = create_string_buffer(1000)
    nparams = windll.RenderDLL.getparams(buf)
    predefined_variables = buf.raw.split("/", nparams)[0:nparams]


def makeMatrix(*data):
    return array.array("f", data)

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

    def brickColor(self):
        return 0x808080

    def export_nchildren(self):
        return 1

    def exportDefinitions(self, exporter):
        for d in reversed(self.definitions):
            d.export(self, exporter)

    def setParamName(self, p_index, p_name):
        pass

    def variableChildren(self):
        return False


class SaveTransform(ObjectNode):
    def getName(self):
        return "Fix"

    def brickColor(self):
        return 0xc060a0

    def export_nchildren(self):
        return len(self.children)

    def export(self, exporter):
        if len(self.children) == 0:
            raise ExportException(self, "Fix node with no children")
        exporter.out += [OP_SAVETRANS]
        return self.children

    def variableChildren(self):
        return True


class Transform(ObjectNode):
    pass

class Identity(Transform):
    def __init__(self):
        Transform.__init__(self)
        self.label = ""

    def getOptions(self):
        return ["label"]

    def getName(self):
        return self.label

    def option(self, op, value):
        if value is not None:
            self.label = value
        return self.label

    def export(self, exporter):
        return self.children


class Move(Transform):
    def __init__(self):
        Transform.__init__(self)

    def getParameters(self):
        return ["x","y","z"]

    def getDefault(self):
        return 0.0

    def getName(self):
        return "move"

    def brickColor(self):
        return 0x4040c0

    def export(self, exporter):
        exporter.out += [OP_TRANSLATE]
        self.exportDefinitions(exporter)
        return self.children

class Scale(Transform):
    def __init__(self):
        Transform.__init__(self)

    def getParameters(self):
        return ["x","y","z"]

    def getDefault(self):
        return 1.0

    def getName(self):
        return "scale"

    def brickColor(self):
        return 0x4080c0

    def export(self, exporter):
        exporter.out += [OP_SCALE]
        self.exportDefinitions(exporter)
        return self.children

class Rotate(Transform):
    AXIS_X = 0
    AXIS_Y = 1
    AXIS_Z = 2

    def __init__(self, axis):
        self.axis = axis
        Transform.__init__(self)

    def getParameters(self):
        return ["angle"]

    def getOptions(self):
        return ["axis"]

    def getDefault(self):
        return 0.0

    def getName(self):
        return "rot%s" % "XYZ"[self.axis]
    
    def option(self, op, value):
        if value:
            if value.upper() == "X": self.axis = Rotate.AXIS_X
            if value.upper() == "Y": self.axis = Rotate.AXIS_Y
            if value.upper() == "Z": self.axis = Rotate.AXIS_Z
        return "XYZ"[self.axis]

    def setAxis(self, axis):
        self.axis = axis

    def brickColor(self):
        return 0x8040c0

    def export(self, exporter):
        return self.export_helper(exporter, 3)

    def export_helper(self, exporter, index):
        axis_index = [1,2,0][self.axis]
        zero = exporter.getConstIndex(0.0, self)
        if axis_index < index:
            # New node
            exporter.out += [zero] * (3 - index)
            exporter.out += [OP_ROTATE]
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
        exporter.todo.append((self.children, len(exporter.out)+1))
        n_rep = self.n+1
        if (n_rep % 256) == 255 or (n_rep / 256) > 254:
            raise ExportException(self, "Illegal repeat count")
        exporter.out += [OP_CALL, 0, (n_rep % 256), (n_rep / 256)]
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
        exporter.todo.append(([self.children[0]], len(exporter.out)))
        exporter.todo.append(([self.children[1]], len(exporter.out)+1))
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


class Text(PrimitiveNode):
    MAX_INDEX = 100

    def __init__(self, index):
        PrimitiveNode.__init__(self, index, Text.MAX_INDEX)

    def getName(self):
        return "Text %d" % (self.index)

    def export(self, exporter):
        exporter.out += [OP_PRIM]
        exporter.out += [self.index]
        self.exportDefinitions(exporter)
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
            '\s+|({|}|\*|\/|%|#|\+|-|\^|\||\(|\))' # delimiters
            )
        operators = {'sin': [0xF2], 'clamp':[0xF3], 'round':[0xF4], '^': [0xF5], '+': [0xF6], '-': [0xF7], '*': [0xF8], '/': [0xF9], '%': [0xFA], '|': [0xFB], '#': [0xFC]}

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
                    try:
                        float(tmp)
                        #hack to allow negative constants
                        tok = '-' + gettoken()
                        tmp = lookahead()
                    except ValueError:
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
                        return [0xF1]
                    return [self.getConstIndex(tok, self.node)]
    
        def factor():
            instructions = prim()
            tmp = lookahead()
            while (tmp in ['^','|', '#']):
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
        if node in self.labelmap:
            if node in self.seenlabels:
                raise ExportException(node, "Loop without repeat")
            self.out += [OP_CALL, self.labelmap[node], 0, 0]
            return
        if node in self.labeled:
            self.seenlabels.add(node)
            label = self.newLabel(node)
            self.out += [OP_LABEL]
        visitchildren = node.export(self)
        if len(visitchildren) != node.export_nchildren():
            if len(visitchildren) == 0:
                self.out += [OP_NOPLEAF]
            if node.export_nchildren() == 0:
                raise ExportException(node, "Primitive node with children")
            if len(visitchildren) > 1:
                self.out += [OP_FANOUT]
        for c in visitchildren:
            self.exportnode(c)
        if len(visitchildren) > 1 or node.variableChildren():
            self.out += [0]
        if node in self.seenlabels:
            self.seenlabels.remove(node)
    
    # return list of byte values and list of constants
    def export(self):
        self.out = []
        self.visited = set()
        self.labeled = set()
        self.marklabels(self.tree)
        self.labeled.add(self.tree)
        self.todo = []
        self.labelmap = {}

        self.seenlabels = set()
        self.exportnode(self.tree)
    
        while self.todo:
            nodes,ref_index = self.todo.pop()
            dummy = Identity()
            dummy.children = list(nodes)
            self.labeled.add(dummy)
            self.seenlabels = set()
            self.exportnode(dummy)
            self.out[ref_index] = self.labelmap[dummy]
            
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


def export(tree):
    exporter = Exporter(tree)
    return exporter.export()

def optimized_export(tree):
    exporter = Exporter(tree)
    return exporter.optimized_export()
