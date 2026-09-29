import ctypes
import logging
import traceback
from _ctypes import COMError
from collections.abc import Callable
from ctypes import HRESULT, POINTER, WINFUNCTYPE, OleDLL, Structure, WinDLL, byref
from ctypes.wintypes import (
    BOOL,
    DWORD,
    HANDLE,
    LPCSTR,
    LPDWORD,
    LPHANDLE,
    LPVOID,
    ULONG,
)
from typing import Any, Optional
from typing import Union as _UnionT

import comtypes
from comtypes import COMObject, IUnknown, hresult
from comtypes._comobject import _MethodFinder
from comtypes.automation import DISPATCH_METHOD, IDispatch
from comtypes.client._generate import GetModule
from comtypes.connectionpoints import IConnectionPoint, IConnectionPointContainer
from comtypes.typeinfo import GUIDKIND_DEFAULT_SOURCE_DISP_IID, IProvideClassInfo2

logger = logging.getLogger(__name__)


class SECURITY_ATTRIBUTES(Structure):
    _fields_ = [
        ("nLength", DWORD),
        ("lpSecurityDescriptor", LPVOID),
        ("bInheritHandle", BOOL),
    ]


_ole32 = OleDLL("ole32")

_CoWaitForMultipleHandles = _ole32.CoWaitForMultipleHandles
_CoWaitForMultipleHandles.argtypes = [DWORD, DWORD, ULONG, LPHANDLE, LPDWORD]
_CoWaitForMultipleHandles.restype = HRESULT


_kernel32 = WinDLL("kernel32")

_CreateEventA = _kernel32.CreateEventA
_CreateEventA.argtypes = [POINTER(SECURITY_ATTRIBUTES), BOOL, BOOL, LPCSTR]
_CreateEventA.restype = HANDLE

_SetEvent = _kernel32.SetEvent
_SetEvent.argtypes = [HANDLE]
_SetEvent.restype = BOOL

PHANDLER_ROUTINE = WINFUNCTYPE(BOOL, DWORD)
_SetConsoleCtrlHandler = _kernel32.SetConsoleCtrlHandler
_SetConsoleCtrlHandler.argtypes = [PHANDLER_ROUTINE, BOOL]
_SetConsoleCtrlHandler.restype = BOOL

_CloseHandle = _kernel32.CloseHandle
_CloseHandle.argtypes = [HANDLE]
_CloseHandle.restype = BOOL

_ReceiverType = _UnionT[COMObject, IUnknown]


class _AdviseConnection:
    cp: Optional[IConnectionPoint]
    cookie: Optional[int]
    receiver: Optional[_ReceiverType]

    def __init__(
        self, source: IUnknown, interface: type[IUnknown], receiver: _ReceiverType
    ) -> None:
        # Pre-initializing attributes to avoid AttributeError after failed connection.
        self.cp = None
        self.cookie = None
        self.receiver = None
        self._connect(source, interface, receiver)

    def _connect(
        self, source: IUnknown, interface: type[IUnknown], receiver: _ReceiverType
    ) -> None:
        cpc = source.QueryInterface(IConnectionPointContainer)
        self.cp = cpc.FindConnectionPoint(byref(interface._iid_))
        logger.debug("Start advise %s", interface)
        # Since `POINTER(IUnknown).from_param`(`_compointer_base.from_param`)
        # can accept a `COMObject` instance, `IConnectionPoint.Advise` can
        # take either a COM object or a COM interface pointer.
        self.cookie = self.cp.Advise(receiver)  # type: ignore
        self.receiver = receiver

    def disconnect(self) -> None:
        if self.cookie:
            assert self.cp is not None
            self.cp.Unadvise(self.cookie)
            logger.debug("Unadvised %s", self.cp)
            self.cp = None
            self.cookie = None
            del self.receiver

    def __del__(self) -> None:
        try:
            if self.cookie is not None:
                assert self.cp is not None
                self.cp.Unadvise(self.cookie)
        except (OSError, COMError):
            # Are we sure we want to ignore errors here?
            pass


