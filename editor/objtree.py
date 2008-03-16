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

OP_FANOUT = 0x01
OP_SAVETRANS = 0x2
OP_CALL = 0x03
OP_PRIM = 0x04
OP_ASSIGN = 0x05
OP_LOCALASSIGN = 0x06
OP_CONDITIONAL = 0x07
OP_NOPLEAF = 0x08
OP_ROTATE = 0x09
OP_SCALE = 0x0a
OP_TRANSLATE = 0x0b
OP_LABEL = 0xff
OP_END = 0xfe




def makeMatrix(*data):
    return array.array("f", data)

def mulMatrix(mat1, mat2):
    result = []
    for i in range(4):
        for j in range(4):
            elem = sum([mat1[i*4+k] * mat2[k*4+j] for k in range(4)])
            result.append(elem)
    return array.array("f", result)

class DefValue(object):
    FUNCTIONS = {
        "sin" : (lambda x : math.sin(x * 2.0 * math.pi)),
        "exp" : (lambda x : math.pow(2.0, x)),
        "clamp" : (lambda x : max(0.0, x)),
        "round" : round,
    }

    def __init__(self, exp):
        self.setExp(exp)

    def setExp(self, exp):
        if isinstance(exp, types.FloatType):
            self.exp = "%.7f" % exp
        else:
            self.exp = str(exp)
        self.compiled = None

    def getValue(self, bindings):
        if self.compiled is None:
            self.compiled = compile(self.exp, "<DefValue>", "eval")
            self.freevars = set(self.compiled.co_names).difference(DefValue.FUNCTIONS)

        for v in self.freevars:
            if v not in bindings:
                bindings[v] = 0.0
        return eval(self.compiled, DefValue.FUNCTIONS, bindings)

    def getFreeVariables(self):
        return self.freevars

    def export(self, node, out, constmap):
        try:
            exportexp(self.exp, out, constmap)
        except Exception, e:
            raise ExportException(node, e.message)


class ObjectNode(object):
    def __init__(self, parameters = []):
        self.children = [] # ObjectNode
        self.parameters = parameters # string
        self.definitions = [] # (string, DefValue)
        self.options = []
        self.default = 0.0

    def getName(self):
        return "default"

    def paramName(self, param):
        return param

    def setConstants(self, *constants):
        for p,cval in constants:
            cdef = (self.paramName(p), DefValue(cval))
            self.definitions.append(cdef)

    def setDefaultValues(self):
        for p in self.parameters:
            cdef = (self.paramName(p), DefValue(self.default))
            self.definitions.append(cdef)

    def getParam(self, pname, bindings, default):
        fullpname = self.paramName(pname)
        if fullpname in bindings:
            return bindings[fullpname]
        return default

    def getParams(self, bindings):
        return [self.getParam(n, bindings, self.default) for n in self.parameters]

    def collectMeshes(self, tmlist, bindings, matrix):
        if self.definitions:
            bindings = bindings.copy()
            for (var, val) in self.definitions:
                bindings[var] = val.getValue(bindings)

        matrix = self.collectOwnMeshes(tmlist, bindings, matrix)

        for c in self.children:
            c.collectMeshes(tmlist, bindings, matrix)

    def collectOwnMeshes(self, tmlist, bindings, matrix):
        return matrix

    def getFreeVariables(self):
        fvars = set()
        for c in self.children:
            fvars.update(c.getFreeVariables())
        fvars.update(self.paramName(p) for p in self.parameters)
        for name,val in reversed(self.definitions):
            fvars.discard(name)
            fvars.update(val.getFreeVariables())
        return list(fvars).sorted()

    def brickColor(self):
        return 0x808080

    def export_nchildren(self):
        return 1

    def exportDefinitions(self, out, constmap):
        for (name, d) in reversed(self.definitions):
            d.export(self, out, constmap)

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

    def export(self, out, labelmap, constmap, todo):
        if len(self.children) == 0:
            raise ExportException(self, "Fix node with no children")
        out += [OP_SAVETRANS]
        return self.children

    def variableChildren(self):
        return True


