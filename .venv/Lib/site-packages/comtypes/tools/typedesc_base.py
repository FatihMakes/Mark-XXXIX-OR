# typedesc.py - classes representing C type descriptions
from typing import Any, Optional, SupportsInt
from typing import Union as _UnionT

import comtypes


class Argument:
    "a Parameter in the argument list of a callable (Function, Method, ...)"

    def __init__(self, atype, name):
        self.atype = atype
        self.name = name


class _HasArgs:
    def __init__(self):
        self.arguments = []

    def add_argument(self, arg):
        assert isinstance(arg, Argument)
        self.arguments.append(arg)

    def iterArgTypes(self):
        for a in self.arguments:
            yield a.atype

    def iterArgNames(self):
        for a in self.arguments:
            yield a.name

    def fixup_argtypes(self, typemap):
        for a in self.arguments:
            a.atype = typemap[a.atype]


################


class Alias:
    # a C preprocessor alias, like #define A B
    def __init__(self, name, alias, typ=None):
        self.name = name
        self.alias = alias
        self.typ = typ


class Macro:
    # a C preprocessor definition with arguments
    def __init__(self, name, args, body):
        # all arguments are strings, args is the literal argument list
        # *with* the parens around it:
        # Example: Macro("CD_INDRIVE", "(status)", "((int)status > 0)")
        self.name = name
        self.args = args
        self.body = body


class File:
    def __init__(self, name):
        self.name = name


class Function(_HasArgs):
    location = None

    def __init__(self, name, returns, attributes, extern):
        _HasArgs.__init__(self)
        self.name = name
        self.returns = returns
        self.attributes = attributes  # dllimport, __stdcall__, __cdecl__
        self.extern = extern


class Constructor(_HasArgs):
    location = None

    def __init__(self, name):
        _HasArgs.__init__(self)
        self.name = name


class OperatorFunction(_HasArgs):
    location = None

    def __init__(self, name, returns):
        _HasArgs.__init__(self)
        self.name = name
        self.returns = returns


class FunctionType(_HasArgs):
    location = None

    def __init__(self, returns, attributes):
        _HasArgs.__init__(self)
        self.returns = returns
        self.attributes = attributes


class Method(_HasArgs):
    location = None

    def __init__(self, name, returns):
        _HasArgs.__init__(self)
        self.name = name
        self.returns = returns


class FundamentalType:
    location = None

    def __init__(self, name, size, align):
        self.name = name
        if name != "void":
            self.size = int(size)
            self.align = int(align)


class PointerType:
    location = None

    def __init__(self, typ, size, align):
        self.typ = typ
        self.size = int(size)
        self.align = int(align)


class Typedef:
    location = None

    def __init__(self, name, typ):
        self.name = name
        self.typ = typ


class ArrayType:
    location = None

    def __init__(self, typ: Any, min: int, max: int) -> None:
        self.typ = typ
        self.min = min
        self.max = max


class StructureHead:
    location = None

    def __init__(self, struct: "_Struct_Union_Base") -> None:
        self.struct = struct


class StructureBody:
    location = None

    def __init__(self, struct: "_Struct_Union_Base") -> None:
        self.struct = struct


class _Struct_Union_Base:
    name: str
    align: int
    members: list[_UnionT["Field", Method, Constructor]]
    bases: list["_Struct_Union_Base"]
    artificial: Optional[Any]
    size: Optional[int]
    _recordinfo_: tuple[str, int, int, int, str]

    location = None

    def __init__(self):
        self.struct_body = StructureBody(self)
        self.struct_head = StructureHead(self)

    def get_body(self) -> StructureBody:
        return self.struct_body

    def get_head(self) -> StructureHead:
        return self.struct_head


class Structure(_Struct_Union_Base):
    def __init__(
        self,
        name: str,
        align: SupportsInt,
        members: list["Field"],
        bases: list[Any],
        size: Optional[SupportsInt],
        artificial: Optional[Any] = None,
    ) -> None:
        self.name = name
        self.align = int(align)
        self.members = members
        self.bases = bases
        self.artificial = artificial
        if size is not None:
            self.size = int(size)
        else:
            self.size = None
        super().__init__()


class Union(_Struct_Union_Base):
    def __init__(
        self,
        name: str,
        align: SupportsInt,
        members: list["Field"],
        bases: list[Any],
        size: Optional[SupportsInt],
        artificial: Optional[Any] = None,
    ) -> None:
        self.name = name
        self.align = int(align)
        self.members = members
        self.bases = bases
        self.artificial = artificial
        if size is not None:
            self.size = int(size)
        else:
            self.size = None
        super().__init__()


class Field:
    def __init__(
        self, name: str, typ: Any, bits: Optional[Any], offset: SupportsInt
    ) -> None:
        self.name = name
        self.typ = typ
        self.bits = bits
        self.offset = int(offset)


class CvQualifiedType:
    def __init__(self, typ, const, volatile):
        self.typ = typ
        self.const = const
        self.volatile = volatile


class Enumeration:
    location = None

    def __init__(self, name: str, size: SupportsInt, align: SupportsInt) -> None:
        self.name = name
        self.size = int(size)
        self.align = int(align)
        self.values: list[EnumValue] = []

    def add_value(self, v: "EnumValue") -> None:
        self.values.append(v)


class EnumValue:
    def __init__(self, name: str, value: int, enumeration: Enumeration) -> None:
        self.name = name
        self.value = value
        self.enumeration = enumeration


class Variable:
    location = None

    def __init__(self, name, typ, init=None):
        self.name = name
        self.typ = typ
        self.init = init


################################################################
