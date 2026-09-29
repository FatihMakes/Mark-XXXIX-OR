import contextlib
import ctypes
import os
import tempfile
import time
import unittest
from _ctypes import COMError
from ctypes import POINTER, WinDLL, byref
from ctypes.wintypes import DWORD, LPCWSTR, LPWSTR, MAX_PATH
from pathlib import Path

from comtypes import GUID, IUnknown, hresult
from comtypes.client import CreateObject, GetModule
from comtypes.persist import IPersistFile
from comtypes.test.monikers_helper import (
    MK_E_NEEDGENERIC,
    MK_E_NOINVERSE,
    MK_E_SYNTAX,
    MKSYS_ANTIMONIKER,
    MKSYS_CLASSMONIKER,
    MKSYS_FILEMONIKER,
    MKSYS_GENERICCOMPOSITE,
    MKSYS_ITEMMONIKER,
    MKSYS_OBJREFMONIKER,
    MKSYS_POINTERMONIKER,
    ROTFLAGS_ALLOWANYCLIENT,
    CLSID_AntiMoniker,
    CLSID_ClassMoniker,
    CLSID_CompositeMoniker,
    CLSID_FileMoniker,
    CLSID_ItemMoniker,
    CLSID_ObjrefMoniker,
    CLSID_PointerMoniker,
    _CreateAntiMoniker,
    _CreateBindCtx,
    _CreateClassMoniker,
    _CreateFileMoniker,
    _CreateGenericComposite,
    _CreateItemMoniker,
    _CreateObjrefMoniker,
    _CreatePointerMoniker,
    _GetRunningObjectTable,
)
from comtypes.test.time_structs_helper import CompareFileTime

with contextlib.redirect_stdout(None):  # supress warnings
    GetModule("msvidctl.dll")
from comtypes.gen import MSVidCtlLib as msvidctl
from comtypes.gen.MSVidCtlLib import (
    IBindCtx,
    IEnumMoniker,
    IMoniker,
    IRunningObjectTable,
)

_kernel32 = WinDLL("kernel32")

_GetLongPathNameW = _kernel32.GetLongPathNameW
_GetLongPathNameW.argtypes = [LPCWSTR, LPWSTR, DWORD]
_GetLongPathNameW.restype = DWORD


def _get_long_path_name(path: str) -> str:
    """Converts a path to its long form using GetLongPathNameW."""
    buffer = ctypes.create_unicode_buffer(MAX_PATH)
    length = _GetLongPathNameW(path, buffer, MAX_PATH)
    return buffer.value[:length]


def _create_generic_composite(mk_first: IMoniker, mk_rest: IMoniker) -> IMoniker:
    mon = POINTER(IMoniker)()
    _CreateGenericComposite(mk_first, mk_rest, byref(mon))
    return mon  # type: ignore


def _create_anti_moniker() -> IMoniker:
    mon = POINTER(IMoniker)()
    _CreateAntiMoniker(byref(mon))
    return mon  # type: ignore


def _create_file_moniker(path: str) -> IMoniker:
    mon = POINTER(IMoniker)()
    _CreateFileMoniker(path, byref(mon))
    return mon  # type: ignore


def _create_item_moniker(delim: str, item: str) -> IMoniker:
    mon = POINTER(IMoniker)()
    _CreateItemMoniker(delim, item, byref(mon))
    return mon  # type: ignore


def _create_pointer_moniker(punk: IUnknown) -> IMoniker:
    mon = POINTER(IMoniker)()
    # `punk` must be an instance of `POINTER(IUnknown)`.
    _CreatePointerMoniker(punk, byref(mon))
    return mon  # type: ignore


def _create_class_moniker(clsid: GUID) -> IMoniker:
    mon = POINTER(IMoniker)()
    _CreateClassMoniker(byref(clsid), byref(mon))
    return mon  # type: ignore


def _create_objref_moniker(punk: IUnknown) -> IMoniker:
    mon = POINTER(IMoniker)()
    _CreateObjrefMoniker(punk, byref(mon))
    return mon  # type: ignore


def _create_bctx() -> IBindCtx:
    bctx = POINTER(IBindCtx)()
    # The first parameter is reserved and must be 0.
    _CreateBindCtx(0, byref(bctx))
    return bctx  # type: ignore


