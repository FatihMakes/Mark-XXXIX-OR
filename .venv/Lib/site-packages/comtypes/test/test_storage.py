import ctypes
import os
import tempfile
import unittest
from _ctypes import COMError
from ctypes import HRESULT, POINTER, OleDLL, byref, c_ubyte
from ctypes.wintypes import DWORD, FILETIME, PWCHAR
from pathlib import Path
from typing import Optional

import comtypes
import comtypes.client
from comtypes.malloc import CoGetMalloc
from comtypes.test.time_structs_helper import (
    SYSTEMTIME,
    CompareFileTime,
    SystemTimeToFileTime,
)

comtypes.client.GetModule("portabledeviceapi.dll")
from comtypes.gen.PortableDeviceApiLib import WSTRING, IStorage, tagSTATSTG

STGTY_STORAGE = 1

STATFLAG_DEFAULT = 0
STATFLAG_NONAME = 1

STGC_DEFAULT = 0
STGM_CREATE = 0x00001000
STGM_DIRECT = 0x00000000
STGM_DELETEONRELEASE = 0x04000000
STGM_READ = 0x00000000
STGM_READWRITE = 0x00000002
STGM_SHARE_EXCLUSIVE = 0x00000010
STGM_TRANSACTED = 0x00010000
STGMOVE_MOVE = 0
STREAM_SEEK_SET = 0

STG_E_PATHNOTFOUND = -2147287038
STG_E_INVALIDFLAG = -2147286785
STG_E_ACCESSDENIED = -2147287035  # 0x80030005

_ole32 = OleDLL("ole32")

_StgCreateDocfile = _ole32.StgCreateDocfile
_StgCreateDocfile.argtypes = [PWCHAR, DWORD, DWORD, POINTER(POINTER(IStorage))]
_StgCreateDocfile.restype = HRESULT


def _get_pwcsname(stat: tagSTATSTG) -> WSTRING:
    return WSTRING.from_address(ctypes.addressof(stat) + tagSTATSTG.pwcsName.offset)


RW_EXCLUSIVE = STGM_READWRITE | STGM_SHARE_EXCLUSIVE
RW_EXCLUSIVE_TX = RW_EXCLUSIVE | STGM_TRANSACTED
RW_EXCLUSIVE_CREATE = RW_EXCLUSIVE | STGM_CREATE
CREATE_TESTDOC = STGM_DIRECT | STGM_CREATE | RW_EXCLUSIVE
CREATE_TEMP_TESTDOC = CREATE_TESTDOC | STGM_DELETEONRELEASE


def _create_docfile(mode: int, name: Optional[str] = None) -> IStorage:
    stg = POINTER(IStorage)()
    _StgCreateDocfile(name, mode, 0, byref(stg))
    return stg  # type: ignore


FIXED_TEST_FILETIME = SystemTimeToFileTime(SYSTEMTIME(wYear=2000, wMonth=1, wDay=1))


