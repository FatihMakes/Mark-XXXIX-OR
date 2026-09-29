from collections.abc import Callable
from ctypes import (
    HRESULT,
    POINTER,
    OleDLL,
    Structure,
    byref,
    c_ulong,
    c_ushort,
    c_void_p,
    c_wchar_p,
    cast,
    pointer,
)
from ctypes.wintypes import DWORD, LPCWSTR, LPVOID
from typing import TYPE_CHECKING, Any, Optional, TypeVar, overload
from typing import Union as _UnionT

from comtypes import CLSCTX_LOCAL_SERVER, CLSCTX_REMOTE_SERVER, CLSCTX_SERVER, GUID
from comtypes._memberspec import COMMETHOD
from comtypes._post_coinit.unknwn import IUnknown
from comtypes.GUID import REFCLSID

if TYPE_CHECKING:
    from ctypes import _CArgObject, _Pointer

    from comtypes import hints as hints  # noqa  # type: ignore


def _is_object(obj):
    """This function determines if the argument is a COM object.  It
    is used in several places to determine whether propputref or
    propput setters have to be used."""
    from comtypes.automation import VARIANT

    # A COM pointer is an 'Object'
    if isinstance(obj, POINTER(IUnknown)):
        return True
    # A COM pointer in a VARIANT is an 'Object', too
    elif isinstance(obj, VARIANT) and isinstance(obj.value, POINTER(IUnknown)):
        return True
    # It may be a dynamic dispatch object.
    return hasattr(obj, "_comobj")


_T_IUnknown = TypeVar("_T_IUnknown", bound=IUnknown)


################################################################
# IPersist is a trivial interface, which allows to ask an object about
# its clsid.
class IPersist(IUnknown):
    _iid_ = GUID("{0000010C-0000-0000-C000-000000000046}")
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, "GetClassID", (["out"], POINTER(GUID), "pClassID")),
    ]
    if TYPE_CHECKING:
        # Should this be "normal" method that calls `self._GetClassID`?
        def GetClassID(self) -> GUID:
            """Returns the CLSID that uniquely represents an object class that
            defines the code that can manipulate the object's data.
            """
            ...


class IServiceProvider(IUnknown):
    _iid_ = GUID("{6D5140C1-7436-11CE-8034-00AA006009FA}")
    _QueryService: Callable[[Any, Any, Any], int]

    # Overridden QueryService to make it nicer to use (passing it an
    # interface and it returns a pointer to that interface)
    def QueryService(
        self, serviceIID: GUID, interface: type[_T_IUnknown]
    ) -> _T_IUnknown:
        p = POINTER(interface)()
        self._QueryService(byref(serviceIID), byref(interface._iid_), byref(p))
        return p  # type: ignore

    _methods_ = [
        COMMETHOD(
            [],
            HRESULT,
            "QueryService",
            (["in"], POINTER(GUID), "guidService"),
            (["in"], POINTER(GUID), "riid"),
            (["in"], POINTER(c_void_p), "ppvObject"),
        )
    ]


################################################################


@overload
def CoGetObject(displayname: str, interface: None) -> IUnknown: ...
@overload
def CoGetObject(displayname: str, interface: type[_T_IUnknown]) -> _T_IUnknown: ...
def CoGetObject(displayname: str, interface: Optional[type[IUnknown]]) -> IUnknown:
    """Convert a displayname to a moniker, then bind and return the object
    identified by the moniker."""
    if interface is None:
        interface = IUnknown
    punk = POINTER(interface)()
    # Do we need a way to specify the BIND_OPTS parameter?
    _CoGetObject(str(displayname), None, byref(interface._iid_), byref(punk))
    return punk  # type: ignore


_pUnkOuter = type["_Pointer[IUnknown]"]


