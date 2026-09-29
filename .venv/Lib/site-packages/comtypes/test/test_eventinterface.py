import gc
import tempfile
import time
import unittest as ut
from ctypes import HRESULT, byref
from ctypes.wintypes import MSG
from pathlib import Path

from comtypes import COMMETHOD, GUID, IUnknown
from comtypes.automation import DISPID
from comtypes.client import CreateObject, GetEvents
from comtypes.messageloop import (
    PM_REMOVE,
    DispatchMessage,
    PeekMessage,
    TranslateMessage,
)

# The primary goal is to verify how `GetEvents` behaves when the
# `interface` argument is explicitly specified versus when it is omitted,
# using an object that has multiple outgoing event interfaces.


class IPropertyNotifySink(IUnknown):
    # https://learn.microsoft.com/en-us/windows/win32/api/ocidl/nn-ocidl-ipropertynotifysink
    _iid_ = GUID("{9BFBBC02-EFF1-101A-84ED-00AA00341D07}")
    _methods_ = [
        # Called when a property has changed.
        COMMETHOD([], HRESULT, "OnChanged", (["in"], DISPID, "dispid")),
        # Called when an object wants to know if it's okay to change a property.
        COMMETHOD([], HRESULT, "OnRequestEdit", (["in"], DISPID, "dispid")),
    ]


class EventSink:
    def __init__(self):
        self._events = []

    # Events from the default dispatch interface
    def onreadystatechange(self, this, *args):
        self._events.append("onreadystatechange")

    def ondataavailable(self, this, *args):
        self._events.append("ondataavailable")

    # Events from `IPropertyNotifySink`
    def OnChanged(self, this, *args):
        self._events.append("OnChanged")

    def OnRequestEdit(self, this, *args):
        self._events.append("OnRequestEdit")


def PumpWaitingMessages():
    msg = MSG()
    while PeekMessage(byref(msg), 0, 0, 0, PM_REMOVE):
        TranslateMessage(byref(msg))
        DispatchMessage(byref(msg))


class Test_MSXML(ut.TestCase):
    def setUp(self):
        # We use `Msxml2.DOMDocument` because it is a built-in Windows
        # component that supports both a default source interface and the
        # `IPropertyNotifySink` connection point.
        self.doc = CreateObject("Msxml2.DOMDocument")
        self.doc.async_ = True

    def tearDown(self):
        del self.doc
        # Force garbage collection and wait slightly to ensure COM resources
        # are released properly between tests.
        gc.collect()
        time.sleep(2)

    def test_default_eventinterface(self):
        # Verify that `GetEvents` automatically connects to the default source
        # interface (dispatch events like `onreadystatechange`) when no
        # interface is explicitly requested.
        sink = EventSink()
        conn = GetEvents(self.doc, sink)
        self.doc.loadXML("<root/>")

        # Give the message loop time to process incoming events.
        for _ in range(50):
            PumpWaitingMessages()
            time.sleep(0.1)
        # Should receive events from the default dispatch interface, but not
        # events from `IPropertyNotifySink`.
        self.assertIn("onreadystatechange", sink._events)
        self.assertNotIn("OnChanged", sink._events)

        del conn

    def test_nondefault_eventinterface(self):
        # Verify that `GetEvents` can connect to a non-default interface
        # (like `IPropertyNotifySink`) when it is explicitly provided.
        sink = EventSink()

        conn = GetEvents(self.doc, sink, interface=IPropertyNotifySink)

        self.doc.loadXML("<root/>")

        # Give the message loop time to process incoming events.
        for _ in range(50):
            PumpWaitingMessages()
            time.sleep(0.1)
        # Should receive events from `IPropertyNotifySink`, but not events from
        # the default dispatch interface.
        self.assertNotIn("onreadystatechange", sink._events)
        self.assertIn("OnChanged", sink._events)

        del conn


class Test_MSHTML(ut.TestCase):
    def test_retrieved_outgoing_iid_is_guid_null(self):
        doc = CreateObject("htmlfile")
        sink = object()
        # MSHTML's HTMLDocument (which is what `CreateObject('htmlfile')`
        # returns) does not expose a valid default source interface through
        # `IProvideClassInfo2`.
        with self.assertRaises(NotImplementedError):
            GetEvents(doc, sink)


class Test_IMAPI2FS(ut.TestCase):
    def setUp(self):
        CLSID_MsftFileSystemImage = GUID("{2C941FC5-975B-59BE-A960-9A2A262853A5}")
        self.image = CreateObject(CLSID_MsftFileSystemImage)
        self.image.FileSystemsToCreate = 1  # FsiFileSystemISO9660
        td = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(td.name)
        self.addCleanup(td.cleanup)

    def tearDown(self):
        del self.image
        # Force garbage collection and wait slightly to ensure COM resources
        # are released properly between tests.
        gc.collect()
        time.sleep(2)

    def test_event_methods_lack_dispids(self):
        sink = object()
        # The default event interface for IMAPI2's FileSystemImage is
        # `DFileSystemImageEvents`. Although it inherits from `IDispatch`,
        # it is a custom interface (`TKIND_INTERFACE`), not a dual or pure
        # dispatch interface (`TKIND_DISPATCH`); therefore, its methods
        # do not have DISPIDs.
        with self.assertRaises(NotImplementedError):
            GetEvents(self.image, sink)


if __name__ == "__main__":
    ut.main()