class Test_CreateStream(unittest.TestCase):
    def test_creates_and_writes_to_stream_in_docfile(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        # When created with `StgCreateDocfile(NULL, ...)`, `pwcsName` is a
        # temporary filename. The file really exists on disk because Windows
        # creates an actual temporary file for the compound storage.
        stat = storage.Stat(STATFLAG_DEFAULT)
        filepath = Path(stat.pwcsName)
        self.assertTrue(filepath.exists())
        stream = storage.CreateStream("example", RW_EXCLUSIVE_CREATE, 0, 0)
        test_data = b"Some data"
        pv = (c_ubyte * len(test_data)).from_buffer(bytearray(test_data))
        stream.RemoteWrite(pv, len(test_data))
        stream.Commit(STGC_DEFAULT)
        stream.RemoteSeek(0, STREAM_SEEK_SET)
        read_buffer, data_read = stream.RemoteRead(1024)
        self.assertEqual(bytearray(read_buffer)[0:data_read], test_data)
        storage.Commit(STGC_DEFAULT)
        self.assertTrue(filepath.exists())
        del storage
        self.assertFalse(filepath.exists())
        name_ptr = _get_pwcsname(stat)
        self.assertEqual(name_ptr.value, stat.pwcsName)
        malloc = CoGetMalloc()
        self.assertEqual(malloc.DidAlloc(name_ptr), 1)
        del stat  # `pwcsName` is expected to be freed here.
        # `DidAlloc` checks are skipped to avoid using a dangling pointer.


# TODO: Auto-generated methods based on type info are remote-side and hard
#       to call from the client.
#       If a proper invocation method or workaround is found, testing
#       becomes possible.
#       See: https://github.com/enthought/comtypes/issues/607
# class Test_RemoteOpenStream(unittest.TestCase):
#     def test_RemoteOpenStream(self):
#         pass


class Test_CreateStorage(unittest.TestCase):
    def test_creates_child_storage_in_parent(self):
        parent = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        child = parent.CreateStorage("child", RW_EXCLUSIVE_TX, 0, 0)
        self.assertEqual("child", child.Stat(STATFLAG_DEFAULT).pwcsName)


class Test_OpenStorage(unittest.TestCase):
    def test_opens_existing_child_storage(self):
        parent = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        with self.assertRaises(COMError) as cm:
            parent.OpenStorage("child", None, RW_EXCLUSIVE_TX, None, 0)
        self.assertEqual(cm.exception.hresult, STG_E_PATHNOTFOUND)
        parent.CreateStorage("child", RW_EXCLUSIVE_TX, 0, 0)
        child = parent.OpenStorage("child", None, RW_EXCLUSIVE_TX, None, 0)
        self.assertEqual("child", child.Stat(STATFLAG_DEFAULT).pwcsName)


class Test_RemoteCopyTo(unittest.TestCase):
    def test_copies_storage_content_to_destination(self):
        src_stg = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        src_stg.CreateStorage("child", RW_EXCLUSIVE_TX, 0, 0)
        dst_stg = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        src_stg.RemoteCopyTo(0, None, None, dst_stg)
        src_stg.Commit(STGC_DEFAULT)
        del src_stg
        opened_stg = dst_stg.OpenStorage("child", None, RW_EXCLUSIVE_TX, None, 0)
        self.assertEqual("child", opened_stg.Stat(STATFLAG_DEFAULT).pwcsName)


class Test_MoveElementTo(unittest.TestCase):
    def test_moves_element_to_new_location_and_renames(self):
        src_stg = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        src_stg.CreateStorage("foo", RW_EXCLUSIVE_TX, 0, 0)
        dst_stg = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        src_stg.MoveElementTo("foo", dst_stg, "bar", STGMOVE_MOVE)
        opened_stg = dst_stg.OpenStorage("bar", None, RW_EXCLUSIVE_TX, None, 0)
        self.assertEqual("bar", opened_stg.Stat(STATFLAG_DEFAULT).pwcsName)
        with self.assertRaises(COMError) as cm:
            src_stg.OpenStorage("foo", None, RW_EXCLUSIVE_TX, None, 0)
        self.assertEqual(cm.exception.hresult, STG_E_PATHNOTFOUND)


class Test_Revert(unittest.TestCase):
    def test_reverts_pending_changes_to_storage(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        foo = storage.CreateStorage("foo", RW_EXCLUSIVE_TX, 0, 0)
        foo.CreateStorage("bar", RW_EXCLUSIVE_TX, 0, 0)
        bar = foo.OpenStorage("bar", None, RW_EXCLUSIVE_TX, None, 0)
        self.assertEqual("bar", bar.Stat(STATFLAG_DEFAULT).pwcsName)
        foo.Revert()
        with self.assertRaises(COMError) as cm:
            foo.OpenStorage("bar", None, RW_EXCLUSIVE_TX, None, 0)
        self.assertEqual(cm.exception.hresult, STG_E_PATHNOTFOUND)


# TODO: Auto-generated methods based on type info are remote-side and hard
#       to call from the client.
#       If a proper invocation method or workaround is found, testing
#       becomes possible.
#       See: https://github.com/enthought/comtypes/issues/607
# class Test_RemoteEnumElements(unittest.TestCase):
#     def test_RemoteEnumElements(self):
#         pass


class Test_DestroyElement(unittest.TestCase):
    def test_destroys_existing_element_in_storage(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        storage.CreateStorage("example", RW_EXCLUSIVE_TX, 0, 0)
        storage.DestroyElement("example")
        with self.assertRaises(COMError) as cm:
            storage.OpenStorage("example", None, RW_EXCLUSIVE_TX, None, 0)
        self.assertEqual(cm.exception.hresult, STG_E_PATHNOTFOUND)

    def test_fails_to_destroy_non_existent_element(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        with self.assertRaises(COMError) as cm:
            storage.DestroyElement("non_existent")
        self.assertEqual(cm.exception.hresult, STG_E_PATHNOTFOUND)


class Test_RenameElement(unittest.TestCase):
    def test_renames_element_in_storage(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        storage.CreateStorage("example", RW_EXCLUSIVE_TX, 0, 0)
        storage.RenameElement("example", "sample")
        sample = storage.OpenStorage("sample", None, RW_EXCLUSIVE_TX, None, 0)
        self.assertEqual("sample", sample.Stat(STATFLAG_DEFAULT).pwcsName)
        with self.assertRaises(COMError) as cm:
            storage.OpenStorage("example", None, RW_EXCLUSIVE_TX, None, 0)
        self.assertEqual(cm.exception.hresult, STG_E_PATHNOTFOUND)

    def test_fails_if_destination_exists(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        storage.CreateStorage("foo", RW_EXCLUSIVE_TX, 0, 0)
        storage.CreateStorage("bar", RW_EXCLUSIVE_TX, 0, 0)
        # Rename "foo" to "bar" (which already exists)
        with self.assertRaises(COMError) as cm:
            storage.RenameElement("foo", "bar")
        self.assertEqual(cm.exception.hresult, STG_E_ACCESSDENIED)

    def test_fails_if_takes_same_name(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        storage.CreateStorage("foo", RW_EXCLUSIVE_TX, 0, 0)
        # Rename "foo" to "foo" (same name)
        with self.assertRaises(COMError) as cm:
            storage.RenameElement("foo", "foo")
        self.assertEqual(cm.exception.hresult, STG_E_ACCESSDENIED)


class Test_SetElementTimes(unittest.TestCase):
    def test_sets_modification_time_for_element(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        sub_name = "SubStorageElement"
        orig_stat = storage.CreateStorage(sub_name, CREATE_TESTDOC, 0, 0).Stat(
            STATFLAG_DEFAULT
        )
        storage.SetElementTimes(
            sub_name,
            None,  # pctime (creation time)
            None,  # patime (access time)
            FIXED_TEST_FILETIME,  # pmtime (modification time)
        )
        storage.Commit(STGC_DEFAULT)
        modified_stat = storage.OpenStorage(
            sub_name, None, RW_EXCLUSIVE_TX, None, 0
        ).Stat(STATFLAG_DEFAULT)
        self.assertEqual(CompareFileTime(orig_stat.ctime, modified_stat.ctime), 0)
        self.assertEqual(CompareFileTime(orig_stat.atime, modified_stat.atime), 0)
        self.assertNotEqual(CompareFileTime(orig_stat.mtime, modified_stat.mtime), 0)
        self.assertEqual(CompareFileTime(FIXED_TEST_FILETIME, modified_stat.mtime), 0)
        with self.assertRaises(COMError) as cm:
            storage.SetElementTimes("NonExistent", None, None, FIXED_TEST_FILETIME)
        self.assertEqual(cm.exception.hresult, STG_E_PATHNOTFOUND)


class Test_SetClass(unittest.TestCase):
    def test_sets_clsid(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        # Initial value is CLSID_NULL.
        self.assertEqual(storage.Stat(STATFLAG_DEFAULT).clsid, comtypes.GUID())
        new_clsid = comtypes.GUID.create_new()
        storage.SetClass(new_clsid)
        self.assertEqual(storage.Stat(STATFLAG_DEFAULT).clsid, new_clsid)
        # Re-set CLSID to CLSID_NULL and verify it is correctly set.
        storage.SetClass(comtypes.GUID())
        self.assertEqual(storage.Stat(STATFLAG_DEFAULT).clsid, comtypes.GUID())


class Test_SetStateBits(unittest.TestCase):
    def test_sets_and_updates_storage_state_bits(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        # Initial state bits should be 0
        self.assertEqual(storage.Stat(STATFLAG_DEFAULT).grfStateBits, 0)
        # 1. Set all bits
        bits1, mask1 = 0xABCD1234, 0xFFFFFFFF
        storage.SetStateBits(bits1, mask1)
        self.assertEqual(storage.Stat(STATFLAG_DEFAULT).grfStateBits, bits1)
        # 2. Partial update using mask (only lower 16 bits)
        bits2, mask2 = 0x00005678, 0x0000FFFF
        storage.SetStateBits(bits2, mask2)
        # Expected: 0xABCD (original upper) + 0x5678 (new lower) = 0xABCD5678
        self.assertEqual(storage.Stat(STATFLAG_DEFAULT).grfStateBits, 0xABCD5678)


class Test_Stat(unittest.TestCase):
    def test_returns_correct_stat_information_for_docfile(self):
        with tempfile.TemporaryDirectory() as t:
            tmpdir = Path(t)
            tmpfile = tmpdir / "test_docfile.cfs"
            self.assertFalse(tmpfile.exists())
            # When created with `StgCreateDocfile(filepath_string, ...)`, the
            # compound file is created at that location.
            storage = _create_docfile(name=str(tmpfile), mode=CREATE_TEMP_TESTDOC)
            self.assertTrue(tmpfile.exists())
            with self.assertRaises(COMError) as cm:
                storage.Stat(0xFFFFFFFF)  # Invalid flag
            self.assertEqual(cm.exception.hresult, STG_E_INVALIDFLAG)
            stat = storage.Stat(STATFLAG_DEFAULT)
            self.assertIsInstance(stat, tagSTATSTG)
            del storage  # Release the storage to prevent 'cannot access the file ...'
        # Validate each field:
        self.assertEqual(
            os.path.normcase(os.path.normpath(Path(stat.pwcsName))),
            os.path.normcase(os.path.normpath(tmpfile)),
        )
        self.assertEqual(stat.type, STGTY_STORAGE)
        # Timestamps (`mtime`, `ctime`, `atime`) are set by the underlying
        # compound file implementation.
        # In many cases (especially on modern Windows with NTFS), all three
        # timestamps are set to the same value at creation time. However, this
        # is not guaranteed by the OLE32 specification.
        # Therefore, we only verify that each timestamp is a valid `FILETIME`
        # (non-zero is sufficient for a newly created file).
        zero_ft = FILETIME()
        self.assertNotEqual(CompareFileTime(stat.ctime, zero_ft), 0)
        self.assertNotEqual(CompareFileTime(stat.atime, zero_ft), 0)
        self.assertNotEqual(CompareFileTime(stat.mtime, zero_ft), 0)
        # Due to header overhead and file system allocation, the size may be
        # greater than 0 bytes.
        self.assertGreaterEqual(stat.cbSize, 0)
        # `grfMode` should reflect the access mode flags from creation.
        self.assertEqual(stat.grfMode, RW_EXCLUSIVE | STGM_DIRECT)
        self.assertEqual(stat.grfLocksSupported, 0)
        self.assertEqual(stat.clsid, comtypes.GUID())  # CLSID_NULL for new creation.
        self.assertEqual(stat.grfStateBits, 0)
        name_ptr = _get_pwcsname(stat)
        self.assertEqual(name_ptr.value, stat.pwcsName)
        malloc = CoGetMalloc()
        self.assertEqual(malloc.DidAlloc(name_ptr), 1)
        del stat  # `pwcsName` is expected to be freed here.
        # `DidAlloc` checks are skipped to avoid using a dangling pointer.

    def test_stat_returns_none_for_pwcsname_with_noname_flag(self):
        storage = _create_docfile(mode=CREATE_TEMP_TESTDOC)
        # Using `STATFLAG_NONAME` should return `None` for `pwcsName`.
        stat = storage.Stat(STATFLAG_NONAME)
        self.assertIsNone(stat.pwcsName)
        # Verify other fields are still present.
        self.assertEqual(stat.type, STGTY_STORAGE)