def _create_rot() -> IRunningObjectTable:
    rot = POINTER(IRunningObjectTable)()
    # The first parameter is reserved and must be 0.
    _GetRunningObjectTable(0, byref(rot))
    return rot  # type: ignore


class Test_IsSystemMoniker_GetDisplayName_Inverse(unittest.TestCase):
    def test_generic_composite(self):
        item_id1 = str(GUID.create_new())
        item_id2 = str(GUID.create_new())
        mon = _create_generic_composite(
            _create_item_moniker("!", item_id1),
            _create_item_moniker("!", item_id2),
        )
        self.assertEqual(mon.IsSystemMoniker(), MKSYS_GENERICCOMPOSITE)
        bctx = _create_bctx()
        self.assertEqual(mon.GetDisplayName(bctx, None), f"!{item_id1}!{item_id2}")
        self.assertEqual(mon.GetClassID(), CLSID_CompositeMoniker)
        self.assertEqual(mon.Inverse().GetClassID(), CLSID_CompositeMoniker)

    def test_file(self):
        with tempfile.NamedTemporaryFile() as f:
            mon = _create_file_moniker(f.name)
            self.assertEqual(mon.IsSystemMoniker(), MKSYS_FILEMONIKER)
            bctx = _create_bctx()
            self.assertEqual(
                os.path.normcase(
                    os.path.normpath(
                        _get_long_path_name(mon.GetDisplayName(bctx, None))
                    )
                ),
                os.path.normcase(os.path.normpath(_get_long_path_name(f.name))),
            )
            self.assertEqual(mon.GetClassID(), CLSID_FileMoniker)
            self.assertEqual(mon.Inverse().GetClassID(), CLSID_AntiMoniker)

    def test_anti(self):
        mon = _create_anti_moniker()
        self.assertEqual(mon.IsSystemMoniker(), MKSYS_ANTIMONIKER)
        bctx = _create_bctx()
        self.assertEqual(mon.GetDisplayName(bctx, None), "\\..")
        self.assertEqual(mon.GetClassID(), CLSID_AntiMoniker)
        # Anti-moniker has NO inverse.
        with self.assertRaises(COMError) as cm:
            mon.Inverse()
        self.assertEqual(cm.exception.hresult, MK_E_NOINVERSE)

    def test_item(self):
        item_id = str(GUID.create_new())
        mon = _create_item_moniker("!", item_id)
        self.assertEqual(mon.IsSystemMoniker(), MKSYS_ITEMMONIKER)
        bctx = _create_bctx()
        self.assertEqual(mon.GetDisplayName(bctx, None), f"!{item_id}")
        self.assertEqual(mon.GetClassID(), CLSID_ItemMoniker)
        self.assertEqual(mon.Inverse().GetClassID(), CLSID_AntiMoniker)

    def test_pointer(self):
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        mon = _create_pointer_moniker(vidctl)
        self.assertEqual(mon.IsSystemMoniker(), MKSYS_POINTERMONIKER)
        bctx = _create_bctx()
        with self.assertRaises(COMError) as cm:
            mon.GetDisplayName(bctx, None)
        self.assertEqual(cm.exception.hresult, hresult.E_NOTIMPL)
        self.assertEqual(mon.GetClassID(), CLSID_PointerMoniker)
        self.assertEqual(mon.Inverse().GetClassID(), CLSID_AntiMoniker)

    def test_class(self):
        clsid = GUID.create_new()
        mon = _create_class_moniker(clsid)
        self.assertEqual(mon.IsSystemMoniker(), MKSYS_CLASSMONIKER)
        bctx = _create_bctx()
        self.assertEqual(
            mon.GetDisplayName(bctx, None), f"clsid:{str(clsid).strip('{}')}:"
        )
        self.assertEqual(mon.GetClassID(), CLSID_ClassMoniker)
        self.assertEqual(mon.Inverse().GetClassID(), CLSID_AntiMoniker)

    def test_objref(self):
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        mon = _create_objref_moniker(vidctl)
        self.assertEqual(mon.IsSystemMoniker(), MKSYS_OBJREFMONIKER)
        bctx = _create_bctx()
        self.assertTrue(mon.GetDisplayName(bctx, None).startswith("objref:"))
        self.assertEqual(mon.GetClassID(), CLSID_ObjrefMoniker)
        self.assertEqual(mon.Inverse().GetClassID(), CLSID_AntiMoniker)


