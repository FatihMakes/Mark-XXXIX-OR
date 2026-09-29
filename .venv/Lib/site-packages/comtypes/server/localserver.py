import logging
import queue
from collections.abc import Sequence
from ctypes import HRESULT, OleDLL, byref, c_ulong, c_void_p
from ctypes.wintypes import DWORD, LPDWORD
from typing import TYPE_CHECKING, Any, Literal, Optional

import comtypes
from comtypes import GUID, COMObject, IUnknown, hresult
from comtypes.GUID import REFCLSID
from comtypes.server import IClassFactory

if TYPE_CHECKING:
    from ctypes import _Pointer


logger = logging.getLogger(__name__)
_debug = logger.debug

REGCLS_SINGLEUSE = 0  # class object only generates one instance
REGCLS_MULTIPLEUSE = 1  # same class object genereates multiple inst.
REGCLS_MULTI_SEPARATE = 2  # multiple use, but separate control over each
REGCLS_SUSPENDED = 4  # register it as suspended, will be activated
REGCLS_SURROGATE = 8  # must be used when a surrogate process

_ole32 = OleDLL("ole32")

_CoRegisterClassObject = _ole32.CoRegisterClassObject
_CoRegisterClassObject.argtypes = [REFCLSID, c_void_p, DWORD, DWORD, LPDWORD]
_CoRegisterClassObject.restype = HRESULT

_CoRevokeClassObject = _ole32.CoRevokeClassObject
_CoRevokeClassObject.argtypes = [DWORD]
_CoRevokeClassObject.restype = HRESULT


def run(classes: Sequence[type[COMObject]]) -> None:
    classobjects = [ClassFactory(cls) for cls in classes]
    COMObject.__run_localserver__(classobjects)


class ClassFactory(COMObject):
    _com_interfaces_ = [IClassFactory]
    _locks: int = 0
    _queue: Optional[queue.Queue] = None
    regcls: int = REGCLS_MULTIPLEUSE

    def __init__(self, cls: type[COMObject], *args, **kw) -> None:
        super().__init__()
        self._cls = cls
        self._register_class()
        self._args = args
        self._kw = kw

    def IUnknown_AddRef(self, this: Any) -> int:
        return 2

    def IUnknown_Release(self, this: Any) -> int:
        return 1

    def _register_class(self) -> None:
        regcls = getattr(self._cls, "_regcls_", self.regcls)
        cookie = c_ulong()
        ptr = self._com_pointers_[IUnknown._iid_]
        clsctx = self._cls._reg_clsctx_  # type: ignore
        clsctx &= ~comtypes.CLSCTX_INPROC  # reset the inproc flags
        _CoRegisterClassObject(
            byref(GUID(self._cls._reg_clsid_)),
            ptr,
            clsctx,
            regcls,
            byref(cookie),
        )
        self.cookie = cookie

    def _revoke_class(self) -> None:
        _CoRevokeClassObject(self.cookie)

    def CreateInstance(
        self,
        this: Any,
        punkOuter: Optional[type["_Pointer[IUnknown]"]],
        riid: "_Pointer[GUID]",
        ppv: c_void_p,
    ) -> int:
        _debug("ClassFactory.CreateInstance(%s)", riid[0])
        obj = self._cls(*self._args, **self._kw)
        result = obj.IUnknown_QueryInterface(None, riid, ppv)
        _debug("CreateInstance() -> %s", result)
        return result

    def LockServer(self, this: Any, fLock: bool) -> Literal[0]:
        assert COMObject.__server__ is not None, "The localserver is not running yet"
        if fLock:
            COMObject.__server__.Lock()
        else:
            COMObject.__server__.Unlock()
        return hresult.S_OK
