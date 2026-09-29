"""comtypes.server.register - register and unregister a COM object.

Exports the UseCommandLine function.  UseCommandLine is called with
the COM object classes that a module exposes.  It parses the Windows
command line and takes the appropriate actions.
These command line options are supported:

/regserver - register the classes with COM.
/unregserver - unregister the classes with COM.

/nodebug - remove all logging configuration from the registry.

/l <name>=<level> - configure the logging level for the standard Python loggind module,
this option may be used several times.

/f <formatter> - specify the formatter string.

Note: Registering and unregistering the objects does remove logging
entries.  Configuring the logging does not change other registry
entries, so it is possible to freeze a comobject with py2exe, register
it, then configure logging afterwards to debug it, and delete the
logging config afterwards.

Sample usage:

Register the COM object:

  python mycomobj.py /regserver

Configure logging info:

  python mycomobj.py /l comtypes=INFO /l comtypes.server=DEBUG /f %(message)s

Now, debug the object, and when done delete logging info:

  python mycomobj.py /nodebug
"""

import _ctypes
import abc
import logging
import os
import sys
import winreg
from collections.abc import Iterable, Iterator
from ctypes import WinDLL, WinError
from ctypes.wintypes import HKEY, LONG, LPCWSTR, MAX_PATH
from typing import Optional, Union
from winreg import HKEY_CLASSES_ROOT as HKCR
from winreg import HKEY_CURRENT_USER as HKCU
from winreg import HKEY_LOCAL_MACHINE as HKLM

import comtypes.server.inprocserver  # noqa
from comtypes import CLSCTX_INPROC_SERVER, CLSCTX_LOCAL_SERVER
from comtypes.hresult import TYPE_E_CANTLOADLIBRARY, TYPE_E_REGISTRYACCESS
from comtypes.server.localserver import run as run_localserver
from comtypes.server.w_getopt import w_getopt
from comtypes.typeinfo import (
    REGKIND_REGISTER,
    GetModuleFileName,
    LoadTypeLibEx,
    UnRegisterTypeLib,
)

_debug = logging.getLogger(__name__).debug


def get_winerror(exception: OSError) -> Optional[int]:
    try:
        return exception.winerror
    except AttributeError:
        return exception.errno


# a SHDeleteKey function, will remove a registry key with all subkeys.
def _non_zero(retval, func, args):
    if retval:
        raise WinError(retval)
    return retval


_shlwapi = WinDLL("shlwapi")
LSTATUS = LONG
SHDeleteKey = _shlwapi.SHDeleteKeyW
SHDeleteKey.errcheck = _non_zero
SHDeleteKey.argtypes = HKEY, LPCWSTR
SHDeleteKey.restype = LSTATUS


_KEYS = {
    HKCR: "HKCR",
    HKLM: "HKLM",
    HKCU: "HKCU",
}


def _explain(hkey: int) -> Union[str, int]:
    return _KEYS.get(hkey, hkey)


def _delete_key(hkey: int, subkey: str, *, force: bool) -> None:
    try:
        if force:
            _debug("SHDeleteKey %s\\%s", _explain(hkey), subkey)
            SHDeleteKey(hkey, subkey)
        else:
            _debug("DeleteKey %s\\%s", _explain(hkey), subkey)
            winreg.DeleteKey(hkey, subkey)
    except OSError as detail:
        if get_winerror(detail) != 2:
            raise


_Entry = tuple[int, str, str, str]


