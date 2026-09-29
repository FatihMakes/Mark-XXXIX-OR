import _ctypes
import os
import sys
import unittest as ut
import winreg
from ctypes.wintypes import MAX_PATH
from unittest import mock

import comtypes
import comtypes.server.inprocserver
from comtypes import GUID
from comtypes.server import register
from comtypes.server.register import (
    FrozenRegistryEntries,
    InterpRegistryEntries,
    Registrar,
    _delete_key,
    _get_serverdll,
)

HKCR = winreg.HKEY_CLASSES_ROOT
MULTI_SZ = winreg.REG_MULTI_SZ
SZ = winreg.REG_SZ

ERROR_ACCESS_DENIED = 5
ERROR_FILE_NOT_FOUND = 2


@mock.patch.object(register, "SHDeleteKey")
@mock.patch.object(register, "winreg")
class Test_delete_key(ut.TestCase):
    def test_calls_sh_deletekey_if_forced(self, _winreg, _sh_deletekey):
        _delete_key(123, "subkey", force=True)
        _winreg.DeleteKey.assert_not_called()
        _sh_deletekey.assert_called_once_with(123, "subkey")

    def test_calls_winreg_deletekey_if_not_forced(self, _winreg, _sh_deletekey):
        _delete_key(123, "subkey", force=False)
        _winreg.DeleteKey.assert_called_once_with(123, "subkey")
        _sh_deletekey.assert_not_called()

    def test_ignores_error_on_sh_deletekey(self, _winreg, _sh_deletekey):
        err = OSError(ERROR_FILE_NOT_FOUND, "msg", "filename", ERROR_FILE_NOT_FOUND)
        _sh_deletekey.side_effect = err
        _delete_key(123, "subkey", force=True)
        _winreg.DeleteKey.assert_not_called()
        _sh_deletekey.assert_called_once_with(123, "subkey")

    def test_ignores_error_on_winreg_deletekey(self, _winreg, _sh_deletekey):
        err = OSError(ERROR_FILE_NOT_FOUND, "msg", "filename", ERROR_FILE_NOT_FOUND)
        _winreg.DeleteKey.side_effect = err
        _delete_key(123, "subkey", force=False)
        _winreg.DeleteKey.assert_called_once_with(123, "subkey")
        _sh_deletekey.assert_not_called()

    def test_not_ignores_winerror_on_sh_deletekey(self, _winreg, _sh_deletekey):
        err = OSError(ERROR_ACCESS_DENIED, "msg", "filename", ERROR_ACCESS_DENIED)
        _sh_deletekey.side_effect = err
        with self.assertRaises(OSError) as e:
            _delete_key(123, "subkey", force=True)
        self.assertEqual(e.exception.winerror, ERROR_ACCESS_DENIED)
        _winreg.DeleteKey.assert_not_called()
        _sh_deletekey.assert_called_once_with(123, "subkey")

    def test_not_ignores_winerror_on_winreg_deletekey(self, _winreg, _sh_deletekey):
        err = OSError(ERROR_ACCESS_DENIED, "msg", "filename", ERROR_ACCESS_DENIED)
        _winreg.DeleteKey.side_effect = err
        with self.assertRaises(OSError) as e:
            _delete_key(123, "subkey", force=False)
        self.assertEqual(e.exception.winerror, ERROR_ACCESS_DENIED)
        _winreg.DeleteKey.assert_called_once_with(123, "subkey")
        _sh_deletekey.assert_not_called()


