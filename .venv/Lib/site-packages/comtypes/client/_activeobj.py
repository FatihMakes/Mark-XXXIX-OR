from typing import Any, Literal, Optional, TypeVar, overload
from typing import Union as _UnionT

import comtypes
import comtypes.client.dynamic
from comtypes import GUID, CoClass, IUnknown, automation
from comtypes.client._managing import _manage

_T_IUnknown = TypeVar("_T_IUnknown", bound=IUnknown)


################################################################
#
# Object creation
#
@overload
def GetActiveObject(
    progid: _UnionT[str, type[CoClass], GUID],
    interface: None = None,
    dynamic: Literal[False] = False,
) -> Any: ...
@overload
def GetActiveObject(
    progid: _UnionT[str, type[CoClass], GUID],
    interface: None = None,
    dynamic: Literal[True] = True,
) -> _UnionT[
    "comtypes.client.lazybind.Dispatch", "comtypes.client.dynamic._Dispatch"
]: ...
@overload
def GetActiveObject(
    progid: _UnionT[str, type[CoClass], GUID],
    interface: type[_T_IUnknown] = IUnknown,
    dynamic: Literal[False] = False,
) -> _T_IUnknown: ...
def GetActiveObject(
    progid: _UnionT[str, type[CoClass], GUID],
    interface: Optional[type[IUnknown]] = None,
    dynamic: bool = False,
) -> Any:
    """Return a pointer to a running COM object that has been
    registered with COM.

    'progid' may be a string like "Excel.Application",
       a string specifying a clsid, a GUID instance, or an object with
       a _clsid_ attribute which should be any of the above.
    'interface' allows to force a certain interface.
    'dynamic=True' will return a dynamic dispatch object.
    """
    clsid = GUID.from_progid(progid)
    if dynamic:
        if interface is not None:
            raise ValueError("interface and dynamic are mutually exclusive")
        interface = automation.IDispatch
    elif interface is None:
        interface = getattr(progid, "_com_interfaces_", [None])[0]
    obj = comtypes.GetActiveObject(clsid, interface=interface)
    if dynamic:
        return comtypes.client.dynamic.Dispatch(obj)
    return _manage(obj, clsid, interface=interface)


def RegisterActiveObject(
    punk: IUnknown, progid: _UnionT[str, type[CoClass], GUID], weak: bool = True
) -> int:
    clsid = GUID.from_progid(progid)
    flags = comtypes.ACTIVEOBJECT_WEAK if weak else comtypes.ACTIVEOBJECT_STRONG
    return comtypes.RegisterActiveObject(punk, clsid, flags)