class Registrar:
    """COM class registration.

    The COM class can override what this does by implementing
    _register and/or _unregister class methods.  These methods will be
    called with the calling instance of Registrar, and so can call the
    Registrars _register and _unregister methods which do the actual
    work.
    """

    _frozen: Union[None, int, str]
    _frozendllhandle: Optional[int]

    def __init__(self) -> None:
        self._frozen = getattr(sys, "frozen", None)
        self._frozendllhandle = getattr(sys, "frozendllhandle", None)

    def _generate_reg_entries(self, cls: type) -> Iterable[_Entry]:
        if self._frozen is None:
            return InterpRegistryEntries(cls)
        return FrozenRegistryEntries(cls, self._frozen, self._frozendllhandle)

    def nodebug(self, cls: type) -> None:
        """Delete logging entries from the registry."""
        clsid = cls._reg_clsid_
        try:
            _debug('DeleteKey( %s\\CLSID\\%s\\Logging"' % (_explain(HKCR), clsid))
            hkey = winreg.OpenKey(HKCR, rf"CLSID\{clsid}")
            winreg.DeleteKey(hkey, "Logging")
        except OSError as detail:
            if get_winerror(detail) != 2:
                raise

    def debug(self, cls: type, levels: list[str], format: Optional[str]) -> None:
        """Write entries in the registry to setup logging for this clsid."""
        # handlers
        # format
        clsid = cls._reg_clsid_
        _debug('CreateKey( %s\\CLSID\\%s\\Logging"' % (_explain(HKCR), clsid))
        hkey = winreg.CreateKey(HKCR, rf"CLSID\{clsid}\Logging")
        for item in levels:
            name, value = item.split("=")
            v = getattr(logging, value)
            assert isinstance(v, int)
        _debug("SetValueEx(levels, %s)" % levels)
        winreg.SetValueEx(hkey, "levels", None, winreg.REG_MULTI_SZ, levels)
        if format:
            _debug("SetValueEx(format, %s)" % format)
            winreg.SetValueEx(hkey, "format", None, winreg.REG_SZ, format)
        else:
            _debug("DeleteValue(format)")
            try:
                winreg.DeleteValue(hkey, "format")
            except OSError as detail:
                if get_winerror(detail) != 2:
                    raise

    def register(self, cls: type, executable: Optional[str] = None) -> None:
        """Register the COM server class."""
        # First, we unregister the object with force=True, to force removal
        # of all registry entries, even if we would not write them.
        # Second, we create new entries.
        # It seems ATL does the same.
        mth = getattr(cls, "_register", None)
        if mth is not None:
            mth(self)
        else:
            self._unregister(cls, force=True)
            self._register(cls, executable)

    def _register(self, cls: type, executable: Optional[str] = None) -> None:
        table = sorted(self._generate_reg_entries(cls))
        _debug("Registering %s", cls)
        for hkey, subkey, valuename, value in table:
            _debug("[%s\\%s]", _explain(hkey), subkey)
            _debug('%s="%s"', valuename or "@", value)
            k = winreg.CreateKey(hkey, subkey)
            winreg.SetValueEx(k, valuename, None, winreg.REG_SZ, str(value))

        tlib = getattr(cls, "_reg_typelib_", None)
        if tlib is not None:
            if self._frozendllhandle is not None:
                frozen_dll = _get_serverdll(self._frozendllhandle)
                _debug("LoadTypeLibEx(%s, REGKIND_REGISTER)", frozen_dll)
                LoadTypeLibEx(frozen_dll, REGKIND_REGISTER)
            else:
                if executable:
                    path = executable
                elif self._frozen is not None:
                    path = sys.executable
                else:
                    path = cls._typelib_path_
                _debug("LoadTypeLibEx(%s, REGKIND_REGISTER)", path)
                LoadTypeLibEx(path, REGKIND_REGISTER)
        _debug("Done")

    def unregister(self, cls: type, force: bool = False) -> None:
        """Unregister the COM server class."""
        mth = getattr(cls, "_unregister", None)
        if mth is not None:
            mth(self)
        else:
            self._unregister(cls, force=force)

    def _unregister(self, cls: type, force: bool = False) -> None:
        # If force==False, we only remove those entries that we
        # actually would have written.  It seems ATL does the same.
        table = [t[:2] for t in self._generate_reg_entries(cls)]
        # reversed and only unique entries
        table = reversed(sorted(list(set(table))))
        _debug("Unregister %s", cls)
        for hkey, subkey in table:
            _delete_key(hkey, subkey, force=force)
        tlib = getattr(cls, "_reg_typelib_", None)
        if tlib is not None:
            try:
                _debug("UnRegisterTypeLib(%s, %s, %s)", *tlib)
                UnRegisterTypeLib(*tlib)
            except OSError as detail:
                if not get_winerror(detail) in (
                    TYPE_E_REGISTRYACCESS,
                    TYPE_E_CANTLOADLIBRARY,
                ):
                    raise
        _debug("Done")


def _get_serverdll(handle: int) -> str:
    """Return the pathname of the dll hosting the COM object."""
    return GetModuleFileName(handle, MAX_PATH)


