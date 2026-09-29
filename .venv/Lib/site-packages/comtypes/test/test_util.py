import sys
import unittest
from ctypes import (
    POINTER,
    Structure,
    Union,
    addressof,
    c_byte,
    c_char,
    c_double,
    c_int,
    c_void_p,
    cast,
    sizeof,
)

PY_3_15_ALPHA_BETA = (
    sys.version_info.major == 3
    and sys.version_info.minor == 15
    and sys.version_info.releaselevel in ("alpha", "beta")
)

try:
    import comtypes.util
except RuntimeError as e:
    SKIP_MSG = (
        "Starting from Python 3.15, PyCArgObject layout is changed. "
        "See https://github.com/enthought/comtypes/issues/938."
    )
    if PY_3_15_ALPHA_BETA:

        def setUpModule():
            raise unittest.SkipTest(SKIP_MSG)
    else:
        raise e
from comtypes import GUID, CoCreateInstance, IUnknown, shelllink


class ByrefAtTest(unittest.TestCase):
    def test_ctypes(self):
        for ctype, value in [
            (c_int, 42),
            (c_double, 3.14),
            (c_char, b"A"),
        ]:
            with self.subTest(ctype=ctype, value=value):
                obj = ctype(value)
                # Test with zero offset - should point to the same location
                ref = comtypes.util.byref_at(obj, 0)
                ptr = cast(ref, POINTER(ctype))
                # byref objects don't have contents, but we can cast them to pointers
                self.assertEqual(addressof(ptr.contents), addressof(obj))
                self.assertEqual(ptr.contents.value, value)

    def test_array_offsets(self):
        elms = [10, 20, 30, 40]
        arr = (c_int * 4)(*elms)  # Create an array
        # Test accessing different elements via offset
        for i, expected in enumerate(elms):
            with self.subTest(index=i, expected=expected):
                ref = comtypes.util.byref_at(arr, offset=sizeof(c_int) * i)
                ptr = cast(ref, POINTER(c_int))
                self.assertEqual(ptr.contents.value, expected)

    def test_pointer_arithmetic(self):
        # Test that byref_at behaves like C pointer arithmetic

        class TestStruct(Structure):
            _fields_ = [
                ("field1", c_int),
                ("field2", c_double),
                ("field3", c_char),
            ]

        struct = TestStruct(123, 3.14, b"X")
        for fname, ftype, expected in [
            ("field1", c_int, 123),
            ("field2", c_double, 3.14),
            ("field3", c_char, b"X"),
        ]:
            with self.subTest(field=fname, type=ftype, expected=expected):
                offset = getattr(TestStruct, fname).offset
                ref = comtypes.util.byref_at(struct, offset)
                ptr = cast(ref, POINTER(ftype))
                self.assertEqual(ptr.contents.value, expected)

    def test_com_interface(self):
        CLSID_ShellLink = GUID("{00021401-0000-0000-C000-000000000046}")
        sc = CoCreateInstance(CLSID_ShellLink, interface=shelllink.IShellLinkA)
        ref = comtypes.util.byref_at(sc, 0)
        ptr = cast(ref, POINTER(POINTER(IUnknown)))
        self.assertEqual(addressof(ptr.contents), addressof(sc))

    def test_large_offset(self):
        # Create a large array to test with large offsets
        arr = (c_int * 100)(*range(100))
        # Test accessing element at index 50 (offset = 50 * sizeof(c_int))
        offset = 50 * sizeof(c_int)
        ref = comtypes.util.byref_at(arr, offset)
        ptr = cast(ref, POINTER(c_int))
        self.assertEqual(ptr.contents.value, 50)

    def test_memory_safety(self):
        for initial in [111, 222, 333, 444]:
            with self.subTest(initial=initial):
                obj = c_int(initial)
                ref = comtypes.util.byref_at(obj, 0)
                ptr = cast(ref, POINTER(c_int))
                # Verify initial value
                self.assertEqual(ptr.contents.value, initial)
                # Modify original objects and verify references still work
                obj.value = 333
                # Verify reference still works after modification
                self.assertEqual(ptr.contents.value, 333)


