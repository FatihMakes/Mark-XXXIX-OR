import contextlib
import ctypes
import logging
import threading
import unittest as ut
from collections.abc import Iterator
from ctypes import POINTER, WinDLL, c_void_p
from ctypes import c_size_t as SIZE_T
from ctypes.wintypes import BOOL, DWORD, HANDLE, LPCWSTR
from queue import Queue
from typing import TYPE_CHECKING, Optional
from typing import Union as _UnionT

from comtypes.client._events import SECURITY_ATTRIBUTES
from comtypes.logutil import NTDebugHandler, deprecated
from comtypes.logutil import (
    _OutputDebugStringW as OutputDebugStringW,
)

if TYPE_CHECKING:
    from ctypes import _CArgObject, _Pointer


class Test_deprecated(ut.TestCase):
    def test_warning_is_raised(self):
        reason_text = "This is deprecated."

        @deprecated(reason_text)
        def test_func():
            return "success"

        with self.assertWarns(DeprecationWarning) as cm:
            result = test_func()
        self.assertEqual(result, "success")
        self.assertEqual(reason_text, str(cm.warning))


_kernel32 = WinDLL("kernel32", use_last_error=True)

# https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw
_CreateEventW = _kernel32.CreateEventW
_CreateEventW.argtypes = [POINTER(SECURITY_ATTRIBUTES), BOOL, BOOL, LPCWSTR]
_CreateEventW.restype = HANDLE

# https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-setevent
_SetEvent = _kernel32.SetEvent
_SetEvent.argtypes = [HANDLE]
_SetEvent.restype = BOOL

# https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject
_WaitForSingleObject = _kernel32.WaitForSingleObject
_WaitForSingleObject.argtypes = [HANDLE, DWORD]
_WaitForSingleObject.restype = DWORD

# https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-createfilemappingw
_CreateFileMappingW = _kernel32.CreateFileMappingW
_CreateFileMappingW.argtypes = [
    HANDLE,
    POINTER(SECURITY_ATTRIBUTES),
    DWORD,
    DWORD,
    DWORD,
    LPCWSTR,
]
_CreateFileMappingW.restype = HANDLE

# https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-mapviewoffile
_MapViewOfFile = _kernel32.MapViewOfFile
_MapViewOfFile.argtypes = [HANDLE, DWORD, DWORD, DWORD, SIZE_T]
_MapViewOfFile.restype = c_void_p

# https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-unmapviewoffile
_UnmapViewOfFile = _kernel32.UnmapViewOfFile
_UnmapViewOfFile.argtypes = [c_void_p]
_UnmapViewOfFile.restype = BOOL

# https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
_CloseHandle = _kernel32.CloseHandle
_CloseHandle.argtypes = [HANDLE]
_CloseHandle.restype = BOOL

# https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getcurrentprocessid
_GetCurrentProcessId = _kernel32.GetCurrentProcessId
_GetCurrentProcessId.argtypes = []
_GetCurrentProcessId.restype = DWORD


@contextlib.contextmanager
def create_file_mapping(
    hfile: int,
    security: _UnionT["_Pointer[SECURITY_ATTRIBUTES]", "_CArgObject", None],
    flprotect: int,
    size_high: int,
    size_low: int,
    name: Optional[str],
) -> Iterator[int]:
    """Context manager to creates a Windows file mapping object."""
    handle = _CreateFileMappingW(hfile, security, flprotect, size_high, size_low, name)
    assert handle, ctypes.FormatError(ctypes.get_last_error())
    try:
        yield handle
    finally:
        _CloseHandle(handle)


@contextlib.contextmanager
def map_view_of_file(
    handle: int, access: int, offset_high: int, offset_low: int, size: int
) -> Iterator[int]:
    """Context manager to map a view of a file mapping into the process's
    address space.
    """
    p_view = _MapViewOfFile(handle, access, offset_high, offset_low, size)
    assert p_view, ctypes.FormatError(ctypes.get_last_error())
    try:
        yield p_view
    finally:
        _UnmapViewOfFile(p_view)


@contextlib.contextmanager
def create_event(
    security: _UnionT["_Pointer[SECURITY_ATTRIBUTES]", "_CArgObject", None],
    manual: bool,
    init: bool,
    name: Optional[str],
) -> Iterator[int]:
    """Context manager to creates a Windows event object."""
    handle = _CreateEventW(security, manual, init, name)
    assert handle, ctypes.FormatError(ctypes.get_last_error())
    try:
        yield handle
    finally:
        _CloseHandle(handle)


DBWIN_BUFFER_SIZE = 4096  # Longer messages are truncated at the source by the OS
WAIT_OBJECT_0 = 0x00000000
PAGE_READWRITE = 0x04
FILE_MAP_READ = 0x04
INVALID_HANDLE_VALUE = -1  # Backed by the system paging file instead of a file on disk


