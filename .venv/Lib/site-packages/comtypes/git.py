"""comtypes.git - access the process wide global interface table

The global interface table provides a way to marshal interface pointers
between different threading appartments.
"""

from ctypes import POINTER
from ctypes.wintypes import DWORD
from typing import Type, TypeVar

from comtypes import (
    CLSCTX_INPROC_SERVER,
    GUID,
    HRESULT,
    STDMETHOD,
    CoCreateInstance,
    IUnknown,
)

_T_IUnknown = TypeVar("_T_IUnknown", bound=IUnknown)


class IGlobalInterfaceTable(IUnknown):
    _iid_ = GUID("{00000146-0000-0000-C000-000000000046}")
    _methods_ = [
        STDMETHOD(
            HRESULT,
            "RegisterInterfaceInGlobal",
            [POINTER(IUnknown), POINTER(GUID), POINTER(DWORD)],
        ),
        STDMETHOD(HRESULT, "RevokeInterfaceFromGlobal", [DWORD]),
        STDMETHOD(
            HRESULT,
            "GetInterfaceFromGlobal",
            [DWORD, POINTER(GUID), POINTER(POINTER(IUnknown))],
        ),
    ]

    def RegisterInterfaceInGlobal(
        self, obj: IUnknown, interface: Type[_T_IUnknown] = IUnknown
    ) -> int:
        cookie = DWORD()
        self.__com_RegisterInterfaceInGlobal(obj, interface._iid_, cookie)  # type: ignore
        return cookie.value

    def GetInterfaceFromGlobal(
        self, cookie: int, interface: Type[_T_IUnknown] = IUnknown
    ) -> _T_IUnknown:
        ptr = POINTER(interface)()
        self.__com_GetInterfaceFromGlobal(cookie, interface._iid_, ptr)  # type: ignore
        return ptr  # type: ignore

    def RevokeInterfaceFromGlobal(self, cookie: int) -> None:
        self.__com_RevokeInterfaceFromGlobal(cookie)  # type: ignore


# It was a pain to get this CLSID: it's neither in the registry, nor
# in any header files. I had to compile a C program, and find it out
# with the debugger.  Apparently it is in uuid.lib.
CLSID_StdGlobalInterfaceTable = GUID("{00000323-0000-0000-C000-000000000046}")

git = CoCreateInstance(
    CLSID_StdGlobalInterfaceTable,
    interface=IGlobalInterfaceTable,
    clsctx=CLSCTX_INPROC_SERVER,
)

RevokeInterfaceFromGlobal = git.RevokeInterfaceFromGlobal
RegisterInterfaceInGlobal = git.RegisterInterfaceInGlobal
GetInterfaceFromGlobal = git.GetInterfaceFromGlobal

# fmt: off
__all__ = [
    "RegisterInterfaceInGlobal", "RevokeInterfaceFromGlobal",
    "GetInterfaceFromGlobal",
]
# fmt: on
