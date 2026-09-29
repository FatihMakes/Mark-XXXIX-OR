import unittest as ut

import comtypes.client
from comtypes import GUID, CoGetClassObject, IUnknown, shelllink
from comtypes.server import IClassFactory

CLSID_ShellLink = GUID("{00021401-0000-0000-C000-000000000046}")

REGDB_E_CLASSNOTREG = -2147221164  # 0x80040154
HKCU = 1  # HKEY_CURRENT_USER


class Test_CreateInstance(ut.TestCase):
    def test_returns_specified_interface_type_instance(self):
        class_factory = CoGetClassObject(CLSID_ShellLink)
        self.assertIsInstance(class_factory, IClassFactory)
        shlnk = class_factory.CreateInstance(interface=shelllink.IShellLinkW)
        self.assertIsInstance(shlnk, shelllink.IShellLinkW)
        shlnk.SetDescription("sample")
        self.assertEqual(shlnk.GetDescription(), "sample")

    def test_returns_iunknown_type_instance(self):
        class_factory = CoGetClassObject(CLSID_ShellLink)
        self.assertIsInstance(class_factory, IClassFactory)
        punk = class_factory.CreateInstance()
        self.assertIsInstance(punk, IUnknown)
        self.assertNotIsInstance(punk, shelllink.IShellLinkW)
        shlnk = punk.QueryInterface(shelllink.IShellLinkW)
        shlnk.SetDescription("sample")
        self.assertEqual(shlnk.GetDescription(), "sample")

    def test_returns_lazybind_dynamic_dispatch_if_typeinfo_is_available(self):
        # When `dynamic=True`, objects providing type information will return a
        # `lazybind.Dispatch` instance.
        class_factory = comtypes.client.GetClassObject("Scripting.Dictionary")
        self.assertIsInstance(class_factory, IClassFactory)
        dic = class_factory.CreateInstance(dynamic=True)
        self.assertIsInstance(dic, comtypes.client.lazybind.Dispatch)
        dic.Item["key"] = "value"
        self.assertEqual(dic.Item["key"], "value")

    def test_returns_fully_dynamic_dispatch_if_typeinfo_is_unavailable(self):
        # When `dynamic=True`, objects that do NOT provide type information (or
        # fail to provide it) will return a `dynamic._Dispatch` instance.
        class_factory = comtypes.client.GetClassObject("WindowsInstaller.Installer")
        self.assertIsInstance(class_factory, IClassFactory)
        inst = class_factory.CreateInstance(dynamic=True)
        self.assertIsInstance(inst, comtypes.client.dynamic._Dispatch)
        self.assertTrue(inst.RegistryValue(HKCU, r"Control Panel\Desktop"))

    def test_raises_valueerror_if_takes_dynamic_true_and_interface_explicitly(self):
        class_factory = CoGetClassObject(CLSID_ShellLink)
        self.assertIsInstance(class_factory, IClassFactory)
        with self.assertRaises(ValueError):
            class_factory.CreateInstance(  # type: ignore
                interface=shelllink.IShellLinkW,
                dynamic=True,  # type: ignore
            )

    def test_raises_class_not_reg_error_if_non_existent_clsid(self):
        # calling `CoGetClassObject` with a non-existent CLSID raises an `OSError`.
        with self.assertRaises(OSError) as cm:
            CoGetClassObject(GUID.create_new())
        self.assertEqual(cm.exception.winerror, REGDB_E_CLASSNOTREG)
