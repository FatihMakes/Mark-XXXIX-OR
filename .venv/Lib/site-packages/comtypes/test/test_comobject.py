import ctypes
import unittest as ut
from _ctypes import COMError
from ctypes import POINTER, FormatError, byref, pointer
from unittest import mock

import comtypes.client
from comtypes import CLSCTX_SERVER, GUID, COMObject, IPersist, IUnknown, hresult
from comtypes._post_coinit.misc import _CoCreateInstance
from comtypes.automation import IDispatch
from comtypes.errorinfo import ReportError
from comtypes.server import IClassFactory
from comtypes.typeinfo import GUIDKIND_DEFAULT_SOURCE_DISP_IID

comtypes.client.GetModule("UIAutomationCore.dll")
comtypes.client.GetModule("scrrun.dll")
from comtypes.gen import Scripting as scrrun
from comtypes.gen import UIAutomationClient as uiac
from comtypes.gen import stdole


class Test_QueryInterface(ut.TestCase):
    def test_custom_interface(self):
        iuia = uiac.CUIAutomation().QueryInterface(uiac.IUIAutomation)
        self.assertTrue(bool(iuia))
        self.assertEqual(iuia.AddRef(), 2)
        punk = iuia.QueryInterface(IUnknown)
        self.assertEqual(iuia.AddRef(), 4)
        self.assertEqual(punk.AddRef(), 5)
        self.assertEqual(iuia.Release(), 4)
        del iuia
        self.assertEqual(punk.Release(), 2)
        self.assertEqual(punk.Release(), 1)

    def test_dispatch_interface(self):
        dic = scrrun.Dictionary().QueryInterface(scrrun.IDictionary)
        self.assertTrue(bool(dic))
        self.assertEqual(dic.GetTypeInfoCount(), 1)
        self.assertEqual(
            dic.GetTypeInfo(0).GetTypeAttr().guid,
            scrrun.IDictionary._iid_,
        )
        self.assertEqual(dic.GetIDsOfNames("Add"), [1])


class Test_IUnknown_QueryInterface(ut.TestCase):
    def test_e_pointer(self):
        hr = scrrun.Dictionary().IUnknown_QueryInterface(
            None, pointer(scrrun.IDictionary._iid_), ctypes.c_void_p()
        )
        self.assertEqual(hr, hresult.E_POINTER)

    def test_e_no_interface(self):
        hr = scrrun.Dictionary().IUnknown_QueryInterface(
            None, pointer(uiac.IUIAutomation._iid_), ctypes.c_void_p()
        )
        self.assertEqual(hr, hresult.E_NOINTERFACE)

    def test_valid_pointer(self):
        ptr = ctypes.c_void_p()
        _CoCreateInstance(
            byref(scrrun.Dictionary._reg_clsid_),
            None,
            CLSCTX_SERVER,
            byref(scrrun.IDictionary._iid_),
            byref(ptr),
        )
        before_val = ptr.value
        hr = scrrun.Dictionary().IUnknown_QueryInterface(
            None, pointer(scrrun.IDictionary._iid_), ptr
        )
        self.assertEqual(hr, hresult.S_OK)
        self.assertEqual(ptr.value, before_val)

    def test_valid_interface(self):
        dic = POINTER(IDispatch)()
        hr = scrrun.Dictionary().IUnknown_QueryInterface(
            None, pointer(scrrun.IDictionary._iid_), byref(dic)
        )
        self.assertEqual(hr, hresult.S_OK)
        self.assertEqual(dic.AddRef(), 2)  # type: ignore
        self.assertEqual(dic.Release(), 1)  # type: ignore
        self.assertEqual(dic.GetTypeInfoCount(), 1)  # type: ignore


class Test_IUnknown_AddRef_IUnknown_Release(ut.TestCase):
    def test(self):
        cuia = uiac.CUIAutomation()
        self.assertEqual(cuia.IUnknown_AddRef(None), 1)
        self.assertEqual(cuia.IUnknown_AddRef(None), 2)
        with mock.patch.object(COMObject, "_final_release_") as release:
            self.assertEqual(cuia.IUnknown_Release(None), 1)
            release.assert_not_called()
            self.assertEqual(cuia.IUnknown_Release(None), 0)
            release.assert_called_once_with()