@mock.patch.object(register, "winreg")
class Test_Registrar_nodebug(ut.TestCase):
    def test_calls_openkey_and_deletekey(self, _winreg):
        hkey = mock.Mock(spec=winreg.HKEYType)
        _winreg.OpenKey.return_value = hkey
        reg_clsid = GUID.create_new()
        registrar = Registrar()

        class Cls:
            _reg_clsid_ = reg_clsid

        registrar.nodebug(Cls)
        _winreg.OpenKey.assert_called_once_with(HKCR, rf"CLSID\{reg_clsid}")
        _winreg.DeleteKey.assert_called_once_with(hkey, "Logging")

    def test_ignores_winerror(self, _winreg):
        err = OSError(ERROR_FILE_NOT_FOUND, "msg", "filename", ERROR_FILE_NOT_FOUND)
        _winreg.OpenKey.side_effect = err
        reg_clsid = GUID.create_new()
        registrar = Registrar()

        class Cls:
            _reg_clsid_ = reg_clsid

        registrar.nodebug(Cls)
        _winreg.OpenKey.assert_called_once_with(HKCR, rf"CLSID\{reg_clsid}")
        _winreg.DeleteKey.assert_not_called()

    def test_not_ignores_winerror(self, _winreg):
        hkey = mock.Mock(spec=winreg.HKEYType)
        _winreg.OpenKey.return_value = hkey
        err = OSError(ERROR_ACCESS_DENIED, "msg", "filename", ERROR_ACCESS_DENIED)
        _winreg.OpenKey.return_value = hkey
        _winreg.DeleteKey.side_effect = err
        reg_clsid = GUID.create_new()
        registrar = Registrar()

        class Cls:
            _reg_clsid_ = reg_clsid

        with self.assertRaises(OSError) as e:
            registrar.nodebug(Cls)
        self.assertEqual(e.exception.winerror, ERROR_ACCESS_DENIED)
        _winreg.OpenKey.assert_called_once_with(HKCR, rf"CLSID\{reg_clsid}")
        _winreg.DeleteKey.assert_called_once_with(hkey, "Logging")


@mock.patch.object(register, "winreg")
class Test_Registrar_debug(ut.TestCase):
    def test_calls_createkey_and_sets_format(self, _winreg):
        _winreg.REG_MULTI_SZ = MULTI_SZ
        _winreg.REG_SZ = SZ
        hkey = mock.Mock(spec=winreg.HKEYType)
        _winreg.CreateKey.return_value = hkey
        levels = ["lv=DEBUG"]
        format = "FMT"
        reg_clsid = GUID.create_new()
        registrar = Registrar()

        class Cls:
            _reg_clsid_ = reg_clsid

        registrar.debug(Cls, levels, format)
        _winreg.CreateKey.assert_called_once_with(HKCR, rf"CLSID\{reg_clsid}\Logging")
        self.assertEqual(
            _winreg.SetValueEx.call_args_list,
            [
                mock.call(hkey, "levels", None, MULTI_SZ, levels),
                mock.call(hkey, "format", None, SZ, format),
            ],
        )

    def test_calls_createkey_and_deletes_format(self, _winreg):
        _winreg.REG_MULTI_SZ = MULTI_SZ
        hkey = mock.Mock(spec=winreg.HKEYType)
        _winreg.CreateKey.return_value = hkey
        levels = ["lv=DEBUG"]
        reg_clsid = GUID.create_new()
        registrar = Registrar()

        class Cls:
            _reg_clsid_ = reg_clsid

        registrar.debug(Cls, levels, None)
        _winreg.CreateKey.assert_called_once_with(HKCR, rf"CLSID\{reg_clsid}\Logging")
        _winreg.SetValueEx.assert_called_once_with(
            hkey, "levels", None, MULTI_SZ, levels
        )
        _winreg.DeleteValue.assert_called_once_with(hkey, "format")

    def test_calls_createkey_and_ignores_errors_on_deleting(self, _winreg):
        _winreg.REG_MULTI_SZ = MULTI_SZ
        hkey = mock.Mock(spec=winreg.HKEYType)
        _winreg.CreateKey.return_value = hkey
        err = OSError(ERROR_FILE_NOT_FOUND, "msg", "filename", ERROR_FILE_NOT_FOUND)
        _winreg.DeleteValue.side_effect = err
        levels = ["lv=DEBUG"]
        reg_clsid = GUID.create_new()
        registrar = Registrar()

        class Cls:
            _reg_clsid_ = reg_clsid

        registrar.debug(Cls, levels, None)
        _winreg.CreateKey.assert_called_once_with(HKCR, rf"CLSID\{reg_clsid}\Logging")
        _winreg.SetValueEx.assert_called_once_with(
            hkey, "levels", None, MULTI_SZ, levels
        )
        _winreg.DeleteValue.assert_called_once_with(hkey, "format")

    def test_calls_createkey_and_not_ignores_errors_on_deleting(self, _winreg):
        _winreg.REG_MULTI_SZ = MULTI_SZ
        hkey = mock.Mock(spec=winreg.HKEYType)
        _winreg.CreateKey.return_value = hkey
        err = OSError(ERROR_ACCESS_DENIED, "msg", "filename", ERROR_ACCESS_DENIED)
        _winreg.DeleteValue.side_effect = err
        levels = ["lv=DEBUG"]
        reg_clsid = GUID.create_new()
        registrar = Registrar()

        class Cls:
            _reg_clsid_ = reg_clsid

        with self.assertRaises(OSError) as e:
            registrar.debug(Cls, levels, None)
        self.assertEqual(e.exception.winerror, ERROR_ACCESS_DENIED)
        _winreg.CreateKey.assert_called_once_with(HKCR, rf"CLSID\{reg_clsid}\Logging")
        _winreg.SetValueEx.assert_called_once_with(
            hkey, "levels", None, MULTI_SZ, levels
        )
        _winreg.DeleteValue.assert_called_once_with(hkey, "format")


