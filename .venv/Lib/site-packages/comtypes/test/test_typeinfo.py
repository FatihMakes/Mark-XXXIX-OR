import ctypes
import os
import sys
import unittest
from _ctypes import COMError
from ctypes.wintypes import MAX_PATH

from comtypes import GUID, hresult, typeinfo
from comtypes.typeinfo import (
    GetModuleFileName,
    LoadRegTypeLib,
    LoadTypeLibEx,
    QueryPathOfRegTypeLib,
)


class Test(unittest.TestCase):
    def test_LoadTypeLibEx(self):
        dllname = "scrrun.dll"
        with self.assertRaises(WindowsError):
            LoadTypeLibEx("<xxx.xx>")
        tlib = LoadTypeLibEx(dllname)
        self.assertTrue(tlib.GetTypeInfoCount())
        tlib.GetDocumentation(-1)
        self.assertEqual(tlib.IsName("ifile"), "IFile")
        self.assertEqual(tlib.IsName("IFILE"), "IFile")
        self.assertTrue(tlib.FindName("IFile"))
        self.assertEqual(tlib.IsName("Spam"), None)
        tlib.GetTypeComp()

    def test_LoadRegTypeLib(self):
        tlib = LoadTypeLibEx("scrrun.dll")
        attr = tlib.GetLibAttr()
        info = attr.guid, attr.wMajorVerNum, attr.wMinorVerNum
        other_tlib = LoadRegTypeLib(*info)
        self.assert_tlibattr_equal(tlib, other_tlib)

    def assert_tlibattr_equal(self, tlib, other_tlib):
        attr, other_attr = tlib.GetLibAttr(), other_tlib.GetLibAttr()
        # `assert tlib == other_tlib` will fail in some environments.
        # But their attributes are equal even if difference of environments.
        self.assertEqual(attr.guid, other_attr.guid)
        self.assertEqual(attr.wMajorVerNum, other_attr.wMajorVerNum)
        self.assertEqual(attr.wMinorVerNum, other_attr.wMinorVerNum)
        self.assertEqual(attr.lcid, other_attr.lcid)
        self.assertEqual(attr.wLibFlags, other_attr.wLibFlags)

        # for n in dir(attr):
        #     if not n.startswith("_"):
        #         print "\t", n, getattr(attr, n)

    def test_QueryPathOfRegTypeLib(self):
        dllname = "scrrun.dll"
        tlib = LoadTypeLibEx(dllname)
        attr = tlib.GetLibAttr()
        info = attr.guid, attr.wMajorVerNum, attr.wMinorVerNum
        path = QueryPathOfRegTypeLib(*info)
        path = path.split("\0")[0]
        self.assertTrue(path.lower().endswith(dllname))

    def test_TypeInfo(self):
        tlib = LoadTypeLibEx("scrrun.dll")
        for index in range(tlib.GetTypeInfoCount()):
            ti = tlib.GetTypeInfo(index)
            ta = ti.GetTypeAttr()
            ti.GetDocumentation(-1)
            c_tlib, c_index = ti.GetContainingTypeLib()
            self.assert_tlibattr_equal(c_tlib, tlib)
            self.assertEqual(c_index, index)
            if ta.typekind in (typeinfo.TKIND_INTERFACE, typeinfo.TKIND_DISPATCH):
                if ta.cImplTypes:
                    href = ti.GetRefTypeOfImplType(0)
                    base = ti.GetRefTypeInfo(href)
                    base.GetDocumentation(-1)
                    ti.GetImplTypeFlags(0)
            for f in range(ta.cFuncs):
                fd = ti.GetFuncDesc(f)
                names = ti.GetNames(fd.memid, 32)
                ti.GetIDsOfNames(*names)
                ti.GetMops(fd.memid)

            for v in range(ta.cVars):
                ti.GetVarDesc(v)

        guid_null = GUID()
        with self.assertRaises(COMError) as cm:
            tlib.GetTypeInfoOfGuid(guid_null)
        self.assertEqual(hresult.TYPE_E_ELEMENTNOTFOUND, cm.exception.hresult)

        IID_IFile = GUID("{C7C3F5A4-88A3-11D0-ABCB-00A0C90FFFC0}")
        ti = tlib.GetTypeInfoOfGuid(IID_IFile)
        c_tlib, c_index = ti.GetContainingTypeLib()
        c_ti = c_tlib.GetTypeInfo(c_index)
        self.assert_tlibattr_equal(c_tlib, tlib)
        self.assertEqual(c_ti, ti)
        self.assertEqual(IID_IFile, ti.GetTypeAttr().guid)

    def test_pure_dispatch_ITypeInfo(self):
        tlib = LoadTypeLibEx("msi.dll")
        IID_Installer = GUID("{000C1090-0000-0000-C000-000000000046}")
        ti = tlib.GetTypeInfoOfGuid(IID_Installer)
        ta = ti.GetTypeAttr()
        self.assertEqual(ta.typekind, typeinfo.TKIND_DISPATCH)
        with self.assertRaises(COMError) as cm:
            ti.GetRefTypeOfImplType(-1)
        self.assertEqual(hresult.TYPE_E_ELEMENTNOTFOUND, cm.exception.hresult)
        self.assertFalse(ti.GetTypeAttr().wTypeFlags & typeinfo.TYPEFLAG_FDUAL)

    def test_custom_interface_ITypeInfo(self):
        tlib = LoadTypeLibEx("UIAutomationCore.dll")
        IID_IUIAutomation = GUID("{30CBE57D-D9D0-452A-AB13-7AC5AC4825EE}")
        ti = tlib.GetTypeInfoOfGuid(IID_IUIAutomation)
        ta = ti.GetTypeAttr()
        self.assertEqual(ta.typekind, typeinfo.TKIND_INTERFACE)
        with self.assertRaises(COMError) as cm:
            ti.GetRefTypeOfImplType(-1)
        self.assertEqual(hresult.TYPE_E_ELEMENTNOTFOUND, cm.exception.hresult)
        self.assertFalse(ti.GetTypeAttr().wTypeFlags & typeinfo.TYPEFLAG_FDUAL)

    def test_dual_interface_ITypeInfo(self):
        tlib = LoadTypeLibEx("scrrun.dll")
        IID_IDictionary = GUID("{42C642C1-97E1-11CF-978F-00A02463E06F}")
        ti = tlib.GetTypeInfoOfGuid(IID_IDictionary)
        ta = ti.GetTypeAttr()
        self.assertEqual(ta.typekind, typeinfo.TKIND_DISPATCH)
        self.assertTrue(ta.wTypeFlags & typeinfo.TYPEFLAG_FDUAL)
        refti = ti.GetRefTypeInfo(ti.GetRefTypeOfImplType(-1))
        refta = refti.GetTypeAttr()
        self.assertEqual(IID_IDictionary, refti.GetTypeAttr().guid)
        self.assertTrue(refta.wTypeFlags & typeinfo.TYPEFLAG_FDUAL)
        self.assertEqual(refta.typekind, typeinfo.TKIND_INTERFACE)
        self.assertEqual(ti, refti.GetRefTypeInfo(refti.GetRefTypeOfImplType(-1)))

    def test_module_ITypeInfo(self):
        # `AddressOfMember` method retrieves the addresses of static functions
        # or variables defined in a module. We will test this functionality by
        # using the 'StdFunctions' module within 'stdole2.tlb', which contains
        # static functions like 'LoadPicture' or 'SavePicture'.
        # NOTE: The name 'stdole2' refers to OLE 2.0; it is a core Windows
        #       component that has remained unchanged for decades to ensure
        #       compatibility, making any future name changes highly improbable.
        tlib = LoadTypeLibEx("stdole2.tlb")
        # Same as `tinfo = GetTypeInfoOfGuid(GUID('{91209AC0-60F6-11CF-9C5D-00AA00C1489E}'))`
        stdfuncs_info = tlib.FindName("StdFunctions")
        self.assertIsNotNone(stdfuncs_info)
        _, tinfo = stdfuncs_info  # type: ignore
        tattr = tinfo.GetTypeAttr()
        self.assertEqual(tattr.cImplTypes, 0)
        self.assertEqual(tattr.typekind, typeinfo.TKIND_MODULE)
        memid, *_ = tinfo.GetIDsOfNames("LoadPicture")
        self.assertEqual(tinfo.GetDocumentation(memid)[0], "LoadPicture")
        # 'LoadPicture' is the alias used within the type library.
        # `GetDllEntry` returns the actual exported name from the DLL, which
        # may be different.
        dll_name, func_name, ordinal = tinfo.GetDllEntry(memid, typeinfo.INVOKE_FUNC)
        # For functions exported by name, `GetDllEntry` returns a 3-tuple:
        # (DLL name, function name, ordinal of 0).
        self.assertIn("oleaut32.dll", dll_name.lower())  # type: ignore
        self.assertEqual(func_name, "OleLoadPictureFileEx")
        self.assertEqual(ordinal, 0)
        _oleaut32 = ctypes.WinDLL(dll_name)
        load_picture = getattr(_oleaut32, func_name)  # type: ignore
        expected_addr = ctypes.cast(load_picture, ctypes.c_void_p).value
        actual_addr = tinfo.AddressOfMember(memid, typeinfo.INVOKE_FUNC)
        self.assertEqual(actual_addr, expected_addr)


