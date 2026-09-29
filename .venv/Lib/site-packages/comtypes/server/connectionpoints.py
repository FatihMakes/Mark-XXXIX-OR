import functools
import logging
from _ctypes import COMError
from collections.abc import Callable, Iterator
from ctypes import c_void_p, pointer
from ctypes.wintypes import DWORD
from typing import TYPE_CHECKING, Any
from typing import Union as _UnionT

from comtypes import GUID, COMObject, IUnknown
from comtypes.automation import IDispatch
from comtypes.connectionpoints import IConnectionPoint
from comtypes.hresult import *
from comtypes.typeinfo import ITypeInfo, LoadRegTypeLib

if TYPE_CHECKING:
    from ctypes import _Pointer
    from typing import ClassVar

    from comtypes import hints  # type: ignore

logger = logging.getLogger(__name__)

__all__ = ["ConnectableObjectMixin"]


class ConnectionPointImpl(COMObject):
    """This object implements a connectionpoint"""

    _com_interfaces_ = [IConnectionPoint]

    def __init__(
        self, sink_interface: type[IUnknown], sink_typeinfo: ITypeInfo
    ) -> None:
        super().__init__()
        self._connections: dict[int, IUnknown] = {}
        self._cookie = 0
        self._sink_interface = sink_interface
        self._typeinfo = sink_typeinfo

    # per MSDN, all interface methods *must* be implemented, E_NOTIMPL
    # is no allowed return value

    def IConnectionPoint_Advise(
        self, this: Any, pUnk: IUnknown, pdwCookie: "_Pointer[DWORD]"
    ) -> "hints.Hresult":
        if not pUnk or not pdwCookie:
            return E_POINTER
        logger.debug("Advise")
        try:
            ptr = pUnk.QueryInterface(self._sink_interface)
        except COMError:
            return CONNECT_E_CANNOTCONNECT
        pdwCookie[0] = self._cookie = self._cookie + 1
        self._connections[self._cookie] = ptr
        return S_OK

    def IConnectionPoint_Unadvise(self, this: Any, dwCookie: int) -> "hints.Hresult":
        logger.debug("Unadvise %s", dwCookie)
        try:
            del self._connections[dwCookie]
        except KeyError:
            return CONNECT_E_NOCONNECTION
        return S_OK

    def IConnectionPoint_GetConnectionPointContainer(
        self, this: Any, ppCPC: c_void_p
    ) -> "hints.Hresult":
        return E_NOTIMPL

    def IConnectionPoint_GetConnectionInterface(
        self, this: Any, pIID: "_Pointer[GUID]"
    ) -> "hints.Hresult":
        return E_NOTIMPL

    def _call_sinks(self, name: str, *args: Any, **kw: Any) -> list[Any]:
        results = []
        logger.debug("_call_sinks(%s, %s, *%s, **%s)", self, name, args, kw)
        # Is it an IDispatch derived interface?  Then, events have to be delivered
        # via Invoke calls (even if it is a dual interface).
        if hasattr(self._sink_interface, "Invoke"):
            # for better performance, we could cache the dispids.
            dispid = self._typeinfo.GetIDsOfNames(name)[0]
            for key, p in self._connections.items():
                mth = functools.partial(p.Invoke, dispid)  # type: ignore
                results.extend(self._call_sink(name, key, mth, *args, **kw))
        else:
            for key, p in self._connections.items():
                mth = getattr(p, name)
                results.extend(self._call_sink(name, key, mth, *args, **kw))
        return results

    def _call_sink(
        self, name: str, key: int, mth: Callable[..., Any], *args: Any, **kw: Any
    ) -> Iterator[Any]:
        try:
            result = mth(*args, **kw)
        except COMError as details:
            if details.hresult == RPC_S_SERVER_UNAVAILABLE:
                warn_msg = "_call_sinks(%s, %s, *%s, **%s) failed; removing connection"
                logger.warning(warn_msg, self, name, args, kw, exc_info=True)
                try:
                    del self._connections[key]
                except KeyError:
                    pass  # connection already gone
            else:
                warn_msg = "_call_sinks(%s, %s, *%s, **%s)"
                logger.warning(warn_msg, self, name, args, kw, exc_info=True)
        else:
            yield result


class ConnectableObjectMixin:
    """Mixin which implements IConnectionPointContainer.

    Call Fire_Event(interface, methodname, *args, **kw) to fire an
    event.  <interface> can either be the source interface, or an
    integer index into the _outgoing_interfaces_ list.
    """

    if TYPE_CHECKING:
        _outgoing_interfaces_: ClassVar[list[type[IDispatch]]]
        _reg_typelib_: ClassVar[tuple[str, int, int]]

    def __init__(self) -> None:
        super().__init__()
        self.__connections: dict[type[IDispatch], ConnectionPointImpl] = {}

        tlib = LoadRegTypeLib(*self._reg_typelib_)
        for itf in self._outgoing_interfaces_:
            typeinfo = tlib.GetTypeInfoOfGuid(itf._iid_)
            self.__connections[itf] = ConnectionPointImpl(itf, typeinfo)

    def IConnectionPointContainer_EnumConnectionPoints(
        self, this: Any, ppEnum: c_void_p
    ) -> "hints.Hresult":
        # according to MSDN, E_NOTIMPL is specificially disallowed
        # because, without typeinfo, there's no way for the caller to
        # find out.
        return E_NOTIMPL

    def IConnectionPointContainer_FindConnectionPoint(
        self, this: Any, refiid: "_Pointer[GUID]", ppcp: c_void_p
    ) -> "hints.Hresult":
        iid = refiid[0]
        logger.debug("FindConnectionPoint %s", iid)
        if not ppcp:
            return E_POINTER
        for itf in self._outgoing_interfaces_:
            if itf._iid_ == iid:
                # 'byref' will not work in this case, since the QueryInterface
                # method implementation is called on Python directly. There's
                # no C layer between which will convert the second parameter
                # from byref() to pointer().
                conn = self.__connections[itf]
                result = conn.IUnknown_QueryInterface(
                    None, pointer(IConnectionPoint._iid_), ppcp
                )
                logger.debug("connectionpoint found, QI() -> %s", result)
                return result
        logger.debug("No connectionpoint found")
        return CONNECT_E_NOCONNECTION

    def Fire_Event(
        self, itf: _UnionT[int, type[IDispatch]], name: str, *args: Any, **kw: Any
    ) -> Any:
        # Fire event 'name' with arguments *args and **kw.
        # Accepts either an interface index or an interface as first argument.
        # Returns a list of results.
        logger.debug("Fire_Event(%s, %s, *%s, **%s)", itf, name, args, kw)
        if isinstance(itf, int):
            itf = self._outgoing_interfaces_[itf]
        return self.__connections[itf]._call_sinks(name, *args, **kw)