class Transform(ObjectNode):
    def collectOwnMeshes(self, tmlist, bindings, matrix):
        self_matrix = self.getMatrix(bindings)
        return mulMatrix(self_matrix, matrix)


class Identity(Transform):
    def __init__(self):
        Transform.__init__(self)
        self.options = ["label"]
        self.label = ""

    def getName(self):
        return self.label

    def option(self, op, value):
        if value is not None:
            self.label = value
        return self.label

    def getMatrix(self, bindings):
        return makeMatrix(1,0,0,0,
                          0,1,0,0,
                          0,0,1,0,
                          0,0,0,1)

    def export(self, out, labelmap, constmap, todo):
        return self.children


class Move(Transform):
    def __init__(self):
        Transform.__init__(self, ["x","y","z"])
        self.default = 0.0
    
    def getName(self):
        return "move"

    def getMatrix(self, bindings):
        p = self.getParams(bindings)
        return makeMatrix(1,0,0,0,
                          0,1,0,0,
                          0,0,1,0,
                          p[0],p[1],p[2],1)

    def brickColor(self):
        return 0x4040c0

    def export(self, out, labelmap, constmap, todo):
        out += [OP_TRANSLATE]
        self.exportDefinitions(out, constmap)
        return self.children

class Scale(Transform):
    def __init__(self):
        Transform.__init__(self, ["x","y","z"])
        self.default = 1.0

    def getName(self):
        return "scale"

    def getMatrix(self, bindings):
        p = self.getParams(bindings)
        return makeMatrix(p[0],0,0,0,
                          0,p[1],0,0,
                          0,0,p[2],0,
                          0,0,0,1)

    def brickColor(self):
        return 0x4080c0

    def export(self, out, labelmap, constmap, todo):
        out += [OP_SCALE]
        self.exportDefinitions(out, constmap)
        return self.children

class Rotate(Transform):
    AXIS_X = 0
    AXIS_Y = 1
    AXIS_Z = 2

    def __init__(self, axis):
        self.axis = axis
        Transform.__init__(self, ["angle"])
        self.default = 0.0
        self.options = ["axis"]

    def getName(self):
        return "rot%s" % "XYZ"[self.axis]
    
    def option(self, op, value):
        if value:
            if value.upper() == "X": self.axis = Rotate.AXIS_X
            if value.upper() == "Y": self.axis = Rotate.AXIS_Y
            if value.upper() == "Z": self.axis = Rotate.AXIS_Z
        return "XYZ"[self.axis]

    def getMatrix(self, bindings):
        p = self.getParams(bindings)
        matrix = makeMatrix(1,0,0,0,
                            0,1,0,0,
                            0,0,1,0,
                            0,0,0,1)
        a = (self.axis + 1) % 3
        b = (self.axis + 2) % 3
        angle = p[0] * (2.0 * math.pi)
        matrix[a*4 + a] = math.cos(angle)
        matrix[a*4 + b] = math.sin(angle)
        matrix[b*4 + a] = -math.sin(angle)
        matrix[b*4 + b] = math.cos(angle)
        return matrix

    def setAxis(self, axis):
        self.axis = axis

    def brickColor(self):
        return 0x8040c0

    def export(self, out, labelmap, constmap, todo):
        out += [OP_ROTATE]
        axis_index = [1,2,0][self.axis]
        zero = getConstIndex(0.0, constmap)
        out += [zero] * axis_index
        self.exportDefinitions(out, constmap)
        out += [zero] * (2 - axis_index)
        return self.children