def FindOutgoingInterface(source: IUnknown) -> type[IUnknown]:
    """XXX Describe the strategy that is used..."""
    # If the COM object implements IProvideClassInfo2, it is easy to
    # find the default outgoing interface.
    try:
        pci = source.QueryInterface(IProvideClassInfo2)
        guid = pci.GetGUID(GUIDKIND_DEFAULT_SOURCE_DISP_IID)
    except COMError:
        pass
    else:
        if guid == comtypes.GUID():
            # Some COM servers, even if they implement `IProvideClassInfo2`,
            # may return GUID_NULL instead of the default source interface's GUID.
            raise NotImplementedError("retrieved outgoing interface IID is GUID_NULL")
        # another try: block needed?
        try:
            interface = comtypes.com_interface_registry[str(guid)]
        except KeyError:
            tinfo = pci.GetClassInfo()
            tlib, index = tinfo.GetContainingTypeLib()
            GetModule(tlib)
            interface = comtypes.com_interface_registry[str(guid)]
        logger.debug("%s using sinkinterface %s", source, interface)
        return interface

    # If we can find the CLSID of the COM object, we can look for a
    # registered outgoing interface (__clsid has been set by
    # comtypes.client):
    clsid = source.__dict__.get("__clsid")
    try:
        interface = comtypes.com_coclass_registry[clsid]._outgoing_interfaces_[0]  # type: ignore
    except KeyError:
        pass
    else:
        logger.debug("%s using sinkinterface from clsid %s", source, interface)
        return interface

    # interface = find_single_connection_interface(source)
    # if interface:
    #     return interface

    raise TypeError("cannot determine source interface")


def find_single_connection_interface(source):
    # Enumerate the connection interfaces.  If we find a single one,
    # return it, if there are more, we give up since we cannot
    # determine which one to use.
    cpc = source.QueryInterface(IConnectionPointContainer)
    enum = cpc.EnumConnectionPoints()
    iid = enum.next().GetConnectionInterface()
    try:
        next(enum)
    except StopIteration:
        try:
            interface = comtypes.com_interface_registry[str(iid)]
        except KeyError:
            return None
        else:
            logger.debug("%s using sinkinterface from iid %s", source, interface)
            return interface
    else:
        logger.debug("%s has more than one connection point", source)

    return None


def report_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    # This decorator preserves parts of the decorated function
    # signature, so that the comtypes special-casing for the 'this'
    # parameter still works.
    if func.__code__.co_varnames[:2] == ("self", "this"):

        def with_this(self, this, *args, **kw):
            try:
                return func(self, this, *args, **kw)
            except:
                traceback.print_exc()
                raise

        error_printer = with_this

    else:

        def without_this(*args, **kw):
            try:
                return func(*args, **kw)
            except:
                traceback.print_exc()
                raise

        error_printer = without_this

    return error_printer


class _SinkMethodFinder(_MethodFinder):
    """Special MethodFinder, for finding and decorating event handler
    methods.  Looks for methods on two objects. Also decorates the
    event handlers with 'report_errors' which will print exceptions in
    event handlers.
    """

    def __init__(self, inst: COMObject, sink: Any) -> None:
        super().__init__(inst)
        self.sink = sink

    def find_method(self, fq_name: str, mthname: str) -> Callable[..., Any]:
        impl = self._find_method(fq_name, mthname)
        # Caller of this method catches AttributeError,
        # so we need to be careful in the following code
        # not to raise one...
        try:
            # impl is a bound method, dissect it...
            im_self, im_func = impl.__self__, impl.__func__
            # decorate it with an error printer...
            method = report_errors(im_func)
            # and make a new bound method from it again.
            return comtypes.instancemethod(method, im_self, type(im_self))
        except AttributeError as details:
            raise RuntimeError(details)

    def _find_method(self, fq_name: str, mthname: str) -> Callable[..., Any]:
        try:
            return super().find_method(fq_name, mthname)
        except AttributeError:
            try:
                return getattr(self.sink, fq_name)
            except AttributeError:
                return getattr(self.sink, mthname)


def CreateEventReceiver(interface: type[IUnknown], handler: Any) -> COMObject:
    class Sink(COMObject):
        _com_interfaces_ = [interface]

        def _get_method_finder_(self, itf: type[IUnknown]) -> _MethodFinder:
            # Use a special MethodFinder that will first try 'self',
            # then the sink.
            return _SinkMethodFinder(self, handler)

    sink = Sink()

    # Since our Sink object doesn't have typeinfo, it needs a
    # _dispimpl_ dictionary to dispatch events received via Invoke.
    if issubclass(interface, IDispatch) and not hasattr(sink, "_dispimpl_"):
        finder = sink._get_method_finder_(interface)
        dispimpl = sink._dispimpl_ = {}
        for m in interface._methods_:
            # Can dispid be at a different index? Should check code generator...
            # ...but hand-written code should also work...
            dispid = m.idlflags[0]
            if not isinstance(dispid, comtypes.dispid):
                # The interface is a subclass of `IDispatch` but its methods do not
                # have DISPIDs, indicating it's not an interface suitable for event
                # handling.
                raise NotImplementedError(
                    "Event receiver creation requires event methods to have DISPIDs "
                    f"for dispatching, but '{interface.__name__}' ({interface._iid_}) "
                    "lacks them, even though it inherits from 'IDispatch'."
                )
            impl = finder.get_impl(interface, m.name, m.paramflags, m.idlflags)
            # XXX Wouldn't work for 'propget', 'propput', 'propputref'
            # methods - are they allowed on event interfaces?
            dispimpl[(dispid, DISPATCH_METHOD)] = impl

    return sink


