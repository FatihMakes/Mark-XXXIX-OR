"""This module defines the funtions byref_at(cobj, offset)
and cast_field(struct, fieldname, fieldtype).
"""

import sys
from ctypes import (
    POINTER,
    Structure,
    Union,
    _SimpleCData,
    addressof,
    byref,
    c_byte,
    c_char,
    c_double,
    c_float,
    c_int,
    c_long,
    c_longdouble,
    c_longlong,
    c_short,
    c_void_p,
    cast,
    sizeof,
)
from ctypes import Array as _CArrayType
from typing import TYPE_CHECKING, TypeVar, overload

if TYPE_CHECKING:
    from ctypes import _CArgObject, _CData

_T = TypeVar("_T")
_CT = TypeVar("_CT", bound="_CData")


def _calc_offset():
    # Internal helper function that calculates where the object
    # returned by a byref() call stores the pointer.

    # The definition of PyCArgObject in C code (that is the type of
    # object that a byref() call returns):
    class PyCArgObject(Structure):
        if sys.version_info >= (3, 14):
            # While C compilers automatically determine appropriate
            # alignment based on field data types, `ctypes` requires
            # explicit control over memory layout.
            #
            # `_pack_ = 8` ensures 8-byte alignment for fields.
            #
            # This works on both 32-bit and 64-bit systems:
            # - On 64-bit systems, this matches the natural alignment
            #   for pointers.
            # - On 32-bit systems, this is more strict than necessary
            #   (4-byte would be enough), but still produces the
            #   correct memory layout with proper padding.
            #
            # With `_pack_`, `ctypes` will automatically add padding
            # here to ensure proper alignment of the `value` field
            # after the `tag` and after the `size`.
            _pack_ = 8
        else:
            # No special packing needed for Python 3.13 and earlier
            # because the default alignment works fine for the legacy
            # structure.
            pass

        class value(Union):
            if sys.version_info >= (3, 14):
                # In Python 3.14, the tagPyCArgObject structure was
                # modified to better support complex types.
                _fields_ = [
                    ("c", c_char),
                    ("b", c_char),
                    ("h", c_short),
                    ("i", c_int),
                    ("l", c_long),
                    ("q", c_longlong),
                    ("g", c_longdouble),
                    ("d", c_double),
                    ("f", c_float),
                    ("p", c_void_p),
                    # arrays for real and imaginary of complex
                    ("D", c_double * 2),
                    ("F", c_float * 2),
                    ("G", c_longdouble * 2),
                ]
            else:
                _fields_ = [
                    ("c", c_char),
                    ("h", c_short),
                    ("i", c_int),
                    ("l", c_long),
                    ("q", c_longlong),
                    ("d", c_double),
                    ("f", c_float),
                    ("p", c_void_p),
                ]

        #
        # Thanks to Lenard Lindstrom for this tip:
        # sizeof(PyObject_HEAD) is the same as object.__basicsize__.
        #
        _fields_ = [
            ("PyObject_HEAD", c_byte * object.__basicsize__),
            ("pffi_type", c_void_p),
            ("tag", c_char),
            ("value", value),
            ("obj", c_void_p),
            ("size", c_int),
        ]

        _anonymous_ = ["value"]

    # additional checks to make sure that everything works as expected
    expected_size = type(byref(c_int())).__basicsize__
    actual_size = sizeof(PyCArgObject)
    if actual_size != expected_size:
        raise RuntimeError(
            f"sizeof(PyCArgObject) mismatch: expected {expected_size}, "
            f"got {actual_size}."
        )

    obj = c_int()
    ref = byref(obj)

    argobj = PyCArgObject.from_address(id(ref))

    if argobj.obj != id(obj) or argobj.p != addressof(obj) or argobj.tag != b"P":
        raise RuntimeError("PyCArgObject field definitions incorrect")

    return PyCArgObject.p.offset  # offset of the pointer field


################################################################
#
# byref_at
#
@overload
def byref_at(obj: _CArrayType, offset: int) -> "_CArgObject": ...
@overload
def byref_at(obj: "_CData", offset: int) -> "_CArgObject": ...
def byref_at(
    obj,
    offset,
    _byref=byref,
    _c_void_p_from_address=c_void_p.from_address,
    _byref_pointer_offset=_calc_offset(),
):
    """byref_at(cobj, offset) behaves similar this C code:

        (((char *)&obj) + offset)

    In other words, the returned 'pointer' points to the address of
    'cobj' + 'offset'.  'offset' is in units of bytes.
    """
    ref = _byref(obj)
    # Change the pointer field in the created byref object by adding
    # 'offset' to it:
    _c_void_p_from_address(id(ref) + _byref_pointer_offset).value += offset
    return ref


################################################################
#
# cast_field
#
@overload
def cast_field(
    struct: Structure, fieldname: str, fieldtype: type["_SimpleCData[_T]"]
) -> _T: ...
@overload
def cast_field(struct: Structure, fieldname: str, fieldtype: type[_CT]) -> _CT: ...
def cast_field(
    struct,
    fieldname,
    fieldtype,
    _POINTER=POINTER,
    _byref_at=byref_at,
):
    """cast_field(struct, fieldname, fieldtype)

    Return the contents of a struct field as it it were of type
    'fieldtype'.
    """
    fieldoffset = getattr(type(struct), fieldname).offset
    return cast(_byref_at(struct, fieldoffset), _POINTER(fieldtype))[0]


__all__ = ["byref_at", "cast_field"]
