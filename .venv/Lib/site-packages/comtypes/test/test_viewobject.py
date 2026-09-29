import contextlib
import ctypes
import unittest
from ctypes import POINTER, OleDLL
from ctypes.wintypes import POINT, RECT, SIZEL

import comtypes.client
from comtypes import IUnknown
from comtypes.test.gdi_helper import _GdiFlush, create_image_rendering_dc
from comtypes.viewobject import (
    DVASPECT_CONTENT,
    IAdviseSink,
    IViewObject,
    IViewObject2,
    IViewObjectEx,
)

comtypes.client.GetModule("inked.dll")
with contextlib.redirect_stdout(None):  # supress warnings
    comtypes.client.GetModule("mshtml.tlb")

import comtypes.gen.INKEDLib as inkedlib
import comtypes.gen.MSHTML as mshtml


def create_html_document() -> IUnknown:
    return comtypes.client.CreateObject(mshtml.HTMLDocument)


_ole32 = OleDLL("ole32")
_OleRun = _ole32.OleRun
_OleRun.argtypes = [POINTER(IUnknown)]


class Test_IViewObject(unittest.TestCase):
    def test_Advise_GetAdvise(self):
        vo = create_html_document().QueryInterface(IViewObject)
        # Test that we can clear any existing advise connection.
        vo.SetAdvise(DVASPECT_CONTENT, 0, None)
        # Verify that no advise connection is present.
        aspect, advf, sink = vo.GetAdvise()
        self.assertIsInstance(aspect, int)
        self.assertIsInstance(advf, int)
        self.assertIsInstance(sink, IAdviseSink)
        self.assertFalse(sink)  # A NULL com pointer evaluates to False.

    def test_Freeze_Unfreeze(self):
        vo = create_html_document().QueryInterface(IViewObject)
        cookie = vo.Freeze(DVASPECT_CONTENT, -1, None)
        self.assertIsInstance(cookie, int)
        vo.Unfreeze(cookie)

    def test_Draw(self):
        # https://learn.microsoft.com/en-us/windows/win32/api/ole/nf-ole-iviewobject-draw
        # It is necessary to use a valid HDC for the `Draw` method.
        ink_edit = comtypes.client.CreateObject(
            inkedlib.InkEdit, interface=inkedlib.IInkEdit
        )
        _OleRun(ink_edit)  # Put InkEdit into running state
        ink_edit.Text = ""
        ink_edit.BackColor = 255 << 16 | 0 << 8 | 0
        vo = ink_edit.QueryInterface(IViewObject)
        width, height = 1, 1
        with create_image_rendering_dc(0, width, height) as (hdc, bits, bmi, _):
            vo.Draw(
                DVASPECT_CONTENT,  # dwDrawAspect
                -1,  # lindex
                None,  # pvAspect
                None,  # ptd
                None,  # hicTargetDev
                hdc,  # hdcDraw
                RECT(left=0, top=0, right=width, bottom=height),  # lprcBounds
                None,  # lprcWBounds
                None,  # pfnContinue
                0,  # dwContinue
            )
            _GdiFlush()  # To ensure all drawing is complete
            # Read the pixel data directly from the bits pointer.
            gdi_data = ctypes.string_at(bits, bmi.bmiHeader.biSizeImage)
        self.assertEqual(gdi_data, b"\xff\x00\x00")


class Test_IViewObject2(unittest.TestCase):
    def test_GetExtent(self):
        vo = create_html_document().QueryInterface(IViewObject2)
        size = vo.GetExtent(DVASPECT_CONTENT, -1, None)
        self.assertTrue(size)
        self.assertIsInstance(size, SIZEL)


class Test_IViewObjectEx(unittest.TestCase):
    def test_GetRect(self):
        vo = create_html_document().QueryInterface(IViewObjectEx)
        rect = vo.GetRect(DVASPECT_CONTENT)
        self.assertTrue(rect)
        self.assertIsInstance(rect, RECT)

    def test_GetViewStatus(self):
        vo = create_html_document().QueryInterface(IViewObjectEx)
        status = vo.GetViewStatus()
        self.assertIsInstance(status, int)

    def test_QueryHitPoint(self):
        vo = create_html_document().QueryInterface(IViewObjectEx)
        # It is assumed that the view is not transparent at the origin.
        bounds = RECT(left=0, top=0, right=100, bottom=100)
        loc = POINT(x=0, y=0)
        hit = vo.QueryHitPoint(DVASPECT_CONTENT, bounds, loc, 0)
        self.assertIsInstance(hit, int)

    def test_QueryHitRect(self):
        vo = create_html_document().QueryInterface(IViewObjectEx)
        # It is assumed that the view is not transparent at the origin.
        bounds = RECT(left=0, top=0, right=100, bottom=100)
        loc = RECT(left=0, top=0, right=1, bottom=1)
        hit = vo.QueryHitRect(DVASPECT_CONTENT, bounds, loc, 0)
        self.assertIsInstance(hit, int)