class Test_ComposeWith(unittest.TestCase):
    def test_generic_composite_with_same_type(self):
        item_id1 = str(GUID.create_new())
        item_id2 = str(GUID.create_new())
        item_id3 = str(GUID.create_new())
        item_id4 = str(GUID.create_new())
        left_mon = _create_generic_composite(
            _create_item_moniker("!", item_id1),
            _create_item_moniker("!", item_id2),
        )
        right_mon = _create_generic_composite(
            _create_item_moniker("!", item_id3),
            _create_item_moniker("!", item_id4),
        )
        comp_mon = left_mon.ComposeWith(right_mon, False)
        self.assertEqual(comp_mon.GetClassID(), CLSID_CompositeMoniker)
        self.assertEqual(
            comp_mon.GetDisplayName(_create_bctx(), None),
            f"!{item_id1}!{item_id2}!{item_id3}!{item_id4}",
        )
        with self.assertRaises(COMError) as cm:
            left_mon.ComposeWith(right_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)

    def test_generic_composite_with_item(self):
        item_id1 = str(GUID.create_new())
        item_id2 = str(GUID.create_new())
        item_id3 = str(GUID.create_new())
        orig_mon = _create_generic_composite(
            _create_item_moniker("!", item_id1),
            _create_item_moniker("!", item_id2),
        )
        item_mon = _create_item_moniker("!", item_id3)
        bctx = _create_bctx()
        comp_with_item = orig_mon.ComposeWith(item_mon, False)
        self.assertEqual(comp_with_item.GetClassID(), CLSID_CompositeMoniker)
        self.assertEqual(
            comp_with_item.GetDisplayName(bctx, None),
            f"!{item_id1}!{item_id2}!{item_id3}",
        )
        item_with_comp = item_mon.ComposeWith(orig_mon, False)
        self.assertEqual(item_with_comp.GetClassID(), CLSID_CompositeMoniker)
        self.assertEqual(
            item_with_comp.GetDisplayName(bctx, None),
            f"!{item_id3}!{item_id1}!{item_id2}",
        )
        with self.assertRaises(COMError) as cm:
            orig_mon.ComposeWith(item_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)
        with self.assertRaises(COMError) as cm:
            item_mon.ComposeWith(orig_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)

    def test_file_with_same_type(self):
        with tempfile.TemporaryDirectory() as t:
            tmpdir = Path(t)
            tmpfile = tmpdir / "tmp.txt"
            left_mon = _create_file_moniker(str(tmpfile))
            # Composing two distinct absolute file monikers results in error.
            for right_mon, only_if_not_generic in [
                (_create_file_moniker(str(tmpfile)), False),
                (_create_file_moniker(str(tmpfile)), True),
                (_create_file_moniker(str(tmpdir / "tmp2.txt")), False),
                (_create_file_moniker(str(tmpdir / "tmp2.txt")), True),
            ]:
                with self.assertRaises(COMError) as cm:
                    left_mon.ComposeWith(right_mon, only_if_not_generic)
                self.assertEqual(cm.exception.hresult, MK_E_SYNTAX)

    def test_anti_with_same_type(self):
        left_mon = _create_anti_moniker()
        right_mon = _create_anti_moniker()
        self.assertEqual(
            left_mon.ComposeWith(right_mon, False).GetClassID(),
            CLSID_CompositeMoniker,
        )
        with self.assertRaises(COMError) as cm:
            left_mon.ComposeWith(right_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)

    def test_anti_with_generic_composite(self):
        item_id1 = str(GUID.create_new())
        item_id2 = str(GUID.create_new())
        orig_mon = _create_generic_composite(
            _create_item_moniker("!", item_id1),
            _create_item_moniker("!", item_id2),
        )
        bctx = _create_bctx()
        comp_with_anti = orig_mon.ComposeWith(_create_anti_moniker(), False)
        self.assertEqual(comp_with_anti.GetClassID(), CLSID_ItemMoniker)
        self.assertEqual(comp_with_anti.GetDisplayName(bctx, None), f"!{item_id1}")
        anti_with_comp = _create_anti_moniker().ComposeWith(orig_mon, False)
        self.assertEqual(anti_with_comp.GetClassID(), CLSID_CompositeMoniker)
        self.assertEqual(
            anti_with_comp.GetDisplayName(bctx, None), f"\\..!{item_id1}!{item_id2}"
        )
        with self.assertRaises(COMError) as cm:
            orig_mon.ComposeWith(_create_anti_moniker(), True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)
        with self.assertRaises(COMError) as cm:
            _create_anti_moniker().ComposeWith(orig_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)

    def test_anti_with_file(self):
        anti_mon = _create_anti_moniker()
        with tempfile.TemporaryDirectory() as t:
            tmpdir = Path(t)
            tmpfile = tmpdir / "tmp.txt"
            file_mon = _create_file_moniker(str(tmpfile))
            # https://learn.microsoft.com/en-us/windows/win32/api/objidl/nf-objidl-imoniker-composewith#implementation-specific-notes
            comp_mon = anti_mon.ComposeWith(file_mon, False)
            self.assertEqual(comp_mon.IsSystemMoniker(), MKSYS_GENERICCOMPOSITE)
            self.assertEqual(comp_mon.GetClassID(), CLSID_CompositeMoniker)
            self.assertEqual(
                comp_mon.GetDisplayName(_create_bctx(), None), f"\\..{tmpfile}"
            )
            with self.assertRaises(COMError) as cm:
                anti_mon.ComposeWith(file_mon, True)
            self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)
            self.assertFalse(file_mon.ComposeWith(anti_mon, False))
            self.assertFalse(file_mon.ComposeWith(anti_mon, True))

    def test_anti_with_item(self):
        anti_mon = _create_anti_moniker()
        item_mon = _create_item_moniker("!", str(GUID.create_new()))
        self.assertEqual(
            anti_mon.ComposeWith(item_mon, False).GetClassID(),
            CLSID_CompositeMoniker,
        )
        with self.assertRaises(COMError) as cm:
            anti_mon.ComposeWith(item_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)
        self.assertFalse(item_mon.ComposeWith(anti_mon, False))
        self.assertFalse(item_mon.ComposeWith(anti_mon, True))

    def test_anti_with_pointer(self):
        anti_mon = _create_anti_moniker()
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        pointer_mon = _create_pointer_moniker(vidctl)
        self.assertFalse(pointer_mon.ComposeWith(anti_mon, False))
        self.assertFalse(pointer_mon.ComposeWith(anti_mon, True))
        self.assertEqual(
            anti_mon.ComposeWith(pointer_mon, False).GetClassID(),
            CLSID_CompositeMoniker,
        )
        with self.assertRaises(COMError) as cm:
            anti_mon.ComposeWith(pointer_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)

    def test_anti_with_class(self):
        anti_mon = _create_anti_moniker()
        class_mon = _create_class_moniker(GUID.create_new())
        self.assertFalse(class_mon.ComposeWith(anti_mon, False))
        self.assertFalse(class_mon.ComposeWith(anti_mon, True))
        self.assertEqual(
            anti_mon.ComposeWith(class_mon, False).GetClassID(),
            CLSID_CompositeMoniker,
        )
        with self.assertRaises(COMError) as cm:
            anti_mon.ComposeWith(class_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)

    def test_anti_with_objref(self):
        anti_mon = _create_anti_moniker()
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        objref_mon = _create_objref_moniker(vidctl)
        self.assertFalse(objref_mon.ComposeWith(anti_mon, False))
        self.assertFalse(objref_mon.ComposeWith(anti_mon, True))
        self.assertEqual(
            anti_mon.ComposeWith(objref_mon, False).GetClassID(),
            CLSID_CompositeMoniker,
        )
        with self.assertRaises(COMError) as cm:
            anti_mon.ComposeWith(objref_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)

    def test_item_with_same_type(self):
        left_id = str(GUID.create_new())
        left_mon = _create_item_moniker("!", left_id)
        right_id = str(GUID.create_new())
        right_mon = _create_item_moniker("!", right_id)
        comp_mon = left_mon.ComposeWith(right_mon, False)
        self.assertEqual(comp_mon.IsSystemMoniker(), MKSYS_GENERICCOMPOSITE)
        self.assertEqual(comp_mon.GetClassID(), CLSID_CompositeMoniker)
        self.assertEqual(
            comp_mon.GetDisplayName(_create_bctx(), None), f"!{left_id}!{right_id}"
        )
        with self.assertRaises(COMError) as cm:
            left_mon.ComposeWith(right_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)

    def test_pointer_with_same_type(self):
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        left_mon = _create_pointer_moniker(vidctl)
        right_mon = _create_pointer_moniker(vidctl)
        self.assertEqual(
            left_mon.ComposeWith(right_mon, False).GetClassID(),
            CLSID_CompositeMoniker,
        )
        with self.assertRaises(COMError) as cm:
            left_mon.ComposeWith(right_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)

    def test_class_with_same_type(self):
        clsid = GUID.create_new()
        left_mon = _create_class_moniker(clsid)
        right_mon = _create_class_moniker(GUID.create_new())
        self.assertEqual(
            left_mon.ComposeWith(right_mon, False).GetClassID(),
            CLSID_CompositeMoniker,
        )
        with self.assertRaises(COMError) as cm:
            left_mon.ComposeWith(right_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)

    def test_objref_with_same_type(self):
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        left_mon = _create_objref_moniker(vidctl)
        right_mon = _create_objref_moniker(vidctl)
        self.assertEqual(
            left_mon.ComposeWith(right_mon, False).GetClassID(),
            CLSID_CompositeMoniker,
        )
        with self.assertRaises(COMError) as cm:
            left_mon.ComposeWith(right_mon, True)
        self.assertEqual(cm.exception.hresult, MK_E_NEEDGENERIC)