class Test_ISupportErrorInfo_InterfaceSupportsErrorInfo(ut.TestCase):
    def test_s_ok(self):
        cuia = uiac.CUIAutomation()
        self.assertEqual(
            cuia.ISupportErrorInfo_InterfaceSupportsErrorInfo(
                None, pointer(IUnknown._iid_)
            ),
            hresult.S_OK,
        )
        self.assertEqual(
            cuia.ISupportErrorInfo_InterfaceSupportsErrorInfo(
                None, pointer(uiac.IUIAutomation._iid_)
            ),
            hresult.S_OK,
        )

    def test_s_false(self):
        cuia = uiac.CUIAutomation()
        self.assertEqual(
            cuia.ISupportErrorInfo_InterfaceSupportsErrorInfo(
                None, pointer(IDispatch._iid_)
            ),
            hresult.S_FALSE,
        )
        self.assertEqual(
            cuia.ISupportErrorInfo_InterfaceSupportsErrorInfo(
                None, pointer(scrrun.IDictionary._iid_)
            ),
            hresult.S_FALSE,
        )


class Test_IProvideClassInfo_GetClassInfo(ut.TestCase):
    def test(self):
        tinfo = uiac.CUIAutomation().IProvideClassInfo_GetClassInfo()
        self.assertEqual(tinfo.GetTypeAttr().guid, uiac.CUIAutomation._reg_clsid_)


class Test_IProvideClassInfo2_GetGUID(ut.TestCase):
    def test(self):
        obj = stdole.StdFont()
        actual = obj.IProvideClassInfo2_GetGUID(GUIDKIND_DEFAULT_SOURCE_DISP_IID)
        self.assertEqual(actual, stdole.FontEvents._iid_)


class Test_IPersist_GetClassID(ut.TestCase):
    def test(self):
        self.assertEqual(
            uiac.CUIAutomation().IPersist_GetClassID(),
            uiac.CUIAutomation._reg_clsid_,
        )


class Test_Vtbl(ut.TestCase):
    def test_com_pointers(self):
        stdpic = stdole.StdPicture()
        cuia = uiac.CUIAutomation()
        self.assertIs(
            type(stdpic._com_pointers_[IPersist._iid_]),
            type(cuia._com_pointers_[IPersist._iid_]),
        )
        self.assertIn(IDispatch._iid_, stdpic._com_pointers_)
        self.assertNotIn(IDispatch._iid_, cuia._com_pointers_)
        self.assertIn(stdole.IPictureDisp._iid_, stdpic._com_pointers_)
        self.assertIn(uiac.IUIAutomation._iid_, cuia._com_pointers_)


class Test_CustomImplementation(ut.TestCase):
    def test_raises_comerror(self):
        ERR_DESC = "Simulated COMError"
        ERR_HELPFILE = "test.hlp"
        ERR_HELPCTX = 42

        class MyClassFactory(COMObject):
            _com_interfaces_ = [IClassFactory]
            _reg_clsid_ = GUID.create_new()

            def CreateInstance(self, this, punkOuter, riid, ppv):
                return ReportError(
                    f"{ERR_DESC}: CreateInstance",
                    IClassFactory._iid_,
                    self._reg_clsid_,
                    ERR_HELPFILE,
                    ERR_HELPCTX,
                    hresult.E_UNEXPECTED,
                )

            def LockServer(self, this, fLock):
                return ReportError(
                    f"{ERR_DESC}: LockServer",
                    IClassFactory._iid_,
                    self._reg_clsid_,
                    ERR_HELPFILE,
                    ERR_HELPCTX,
                    hresult.E_FAIL,
                )

        # Get a COM pointer to the interface of our custom object.
        cf = MyClassFactory().QueryInterface(IClassFactory)
        # calling `LockServer`
        with self.assertRaises(COMError) as cm:
            cf.CreateInstance(interface=IUnknown)
        self.assertEqual(cm.exception.hresult, hresult.E_UNEXPECTED)
        self.assertEqual(cm.exception.text, FormatError(hresult.E_UNEXPECTED))
        self.assertEqual(
            cm.exception.details,
            (f"{ERR_DESC}: CreateInstance", None, ERR_HELPFILE, ERR_HELPCTX, None),
        )
        # calling `LockServer`
        with self.assertRaises(COMError) as cm:
            cf.LockServer(True)
        self.assertEqual(cm.exception.hresult, hresult.E_FAIL)
        self.assertEqual(cm.exception.text, FormatError(hresult.E_FAIL))
        self.assertEqual(
            cm.exception.details,
            (f"{ERR_DESC}: LockServer", None, ERR_HELPFILE, ERR_HELPCTX, None),
        )
