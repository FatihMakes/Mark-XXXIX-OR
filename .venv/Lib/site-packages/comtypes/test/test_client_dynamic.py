import ctypes
import unittest as ut

from comtypes import GUID, COMError, IUnknown, automation, hresult, typeinfo
from comtypes.client import CreateObject, GetModule, dynamic, lazybind


class Test_Dispatch_Function(ut.TestCase):
    def test_returns_lazybind_Dispatch(self):
        # When `dynamic=True`, objects providing type information will return a
        # `lazybind.Dispatch` instance.
        orig = CreateObject("Scripting.Dictionary", interface=automation.IDispatch)
        disp = dynamic.Dispatch(orig)
        self.assertIsInstance(disp, lazybind.Dispatch)
        # Calling `dynamic.Dispatch` with an already dispatched object should
        # return the same instance.
        self.assertIs(disp, dynamic.Dispatch(disp))

    def test_returns_dynamic_Dispatch(self):
        # When `dynamic=True`, objects that do NOT provide type information (or
        # fail to provide it) will return a `dynamic._Dispatch` instance.
        orig = CreateObject(
            "WindowsInstaller.Installer", interface=automation.IDispatch
        )
        disp = dynamic.Dispatch(orig)
        self.assertIsInstance(disp, dynamic._Dispatch)
        # Calling `dynamic.Dispatch` on an already dispatched object should
        # return the same instance.
        self.assertIs(disp, dynamic.Dispatch(disp))


HKCU = 1  # HKEY_CURRENT_USER
msiInstallStateUnknown = -1


class Test_dynamic_Dispatch(ut.TestCase):
    # `MethodCaller` and `_Collection` are indirectly covered in this.
    def test_dict(self):
        # The following conditional branches are not covered;
        # - not `hresult in ERRORS_BAD_CONTEXT`
        # - not `0 != enum.Skip(index)`
        # - other than `COMError` raises in `__getattr__`
        orig = CreateObject("Scripting.Dictionary", interface=automation.IDispatch)
        d = dynamic._Dispatch(orig)
        d.CompareMode = 42
        d.Item["foo"] = 1
        d.Item["bar"] = "spam foo"
        d.Item["baz"] = 3.14
        self.assertEqual(d[0], "foo")
        self.assertEqual(d.Item["foo"], 1)
        self.assertEqual([k for k in iter(d)], ["foo", "bar", "baz"])
        self.assertIsInstance(hash(d), int)
        d._FlagAsMethod("_NewEnum")
        self.assertIs(type(d._NewEnum()), ctypes.POINTER(IUnknown))
        scrrun = GetModule("scrrun.dll")
        scr_dict = d.QueryInterface(scrrun.IDictionary)
        self.assertIsInstance(scr_dict, scrrun.IDictionary)
        d.Item["qux"] = scr_dict
        # `dynamic._Dispatch` reflects the underlying COM object's behavior.
        # For `Scripting.Dictionary`, out-of-bounds index access via `IDispatch`
        # typically results in a `COMError`, which is wrapped as `IndexError`.
        with self.assertRaises(IndexError):
            d[4]
        with self.assertRaises(AttributeError):
            d.__foo__
        with self.assertRaises(COMError) as cm:
            # Access a member that definitely does not exist.
            _ = d.DefinitelyNonExistentMember
        self.assertEqual(cm.exception.hresult, hresult.DISP_E_UNKNOWNNAME)

    def test_installer(self):
        orig = CreateObject(
            "WindowsInstaller.Installer", interface=automation.IDispatch
        )
        installer = dynamic._Dispatch(orig)
        # Access a known property and method
        self.assertIsInstance(installer.Version, str)
        self.assertTrue(installer.RegistryValue(HKCU, r"Control Panel\Desktop"))
        # Test that calling `ProductState` as a method raises a `COMError`
        with self.assertRaises(COMError):
            installer.ProductState(str(GUID()))
        # Test `ProductState` as an item access
        self.assertEqual(msiInstallStateUnknown, installer.ProductState[str(GUID())])
        # Accessing a non-existent attribute should raise `AttributeError`
        with self.assertRaises(AttributeError):
            installer.__foo__


class Test_lazybind_Dispatch(ut.TestCase):
    def test_dict(self):
        orig = CreateObject("Scripting.Dictionary", interface=automation.IDispatch)
        tinfo = orig.GetTypeInfo(0)
        d = lazybind.Dispatch(orig, tinfo)
        d.CompareMode = 42
        d.Item["foo"] = 1
        d.Item["bar"] = "spam foo"
        d.Item["baz"] = 3.14
        self.assertEqual(d.Item["foo"], 1)
        self.assertEqual([k for k in iter(d)], ["foo", "bar", "baz"])
        self.assertIsInstance(hash(d), int)
        # No `_FlagAsMethod` in `lazybind.Dispatch`
        self.assertIs(type(d._NewEnum()), ctypes.POINTER(IUnknown))
        scrrun = GetModule("scrrun.dll")
        scr_dict = d.QueryInterface(scrrun.IDictionary)
        self.assertIsInstance(scr_dict, scrrun.IDictionary)
        d.Item["qux"] = scr_dict
        # `lazybind.Dispatch`, using type information, might return `None` for
        # non-existent keys when accessed via direct index (`d[4]`),
        # as it doesn't directly map to the `Item` property's error handling.
        self.assertIsNone(d[4])
        with self.assertRaises(AttributeError):
            d.__foo__
        with self.assertRaises(NameError):
            # Access a member that definitely does not exist.
            _ = d.DefinitelyNonExistentMember

    def test_installer(self):
        IID_Installer = GUID("{000C1090-0000-0000-C000-000000000046}")
        tlib = typeinfo.LoadTypeLibEx("msi.dll")
        tinfo = tlib.GetTypeInfoOfGuid(IID_Installer)
        orig = CreateObject(
            "WindowsInstaller.Installer", interface=automation.IDispatch
        )
        installer = lazybind.Dispatch(orig, tinfo)
        # Access a known property and method
        self.assertIsInstance(installer.Version, str)
        self.assertTrue(installer.RegistryValue(HKCU, r"Control Panel\Desktop"))
        # Test `ProductState` as a method call
        self.assertEqual(msiInstallStateUnknown, installer.ProductState(str(GUID())))
        # Test `ProductState` as an item access
        self.assertEqual(msiInstallStateUnknown, installer.ProductState[str(GUID())])
        # Accessing a non-existent attribute should raise `AttributeError`
        with self.assertRaises(AttributeError):
            installer.__foo__


if __name__ == "__main__":
    ut.main()