@overload
def CoCreateInstance(
    clsid: GUID,
    interface: None = None,
    clsctx: Optional[int] = None,
    punkouter: Optional[_pUnkOuter] = None,
) -> IUnknown: ...
@overload
def CoCreateInstance(
    clsid: GUID,
    interface: type[_T_IUnknown],
    clsctx: Optional[int] = None,
    punkouter: Optional[_pUnkOuter] = None,
) -> _T_IUnknown: ...
def CoCreateInstance(
    clsid: GUID,
    interface: Optional[type[IUnknown]] = None,
    clsctx: Optional[int] = None,
    punkouter: Optional[_pUnkOuter] = None,
) -> IUnknown:
    """The basic windows api to create a COM class object and return a
    pointer to an interface.
    """
    if clsctx is None:
        clsctx = CLSCTX_SERVER
    if interface is None:
        interface = IUnknown
    p = POINTER(interface)()
    iid = interface._iid_
    _CoCreateInstance(byref(clsid), punkouter, clsctx, byref(iid), byref(p))
    return p  # type: ignore


@overload
def CoGetClassObject(
    clsid: GUID,
    clsctx: Optional[int] = None,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
    interface: None = None,
) -> "hints.IClassFactory": ...
@overload
def CoGetClassObject(
    clsid: GUID,
    clsctx: Optional[int] = None,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
    interface: type[_T_IUnknown] = IUnknown,
) -> _T_IUnknown: ...
def CoGetClassObject(
    clsid: GUID,
    clsctx: Optional[int] = None,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
    interface: Optional[type[IUnknown]] = None,
) -> IUnknown:
    if clsctx is None:
        clsctx = CLSCTX_SERVER
    if interface is None:
        import comtypes.server

        interface = comtypes.server.IClassFactory
    p = POINTER(interface)()
    _CoGetClassObject(clsid, clsctx, pServerInfo, interface._iid_, byref(p))
    return p  # type: ignore


class MULTI_QI(Structure):
    _fields_ = [("pIID", POINTER(GUID)), ("pItf", POINTER(c_void_p)), ("hr", HRESULT)]
    if TYPE_CHECKING:
        pIID: GUID
        pItf: _Pointer[c_void_p]
        hr: HRESULT


class _COAUTHIDENTITY(Structure):
    _fields_ = [
        ("User", POINTER(c_ushort)),
        ("UserLength", c_ulong),
        ("Domain", POINTER(c_ushort)),
        ("DomainLength", c_ulong),
        ("Password", POINTER(c_ushort)),
        ("PasswordLength", c_ulong),
        ("Flags", c_ulong),
    ]


COAUTHIDENTITY = _COAUTHIDENTITY


class _COAUTHINFO(Structure):
    _fields_ = [
        ("dwAuthnSvc", c_ulong),
        ("dwAuthzSvc", c_ulong),
        ("pwszServerPrincName", c_wchar_p),
        ("dwAuthnLevel", c_ulong),
        ("dwImpersonationLevel", c_ulong),
        ("pAuthIdentityData", POINTER(_COAUTHIDENTITY)),
        ("dwCapabilities", c_ulong),
    ]


COAUTHINFO = _COAUTHINFO


class _COSERVERINFO(Structure):
    _fields_ = [
        ("dwReserved1", c_ulong),
        ("pwszName", c_wchar_p),
        ("pAuthInfo", POINTER(_COAUTHINFO)),
        ("dwReserved2", c_ulong),
    ]
    if TYPE_CHECKING:
        dwReserved1: int
        pwszName: Optional[str]
        pAuthInfo: _COAUTHINFO
        dwReserved2: int


_ole32 = OleDLL("ole32")

COSERVERINFO = _COSERVERINFO
_CoGetClassObject = _ole32.CoGetClassObject
_CoGetClassObject.argtypes = [
    POINTER(GUID),
    DWORD,
    POINTER(COSERVERINFO),
    POINTER(GUID),
    POINTER(c_void_p),
]
_CoGetClassObject.restype = HRESULT

_CoCreateInstance = _ole32.CoCreateInstance
_CoCreateInstance.argtypes = [
    REFCLSID,
    POINTER(IUnknown),
    DWORD,
    POINTER(GUID),
    POINTER(LPVOID),
]
_CoCreateInstance.restype = HRESULT

_CoCreateInstanceEx = _ole32.CoCreateInstanceEx
_CoCreateInstanceEx.argtypes = [
    REFCLSID,
    POINTER(IUnknown),
    DWORD,
    POINTER(COSERVERINFO),
    DWORD,
    POINTER(MULTI_QI),
]
_CoCreateInstanceEx.restype = HRESULT