class CastFieldTest(unittest.TestCase):
    def test_ctypes(self):
        class TestStruct(Structure):
            _fields_ = [
                ("int_field", c_int),
                ("double_field", c_double),
                ("char_field", c_char),
            ]

        struct = TestStruct(42, 3.14, b"X")
        for fname, ftype, expected in [
            ("int_field", c_int, 42),
            ("double_field", c_double, 3.14),
            ("char_field", c_char, b"X"),
        ]:
            with self.subTest(fname=fname, ftype=ftype):
                actual = comtypes.util.cast_field(struct, fname, ftype)
                self.assertEqual(actual, expected)

    def test_type_reinterpretation(self):
        class TestStruct(Structure):
            _fields_ = [
                ("data", c_int),
            ]

        # Create struct with known bit pattern
        struct = TestStruct(0x41424344)  # ASCII "ABCD" in little-endian
        # Cast the int field as a char array to see individual bytes
        char_value = comtypes.util.cast_field(struct, "data", c_char)
        # This should give us the first byte of the int
        self.assertIsInstance(char_value, bytes)

    def test_pointers(self):
        class TestStruct(Structure):
            _fields_ = [
                ("ptr_field", c_void_p),
                ("int_field", c_int),
            ]

        target_int = c_int(99)
        struct = TestStruct(addressof(target_int), 123)
        for fname, ftype, expected in [
            ("ptr_field", c_void_p, addressof(target_int)),
            ("int_field", c_int, 123),
        ]:
            with self.subTest(fname=fname, ftype=ftype, expected=expected):
                actual_value = comtypes.util.cast_field(struct, fname, ftype)
                self.assertEqual(actual_value, expected)

    def test_nested_structures(self):
        class InnerStruct(Structure):
            _fields_ = [
                ("inner_int", c_int),
                ("inner_char", c_char),
            ]

        class OuterStruct(Structure):
            _fields_ = [
                ("outer_int", c_int),
                ("inner", InnerStruct),
            ]

        inner = InnerStruct(456, b"Y")
        outer = OuterStruct(789, inner)
        # Cast the nested structure field
        inner_value = comtypes.util.cast_field(outer, "inner", InnerStruct)
        self.assertEqual(inner_value.inner_int, 456)
        self.assertEqual(inner_value.inner_char, b"Y")
        # Cast outer int field
        outer_int = comtypes.util.cast_field(outer, "outer_int", c_int)
        self.assertEqual(outer_int, 789)

    def test_arrays(self):
        class TestStruct(Structure):
            _fields_ = [
                ("int_array", c_int * 3),
                ("single_int", c_int),
            ]

        arr = (c_int * 3)(10, 20, 30)
        struct = TestStruct(arr, 40)
        # Cast array field as array type
        array_value = comtypes.util.cast_field(struct, "int_array", c_int * 3)
        self.assertEqual(list(array_value), [10, 20, 30])
        # Cast single int
        int_value = comtypes.util.cast_field(struct, "single_int", c_int)
        self.assertEqual(int_value, 40)

    def test_union(self):
        class TestUnion(Union):
            _fields_ = [
                ("as_int", c_int),
                ("as_bytes", c_byte * 4),
            ]

        class TestStruct(Structure):
            _fields_ = [
                ("union_field", TestUnion),
                ("regular_field", c_int),
            ]

        union_val = TestUnion()
        union_val.as_int = 0x41424344  # "ABCD" in ASCII
        struct = TestStruct(union_val, 999)
        union_result = comtypes.util.cast_field(struct, "union_field", TestUnion)
        self.assertEqual(union_result.as_int, 0x41424344)
        int_result = comtypes.util.cast_field(struct, "regular_field", c_int)
        self.assertEqual(int_result, 999)

    def test_void_p(self):
        class VTableLikeStruct(Structure):
            _fields_ = [
                ("QueryInterface", c_void_p),
                ("AddRef", c_void_p),
                ("Release", c_void_p),
                ("custom_method", c_void_p),
            ]

        # Initialize with some dummy pointers
        struct = VTableLikeStruct(0x1000, 0x2000, 0x3000, 0x4000)
        # Test accessing different entries
        for fname, expected in [
            ("QueryInterface", 0x1000),
            ("AddRef", 0x2000),
            ("Release", 0x3000),
            ("custom_method", 0x4000),
        ]:
            with self.subTest(fname=fname, expected=expected):
                ptr_value = comtypes.util.cast_field(struct, fname, c_void_p)
                self.assertEqual(ptr_value, expected)
