import contextlib
from collections.abc import Iterator
from ctypes import POINTER, Structure, WinDLL, byref, c_void_p, sizeof
from ctypes.wintypes import (
    BOOL,
    DWORD,
    HANDLE,
    HDC,
    HGDIOBJ,
    HWND,
    INT,
    LONG,
    UINT,
    WORD,
)
from typing import Optional

BI_RGB = 0  # No compression
DIB_RGB_COLORS = 0

_user32 = WinDLL("user32")

_GetDC = _user32.GetDC
_GetDC.argtypes = (HWND,)
_GetDC.restype = HDC

_ReleaseDC = _user32.ReleaseDC
_ReleaseDC.argtypes = (HWND, HDC)
_ReleaseDC.restype = INT

_gdi32 = WinDLL("gdi32")

_CreateCompatibleDC = _gdi32.CreateCompatibleDC
_CreateCompatibleDC.argtypes = (HDC,)
_CreateCompatibleDC.restype = HDC

_DeleteDC = _gdi32.DeleteDC
_DeleteDC.argtypes = (HDC,)
_DeleteDC.restype = BOOL

_SelectObject = _gdi32.SelectObject
_SelectObject.argtypes = (HDC, HGDIOBJ)
_SelectObject.restype = HGDIOBJ

_DeleteObject = _gdi32.DeleteObject
_DeleteObject.argtypes = (HGDIOBJ,)
_DeleteObject.restype = BOOL

_GdiFlush = _gdi32.GdiFlush
_GdiFlush.argtypes = []
_GdiFlush.restype = BOOL


class BITMAPINFOHEADER(Structure):
    _fields_ = [
        ("biSize", DWORD),
        ("biWidth", LONG),
        ("biHeight", LONG),
        ("biPlanes", WORD),
        ("biBitCount", WORD),
        ("biCompression", DWORD),
        ("biSizeImage", DWORD),
        ("biXPelsPerMeter", LONG),
        ("biYPelsPerMeter", LONG),
        ("biClrUsed", DWORD),
        ("biClrImportant", DWORD),
    ]


class BITMAPINFO(Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", DWORD * 1),  # Placeholder for color table, not used for 32bpp
    ]


_CreateDIBSection = _gdi32.CreateDIBSection
_CreateDIBSection.argtypes = (
    HDC,
    POINTER(BITMAPINFO),
    UINT,  # DIB_RGB_COLORS
    POINTER(c_void_p),  # lplpBits
    HANDLE,  # hSection
    DWORD,  # dwOffset
)
_CreateDIBSection.restype = HGDIOBJ


@contextlib.contextmanager
def get_dc(hwnd: Optional[int]) -> Iterator[int]:
    """Context manager to get and release a device context (DC)."""
    dc = _GetDC(hwnd)
    assert dc, "Failed to get device context."
    try:
        yield dc
    finally:
        # Release the device context
        _ReleaseDC(hwnd, dc)


@contextlib.contextmanager
def create_compatible_dc(hdc: Optional[int]) -> Iterator[int]:
    """Context manager to create and delete a compatible device context."""
    mem_dc = _CreateCompatibleDC(hdc)
    assert mem_dc, "Failed to create compatible memory DC."
    try:
        yield mem_dc
    finally:
        _DeleteDC(mem_dc)


@contextlib.contextmanager
def create_dib_section(
    hdc: int, bmi: BITMAPINFO, usage: int, hsection: int, dwoffset: int
) -> Iterator[tuple[int, int]]:
    """Context manager to create and manage a DIB section.

    This function creates a device-independent bitmap (DIB) that applications
    can write to directly. It provides a handle to the DIB and a pointer
    address to its bitmap bits.
    """
    bits = c_void_p()
    try:
        hbm = _CreateDIBSection(
            hdc,
            byref(bmi),
            usage,
            byref(bits),
            hsection,
            dwoffset,
        )
        assert hbm, "Failed to create DIB section."
        assert bits.value, "Failed to get the bitmap's bit value."
        yield hbm, bits.value
    finally:
        _DeleteObject(hbm)


@contextlib.contextmanager
def select_object(hdc: int, obj: int) -> Iterator[int]:
    """Context manager to select a GDI object into a device context and restore
    the original.
    """
    old_obj = _SelectObject(hdc, obj)
    assert old_obj, "Failed to select object into DC."
    try:
        yield obj
    finally:
        _SelectObject(hdc, old_obj)


def create_24bitmap_info(width: int, height: int) -> BITMAPINFO:
    """Creates a BITMAPINFO structure for a 24bpp BGR DIB section."""
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height  # Negative for top-down DIB
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 24
    bmi.bmiHeader.biCompression = BI_RGB
    # width*height pixels * 3 bytes/pixel (BGR)
    bmi.bmiHeader.biSizeImage = width * height * 3
    return bmi


@contextlib.contextmanager
def create_image_rendering_dc(
    hwnd: int,
    width: int,
    height: int,
    usage: int = DIB_RGB_COLORS,
    hsection: int = 0,
    dwoffset: int = 0,
) -> Iterator[tuple[int, int, BITMAPINFO, int]]:
    """Context manager to create a device context for off-screen image rendering.

    This sets up a memory device context (DC) with a DIB section, allowing
    GDI operations to render into a memory buffer.

    Args:
        hwnd: Handle to the window (0 for desktop).
        width: Width of the image buffer.
        height: Height of the image buffer.
        usage: The type of DIB. Default is DIB_RGB_COLORS (0).
        hsection: A handle to a file-mapping object. If NULL (0), the system
                  allocates memory for the DIB.
        dwoffset: The offset from the beginning of the file-mapping object
                  specified by `hsection` to where the DIB bitmap begins.

    Yields:
        A tuple containing:
            - mem_dc: The handle to the memory device context.
            - bits: Pointer address to the pixel data of the DIB section.
            - bmi: The structure describing the DIB section.
            - hbm: The handle to the created DIB section bitmap.
    """
    # Get a screen DC to use as a reference for creating a compatible DC
    with get_dc(hwnd) as screen_dc, create_compatible_dc(screen_dc) as mem_dc:
        bmi = create_24bitmap_info(width, height)
        with create_dib_section(mem_dc, bmi, usage, hsection, dwoffset) as (hbm, bits):
            with select_object(mem_dc, hbm):
                yield mem_dc, bits, bmi, hbm