class Test_IsEqual(unittest.TestCase):
    def test_item(self):
        item_id = str(GUID.create_new())
        mon1 = _create_item_moniker("!", item_id)
        mon2 = _create_item_moniker("!", item_id)  # Should be equal
        mon3 = _create_item_moniker("!", str(GUID.create_new()))  # Should not be equal
        self.assertEqual(mon1.IsEqual(mon2), hresult.S_OK)
        self.assertEqual(mon1.IsEqual(mon3), hresult.S_FALSE)


class Test_Hash(unittest.TestCase):
    def test_item(self):
        item_id = str(GUID.create_new())
        mon1 = _create_item_moniker("!", item_id)
        mon2 = _create_item_moniker("!", item_id)  # Should be equal
        mon3 = _create_item_moniker("!", str(GUID.create_new()))  # Should not be equal
        self.assertEqual(mon1.Hash(), mon2.Hash())
        self.assertNotEqual(mon1.Hash(), mon3.Hash())
        self.assertNotEqual(mon2.Hash(), mon3.Hash())


class Test_IsRunning(unittest.TestCase):
    def test_item(self):
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        item_id = str(GUID.create_new())
        mon = _create_item_moniker("!", item_id)
        rot = _create_rot()
        bctx = _create_bctx()
        # Before registering: should NOT be running
        self.assertEqual(mon.IsRunning(bctx, None, None), hresult.S_FALSE)
        dw_reg = rot.Register(ROTFLAGS_ALLOWANYCLIENT, vidctl, mon)
        # After registering: should be running
        self.assertEqual(mon.IsRunning(bctx, None, None), hresult.S_OK)
        rot.Revoke(dw_reg)
        # After revoking: should NOT be running again
        self.assertEqual(mon.IsRunning(bctx, None, None), hresult.S_FALSE)


