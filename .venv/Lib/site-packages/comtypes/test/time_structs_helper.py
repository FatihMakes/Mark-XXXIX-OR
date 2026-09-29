from ctypes import POINTER, Structure, WinDLL, byref
from ctypes.wintypes import BOOL, FILETIME, LONG, WORD
from typing import Literal


class SYSTEMTIME(Structure):
    _fields_ = [
        ("wYear", WORD),
        ("wMonth", WORD),
        ("wDayOfWeek", WORD),
        ("wDay", WORD),
        ("wHour", WORD),
        ("wMinute", WORD),
        ("wSecond", WORD),
        ("wMilliseconds", WORD),
    ]


_kernel32 = WinDLL("kernel32")

# https://learn.microsoft.com/en-us/windows/win32/api/timezoneapi/nf-timezoneapi-systemtimetofiletime
_SystemTimeToFileTime = _kernel32.SystemTimeToFileTime
_SystemTimeToFileTime.argtypes = [POINTER(SYSTEMTIME), POINTER(FILETIME)]
_SystemTimeToFileTime.restype = BOOL

# https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-comparefiletime
_CompareFileTime = _kernel32.CompareFileTime
_CompareFileTime.argtypes = [POINTER(FILETIME), POINTER(FILETIME)]
_CompareFileTime.restype = LONG


def SystemTimeToFileTime(st: SYSTEMTIME, /) -> FILETIME:
    ft = FILETIME()
    assert _SystemTimeToFileTime(byref(st), byref(ft))
    return ft


def CompareFileTime(ft1: FILETIME, ft2: FILETIME, /) -> Literal[-1, 0, 1]:
    return _CompareFileTime(byref(ft1), byref(ft2))