class Repeat(ObjectNode):
    def __init__(self, n):
        ObjectNode.__init__(self)
        self.n = n
        self.options = ["n"]

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

    def collectMeshes(self, tmlist, bindings, matrix):
        if self.n > 0:
            self.n -= 1
            ObjectNode.collectMeshes(self, tmlist, bindings, matrix)
            self.n += 1

    def brickColor(self):
        return 0x40c040

    def export_nchildren(self):
        return 0

    def export(self, out, labelmap, constmap, todo):
        todo.append((self.children, len(out)+1))
        n_rep = self.n+1
        if (n_rep % 256) == 255 or (n_rep / 256) > 254:
            raise ExportException(self, "Illegal repeat count")
        out += [OP_CALL, 0, (n_rep % 256), (n_rep / 256)]
        return []


class Conditional(ObjectNode):
    def __init__(self):
        ObjectNode.__init__(self, ["condition"])

    def getName(self):
        return self.definitions[0][1].exp

    def brickColor(self):
        return 0x20a080

    def collectMeshes(self, tmlist, bindings, matrix):
        bindings = bindings.copy()
        for (var, val) in self.definitions:
            bindings[var] = val.getValue(bindings)

        p = self.getParams(bindings)
        if p[0] >= 0 and len(self.children) >= 2:
            self.children[1].collectMeshes(tmlist, bindings, matrix)
        elif len(self.children) >= 1:
            self.children[0].collectMeshes(tmlist, bindings, matrix)

    def export_nchildren(self):
        return 0

    def export(self, out, labelmap, constmap, todo):
        if len(self.children) != 2:
            raise ExportException(self, "Conditional must have two children")
        out += [OP_CONDITIONAL]
        self.exportDefinitions(out, constmap)
        todo.append(([self.children[0]], len(out)))
        todo.append(([self.children[1]], len(out)+1))
        out += [0,0]
        return []


class DefinitionNode(ObjectNode):
    def __init__(self, var):
        self.var = var
        ObjectNode.__init__(self)
        self.definitions = [(var, DefValue(0.0))]

    def getName(self):
        name = "%s = %s" % (self.var, self.definitions[0][1].exp)
        if len(name) > 14:
            name = name[0:14]
        return name

    def setParamName(self, p_index, p_name):
        if p_name.isalnum() and p_name[0].isalpha():
            self.var = p_name
            self.definitions = [(p_name, self.definitions[0][1])]
            self.parameters = [p_name]


class GlobalDefinition(DefinitionNode):
    def brickColor(self):
        return 0xa0a080

    def export(self, out, labelmap, constmap, todo):
        var_index = getConstIndex(self.var, constmap)
        out += [OP_ASSIGN]
        self.exportDefinitions(out, constmap)
        out += [var_index]
        return self.children


class LocalDefinition(DefinitionNode):
    def brickColor(self):
        return 0xc09080

    def export(self, out, labelmap, constmap, todo):
        var_index = getConstIndex(self.var, constmap)
        out += [OP_LOCALASSIGN]
        self.exportDefinitions(out, constmap)
        out += [var_index]
        return self.children


class TextPrimitive(ObjectNode):
    def __init__(self, fontname, text, color):
        ObjectNode.__init__(self, name = "text")
        self.fontname = fontname
        self.text = text
        self.color = color
        self.mesh = None

    def getName(self):
        return "text"

    def collectOwnMeshes(self, tmlist, bindings, matrix):
        if not self.mesh:
            font = d3d.Font(self.fontname, 12)
            self.mesh = d3d.StaticMesh.fromFont(font, self.text)
        tmlist.append((matrix, self.mesh, self.color))
        return matrix

    def brickColor(self):
        return 0xe0e020


