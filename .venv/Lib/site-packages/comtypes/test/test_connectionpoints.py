import contextlib
import time
import unittest as ut
from collections.abc import Sequence
from ctypes import byref

import comtypes.client
from comtypes import COMObject, IUnknown
from comtypes.connectionpoints import IConnectionPointContainer

# generating `MSVidCtlLib` also generates `stdole`.
with contextlib.redirect_stdout(None):  # supress warnings
    comtypes.client.GetModule("msvidctl.dll")
from comtypes.gen import MSVidCtlLib as msvidctl
from comtypes.gen import stdole


class Test_IConnectionPointContainer(ut.TestCase):
    EVENT_IID = msvidctl._IMSVidCtlEvents._iid_

    def setUp(self):
        self.impl = comtypes.client.CreateObject(
            msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl
        )
        self.cpc = self.impl.QueryInterface(IConnectionPointContainer)

    def test_EnumConnectionPoints(self):
        conn_pts = list(self.cpc.EnumConnectionPoints())
        self.assertGreater(len(conn_pts), 0)
        self.assertTrue(
            all(pt.GetConnectionPointContainer() == self.cpc for pt in conn_pts)
        )

    def test_FindConnectionPoint(self):
        cp = self.cpc.FindConnectionPoint(byref(self.EVENT_IID))
        self.assertEqual(cp.GetConnectionPointContainer(), self.cpc)


class Test_IConnectionPoint(ut.TestCase):
    EVENT_IID = msvidctl._IMSVidCtlEvents._iid_
    OUTGOING_ITF = msvidctl._IMSVidCtlEvents

    def setUp(self):
        self.impl = comtypes.client.CreateObject(
            msvidctl.MSVidCtl, interface=msvidctl.IMSVidCtl
        )
        self.cpc = self.impl.QueryInterface(IConnectionPointContainer)
        self.cp = self.cpc.FindConnectionPoint(byref(self.EVENT_IID))

    @classmethod
    def create_sink(cls) -> COMObject:
        class Sink(COMObject):
            _com_interfaces_ = [cls.OUTGOING_ITF]

        return Sink()

    def test_GetConnectionInterface(self):
        self.assertEqual(self.cp.GetConnectionInterface(), self.EVENT_IID)

    def test_GetConnectionPointContainer(self):
        self.assertEqual(self.cp.GetConnectionPointContainer(), self.cpc)

    def test_Advise_Unadvise(self):
        # Verify the connection DOES NOT exist.
        self.assertEqual(len(list(self.cp.EnumConnections())), 0)
        sink = self.create_sink()
        # Since `POINTER(IUnknown).from_param`(`_compointer_base.from_param`)
        # can accept a `COMObject` instance, `IConnectionPoint.Advise` can
        # take either a COM object or a COM interface pointer.
        cookie = self.cp.Advise(sink)
        # Verify the connection exists.
        self.assertEqual(len(list(self.cp.EnumConnections())), 1)
        self.cp.Unadvise(cookie)
        # Verify the connection DOES NOT exist again.
        self.assertEqual(len(list(self.cp.EnumConnections())), 0)

    def test_EnumConnections(self):
        sink = self.create_sink().QueryInterface(self.OUTGOING_ITF)
        cookie = self.cp.Advise(sink)
        conns = [
            (data.pUnk.QueryInterface(self.OUTGOING_ITF), data.dwCookie)
            for data in self.cp.EnumConnections()
        ]
        self.assertEqual(len(conns), 1)
        ((punk, ck),) = conns
        self.assertEqual(ck, cookie)
        self.assertEqual(punk, sink)
        self.cp.Unadvise(cookie)


class Test_Sink(ut.TestCase):
    EVENT_IID = stdole.FontEvents._iid_
    OUTGOING_ITF = stdole.FontEvents

    def setUp(self):
        self.impl = comtypes.client.CreateObject(stdole.StdFont, interface=stdole.IFont)
        self.cpc = self.impl.QueryInterface(IConnectionPointContainer)
        self.cp = self.cpc.FindConnectionPoint(byref(self.EVENT_IID))

    @classmethod
    def create_sink_and_log(cls) -> tuple[IUnknown, Sequence[str]]:
        eventlog = []

        class Sink(COMObject):
            _com_interfaces_ = [cls.OUTGOING_ITF]

            # This method directly handles the event from the COM object.
            # Its name and signature must match the event definition in the
            # COM interface.
            # In a real-world scenario, event utilities in `client` module
            # would dynamically generate or map these methods.
            def FontChanged(self, PropertyName: str) -> None:
                eventlog.append(PropertyName)

        return Sink().QueryInterface(IUnknown), eventlog

    def test_sink(self):
        sink, fired_events = self.create_sink_and_log()
        cookie = self.cp.Advise(sink)
        self.assertFalse(fired_events)
        # Trigger the event by changing a property
        self.impl.Bold = not self.impl.Bold
        # We need to ensure the event has a chance to fire.
        # For testing, we need a small delay (or a COM message pump).
        time.sleep(0.05)
        # Assert the event was fired
        self.assertEqual(fired_events, ["Bold"])
        self.cp.Unadvise(cookie)