class Test_ITypeComp_BindType(unittest.TestCase):
    def test_interface(self):
        IID_IFile = GUID("{C7C3F5A4-88A3-11D0-ABCB-00A0C90FFFC0}")
        tlib = LoadTypeLibEx("scrrun.dll")
        tcomp = tlib.GetTypeComp()
        ti_file, tc_file = tcomp.BindType("IFile")
        self.assertEqual(ti_file.GetDocumentation(-1)[0], "IFile")
        self.assertFalse(tc_file)
        self.assertEqual(ti_file.GetTypeAttr().guid, IID_IFile)


class Test_ITypeComp_Bind(unittest.TestCase):
    def test_enum(self):
        tlib = LoadTypeLibEx("stdole2.tlb")
        tcomp = tlib.GetTypeComp()
        tristate_kind, tristate_tcomp = tcomp.Bind("OLE_TRISTATE")  # type: ignore
        self.assertEqual(tristate_kind, "type")
        self.assertIsInstance(tristate_tcomp, typeinfo.ITypeComp)
        gray_kind, gray_vd = tristate_tcomp.Bind("Gray")  # type: ignore
        self.assertEqual(gray_kind, "variable")
        self.assertIsInstance(gray_vd, typeinfo.tagVARDESC)
        self.assertEqual(gray_vd.varkind, typeinfo.VAR_CONST)  # type: ignore

    def test_interface(self):
        tlib = LoadTypeLibEx("stdole2.tlb")
        IID_Picture = GUID("{7BF80981-BF32-101A-8BBB-00AA00300CAB}")
        tinfo = tlib.GetTypeInfoOfGuid(IID_Picture)
        tcomp = tinfo.GetTypeComp()
        handle_kind, handle_vd = tcomp.Bind("Handle")  # type: ignore
        self.assertEqual(handle_kind, "variable")
        self.assertIsInstance(handle_vd, typeinfo.VARDESC)
        self.assertEqual(handle_vd.varkind, typeinfo.VAR_DISPATCH)  # type: ignore
        render_kind, render_fd = tcomp.Bind("Render")  # type: ignore
        self.assertEqual(render_kind, "function")
        self.assertIsInstance(render_fd, typeinfo.tagFUNCDESC)
        self.assertEqual(render_fd.funckind, typeinfo.FUNC_DISPATCH)  # type: ignore

    def test_non_existent_name(self):
        tlib = LoadTypeLibEx("scrrun.dll")
        tcomp = tlib.GetTypeComp()
        with self.assertRaises(NameError):
            tcomp.Bind("NonExistentNameForTest")


