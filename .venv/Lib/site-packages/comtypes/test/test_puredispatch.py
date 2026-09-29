import re
import unittest as ut
import winreg

import comtypes.client
from comtypes import GUID, typeinfo
from comtypes.automation import IDispatch

MSI_TLIB = typeinfo.LoadTypeLibEx("msi.dll")
comtypes.client.GetModule(MSI_TLIB)
import comtypes.gen.WindowsInstaller as msi

HKCR = 0  # HKEY_CLASSES_ROOT
HKCU = 1  # HKEY_CURRENT_USER

NAMED_PARAM_ERRMSG = "named parameters not yet implemented"


class Test_Installer(ut.TestCase):
    def test_registry_value_with_root_key_value(self):
        # `WindowsInstaller.Installer` provides access to Windows configuration.
        inst = comtypes.client.CreateObject(
            "WindowsInstaller.Installer", interface=msi.Installer
        )
        # Both methods below get the "Programmatic Identifier" used to handle
        # ".txt" files.
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".txt") as key:
            progid, _ = winreg.QueryValueEx(key, "")
        # This confirms that the Installer can correctly read system information.
        self.assertEqual(progid, inst.RegistryValue(HKCR, ".txt", ""))

    def test_registry_value_with_root_key(self):
        inst = comtypes.client.CreateObject(
            "WindowsInstaller.Installer", interface=msi.Installer
        )
        # If the third arg is missing, `Installer.RegistryValue` returns a Boolean
        # designating whether the key exists.
        # https://learn.microsoft.com/en-us/windows/win32/msi/installer-registryvalue
        # The `HKEY_CURRENT_USER\\Control Panel\\Desktop` registry key is a standard
        # registry key that exists across all versions of the Windows.
        self.assertTrue(inst.RegistryValue(HKCU, r"Control Panel\Desktop"))
        # Since a single backslash is reserved as a path separator and cannot be used
        # in a key name itself. Therefore, such a key exists in no version of Windows.
        self.assertFalse(inst.RegistryValue(HKCU, "\\"))

    def test_registry_value_with_named_params(self):
        inst = comtypes.client.CreateObject(
            "WindowsInstaller.Installer", interface=msi.Installer
        )
        IID_Installer = msi.Installer._iid_
        # This confirms that the Installer is a pure dispatch interface.
        self.assertIsInstance(inst, IDispatch)
        ti = MSI_TLIB.GetTypeInfoOfGuid(IID_Installer)
        ta = ti.GetTypeAttr()
        self.assertEqual(IID_Installer, ta.guid)
        self.assertFalse(ta.wTypeFlags & typeinfo.TYPEFLAG_FDUAL)
        # NOTE: Named parameters are not yet implemented for the dispmethod called
        # via the `Invoke` method.
        # See https://github.com/enthought/comtypes/issues/371
        # As a safeguard until implementation is complete, an error will be raised
        # if named arguments are passed to prevent invalid calls.
        # TODO: After named parameters are supported, this will become a test to
        # assert the return value.
        PTN = re.compile(rf"^{re.escape(NAMED_PARAM_ERRMSG)}$")
        with self.assertRaisesRegex(ValueError, PTN):
            inst.RegistryValue(Root=HKCR, Key=".txt", Value="")  # type: ignore
        with self.assertRaisesRegex(ValueError, PTN):
            inst.RegistryValue(Value="", Root=HKCR, Key=".txt")  # type: ignore
        with self.assertRaisesRegex(ValueError, PTN):
            inst.RegistryValue(HKCR, Key=".txt", Value="")  # type: ignore
        with self.assertRaisesRegex(ValueError, PTN):
            inst.RegistryValue(HKCR, ".txt", Value="")  # type: ignore
        with self.assertRaisesRegex(ValueError, PTN):
            inst.RegistryValue(Root=HKCU, Key=r"Control Panel\Desktop")  # type: ignore
        with self.assertRaisesRegex(ValueError, PTN):
            inst.RegistryValue(Key=r"Control Panel\Desktop", Root=HKCR)  # type: ignore
        with self.assertRaisesRegex(ValueError, PTN):
            inst.RegistryValue(HKCR, Key=r"Control Panel\Desktop")  # type: ignore

    def test_product_state(self):
        inst = comtypes.client.CreateObject(
            "WindowsInstaller.Installer", interface=msi.Installer
        )
        # There is no product associated with the Null GUID.
        pdcode = str(GUID())
        expected = msi.msiInstallStateUnknown
        self.assertEqual(expected, inst.ProductState(pdcode))
        self.assertEqual(expected, inst.ProductState[pdcode])
        # The `ProductState` property is a read-only property.
        # https://learn.microsoft.com/en-us/windows/win32/msi/installer-productstate-property
        with self.assertRaises(TypeError):
            inst.ProductState[pdcode] = msi.msiInstallStateDefault  # type: ignore
        # NOTE: Named parameters are not yet implemented for the named property.
        # See https://github.com/enthought/comtypes/issues/371
        # TODO: After named parameters are supported, this will become a test to
        # assert the return value.
        with self.assertRaises(TypeError):
            inst.ProductState(Product=pdcode)  # type: ignore