class RegistryEntries(abc.ABC):
    """Iterator of tuples containing registry entries.

    The tuples must be (key, subkey, name, value).

    Required entries:
    =================
    _reg_clsid_ - a string or GUID instance
    _reg_clsctx_ - server type(s) to register

    Optional entries:
    =================
    _reg_desc_ - a string
    _reg_progid_ - a string naming the progid, typically 'MyServer.MyObject.1'
    _reg_novers_progid_ - version independend progid, typically 'MyServer.MyObject'
    _reg_typelib_ - an tuple (libid, majorversion, minorversion) specifying a typelib.
    _reg_threading_ - a string specifying the threading model

    Note that the first part of the progid string is typically the
    IDL library name of the type library containing the coclass.
    """

    @abc.abstractmethod
    def __iter__(self) -> Iterator[_Entry]: ...


class FrozenRegistryEntries(RegistryEntries):
    def __init__(
        self,
        cls: type,
        frozen: Union[str, int],
        frozendllhandle: Optional[int] = None,
    ) -> None:
        self._cls = cls
        self._frozen = frozen
        self._frozendllhandle = frozendllhandle

    def __iter__(self) -> Iterator[_Entry]:
        # that's the only required attribute for registration
        reg_clsid = str(self._cls._reg_clsid_)
        yield from _iter_reg_entries(self._cls, reg_clsid)
        clsctx: int = getattr(self._cls, "_reg_clsctx_", 0)
        localsvr_ctx = bool(clsctx & CLSCTX_LOCAL_SERVER)
        inprocsvr_ctx = bool(clsctx & CLSCTX_INPROC_SERVER)
        if localsvr_ctx and self._frozendllhandle is None:
            yield from _iter_frozen_local_ctx_entries(self._cls, reg_clsid)
        if inprocsvr_ctx and self._frozen == "dll":
            assert self._frozendllhandle is not None
            frozen_dll = _get_serverdll(self._frozendllhandle)
            yield from _iter_inproc_ctx_entries(reg_clsid, frozen_dll)
            yield from _iter_inproc_threading_model_entries(self._cls, reg_clsid)
        yield from _iter_tlib_entries(self._cls, reg_clsid)


class InterpRegistryEntries(RegistryEntries):
    def __init__(self, cls: type) -> None:
        self._cls = cls

    def __iter__(self) -> Iterator[_Entry]:
        # that's the only required attribute for registration
        reg_clsid = str(self._cls._reg_clsid_)
        yield from _iter_reg_entries(self._cls, reg_clsid)
        clsctx: int = getattr(self._cls, "_reg_clsctx_", 0)
        localsvr_ctx = bool(clsctx & CLSCTX_LOCAL_SERVER)
        inprocsvr_ctx = bool(clsctx & CLSCTX_INPROC_SERVER)
        if localsvr_ctx:
            yield from _iter_interp_local_ctx_entries(self._cls, reg_clsid)
        if inprocsvr_ctx:
            yield from _iter_inproc_ctx_entries(reg_clsid, _ctypes.__file__)
            # only for non-frozen inproc servers the PythonPath/PythonClass is needed.
            yield from _iter_inproc_python_entries(self._cls, reg_clsid)
            yield from _iter_inproc_threading_model_entries(self._cls, reg_clsid)
        yield from _iter_tlib_entries(self._cls, reg_clsid)


def _get_full_classname(cls: type) -> str:
    """Return <modulename>.<classname> for 'cls'."""
    modname = cls.__module__
    if modname == "__main__":
        modname = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    return f"{modname}.{cls.__name__}"


def _get_pythonpath(cls: type) -> str:
    """Return the filesystem path of the module containing 'cls'."""
    modname = cls.__module__
    dirname = os.path.dirname(sys.modules[modname].__file__)  # type: ignore
    return os.path.abspath(dirname)


