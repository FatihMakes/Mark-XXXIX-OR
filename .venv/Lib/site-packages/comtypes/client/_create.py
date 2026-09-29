import logging
from typing import TYPE_CHECKING, Any, Literal, Optional, TypeVar, overload
from typing import Union as _UnionT

import comtypes
import comtypes.client.dynamic
from comtypes import COSERVERINFO, GUID, CoClass, IUnknown, automation
from comtypes.client._managing import _manage

if TYPE_CHECKING:
    from ctypes import _CArgObject

    from comtypes import hints  # type: ignore


_T_IUnknown = TypeVar("_T_IUnknown", bound=IUnknown)
logger = logging.getLogger(__name__)


################################################################
#
# Object creation
#
@overload
def GetClassObject(
    progid: _UnionT[str, type[CoClass], GUID],
    clsctx: Optional[int] = None,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
    interface: None = None,
) -> "hints.IClassFactory": ...
@overload
def GetClassObject(
    progid: _UnionT[str, type[CoClass], GUID],
    clsctx: Optional[int] = None,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
    interface: type[_T_IUnknown] = IUnknown,
) -> _T_IUnknown: ...
def GetClassObject(
    progid: _UnionT[str, type[CoClass], GUID],
    clsctx: Optional[int] = None,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
    interface: Optional[type[IUnknown]] = None,
) -> IUnknown:
    """Create and return the class factory for a COM object.

    'clsctx' specifies how to create the object, use the CLSCTX_... constants.
    'pServerInfo', if used, must be a pointer to a comtypes.COSERVERINFO instance
    'interface' may be used to request an interface other than IClassFactory
    """
    clsid = GUID.from_progid(progid)
    return comtypes.CoGetClassObject(clsid, clsctx, pServerInfo, interface)


@overload
def CreateObject(progid: _UnionT[str, type[CoClass], GUID]) -> Any: ...
@overload
def CreateObject(
    progid: _UnionT[str, type[CoClass], GUID],
    clsctx: Optional[int] = None,
    machine: Optional[str] = None,
    interface: None = None,
    dynamic: Literal[False] = False,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
) -> Any: ...
@overload
def CreateObject(
    progid: _UnionT[str, type[CoClass], GUID],
    clsctx: Optional[int] = None,
    machine: Optional[str] = None,
    interface: None = None,
    dynamic: Literal[True] = True,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
) -> _UnionT[
    "comtypes.client.lazybind.Dispatch", "comtypes.client.dynamic._Dispatch"
]: ...
@overload
def CreateObject(
    progid: _UnionT[str, type[CoClass], GUID],
    clsctx: Optional[int] = None,
    machine: Optional[str] = None,
    interface: type[_T_IUnknown] = IUnknown,
    dynamic: Literal[False] = False,
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,
) -> _T_IUnknown: ...
def CreateObject(
    progid: _UnionT[str, type[CoClass], GUID],  # which object to create
    clsctx: Optional[int] = None,  # how to create the object
    machine: Optional[str] = None,  # where to create the object
    interface: Optional[type[IUnknown]] = None,  # the interface we want
    dynamic: bool = False,  # use dynamic dispatch
    pServerInfo: "_UnionT[None, _CArgObject, COSERVERINFO]" = None,  # server info struct for remoting
) -> Any:
    """Create a COM object from 'progid', and try to QueryInterface()
    it to the most useful interface, generating typelib support on
    demand.  A pointer to this interface is returned.

    'progid' may be a string like "InternetExplorer.Application",
       a string specifying a clsid, a GUID instance, or an object with
       a _clsid_ attribute which should be any of the above.
    'clsctx' specifies how to create the object, use the CLSCTX_... constants.
    'machine' allows to specify a remote machine to create the object on.
    'interface' allows to force a certain interface
    'dynamic=True' will return a dynamic dispatch object
    'pServerInfo', if used, must be a pointer to a comtypes.COSERVERINFO instance
        This supercedes 'machine'.

    You can also later request to receive events with GetEvents().
    """
    clsid = GUID.from_progid(progid)
    logger.debug("%s -> %s", progid, clsid)
    if dynamic:
        if interface:
            raise ValueError("interface and dynamic are mutually exclusive")
        interface = automation.IDispatch
    elif interface is None:
        interface = getattr(progid, "_com_interfaces_", [None])[0]
    if machine is None and pServerInfo is None:
        logger.debug(
            "CoCreateInstance(%s, clsctx=%s, interface=%s)", clsid, clsctx, interface
        )
        obj = comtypes.CoCreateInstance(clsid, clsctx=clsctx, interface=interface)
    else:
        logger.debug(
            "CoCreateInstanceEx(%s, clsctx=%s, interface=%s, machine=%s,\
                        pServerInfo=%s)",
            clsid,
            clsctx,
            interface,
            machine,
            pServerInfo,
        )
        if machine is not None and pServerInfo is not None:
            msg = "You cannot set both the machine name and server info."
            raise ValueError(msg)
        obj = comtypes.CoCreateInstanceEx(
            clsid,
            clsctx=clsctx,
            interface=interface,
            machine=machine,
            pServerInfo=pServerInfo,
        )
    if dynamic:
        return comtypes.client.dynamic.Dispatch(obj)
    return _manage(obj, clsid, interface=interface)


@overload
def CoGetObject(
    displayname: str,
    interface: None = None,
    dynamic: Literal[False] = False,
) -> Any: ...
@overload
def CoGetObject(
    displayname: str,
    interface: None = None,
    dynamic: Literal[True] = True,
) -> _UnionT[
    "comtypes.client.lazybind.Dispatch", "comtypes.client.dynamic._Dispatch"
]: ...
@overload
def CoGetObject(
    displayname: str,
    interface: type[_T_IUnknown],
    dynamic: Literal[False] = False,
) -> _T_IUnknown: ...
def CoGetObject(
    displayname: str,
    interface: Optional[type[IUnknown]] = None,
    dynamic: bool = False,
) -> Any:
    """Create an object by calling CoGetObject(displayname).

    Additional parameters have the same meaning as in CreateObject().
    """
    if dynamic:
        if interface is not None:
            raise ValueError("interface and dynamic are mutually exclusive")
        interface = automation.IDispatch
    punk = comtypes.CoGetObject(displayname, interface)
    if dynamic:
        return comtypes.client.dynamic.Dispatch(punk)
    return _manage(punk, clsid=None, interface=interface)