@contextlib.contextmanager
def open_dbwin_debug_channels() -> Iterator[tuple[int, int, int]]:
    """Context manager to open the standard Windows debug output channels
    (events and shared memory).
    Yields handles to `DBWIN_BUFFER_READY`, `DBWIN_DATA_READY`, and a pointer
    to `DBWIN_BUFFER`.
    """
    with (
        # "DBWIN_BUFFER_READY": An event signaled by the listener to indicate
        # it's ready to receive debug output. `OutputDebugString` waits for this.
        create_event(None, False, False, "DBWIN_BUFFER_READY") as h_buffer_ready,
        # "DBWIN_DATA_READY": An event signaled by `OutputDebugString` to
        # indicate new data is written to the shared buffer. Listener waits.
        create_event(None, False, False, "DBWIN_DATA_READY") as h_data_ready,
        # "DBWIN_BUFFER": A shared memory region where `OutputDebugString`
        # writes the debug string data.
        create_file_mapping(
            INVALID_HANDLE_VALUE,
            None,
            PAGE_READWRITE,
            0,
            DBWIN_BUFFER_SIZE,
            "DBWIN_BUFFER",
        ) as h_mapping,
        # Map the shared memory region into the listener's address space
        # for reading the debug strings.
        map_view_of_file(h_mapping, FILE_MAP_READ, 0, 0, DBWIN_BUFFER_SIZE) as p_view,
    ):
        yield (h_buffer_ready, h_data_ready, p_view)


def _listen_on_dbwin_channel(
    interval_ms: int,
    messages: Queue,
    ready: threading.Event,
    stop: threading.Event,
    pid: int,
) -> None:
    # Create/open named events and file mapping for interprocess communication.
    # These objects are part of the Windows Debugging API contract.
    with open_dbwin_debug_channels() as (h_buffer_ready, h_data_ready, p_view):
        ready.set()  # Signal to the main thread that listener is ready.
        while not stop.is_set():  # Loop until the main thread signals to finish.
            _SetEvent(h_buffer_ready)  # Signal readiness to `OutputDebugString`.
            # Wait for `OutputDebugString` to signal that data is ready.
            if _WaitForSingleObject(h_data_ready, interval_ms) == WAIT_OBJECT_0:
                # Debug string buffer format: [4 bytes: PID][N bytes: string].
                # Check if the process ID in the buffer matches the current PID.
                if ctypes.cast(p_view, POINTER(DWORD)).contents.value == pid:
                    # Extract the null-terminated string, skipping the PID,
                    # and put it into the queue.
                    messages.put(ctypes.string_at(p_view + 4).strip(b"\x00"))


@contextlib.contextmanager
def _run_dbwin_listener(ready: threading.Event, interval_ms: int) -> Iterator[Queue]:
    messages = Queue()
    stop = threading.Event()
    th = threading.Thread(
        target=_listen_on_dbwin_channel,
        args=(interval_ms, messages, ready, stop, _GetCurrentProcessId()),
        daemon=True,
    )
    th.start()
    try:
        yield messages
    finally:
        stop.set()
        th.join()


@contextlib.contextmanager
def capture_debug_strings(*, timeout: float, interval: float) -> Iterator[Queue]:
    """Context manager to capture debug strings emitted via `OutputDebugString`.
    Spawns a listener thread to monitor the debug channels.

    Parameters are floats in seconds.
    """
    ready = threading.Event()
    with _run_dbwin_listener(ready, int(interval * 1000)) as messages:
        ready.wait(timeout=timeout)  # Wait for the listener to be ready
        yield messages


class Test_OutputDebugStringW(ut.TestCase):
    def test(self):
        with capture_debug_strings(timeout=5, interval=0.1) as cap:
            OutputDebugStringW("hello world")
            OutputDebugStringW("test message")
        self.assertEqual(cap.get(), b"hello world")
        self.assertEqual(cap.get(), b"test message")


class Test_NTDebugHandler(ut.TestCase):
    def test_emit(self):
        handler = NTDebugHandler()
        # Direct `Logger()` instantiation for test isolation: bypasses global
        # registration and prevents any side effects / cross-test pollution.
        # (The official 'Loggers should NEVER be instantiated directly' rule
        # targets production code where hierarchy and propagation matter;
        # here we want neither.)
        # https://docs.python.org/3/library/logging.html#logger-objects
        logger = logging.Logger("test_ntdebug_handler")
        # Clear existing handlers to prevent interference from other tests
        logger.propagate = False
        logger.handlers = []
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        with capture_debug_strings(timeout=5, interval=0.1) as cap:
            msg = "This is a test message from NTDebugHandler."
            logger.info(msg)
        logger.removeHandler(handler)
        handler.close()
        self.assertEqual(cap.get(), msg.encode("utf-8") + b"\n")
