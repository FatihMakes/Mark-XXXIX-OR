import ctypes
from ctypes import POINTER, WinDLL, WinError, byref
from ctypes.wintypes import BOOL, HWND, MSG
from ctypes.wintypes import LPLONG as LRESULT
from typing import TYPE_CHECKING, SupportsIndex

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from ctypes import _CArgObject
    from typing import Any

    _FilterCallable = Callable[["_CArgObject"], Iterable[Any]]  # type: ignore

# PeekMessage options
PM_NOREMOVE = 0x0000
PM_REMOVE = 0x0001
PM_NOYIELD = 0x0002

_user32 = WinDLL("user32")

GetMessage = _user32.GetMessageA
GetMessage.argtypes = [POINTER(MSG), HWND, ctypes.c_uint, ctypes.c_uint]
GetMessage.restype = BOOL

TranslateMessage = _user32.TranslateMessage
TranslateMessage.argtypes = [POINTER(MSG)]
TranslateMessage.restype = BOOL

DispatchMessage = _user32.DispatchMessageA
DispatchMessage.argtypes = [POINTER(MSG)]
DispatchMessage.restype = LRESULT

# https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-peekmessagea
PeekMessage = _user32.PeekMessageA
PeekMessage.argtypes = [POINTER(MSG), HWND, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
PeekMessage.restype = BOOL


class _MessageLoop:
    def __init__(self) -> None:
        self._filters: list["_FilterCallable"] = []

    def insert_filter(self, obj: "_FilterCallable", index: SupportsIndex = -1) -> None:
        self._filters.insert(index, obj)

    def remove_filter(self, obj: "_FilterCallable") -> None:
        self._filters.remove(obj)

    def run(self) -> None:
        msg = MSG()
        lpmsg = byref(msg)
        while 1:
            ret = GetMessage(lpmsg, 0, 0, 0)
            if ret == -1:
                raise WinError()
            elif ret == 0:
                return  # got WM_QUIT
            if not self.filter_message(lpmsg):
                TranslateMessage(lpmsg)
                DispatchMessage(lpmsg)

    def filter_message(self, lpmsg: "_CArgObject") -> bool:
        return any(list(filter(lpmsg)) for filter in self._filters)


_messageloop = _MessageLoop()

run = _messageloop.run
insert_filter = _messageloop.insert_filter
remove_filter = _messageloop.remove_filter

__all__ = ["run", "insert_filter", "remove_filter"]