class tagBIND_OPTS(Structure):
    _fields_ = [
        ("cbStruct", c_ulong),
        ("grfFlags", c_ulong),
        ("grfMode", c_ulong),
        ("dwTickCountDeadline", c_ulong),
    ]


# XXX Add __init__ which sets cbStruct?
BIND_OPTS = tagBIND_OPTS
_CoGetObject = _ole32.CoGetObject
_CoGetObject.argtypes = [LPCWSTR, POINTER(BIND_OPTS), POINTER(GUID), POINTER(LPVOID)]
_CoGetObject.restype = HRESULT


class tagBIND_OPTS2(Structure):
    _fields_ = [
        ("cbStruct", c_ulong),
        ("grfFlags", c_ulong),
        ("grfMode", c_ulong),
        ("dwTickCountDeadline", c_ulong),
        ("dwTrackFlags", c_ulong),
        ("dwClassContext", c_ulong),
        ("locale", c_ulong),
        ("pServerInfo", POINTER(_COSERVERINFO)),
    ]


# XXX Add __init__ which sets cbStruct?
BINDOPTS2 = tagBIND_OPTS2


# Structures for security setups
#########################################
class _SEC_WINNT_AUTH_IDENTITY(Structure):
    _fields_ = [
        ("User", POINTER(c_ushort)),
        ("UserLength", c_ulong),
        ("Domain", POINTER(c_ushort)),
        ("DomainLength", c_ulong),
        ("Password", POINTER(c_ushort)),
        ("PasswordLength", c_ulong),
        ("Flags", c_ulong),
    ]


SEC_WINNT_AUTH_IDENTITY = _SEC_WINNT_AUTH_IDENTITY


class _SOLE_AUTHENTICATION_INFO(Structure):
    _fields_ = [
        ("dwAuthnSvc", c_ulong),
        ("dwAuthzSvc", c_ulong),
        ("pAuthInfo", POINTER(_SEC_WINNT_AUTH_IDENTITY)),
    ]


SOLE_AUTHENTICATION_INFO = _SOLE_AUTHENTICATION_INFO


class _SOLE_AUTHENTICATION_LIST(Structure):
    _fields_ = [
        ("cAuthInfo", c_ulong),
        ("pAuthInfo", POINTER(_SOLE_AUTHENTICATION_INFO)),
    ]


SOLE_AUTHENTICATION_LIST = _SOLE_AUTHENTICATION_LIST


@overload
def CoCreateInstanceEx(
    clsid: GUID,
    interface: None = None,
    clsctx: Optional[int] = None,
    machine: Optional[str] = None,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
) -> IUnknown: ...
@overload
def CoCreateInstanceEx(
    clsid: GUID,
    interface: type[_T_IUnknown],
    clsctx: Optional[int] = None,
    machine: Optional[str] = None,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
) -> _T_IUnknown: ...
def CoCreateInstanceEx(
    clsid: GUID,
    interface: Optional[type[IUnknown]] = None,
    clsctx: Optional[int] = None,
    machine: Optional[str] = None,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
) -> IUnknown:
    """The basic windows api to create a COM class object and return a
    pointer to an interface, possibly on another machine.

    Passing both "machine" and "pServerInfo" results in a ValueError.

    """
    if clsctx is None:
        clsctx = CLSCTX_LOCAL_SERVER | CLSCTX_REMOTE_SERVER

    if pServerInfo is not None:
        if machine is not None:
            msg = "Can not specify both machine name and server info"
            raise ValueError(msg)
    elif machine is not None:
        serverinfo = COSERVERINFO()
        serverinfo.pwszName = machine
        pServerInfo = byref(serverinfo)  # type: ignore

    if interface is None:
        interface = IUnknown
    multiqi = MULTI_QI()
    multiqi.pIID = pointer(interface._iid_)  # type: ignore
    _CoCreateInstanceEx(byref(clsid), None, clsctx, pServerInfo, 1, byref(multiqi))
    return cast(multiqi.pItf, POINTER(interface))  # type: ignore