def GetEvents(
    source: IUnknown, sink: Any, interface: Optional[type[IUnknown]] = None
) -> _AdviseConnection:
    """Receive COM events from 'source'.  Events will call methods on
    the 'sink' object.  'interface' is the source interface to use.
    """
    # When called from CreateObject, the sourceinterface has already
    # been determined by the coclass.  Otherwise, the only thing that
    # makes sense is to use IProvideClassInfo2 to get the default
    # source interface.
    if interface is None:
        interface = FindOutgoingInterface(source)

    rcv = CreateEventReceiver(interface, sink)
    return _AdviseConnection(source, interface, rcv)


class EventDumper:
    """Universal sink for COM events."""

    def __getattr__(self, name: str) -> Callable[..., Any]:
        "Create event handler methods on demand"
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        print("# event found:", name)

        def handler(self, this, *args, **kw):
            # XXX handler is called with 'this'.  Should we really print "None" instead?
            args = (None,) + args
            print(f"Event {name}({', '.join([repr(a) for a in args])})")

        return comtypes.instancemethod(handler, self, EventDumper)


def ShowEvents(
    source: IUnknown, interface: Optional[type[IUnknown]] = None
) -> _AdviseConnection:
    """Receive COM events from 'source'.  A special event sink will be
    used that first prints the names of events that are found in the
    outgoing interface, and will also print out the events when they
    are fired.
    """
    return GetEvents(source, sink=EventDumper(), interface=interface)


# This type is used inside 'PumpEvents', but if we create the type
# afresh each time 'PumpEvents' is called we end up creating cyclic
# garbage for each call.  So we define it here instead.
_handles_type = ctypes.c_void_p * 1

# The type of control signal received by the handler.
CTRL_C_EVENT = 0
CTRL_BREAK_EVENT = 1
CTRL_CLOSE_EVENT = 2
CTRL_LOGOFF_EVENT = 5
CTRL_SHUTDOWN_EVENT = 6

# Specifiers for the behavior of the CoWaitForMultipleHandles function.
# tagCOWAIT_FLAGS = ctypes.c_int
COWAIT_DEFAULT = 0
COWAIT_WAITALL = 1
COWAIT_ALERTABLE = 2
COWAIT_INPUTAVAILABLE = 4
COWAIT_DISPATCH_CALLS = 8
COWAIT_DISPATCH_WINDOW_MESSAGES = 16


def PumpEvents(timeout: Any) -> None:
    """This following code waits for 'timeout' seconds in the way
    required for COM, internally doing the correct things depending
    on the COM appartment of the current thread.  It is possible to
    terminate the message loop by pressing CTRL+C, which will raise
    a KeyboardInterrupt.
    """
    # XXX Should there be a way to pass additional event handles which
    # can terminate this function?

    # XXX XXX XXX
    #
    # It may be that I misunderstood the CoWaitForMultipleHandles
    # function.  Is a message loop required in a STA?  Seems so...
    #
    # MSDN says:
    #
    # If the caller resides in a single-thread apartment,
    # CoWaitForMultipleHandles enters the COM modal loop, and the
    # thread's message loop will continue to dispatch messages using
    # the thread's message filter. If no message filter is registered
    # for the thread, the default COM message processing is used.
    #
    # If the calling thread resides in a multithread apartment (MTA),
    # CoWaitForMultipleHandles calls the Win32 function
    # MsgWaitForMultipleObjects.

    hevt = _CreateEventA(None, True, False, None)
    handles = _handles_type(hevt)

    # @ctypes.WINFUNCTYPE(BOOL, DWORD)
    def HandlerRoutine(dwCtrlType):
        if dwCtrlType == CTRL_C_EVENT:  # CTRL+C
            _SetEvent(hevt)
            return 1
        return 0

    _SetConsoleCtrlHandler(PHANDLER_ROUTINE(HandlerRoutine), 1)

    try:
        try:
            _CoWaitForMultipleHandles(
                COWAIT_DEFAULT,
                int(timeout * 1000),
                len(handles),
                handles,
                byref(ctypes.c_ulong()),
            )
        except OSError as details:
            if details.winerror != hresult.RPC_S_CALLPENDING:  # timeout expired
                raise
        else:
            raise KeyboardInterrupt
    finally:
        _CloseHandle(hevt)
        _SetConsoleCtrlHandler(PHANDLER_ROUTINE(HandlerRoutine), 0)
