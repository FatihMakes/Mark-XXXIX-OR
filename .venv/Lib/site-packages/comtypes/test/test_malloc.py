import unittest as ut
from ctypes import HRESULT, POINTER, OleDLL, byref
from ctypes.wintypes import DWORD, HANDLE, LPWSTR
from pathlib import Path

from comtypes import GUID, hresult
from comtypes.malloc import CoGetMalloc, _CoTaskMemFree

# Constants
# KNOWNFOLDERID
# https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid
FOLDERID_System = GUID("{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}")
# https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/ne-shlobj_core-known_folder_flag
KF_FLAG_DEFAULT = 0x00000000

_shell32 = OleDLL("shell32")
_SHGetKnownFolderPath = _shell32.SHGetKnownFolderPath
_SHGetKnownFolderPath.argtypes = [
    POINTER(GUID),  # rfid
    DWORD,  # dwFlags
    HANDLE,  # hToken
    POINTER(LPWSTR),  # ppszPath
]
_SHGetKnownFolderPath.restype = HRESULT


class Test(ut.TestCase):
    def test_Realloc(self):
        malloc = CoGetMalloc()
        size1 = 4
        ptr1 = malloc.Alloc(size1)
        self.assertEqual(malloc.DidAlloc(ptr1), 1)
        self.assertEqual(malloc.GetSize(ptr1), size1)
        size2 = size1 - 1
        ptr2 = malloc.Realloc(ptr1, size2)
        self.assertEqual(malloc.DidAlloc(ptr2), 1)
        self.assertEqual(malloc.GetSize(ptr2), size2)
        size3 = size1 + 1
        ptr3 = malloc.Realloc(ptr2, size3)
        self.assertEqual(malloc.DidAlloc(ptr3), 1)
        self.assertEqual(malloc.GetSize(ptr3), size3)
        malloc.Free(ptr3)
        self.assertEqual(malloc.DidAlloc(ptr3), 0)
        malloc.HeapMinimize()
        del ptr3

    def test_SHGetKnownFolderPath(self):
        ptr = LPWSTR()
        hr = _SHGetKnownFolderPath(
            byref(FOLDERID_System), KF_FLAG_DEFAULT, None, byref(ptr)
        )
        self.assertEqual(hr, hresult.S_OK)
        self.assertIsInstance(ptr.value, str)
        self.assertTrue(Path(ptr.value).exists())  # type: ignore
        malloc = CoGetMalloc()
        self.assertEqual(malloc.DidAlloc(ptr), 1)
        self.assertGreater(malloc.GetSize(ptr), 0)
        _CoTaskMemFree(ptr)
        self.assertEqual(malloc.DidAlloc(ptr), 0)
        malloc.HeapMinimize()
        del ptr
