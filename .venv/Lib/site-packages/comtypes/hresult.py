# comtypes.hresult
# COM success and error codes
#
# Note that the codes should be written in decimal notation!

from ctypes import c_long

S_OK = 0
S_FALSE = 1

E_UNEXPECTED = -2147418113  # 0x8000FFFFL

E_NOTIMPL = -2147467263  # 0x80004001L
E_NOINTERFACE = -2147467262  # 0x80004002L
E_POINTER = -2147467261  # 0x80004003L
E_FAIL = -2147467259  # 0x80004005L
E_INVALIDARG = -2147024809  # 0x80070057L
E_OUTOFMEMORY = -2147024882  # 0x8007000EL

CLASS_E_NOAGGREGATION = -2147221232  # 0x80040110L
CLASS_E_CLASSNOTAVAILABLE = -2147221231  # 0x80040111L

CO_E_CLASSSTRING = -2147221005  # 0x800401F3L

# connection point error codes
CONNECT_E_CANNOTCONNECT = -2147220990
CONNECT_E_ADVISELIMIT = -2147220991
CONNECT_E_NOCONNECTION = -2147220992

TYPE_E_ELEMENTNOTFOUND = -2147319765  # 0x8002802B

TYPE_E_REGISTRYACCESS = -2147319780  # 0x8002801CL
TYPE_E_CANTLOADLIBRARY = -2147312566  # 0x80029C4AL

# all the DISP_E_ values from windows.h
DISP_E_BUFFERTOOSMALL = -2147352557
DISP_E_DIVBYZERO = -2147352558
DISP_E_NOTACOLLECTION = -2147352559
DISP_E_BADCALLEE = -2147352560
DISP_E_PARAMNOTOPTIONAL = -2147352561  # 0x8002000F
DISP_E_BADPARAMCOUNT = -2147352562  # 0x8002000E
DISP_E_ARRAYISLOCKED = -2147352563  # 0x8002000D
DISP_E_UNKNOWNLCID = -2147352564  # 0x8002000C
DISP_E_BADINDEX = -2147352565  # 0x8002000B
DISP_E_OVERFLOW = -2147352566  # 0x8002000A
DISP_E_EXCEPTION = -2147352567  # 0x80020009
DISP_E_BADVARTYPE = -2147352568  # 0x80020008
DISP_E_NONAMEDARGS = -2147352569  # 0x80020007
DISP_E_UNKNOWNNAME = -2147352570  # 0x80020006
DISP_E_TYPEMISMATCH = -2147352571  # 0800020005
DISP_E_PARAMNOTFOUND = -2147352572  # 0x80020004
DISP_E_MEMBERNOTFOUND = -2147352573  # 0x80020003
DISP_E_UNKNOWNINTERFACE = -2147352575  # 0x80020001

RPC_E_CHANGED_MODE = -2147417850  # 0x80010106
RPC_E_SERVERFAULT = -2147417851  # 0x80010105

RPC_E_NO_SYNC = -2147417824  # 0x80010120
RPC_S_CALLPENDING = -2147417835  # 0x80010115

# 'macros' and constants to create your own HRESULT values:


def MAKE_HRESULT(sev: int, fac: int, code: int) -> int:
    """Creates an HRESULT value from its component pieces."""
    # A hresult is SIGNED in comtypes
    return c_long((sev << 31 | fac << 16 | code)).value


SEVERITY_ERROR = 1
SEVERITY_SUCCESS = 0

FACILITY_ITF = 4
FACILITY_WIN32 = 7


def HRESULT_FROM_WIN32(x: int) -> int:
    """Converts a system error code to an HRESULT value."""
    # make signed
    x = c_long(x).value
    if x < 0:
        return x
    # 0x80000000 | FACILITY_WIN32 << 16 | x & 0xFFFF
    return c_long(0x80070000 | (x & 0xFFFF)).value


# Win32 error codes are defined as unsigned 32-bit integers. However, to
# ensure compatibility with COM and other HRESULT-based APIs, Windows converts
# them into HRESULT values by setting the high bit, ensuring a consistent way
# to indicate failure across these APIs.
RPC_S_SERVER_UNAVAILABLE = -2147023174  # 0x800706BA (WIN32: 1722 0x6BA)


################################################################
# signed32bithex
#
# When using this package, error codes for exceptions like
# `COMError` or `WindowsError` are base10 integers.
#
# However, as shown below, many technical references represent
# HRESULT values using signed 32-bit hexadecimal notation:
# https://learn.microsoft.com/en-us/windows/win32/seccrypto/common-hresult-values
# https://learn.microsoft.com/en-us/windows/win32/learnwin32/error-codes-in-com
#
# If you search for the error code using the proper notation,
# you might be able to find the reference.
#
# Don't be overly afraid of `COMError` or `WindowsError`!


def signed32bithex_to_int(value: str, /) -> int:
    """Converts a string in signed 32-bit hexadecimal notation to an integer.

    Examples:

        >>> signed32bithex_to_int('0x00000000') == 0  # S_OK
        True
        >>> signed32bithex_to_int('0x00000001') == 1  # S_FALSE
        True
        >>> signed32bithex_to_int('0x8000FFFF') == -2147418113  # E_UNEXPECTED
        True
    """
    val = int(value, 16)
    if val < 0x80000000:
        return val
    return val - 0x100000000


def int_to_signed32bithex(value: int, /) -> str:
    """Converts an integer to a string in signed 32-bit hexadecimal notation.

    Examples:

        >>> import comtypes.hresult as hr
        >>> int_to_signed32bithex(hr.S_OK)
        '0x00000000'
        >>> int_to_signed32bithex(hr.S_FALSE)
        '0x00000001'
        >>> int_to_signed32bithex(hr.E_UNEXPECTED)
        '0x8000FFFF'

        >>> from comtypes import CoCreateInstance
        >>> from comtypes import shelllink, automation
        >>> CLSID_ShellLink = shelllink.ShellLink().IPersist_GetClassID()
        >>> p = CoCreateInstance(CLSID_ShellLink)
        >>> p.QueryInterface(shelllink.IShellLinkA)  # doctest: +ELLIPSIS
        <POINTER(IShellLinkA) ptr=0x... at ...>
        >>> p.QueryInterface(automation.IDispatch)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        _ctypes.COMError: (-2147467262, ..., (None, None, None, 0, None))
        >>> int_to_signed32bithex(-2147467262)  # E_NOINTERFACE
        '0x80004002'
    """
    # it is simpler than using `hex(value & 0xFFFFFFFF)`
    return f"0x{value & 0xFFFFFFFF:08X}"


################################################################