class Test_GetTimeOfLastChange(unittest.TestCase):
    def test_file(self):
        bctx = _create_bctx()
        with tempfile.NamedTemporaryFile() as f:
            tmpfile = Path(f.name)
            f.write(b"test data")
            # Create a File Moniker for the temporary file
            file_mon = _create_file_moniker(str(tmpfile))
            # Get initial time of last change for the file
            initial_ft = file_mon.GetTimeOfLastChange(bctx, None)
            # Modify the file to change its last write time
            time.sleep(0.01)  # Ensure a different timestamp
            os.write(f.fileno(), b"more data")
            after_change_ft = file_mon.GetTimeOfLastChange(bctx, None)
            # Verify the time has changed (after_change_ft > initial_ft)
            self.assertEqual(CompareFileTime(after_change_ft, initial_ft), 1)


class Test_CommonPrefixWith(unittest.TestCase):
    def test_file(self):
        bctx = _create_bctx()
        # Create temporary directories and files for realistic File Monikers
        with tempfile.TemporaryDirectory() as t:
            tmpdir = Path(t)
            dir_a = tmpdir / "dir_a"
            dir_b = tmpdir / "dir_a" / "dir_b"
            dir_b.mkdir(parents=True)
            file1 = dir_a / "file1.txt"
            file2 = dir_b / "file2.txt"
            file3 = tmpdir / "file3.txt"
            mon1 = _create_file_moniker(str(file1))  # tmpdir/dir_a/file1.txt
            mon2 = _create_file_moniker(str(file2))  # tmpdir/dir_a/dir_b/file2.txt
            mon3 = _create_file_moniker(str(file3))  # tmpdir/file3.txt
            # Common prefix between mon1 and mon2 (tmpdir/dir_a)
            self.assertEqual(
                os.path.normcase(
                    os.path.normpath(
                        mon1.CommonPrefixWith(mon2).GetDisplayName(bctx, None)
                    )
                ),
                os.path.normcase(os.path.normpath(dir_a)),
            )
            # Common prefix between mon1 and mon3 (tmpdir)
            self.assertEqual(
                os.path.normcase(
                    os.path.normpath(
                        mon1.CommonPrefixWith(mon3).GetDisplayName(bctx, None)
                    )
                ),
                os.path.normcase(os.path.normpath(tmpdir)),
            )


