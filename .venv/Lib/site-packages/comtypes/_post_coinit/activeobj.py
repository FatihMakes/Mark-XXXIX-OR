from ctypes import HRESULT, POINTER, OleDLL, byref, c_ulong, c_void_p
from ctypes.wintypes import DWORD, LPVOID
from typing import TYPE_CHECKING, Optional, TypeVar, overload
from typing import Union as _UnionT

from comtypes import GUID
from comtypes._post_coinit.unknwn import IUnknown
from comtypes.GUID import REFCLSID

if TYPE_CHECKING:
    from comtypes import hints  # type: ignore


_T_IUnknown = TypeVar("_T_IUnknown", bound=IUnknown)

ACTIVEOBJECT_STRONG = 0x0
ACTIVEOBJECT_WEAK = 0x1


def RegisterActiveObject(
    punk: "_UnionT[IUnknown, hints.LP_LP_Vtbl]", clsid: GUID, flags: int
) -> int:
    """Registers a pointer as the active object for its class and returns the handle."""
    handle = c_ulong()
    _RegisterActiveObject(punk, byref(clsid), flags, byref(handle))
    return handle.value


def RevokeActiveObject(handle: int) -> None:
    """Ends a pointer's status as active."""
    _RevokeActiveObject(handle, None)


@overload
def GetActiveObject(clsid: GUID, interface: None = None) -> IUnknown: ...
@overload
def GetActiveObject(clsid: GUID, interface: type[_T_IUnknown]) -> _T_IUnknown: ...
def GetActiveObject(
    clsid: GUID, interface: Optional[type[IUnknown]] = None
) -> IUnknown:
    """Retrieves a pointer to a running object"""
    p = POINTER(IUnknown)()
    _GetActiveObject(byref(clsid), None, byref(p))
    if interface is not None:
        p = p.QueryInterface(interface)  # type: ignore
    return p  # type: ignore


_oleaut32 = OleDLL("oleaut32")

_RegisterActiveObject = _oleaut32.RegisterActiveObject
_RegisterActiveObject.argtypes = [c_void_p, REFCLSID, DWORD, POINTER(DWORD)]
_RegisterActiveObject.restype = HRESULT

_RevokeActiveObject = _oleaut32.RevokeActiveObject
_RevokeActiveObject.argtypes = [DWORD, LPVOID]
_RevokeActiveObject.restype = HRESULT

_GetActiveObject = _oleaut32.GetActiveObject
_GetActiveObject.argtypes = [REFCLSID, LPVOID, POINTER(POINTER(IUnknown))]
_GetActiveObject.restype = HRESULT
