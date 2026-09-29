import sys
from ctypes import POINTER, OleDLL, byref, c_wchar_p
from ctypes.wintypes import DWORD, ULONG
from typing import TYPE_CHECKING, Optional
from typing import Union as _UnionT

from comtypes import BSTR, COMMETHOD, GUID, HRESULT, IUnknown
from comtypes.hresult import DISP_E_EXCEPTION, S_OK

if TYPE_CHECKING:
    from comtypes import hints  # type: ignore

LPCOLESTR = c_wchar_p


class ICreateErrorInfo(IUnknown):
    _iid_ = GUID("{22F03340-547D-101B-8E65-08002B2BD119}")
    _methods_ = [
        COMMETHOD([], HRESULT, "SetGUID", (["in"], POINTER(GUID), "rguid")),
        COMMETHOD([], HRESULT, "SetSource", (["in"], LPCOLESTR, "szSource")),
        COMMETHOD([], HRESULT, "SetDescription", (["in"], LPCOLESTR, "szDescription")),
        COMMETHOD([], HRESULT, "SetHelpFile", (["in"], LPCOLESTR, "szHelpFile")),
        COMMETHOD([], HRESULT, "SetHelpContext", (["in"], DWORD, "dwHelpContext")),
    ]
    if TYPE_CHECKING:

        def SetGUID(self, rguid: GUID) -> hints.Hresult: ...
        def SetSource(self, szSource: str) -> hints.Hresult: ...
        def SetDescription(self, szDescription: str) -> hints.Hresult: ...
        def SetHelpFile(self, szHelpFile: str) -> hints.Hresult: ...
        def SetHelpContext(self, dwHelpContext: int) -> hints.Hresult: ...


class IErrorInfo(IUnknown):
    _iid_ = GUID("{1CF2B120-547D-101B-8E65-08002B2BD119}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetGUID", (["out"], POINTER(GUID), "pGUID")),
        COMMETHOD([], HRESULT, "GetSource", (["out"], POINTER(BSTR), "pBstrSource")),
        COMMETHOD(
            [], HRESULT, "GetDescription", (["out"], POINTER(BSTR), "pBstrDescription")
        ),
        COMMETHOD(
            [], HRESULT, "GetHelpFile", (["out"], POINTER(BSTR), "pBstrHelpFile")
        ),
        COMMETHOD(
            [], HRESULT, "GetHelpContext", (["out"], POINTER(DWORD), "pdwHelpContext")
        ),
    ]
    if TYPE_CHECKING:

        def GetGUID(self) -> GUID: ...
        def GetSource(self) -> str: ...
        def GetDescription(self) -> str: ...
        def GetHelpFile(self) -> str: ...
        def GetHelpContext(self) -> int: ...


class ISupportErrorInfo(IUnknown):
    _iid_ = GUID("{DF0B3D60-548F-101B-8E65-08002B2BD119}")
    _methods_ = [
        COMMETHOD(
            [], HRESULT, "InterfaceSupportsErrorInfo", (["in"], POINTER(GUID), "riid")
        )
    ]
    if TYPE_CHECKING:

        def InterfaceSupportsErrorInfo(self, riid: GUID) -> hints.Hresult: ...


################################################################
_oleaut32 = OleDLL("oleaut32")

_CreateErrorInfo = _oleaut32.CreateErrorInfo
_CreateErrorInfo.argtypes = [POINTER(POINTER(ICreateErrorInfo))]
_CreateErrorInfo.restype = HRESULT

_GetErrorInfo = _oleaut32.GetErrorInfo
_GetErrorInfo.argtypes = [ULONG, POINTER(POINTER(IErrorInfo))]
_GetErrorInfo.restype = HRESULT

_SetErrorInfo = _oleaut32.SetErrorInfo
_SetErrorInfo.argtypes = [ULONG, POINTER(IErrorInfo)]
_SetErrorInfo.restype = HRESULT


def CreateErrorInfo() -> ICreateErrorInfo:
    """Creates an instance of a generic error object."""
    cei = POINTER(ICreateErrorInfo)()
    _CreateErrorInfo(byref(cei))
    return cei  # type: ignore


def GetErrorInfo() -> Optional[IErrorInfo]:
    """Get the error information for the current thread."""
    errinfo = POINTER(IErrorInfo)()
    if S_OK == _GetErrorInfo(0, byref(errinfo)):
        return errinfo  # type: ignore
    return None


def SetErrorInfo(errinfo: _UnionT[IErrorInfo, ICreateErrorInfo]) -> "hints.Hresult":
    """Set error information for the current thread."""
    # ICreateErrorInfo can QueryInterface with IErrorInfo, so both types are
    # accepted, thanks to the magic of from_param.
    return _SetErrorInfo(0, errinfo)


def ReportError(
    text: str,
    iid: GUID,
    clsid: _UnionT[None, str, GUID] = None,
    helpfile: Optional[str] = None,
    helpcontext: Optional[int] = 0,
    hresult: int = DISP_E_EXCEPTION,
) -> int:
    """Report a COM error.  Returns the passed in hresult value."""
    ei = CreateErrorInfo()
    ei.SetDescription(text)
    ei.SetGUID(iid)
    if helpfile is not None:
        ei.SetHelpFile(helpfile)
    if helpcontext is not None:
        ei.SetHelpContext(helpcontext)
    if clsid is not None:
        if isinstance(clsid, str):
            clsid = GUID(clsid)
        try:
            progid = clsid.as_progid()
        except OSError:
            pass
        else:
            # progid for the class or application that created the error
            ei.SetSource(progid)
    SetErrorInfo(ei)
    return hresult


def ReportException(
    hresult: int,
    iid: GUID,
    clsid: _UnionT[None, str, GUID] = None,
    helpfile: Optional[str] = None,
    helpcontext: Optional[int] = None,
    stacklevel: Optional[int] = None,
) -> int:
    """Report a COM exception.  Returns the passed in hresult value."""
    typ, value, tb = sys.exc_info()
    if stacklevel is not None:
        for _ in range(stacklevel):
            if tb is None:
                raise ValueError("'stacklevel' exceeds the available depth.")
            tb = tb.tb_next
        if tb is None:
            raise ValueError("'stacklevel' is specified, but no error information.")
        line = tb.tb_frame.f_lineno
        name = tb.tb_frame.f_globals["__name__"]
        text = f"{typ}: {value} ({name}, line {line:d})"
    else:
        text = f"{typ}: {value}"
    return ReportError(
        text,
        iid,
        clsid=clsid,
        helpfile=helpfile,
        helpcontext=helpcontext,
        hresult=hresult,
    )


# fmt: off
__all__ = [
    "ICreateErrorInfo", "IErrorInfo", "ISupportErrorInfo", "ReportError",
    "ReportException", "SetErrorInfo", "GetErrorInfo", "CreateErrorInfo",
]
# fmt: on
