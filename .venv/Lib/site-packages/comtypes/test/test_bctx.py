import contextlib
import unittest
from _ctypes import COMError
from ctypes import POINTER, byref, sizeof

from comtypes import GUID, hresult, tagBIND_OPTS2
from comtypes.client import CreateObject, GetModule
from comtypes.test.monikers_helper import (
    ROTFLAGS_ALLOWANYCLIENT,
    _CreateBindCtx,
    _CreateItemMoniker,
    _GetRunningObjectTable,
)

with contextlib.redirect_stdout(None):  # supress warnings
    GetModule("msvidctl.dll")
from comtypes.gen import MSVidCtlLib as msvidctl
from comtypes.gen.MSVidCtlLib import IBindCtx, IMoniker, IRunningObjectTable


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


class Test_EnumObjectParam(unittest.TestCase):
    def test_cannot_call(self):
        bctx = _create_bctx()
        with self.assertRaises(COMError) as cm:
            # calling `EnumObjectParam` results in a return value of E_NOTIMPL.
            # https://learn.microsoft.com/en-us/windows/win32/api/objidl/nf-objidl-ibindctx-enumobjectparam#notes-to-callers
            bctx.EnumObjectParam()
        self.assertEqual(cm.exception.hresult, hresult.E_NOTIMPL)


class Test_GetRunningObjectTable(unittest.TestCase):
    def test_returns_rot(self):
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        item_id = str(GUID.create_new())
        mon = _create_item_moniker("!", item_id)
        bctx = _create_bctx()
        # Before registering: should NOT be running
        rot_from_bctx = bctx.GetRunningObjectTable()
        self.assertIsInstance(rot_from_bctx, IRunningObjectTable)
        rot_from_func = _create_rot()
        dw_reg = rot_from_func.Register(ROTFLAGS_ALLOWANYCLIENT, vidctl, mon)
        # After registering: should be running
        self.assertEqual(rot_from_bctx.IsRunning(mon), hresult.S_OK)
        rot_from_func.Revoke(dw_reg)
        # After revoking: should NOT be running again
        self.assertEqual(rot_from_bctx, rot_from_func)


class Test_Register_Revoke_Release_ObjectBound(unittest.TestCase):
    def test_register_and_revoke(self):
        bctx = _create_bctx()
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        # Binds the object to the bind context, ensuring it stays alive during
        # the binding operation.
        hr = bctx.RegisterObjectBound(vidctl)
        self.assertEqual(hr, hresult.S_OK)
        # At this point, `bctx` holds a reference to `vidctl`.
        # Unlike `RegisterObjectParam`, there is no public API to retrieve
        # objects registered via `RegisterObjectBound` from `IBindCtx`.
        # Therefore, direct testing of `vidctl`'s accessibility via `bctx`
        # after binding (similar to `GetObjectParam`) is not possible.
        # Releases the reference to the object previously registered.
        hr = bctx.RevokeObjectBound(vidctl)
        self.assertEqual(hr, hresult.S_OK)
        # `bctx` holds a reference to `vidctl` again.
        # Releases all object references currently held by the bind context.
        bctx.RegisterObjectBound(vidctl)
        hr = bctx.ReleaseBoundObjects()
        self.assertEqual(hr, hresult.S_OK)


class Test_Get_Register_Revoke_ObjectParam(unittest.TestCase):
    def test_get_and_register_and_revoke(self):
        bctx = _create_bctx()
        key = str(GUID.create_new())
        vidctl = CreateObject(msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl)
        # `GetObjectParam` should fail as it's NOT registered yet
        with self.assertRaises(COMError) as cm:
            bctx.GetObjectParam(key)
        self.assertEqual(cm.exception.hresult, hresult.E_FAIL)
        # Register object
        hr = bctx.RegisterObjectParam(key, vidctl)
        self.assertEqual(hr, hresult.S_OK)
        # `GetObjectParam` should succeed now
        ret_obj = bctx.GetObjectParam(key)
        self.assertEqual(ret_obj.QueryInterface(msvidctl.IMSVidCtl), vidctl)
        # Revoke object
        hr = bctx.RevokeObjectParam(key)
        self.assertEqual(hr, hresult.S_OK)
        # `GetObjectParam` should fail again after revoke
        with self.assertRaises(COMError) as cm:
            bctx.GetObjectParam(key)
        self.assertEqual(cm.exception.hresult, hresult.E_FAIL)


class Test_Set_Get_BindOptions(unittest.TestCase):
    def test_set_get_bind_options(self):
        bctx = _create_bctx()
        # Create an instance of `BIND_OPTS2` and set some values.
        # In comtypes, instances of Structure subclasses like `tagBIND_OPTS2`
        # can be passed directly as arguments where COM methods expect a
        # pointer to the structure.
        hr = bctx.RemoteSetBindOptions(
            tagBIND_OPTS2(
                cbStruct=sizeof(tagBIND_OPTS2),
                grfFlags=0x11223344,
                grfMode=0x55667788,
                dwTickCountDeadline=12345,
            )
        )
        self.assertEqual(hr, hresult.S_OK)
        # Create a new instance for retrieval.
        # The `cbStruct` field is crucial in COM as it indicates the size of
        # the structure to the COM component, allowing it to handle different
        # versions of the structure (for backward and forward compatibility).
        # https://learn.microsoft.com/en-us/windows/win32/api/objidl/nf-objidl-ibindctx-getbindoptions#notes-to-callers
        bind_opts = tagBIND_OPTS2(cbStruct=sizeof(tagBIND_OPTS2))
        ret = bctx.RemoteGetBindOptions(bind_opts)
        self.assertIsInstance(ret, tagBIND_OPTS2)
        self.assertEqual(bind_opts.cbStruct, sizeof(tagBIND_OPTS2))
        self.assertEqual(bind_opts.grfFlags, 0x11223344)
        self.assertEqual(bind_opts.grfMode, 0x55667788)
        self.assertEqual(bind_opts.dwTickCountDeadline, 12345)
