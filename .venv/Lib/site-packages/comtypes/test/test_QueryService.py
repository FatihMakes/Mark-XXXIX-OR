import contextlib
import time
import unittest
from ctypes import POINTER

import comtypes
from comtypes import GUID
from comtypes.client import CreateObject, GetModule

with contextlib.redirect_stdout(None):  # supress warnings
    GetModule("mshtml.tlb")
import comtypes.gen.MSHTML as mshtml

SID_SHTMLEditServices = GUID("{3050F7F9-98B5-11CF-BB82-00AA00BDCE0B}")


class TestCase(unittest.TestCase):
    def test(self):
        doc = CreateObject(mshtml.HTMLDocument, interface=mshtml.IHTMLDocument2)
        doc.designMode = "On"
        doc.write("<html><body><div id='test'>Hello</div></body></html>")
        doc.close()
        while doc.readyState != "complete":
            time.sleep(0.01)
        sp = doc.QueryInterface(comtypes.IServiceProvider)
        # This behavior is described in Microsoft documentation:
        # https://learn.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/platform-apis/aa704048(v=vs.85)
        es = sp.QueryService(SID_SHTMLEditServices, mshtml.IHTMLEditServices)
        self.assertIsInstance(es, POINTER(mshtml.IHTMLEditServices))
        mc = doc.QueryInterface(mshtml.IMarkupContainer)
        ss = es.GetSelectionServices(mc)
        # QueryInterface for `IHTMLDocument3` to access `getElementById`.
        element = doc.QueryInterface(mshtml.IHTMLDocument3).getElementById("test")
        self.assertEqual(element.innerHTML, "Hello")
        # MarkupPointer related tests:
        ms = doc.QueryInterface(mshtml.IMarkupServices)
        p_start = ms.CreateMarkupPointer()
        p_end = ms.CreateMarkupPointer()
        # QueryInterface for `IHTMLBodyElement` to access `createTextRange`.
        rng = doc.body.QueryInterface(mshtml.IHTMLBodyElement).createTextRange()
        rng.moveToElementText(element)
        ms.MovePointersToRange(rng, p_start, p_end)
        self.assertTrue(p_start.IsLeftOf(p_end))
        self.assertTrue(p_end.IsRightOf(p_start))
        self.assertFalse(p_start.IsEqualTo(p_end))
        seg = ss.AddSegment(p_start, p_end)
        q_start = ms.CreateMarkupPointer()
        q_end = ms.CreateMarkupPointer()
        self.assertFalse(p_start.IsEqualTo(q_start))
        self.assertFalse(p_end.IsEqualTo(q_end))
        seg.GetPointers(q_start, q_end)
        self.assertTrue(p_start.IsEqualTo(q_start))
        self.assertTrue(p_end.IsEqualTo(q_end))
        ss.RemoveSegment(seg)
        # Verify state changes of `p_start` and `p_end`.
        p_start.MoveToPointer(p_end)
        self.assertTrue(p_start.IsEqualTo(p_end))


if __name__ == "__main__":
    unittest.main()