class Test_GetModuleFileName(unittest.TestCase):
    @unittest.skipUnless(
        sys.prefix == sys.base_prefix,
        "This will fail in a virtual environment.",
    )
    def test_null_handler_sys_executable(self):
        self.assertEqual(GetModuleFileName(None, MAX_PATH), sys.executable)

    def test_null_handler_sys_base_prefix(self):
        self.assertEqual(
            os.path.commonpath([GetModuleFileName(None, MAX_PATH), sys.base_prefix]),
            sys.base_prefix,
        )

    def test_loaded_module_handle(self):
        import _ctypes

        dll_path = _ctypes.__file__
        hmodule = ctypes.WinDLL(dll_path)._handle
        self.assertEqual(GetModuleFileName(hmodule, MAX_PATH), dll_path)

    def test_invalid_handle(self):
        with self.assertRaises(OSError) as ce:
            GetModuleFileName(1, MAX_PATH)
        ERROR_MOD_NOT_FOUND = 126
        self.assertEqual(ce.exception.winerror, ERROR_MOD_NOT_FOUND)

    def test_invalid_nsize(self):
        import _ctypes

        dll_path = _ctypes.__file__
        hmodule = ctypes.WinDLL(dll_path)._handle
        with self.assertRaises(OSError) as ce:
            GetModuleFileName(hmodule, 0)
        ERROR_INSUFFICIENT_BUFFER = 122
        self.assertEqual(ce.exception.winerror, ERROR_INSUFFICIENT_BUFFER)


if __name__ == "__main__":
    unittest.main()