def _iter_reg_entries(cls: type, reg_clsid: str) -> Iterator[_Entry]:
    # basic entry - names the comobject
    reg_desc = getattr(cls, "_reg_desc_", "")
    if not reg_desc:
        # Simple minded algorithm to construct a description from the progid:
        reg_desc = getattr(cls, "_reg_novers_progid_", getattr(cls, "_reg_progid_", ""))
        if reg_desc:
            reg_desc = reg_desc.replace(".", " ")
    yield (HKCR, rf"CLSID\{reg_clsid}", "", reg_desc)

    reg_progid = getattr(cls, "_reg_progid_", None)
    if reg_progid:
        # for ProgIDFromCLSID:
        yield (HKCR, rf"CLSID\{reg_clsid}\ProgID", "", reg_progid)  # 1

        # for CLSIDFromProgID
        if reg_desc:
            yield (HKCR, reg_progid, "", reg_desc)  # 2
        yield (HKCR, rf"{reg_progid}\CLSID", "", reg_clsid)  # 3

        reg_novers_progid = getattr(cls, "_reg_novers_progid_", None)
        if reg_novers_progid:
            yield (
                HKCR,
                rf"CLSID\{reg_clsid}\VersionIndependentProgID",  # 1a
                "",
                reg_novers_progid,
            )
            if reg_desc:
                yield (HKCR, reg_novers_progid, "", reg_desc)  # 2a
            yield (HKCR, rf"{reg_novers_progid}\CurVer", "", reg_progid)  #
            yield (HKCR, rf"{reg_novers_progid}\CLSID", "", reg_clsid)  # 3a


def _iter_interp_local_ctx_entries(cls: type, reg_clsid: str) -> Iterator[_Entry]:
    exe = sys.executable
    exe = f'"{exe}"' if " " in exe else exe
    exe = f"{exe} -O" if not __debug__ else exe
    script = os.path.abspath(sys.modules[cls.__module__].__file__)  # type: ignore
    script = f'"{script}"' if " " in script else script
    yield (HKCR, rf"CLSID\{reg_clsid}\LocalServer32", "", f"{exe} {script}")


def _iter_frozen_local_ctx_entries(cls: type, reg_clsid: str) -> Iterator[_Entry]:
    exe = sys.executable
    exe = f'"{exe}"' if " " in exe else exe
    yield (HKCR, rf"CLSID\{reg_clsid}\LocalServer32", "", f"{exe}")


def _iter_inproc_ctx_entries(reg_clsid: str, dllfile: str) -> Iterator[_Entry]:
    # Register InprocServer32 only when run from script or from
    # py2exe dll server, not from py2exe exe server.
    yield (HKCR, rf"CLSID\{reg_clsid}\InprocServer32", "", dllfile)


def _iter_inproc_python_entries(cls: type, reg_clsid: str) -> Iterator[_Entry]:
    # only for non-frozen inproc servers the PythonPath/PythonClass is needed.
    yield (
        HKCR,
        rf"CLSID\{reg_clsid}\InprocServer32",
        "PythonClass",
        _get_full_classname(cls),
    )
    yield (
        HKCR,
        rf"CLSID\{reg_clsid}\InprocServer32",
        "PythonPath",
        _get_pythonpath(cls),
    )


def _iter_inproc_threading_model_entries(cls: type, reg_clsid: str) -> Iterator[_Entry]:
    reg_threading = getattr(cls, "_reg_threading_", None)
    if reg_threading is not None:
        yield (
            HKCR,
            rf"CLSID\{reg_clsid}\InprocServer32",
            "ThreadingModel",
            reg_threading,
        )


def _iter_tlib_entries(cls: type, reg_clsid: str) -> Iterator[_Entry]:
    reg_tlib = getattr(cls, "_reg_typelib_", None)
    if reg_tlib is not None:
        yield (HKCR, rf"CLSID\{reg_clsid}\Typelib", "", reg_tlib[0])


################################################################


def register(cls: type) -> None:
    Registrar().register(cls)


def unregister(cls: type) -> None:
    Registrar().unregister(cls)


def UseCommandLine(*classes: type) -> int:
    usage = f"""Usage: {sys.argv[0]} [-regserver] [-unregserver] [-nodebug] [-f logformat] [-l loggername=level]"""
    opts, args = w_getopt(sys.argv[1:], "regserver unregserver embedding l: f: nodebug")
    if not opts:
        sys.stderr.write(usage + "\n")
        return 0  # nothing for us to do

    levels = []
    format = None
    nodebug = False
    runit = False
    for option, value in opts:
        if option == "regserver":
            for cls in classes:
                register(cls)
        elif option == "unregserver":
            for cls in classes:
                unregister(cls)
        elif option == "embedding":
            runit = True
        elif option == "f":
            format = value
        elif option == "l":
            levels.append(value)
        elif option == "nodebug":
            nodebug = True

    if levels or format is not None:
        for cls in classes:
            Registrar().debug(cls, levels, format)
    if nodebug:
        for cls in classes:
            Registrar().nodebug(cls)

    if runit:
        run_localserver(classes)

    return 1  # we have done something


if __name__ == "__main__":
    UseCommandLine()