class Test_RelativePathTo(unittest.TestCase):
    def test_file(self):
        bctx = _create_bctx()
        with tempfile.TemporaryDirectory() as t:
            tmpdir = Path(t)
            dir_a = tmpdir / "dir_a"
            dir_b = tmpdir / "dir_b"
            dir_a.mkdir()
            dir_b.mkdir()
            file1 = dir_a / "file1.txt"
            file2 = dir_b / "file2.txt"
            mon_from = _create_file_moniker(str(file1))  # tmpdir/dir_a/file1.txt
            mon_to = _create_file_moniker(str(file2))  # tmpdir/dir_b/file2.txt
            # The COM API returns paths with backslashes on Windows, so we normalize.
            self.assertEqual(
                # Check the display name of the relative moniker
                # The moniker's `RelativePathTo` method calculates the path from
                # the base of the `mon_from` to the target `mon_to`.
                os.path.normcase(
                    os.path.normpath(
                        mon_from.RelativePathTo(mon_to).GetDisplayName(bctx, None)
                    )
                ),
                # Calculate the relative path from the directory of file1 to file2
                os.path.normcase(os.path.normpath("..\\..\\dir_b\\file2.txt")),
            )


class Test_Enum(unittest.TestCase):
    def test_generic_composite(self):
        item_id1 = str(GUID.create_new())
        item_id2 = str(GUID.create_new())
        item_mon1 = _create_item_moniker("!", item_id1)
        item_mon2 = _create_item_moniker("!", item_id2)
        # Create a composite moniker to ensure multiple elements for enumeration
        comp_mon = _create_generic_composite(item_mon1, item_mon2)
        enum_moniker = comp_mon.Enum(True)  # True for forward enumeration
        self.assertIsInstance(enum_moniker, IEnumMoniker)


class Test_RemoteBindToObject(unittest.TestCase):
    def test_file(self):
        bctx = _create_bctx()
        with tempfile.TemporaryDirectory() as t:
            tmpdir = Path(t)
            tmpfile = tmpdir / "tmp.lnk"
            tmpfile.touch()
            mon = _create_file_moniker(str(tmpfile))
            bound_obj = mon.RemoteBindToObject(bctx, None, IPersistFile._iid_)
            pf = bound_obj.QueryInterface(IPersistFile)
            self.assertEqual(
                os.path.normcase(os.path.normpath(_get_long_path_name(str(tmpfile)))),
                os.path.normcase(
                    os.path.normpath(_get_long_path_name(pf.GetCurFile()))
                ),
            )
