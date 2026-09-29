import logging
import unittest
from ctypes import (
    c_wchar,
    c_wchar_p,
    cast,
    create_unicode_buffer,
    memmove,
    sizeof,
    wstring_at,
)
from unittest.mock import patch

from comtypes.malloc import CoGetMalloc, _CoTaskMemAlloc, _CoTaskMemFree

logger = logging.getLogger(__name__)


malloc = CoGetMalloc()
assert bool(malloc)


def from_outparam(self):
    if not self:
        return None
    result = wstring_at(self)
    # `DidAlloc` method returns;
    # *  1 (allocated)
    # *  0 (not allocated)
    # * -1 (cannot determine or NULL)
    # https://learn.microsoft.com/en-us/windows/win32/api/objidl/nf-objidl-imalloc-didalloc
    assert malloc.DidAlloc(self), "memory was NOT allocated by CoTaskMemAlloc"
    _CoTaskMemFree(self)
    return result


def comstring(text, typ=c_wchar_p):
    size = (len(text) + 1) * sizeof(c_wchar)
    mem = _CoTaskMemAlloc(size)
    logger.debug("malloc'd 0x%x, %d bytes" % (mem, size))
    ptr = cast(mem, typ)
    memmove(mem, text, size)
    return ptr


class Test(unittest.TestCase):
    @patch.object(c_wchar_p, "__ctypes_from_outparam__", from_outparam)
    def test_c_char(self):
        # Allocate memory from the Python/C runtime heap.
        # This ensures the address is valid but "unallocated" from COM.
        buf = create_unicode_buffer("abc")
        ptr = cast(buf, c_wchar_p)
        # Confirm the memory is not managed by the COM task allocator.
        self.assertEqual(malloc.DidAlloc(ptr), 0)

        x = comstring("Hello, World")
        y = comstring("foo bar")
        z = comstring("spam, spam, and spam")

        # The `__ctypes_from_outparam__` method is called to convert an output
        # parameter into a Python object. In this test, the custom
        # `from_outparam` function not only converts the `c_wchar_p` to a
        # Python string but also frees the associated memory. Therefore, it can
        # only be called once for each allocated memory block.
        for wchar_ptr, expected in [
            (x, "Hello, World"),
            (y, "foo bar"),
            (z, "spam, spam, and spam"),
        ]:
            with self.subTest(wchar_ptr=wchar_ptr, expected=expected):
                self.assertEqual(malloc.DidAlloc(wchar_ptr), 1)
                self.assertEqual(wchar_ptr.__ctypes_from_outparam__(), expected)
                self.assertEqual(malloc.DidAlloc(wchar_ptr), 0)


if __name__ == "__main__":
    unittest.main()