class Test_Registrar_register(ut.TestCase):
    def test_calls_cls_register(self):
        cls = mock.Mock(spec=["_register"])
        registrar = Registrar()
        registrar.register(cls)
        cls._register.assert_called_once_with(registrar)

    # The coverage for COM server registration is ensured by the setup
    # of `test_comserver` and `test_dispinterface`, so no additional tests
    # are performed here now.


class Test_Registrar_unregister(ut.TestCase):
    def test_calls_cls_unregister(self):
        cls = mock.Mock(spec=["_unregister"])
        registrar = Registrar()
        registrar.unregister(cls)
        cls._unregister.assert_called_once_with(registrar)

    # The coverage for COM server unregistration is ensured by the teardown
    # of `test_comserver` and `test_dispinterface`, so no additional tests
    # are performed here now.


class Test_get_serverdll(ut.TestCase):
    @mock.patch.object(register, "GetModuleFileName")
    def test_frozen(self, GetModuleFileName):
        handle, dll_path = 1234, r"path\to\frozen.dll"
        GetModuleFileName.return_value = dll_path
        self.assertEqual(dll_path, _get_serverdll(handle))
        (((hmodule, maxsize), _),) = GetModuleFileName.call_args_list
        self.assertEqual(handle, hmodule)
        self.assertEqual(MAX_PATH, maxsize)


