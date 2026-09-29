import contextlib
import unittest
from _ctypes import COMError
from ctypes import POINTER, byref

from comtypes import GUID, hresult
from comtypes.client import CreateObject, GetModule
from comtypes.test.monikers_helper import (
    MK_E_UNAVAILABLE,
    ROTFLAGS_ALLOWANYCLIENT,
    _CreateBindCtx,
    _CreateItemMoniker,
    _GetRunningObjectTable,
)
from comtypes.test.time_structs_helper import (
    SYSTEMTIME,
    CompareFileTime,
    SystemTimeToFileTime,
)

with contextlib.redirect_stdout(None):  # supress warnings
    GetModule("msvidctl.dll")
from comtypes.gen import MSVidCtlLib as msvidctl
from comtypes.gen.MSVidCtlLib import (
    IBindCtx,
    IEnumMoniker,
    IMoniker,
    IRunningObjectTable,
)


def _create_item_moniker(delim: str, item: str) -> IMoniker:
    mon = POINTER(IMoniker)()
    _CreateItemMoniker(delim, item, byref(mon))
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


class Test_Register_Revoke_GetObject_IsRunning(unittest.TestCase):
    def test_item(self):
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        item_id = str(GUID.create_new())
        mon = _create_item_moniker("!", item_id)
        rot = _create_rot()
        bctx = _create_bctx()
        # Before registering: should NOT be running
        with self.assertRaises(COMError) as cm:
            rot.GetObject(mon)
        self.assertEqual(cm.exception.hresult, MK_E_UNAVAILABLE)
        self.assertEqual(rot.IsRunning(mon), hresult.S_FALSE)
        # After registering: should be running
        dw_reg = rot.Register(ROTFLAGS_ALLOWANYCLIENT, vidctl, mon)
        self.assertEqual(rot.IsRunning(mon), hresult.S_OK)
        self.assertEqual(mon.IsRunning(bctx, None, None), hresult.S_OK)
        self.assertEqual(rot.GetObject(mon).QueryInterface(msvidctl.IMSVidCtl), vidctl)
        rot.Revoke(dw_reg)
        # After revoking: should NOT be running again
        self.assertEqual(rot.IsRunning(mon), hresult.S_FALSE)
        with self.assertRaises(COMError) as cm:
            rot.GetObject(mon)
        self.assertEqual(cm.exception.hresult, MK_E_UNAVAILABLE)


class Test_EnumRunning(unittest.TestCase):
    def test_returns_enum_moniker(self):
        rot = _create_rot()
        enum_moniker = rot.EnumRunning()
        self.assertIsInstance(enum_moniker, IEnumMoniker)


class Test_NoteChangeTime_GetTimeOfLastChange(unittest.TestCase):
    def test_modified_time(self):
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        item_id = str(GUID.create_new())
        mon = _create_item_moniker("!", item_id)
        rot = _create_rot()
        dw_reg = rot.Register(ROTFLAGS_ALLOWANYCLIENT, vidctl, mon)
        ft = SystemTimeToFileTime(SYSTEMTIME(wYear=2000, wMonth=1, wDay=1))
        rot.NoteChangeTime(dw_reg, ft)
        self.assertEqual(CompareFileTime(rot.GetTimeOfLastChange(mon), ft), 0)
        rot.Revoke(dw_reg)
