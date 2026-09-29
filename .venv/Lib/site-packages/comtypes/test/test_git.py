import base64
import contextlib
import os
import tempfile
import threading
import unittest as ut
from _ctypes import COMError
from collections.abc import Iterator
from ctypes import HRESULT, POINTER, OleDLL, WinDLL, byref
from ctypes.wintypes import BOOL, DWORD, HANDLE, MSG
from pathlib import Path
from queue import Queue

import comtypes
from comtypes import GUID, IUnknown
from comtypes.git import (
    GetInterfaceFromGlobal,
    RegisterInterfaceInGlobal,
    RevokeInterfaceFromGlobal,
)
from comtypes.messageloop import (
    PM_REMOVE,
    DispatchMessage,
    PeekMessage,
    TranslateMessage,
)
from comtypes.persist import STGM_READ, IPersistFile

_user32 = WinDLL("user32")

# https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-msgwaitformultipleobjects
MsgWaitForMultipleObjects = _user32.MsgWaitForMultipleObjects
MsgWaitForMultipleObjects.restype = DWORD
MsgWaitForMultipleObjects.argtypes = [
    DWORD,  # nCount
    POINTER(HANDLE),  # pHandles
    BOOL,  # bWaitAll
    DWORD,  # dwMilliseconds
    DWORD,  # dwWakeMask
]

_ole32 = OleDLL("ole32")
_CoGetApartmentType = _ole32.CoGetApartmentType
_CoGetApartmentType.argtypes = [
    POINTER(DWORD),  # pAptType
    POINTER(DWORD),  # pAptQualifier
]
_CoGetApartmentType.restype = HRESULT

QS_ALLINPUT = 0x04FF  # All message types including SendMessage

APTTYPE_MAINSTA = 3

RPC_E_WRONG_THREAD = -2147417842  # 0x8001010E

DOT_B64_IMG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
IMG_DATA = base64.b64decode(DOT_B64_IMG)


def CoGetApartmentType() -> tuple[int, int]:
    # https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-cogetapartmenttype
    # https://learn.microsoft.com/en-us/windows/desktop/api/objidl/ne-objidl-apttype
    # https://learn.microsoft.com/en-us/windows/desktop/api/objidl/ne-objidl-apttypequalifier
    typ, qf = DWORD(), DWORD()
    _CoGetApartmentType(typ, qf)
    return typ.value, qf.value


@contextlib.contextmanager
def register_in_global(obj: IUnknown) -> Iterator[int]:
    cookie = RegisterInterfaceInGlobal(obj)
    try:
        yield cookie
    finally:
        RevokeInterfaceFromGlobal(cookie)


def pump(event: threading.Event) -> None:
    # This function ensures preventing deadlocks.
    msg = MSG()
    while not event.is_set():
        MsgWaitForMultipleObjects(0, None, False, 10, QS_ALLINPUT)
        while PeekMessage(byref(msg), 0, 0, 0, PM_REMOVE):
            TranslateMessage(byref(msg))
            DispatchMessage(byref(msg))


# `Paint.Picture` is a standard COM object available on most Windows systems.
# It is an out-of-process, STA-only COM object that implements `IPersistFile`.
# This makes it suitable for demonstrating object persistence and marshaling
# across apartment boundaries.
CLSID_PaintPicture = GUID.from_progid("Paint.Picture")


class Test_ApartmentMarshaling(ut.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmpdir = Path(td.name)
        self.imgfile = self.tmpdir / "img.png"
        self.imgfile.write_bytes(IMG_DATA)

    def test(self):
        def work_with_git(ck: int, evt: threading.Event, res: Queue) -> None:
            comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
            try:
                obj = GetInterfaceFromGlobal(ck, interface=IPersistFile)
                res.put(obj.GetCurFile())
            finally:
                comtypes.CoUninitialize()
                evt.set()

        def work_without_git(
            obj: IPersistFile, evt: threading.Event, res: Queue
        ) -> None:
            comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
            try:
                obj.GetCurFile()
            except COMError as e:
                res.put(e)
            finally:
                comtypes.CoUninitialize()
                evt.set()

        # This test assumes that the `Paint.Picture` instance is created within
        # a Single-Threaded Apartment (STA, `COINIT_APARTMENTTHREADED`), which
        # is the default for this package.
        # If main thread apartment type were to change to MTA, the test's
        # assertions regarding COM marshaling behavior would no longer hold true.
        pf = comtypes.CoCreateInstance(CLSID_PaintPicture, interface=IPersistFile)
        # Ensure that this test is executed on the main STA thread.
        self.assertEqual(CoGetApartmentType()[0], APTTYPE_MAINSTA)
        pf.Load(str(self.imgfile), STGM_READ)
        self.assertEqual(
            os.path.normcase(os.path.normpath(self.imgfile)),
            os.path.normcase(os.path.normpath(pf.GetCurFile())),
        )
        self.assertEqual((pf.AddRef(), pf.Release()), (2, 1))
        event = threading.Event()
        results = Queue(maxsize=1)
        with register_in_global(pf) as cookie:
            # When an object is registered to GIT, `AddRef` is called,
            # incrementing its reference count. This ensures the object
            # remains valid as long as it's globally registered in the GIT.
            self.assertEqual((pf.AddRef(), pf.Release()), (3, 2))
            thread_with_git = threading.Thread(
                target=work_with_git, args=(cookie, event, results)
            )
            thread_with_git.start()
            pump(event)
            thread_with_git.join()
            self.assertEqual(
                os.path.normcase(os.path.normpath(self.imgfile)),
                os.path.normcase(os.path.normpath(results.get())),
            )
            event.clear()
            self.assertTrue(results.empty())
            thread_without_git = threading.Thread(
                target=work_without_git, args=(pf, event, results)
            )
            thread_without_git.start()
            pump(event)
            thread_without_git.join()
            err = results.get()
            # `RPC_E_WRONG_THREAD` occurs because `PaintPicture` is an STA
            # object created in the main thread, and `work_without_git`
            # attempts to access it directly from a different thread without
            # proper marshaling. COM rejects this direct access.
            self.assertEqual(err.hresult, RPC_E_WRONG_THREAD)
            self.assertEqual((pf.AddRef(), pf.Release()), (3, 2))
        # When an object is revoked from the GIT, `Release` is called,
        # decrementing its reference count. This allows the object to be
        # garbage collected if no other references exist, ensuring proper
        # resource management.
        self.assertEqual((pf.AddRef(), pf.Release()), (2, 1))