class Test_InterpRegistryEntries(ut.TestCase):
    def test_reg_clsid(self):
        reg_clsid = GUID.create_new()

        class Cls:
            _reg_clsid_ = reg_clsid

        expected = [(HKCR, rf"CLSID\{reg_clsid}", "", "")]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))

    def test_reg_desc(self):
        reg_clsid = GUID.create_new()
        reg_desc = "description for testing"

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_desc_ = reg_desc

        expected = [(HKCR, rf"CLSID\{reg_clsid}", "", reg_desc)]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))

    def test_reg_novers_progid(self):
        reg_clsid = GUID.create_new()
        reg_novers_progid = "Lib.Server"

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_novers_progid_ = reg_novers_progid

        expected = [(HKCR, rf"CLSID\{reg_clsid}", "", "Lib Server")]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))

    def test_progid(self):
        reg_clsid = GUID.create_new()
        reg_progid = "Lib.Server.1"

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_progid_ = reg_progid

        expected = [
            (HKCR, rf"CLSID\{reg_clsid}", "", "Lib Server 1"),
            (HKCR, rf"CLSID\{reg_clsid}\ProgID", "", reg_progid),
            (HKCR, reg_progid, "", "Lib Server 1"),
            (HKCR, rf"{reg_progid}\CLSID", "", str(reg_clsid)),
        ]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))

    def test_reg_progid_reg_desc(self):
        reg_clsid = GUID.create_new()
        reg_progid = "Lib.Server.1"
        reg_desc = "description for testing"

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_progid_ = reg_progid
            _reg_desc_ = reg_desc

        expected = [
            (HKCR, rf"CLSID\{reg_clsid}", "", reg_desc),
            (HKCR, rf"CLSID\{reg_clsid}\ProgID", "", reg_progid),
            (HKCR, reg_progid, "", "description for testing"),
            (HKCR, rf"{reg_progid}\CLSID", "", str(reg_clsid)),
        ]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))

    def test_reg_progid_reg_novers_progid(self):
        reg_clsid = GUID.create_new()
        reg_progid = "Lib.Server.1"
        reg_novers_progid = "Lib.Server"

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_progid_ = reg_progid
            _reg_novers_progid_ = reg_novers_progid

        clsid_sub = rf"CLSID\{reg_clsid}"
        expected = [
            (HKCR, clsid_sub, "", "Lib Server"),
            (HKCR, rf"{clsid_sub}\ProgID", "", reg_progid),
            (HKCR, reg_progid, "", "Lib Server"),
            (HKCR, rf"{reg_progid}\CLSID", "", str(reg_clsid)),
            (HKCR, rf"{clsid_sub}\VersionIndependentProgID", "", reg_novers_progid),
            (HKCR, reg_novers_progid, "", "Lib Server"),
            (HKCR, rf"{reg_novers_progid}\CurVer", "", "Lib.Server.1"),
            (HKCR, rf"{reg_novers_progid}\CLSID", "", str(reg_clsid)),
        ]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))

    def test_local_server(self):
        reg_clsid = GUID.create_new()
        reg_clsctx = comtypes.CLSCTX_LOCAL_SERVER

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_clsctx_ = reg_clsctx

        clsid_sub = rf"CLSID\{reg_clsid}"
        local_srv_sub = rf"{clsid_sub}\LocalServer32"
        expected = [
            (HKCR, clsid_sub, "", ""),
            (HKCR, local_srv_sub, "", f"{sys.executable} {__file__}"),
        ]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))

    def test_inproc_server(self):
        reg_clsid = GUID.create_new()
        reg_clsctx = comtypes.CLSCTX_INPROC_SERVER

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_clsctx_ = reg_clsctx

        clsid_sub = rf"CLSID\{reg_clsid}"
        inproc_srv_sub = rf"{clsid_sub}\InprocServer32"
        full_classname = f"{__name__}.Cls"
        expected = [
            (HKCR, clsid_sub, "", ""),
            (HKCR, inproc_srv_sub, "", _ctypes.__file__),
            (HKCR, inproc_srv_sub, "PythonClass", full_classname),
            (HKCR, inproc_srv_sub, "PythonPath", os.path.dirname(__file__)),
        ]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))

    def test_inproc_server_reg_threading(self):
        reg_clsid = GUID.create_new()
        reg_threading = "Both"
        reg_clsctx = comtypes.CLSCTX_INPROC_SERVER

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_threading_ = reg_threading
            _reg_clsctx_ = reg_clsctx

        clsid_sub = rf"CLSID\{reg_clsid}"
        inproc_srv_sub = rf"{clsid_sub}\InprocServer32"
        full_classname = f"{__name__}.Cls"
        expected = [
            (HKCR, clsid_sub, "", ""),
            (HKCR, inproc_srv_sub, "", _ctypes.__file__),
            (HKCR, inproc_srv_sub, "PythonClass", full_classname),
            (HKCR, inproc_srv_sub, "PythonPath", os.path.dirname(__file__)),
            (HKCR, inproc_srv_sub, "ThreadingModel", reg_threading),
        ]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))

    def test_reg_typelib(self):
        reg_clsid = GUID.create_new()
        libid = str(GUID.create_new())
        reg_typelib = (libid, 1, 0)

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_typelib_ = reg_typelib

        expected = [
            (HKCR, rf"CLSID\{reg_clsid}", "", ""),
            (HKCR, rf"CLSID\{reg_clsid}\Typelib", "", libid),
        ]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))

    def test_all_entries(self):
        reg_clsid = GUID.create_new()
        libid = str(GUID.create_new())
        reg_typelib = (libid, 1, 0)
        reg_threading = "Both"
        reg_progid = "Lib.Server.1"
        reg_novers_progid = "Lib.Server"
        reg_desc = "description for testing"
        reg_clsctx = comtypes.CLSCTX_INPROC_SERVER | comtypes.CLSCTX_LOCAL_SERVER

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_typelib_ = reg_typelib
            _reg_threading_ = reg_threading
            _reg_progid_ = reg_progid
            _reg_novers_progid_ = reg_novers_progid
            _reg_desc_ = reg_desc
            _reg_clsctx_ = reg_clsctx

        clsid_sub = rf"CLSID\{reg_clsid}"
        inproc_srv_sub = rf"{clsid_sub}\InprocServer32"
        local_srv_sub = rf"{clsid_sub}\LocalServer32"
        full_classname = f"{__name__}.Cls"
        expected = [
            (HKCR, clsid_sub, "", reg_desc),
            (HKCR, rf"{clsid_sub}\ProgID", "", reg_progid),
            (HKCR, reg_progid, "", reg_desc),
            (HKCR, rf"{reg_progid}\CLSID", "", str(reg_clsid)),
            (HKCR, rf"{clsid_sub}\VersionIndependentProgID", "", reg_novers_progid),
            (HKCR, reg_novers_progid, "", reg_desc),
            (HKCR, rf"{reg_novers_progid}\CurVer", "", reg_progid),
            (HKCR, rf"{reg_novers_progid}\CLSID", "", str(reg_clsid)),
            (HKCR, local_srv_sub, "", f"{sys.executable} {__file__}"),
            (HKCR, inproc_srv_sub, "", _ctypes.__file__),
            (HKCR, inproc_srv_sub, "PythonClass", full_classname),
            (HKCR, inproc_srv_sub, "PythonPath", os.path.dirname(__file__)),
            (HKCR, inproc_srv_sub, "ThreadingModel", reg_threading),
            (HKCR, rf"{clsid_sub}\Typelib", "", libid),
        ]
        self.assertEqual(expected, list(InterpRegistryEntries(Cls)))