class Primitive(ObjectNode):
    NAMES = ["box","sphere","cylinder","smoothbox"]
    meshes = None

    def __init__(self, index):
        ObjectNode.__init__(self, ["r","g","b"])
        self.index = index
        self.meshes = None
        self.default = 0.5
        self.options = ["kind"]

    def option(self, op, value):
        if value:
            intval = int(value)
            if intval >= 0 and intval < len(Primitive.NAMES):
                self.index = intval
        return self.index

    def getName(self):
        return Primitive.NAMES[self.index]

    def collectOwnMeshes(self, tmlist, bindings, matrix):
        if not Primitive.meshes:
            Primitive.meshes = [
                d3d.StaticMesh(unicode(name+".x")) for name in Primitive.NAMES
            ]
        rgb = self.getParams(bindings)

        color = sum((int(c * 255.0) & 255) << ((2-i)*8) for i,c in enumerate(rgb))
        tmlist.append((matrix, Primitive.meshes[self.index], color))
        return matrix

    def brickColor(self):
        return 0xe0e020

    def export_nchildren(self):
        return 0

    def export(self, out, labelmap, constmap, todo):
        out += [OP_PRIM]
        out += [self.index]
        self.exportDefinitions(out, constmap)
        return self.children


def getConstIndex(value, constmap):
    try:
        fval = float(value)
        frep = struct.pack('f', fval)
        #frep = chr(0)*2 + frep[2:4]
        value = struct.unpack('f', frep)[0]
    except ValueError:
        pass
    
    if value in constmap:
        return constmap[value]
    next_index = len(constmap)
    constmap[value] = next_index
    return next_index

def newLabel(node, labelmap):
    next_label = len(labelmap)
    labelmap[node] = next_label
    return next_label


def exportexp(exp, out, constmap):
    id_regexp = re.compile('[a-zA-Z_][0-9a-zA-Z_]*')
    tokens_regexp = re.compile(
        '\s+|({|}|\*|\/|%|\+|-|\^|\||\(|\))' # delimiters
        )
    operators = {'sin': [0x82], 'clamp':[0x83], 'round':[0x84], '^':[0x85], '+': [0x86], '-': [0x87], '*': [0x88], '/': [0x89], '%': [0x8A], '|': [0x8B]}

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
                    return operators['-'] + [getConstIndex(0.0, constmap)] + prim()
    
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
                    return [0x81]
                return [getConstIndex(tok, constmap)]

    def factor():
        instructions = prim()
        tmp = lookahead()
        while (tmp in ['^','|']):
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
    out += instructions


class ExportException(Exception):
    def __init__(self, node, message):
        Exception.__init__(self, message)
        self.node = node

def marklabels(node, visited, labeled):
    if node in visited:
        labeled.add(node)
    else:
        visited.add(node)
        for c in node.children:
            marklabels(c, visited, labeled)

def exportnode(node, out, labeled, labelmap, constmap, todo):
    if node in labelmap:
        out += [OP_CALL, labelmap[node], 0, 0]
        return
    if node in labeled:
        label = newLabel(node, labelmap)
        out += [OP_LABEL]
    visitchildren = node.export(out, labelmap, constmap, todo)
    if len(visitchildren) != node.export_nchildren():
        if len(visitchildren) == 0:
            out += [OP_NOPLEAF]
        if node.export_nchildren() == 0:
            raise ExportException(node, "Primitive node with children")
        if len(visitchildren) > 1:
            out += [OP_FANOUT]
    for c in visitchildren:
        exportnode(c, out, labeled, labelmap, constmap, todo)
    if len(visitchildren) > 1 or node.variableChildren():
        out += [0]

# return list of byte values and list of constants
def export(root):
    out = []
    visited = set()
    labeled = set()
    marklabels(root, visited, labeled)
    labeled.add(root)
    todo = []
    labelmap = {}
    constmap = {}
    constmap["time"] = 0
    constmap["frame"] = 1
    constmap["seed"] = 2
    for i in range(16):
        constmap["chan%d" % i] = i+3
    exportnode(root, out, labeled, labelmap, constmap, todo)

    while todo:
        nodes,ref_index = todo.pop()
        dummy = Identity()
        dummy.children = list(nodes)
        labeled.add(dummy)
        exportnode(dummy, out, labeled, labelmap, constmap, todo)
        out[ref_index] = labelmap[dummy]
        
    out += [OP_LABEL, OP_END]

    constants = [0.0] * len(constmap)
    for val,index in constmap.iteritems():
        if isinstance(val, types.FloatType):
            constants[index] = val

    return out, constants, constmap