class Test_FrozenRegistryEntries(ut.TestCase):
    SERVERDLL = r"my\target\server.dll"

    # We do not test the scenario where `frozen` is `'dll'` but
    # `frozendllhandle` is `None`, as it is not a situation
    # we anticipate.

    def test_local_dll(self):
        reg_clsid = GUID.create_new()
        reg_clsctx = comtypes.CLSCTX_LOCAL_SERVER

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_clsctx_ = reg_clsctx

        # In such cases, the server does not start because the
        # InprocServer32/LocalServer32 keys are not registered.
        expected = [(HKCR, rf"CLSID\{reg_clsid}", "", "")]
        entries = FrozenRegistryEntries(Cls, frozen="dll", frozendllhandle=1234)
        self.assertEqual(expected, list(entries))

    def test_local_windows_exe(self):
        reg_clsid = GUID.create_new()
        reg_clsctx = comtypes.CLSCTX_LOCAL_SERVER

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_clsctx_ = reg_clsctx

        expected = [
            (HKCR, rf"CLSID\{reg_clsid}", "", ""),
            (HKCR, rf"CLSID\{reg_clsid}\LocalServer32", "", sys.executable),
        ]
        self.assertEqual(
            expected, list(FrozenRegistryEntries(Cls, frozen="windows_exe"))
        )

    @mock.patch.object(register, "_get_serverdll", return_value=SERVERDLL)
    def test_inproc_dll(self, get_serverdll):
        reg_clsid = GUID.create_new()
        reg_clsctx = comtypes.CLSCTX_INPROC_SERVER

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_clsctx_ = reg_clsctx

        clsid_sub = rf"CLSID\{reg_clsid}"
        inproc_srv_sub = rf"{clsid_sub}\InprocServer32"
        expected = [
            (HKCR, clsid_sub, "", ""),
            (HKCR, inproc_srv_sub, "", self.SERVERDLL),
        ]

        entries = FrozenRegistryEntries(Cls, frozen="dll", frozendllhandle=1234)
        self.assertEqual(expected, list(entries))
        get_serverdll.assert_called_once_with(1234)

    @mock.patch.object(register, "_get_serverdll", return_value=SERVERDLL)
    def test_inproc_reg_threading(self, get_serverdll):
        reg_clsid = GUID.create_new()
        reg_threading = "Both"
        reg_clsctx = comtypes.CLSCTX_INPROC_SERVER

        class Cls:
            _reg_clsid_ = reg_clsid
            _reg_threading_ = reg_threading
            _reg_clsctx_ = reg_clsctx

        clsid_sub = rf"CLSID\{reg_clsid}"
        inproc_srv_sub = rf"{clsid_sub}\InprocServer32"
        expected = [
            (HKCR, clsid_sub, "", ""),
            (HKCR, inproc_srv_sub, "", self.SERVERDLL),
            (HKCR, inproc_srv_sub, "ThreadingModel", reg_threading),
        ]
        self.assertEqual(
            expected,
            list(FrozenRegistryEntries(Cls, frozen="dll", frozendllhandle=1234)),
        )
        get_serverdll.assert_called_once_with(1234)
