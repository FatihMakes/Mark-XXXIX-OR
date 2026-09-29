import contextlib
import ctypes
import os
import struct
import tempfile
import unittest as ut
from _ctypes import COMError
from collections.abc import Iterator
from ctypes import (
    HRESULT,
    POINTER,
    OleDLL,
    Structure,
    WinDLL,
    byref,
    c_size_t,
    c_ubyte,
    c_ulonglong,
    c_void_p,
    pointer,
)
from ctypes.wintypes import (
    BOOL,
    DWORD,
    HGDIOBJ,
    HGLOBAL,
    INT,
    LONG,
    LPCWSTR,
    LPVOID,
    UINT,
    ULARGE_INTEGER,
)
from pathlib import Path
from typing import Optional

import comtypes.client
from comtypes import hresult
from comtypes.malloc import CoGetMalloc
from comtypes.test.gdi_helper import BI_RGB, _GdiFlush, create_image_rendering_dc

comtypes.client.GetModule("portabledeviceapi.dll")
# The stdole module is generated automatically during the portabledeviceapi
# module generation.
import comtypes.gen.stdole as stdole
from comtypes.gen.PortableDeviceApiLib import WSTRING, IStream, tagSTATSTG

SIZE_T = c_size_t

STATFLAG_DEFAULT = 0
STGC_DEFAULT = 0

EACCES = 13  # Permission denied

STGTY_STREAM = 2
STREAM_SEEK_SET = 0
STREAM_SEEK_CUR = 1
STREAM_SEEK_END = 2

STGM_CREATE = 0x00001000
STGM_READWRITE = 0x00000002
STGM_SHARE_DENY_NONE = 0x00000040

STG_E_INVALIDFUNCTION = -2147287039  # 0x80030001

LOCK_EXCLUSIVE = 2

FILE_ATTRIBUTE_NORMAL = 0x80

_ole32 = OleDLL("ole32")

_CreateStreamOnHGlobal = _ole32.CreateStreamOnHGlobal
_CreateStreamOnHGlobal.argtypes = [HGLOBAL, BOOL, POINTER(POINTER(IStream))]
_CreateStreamOnHGlobal.restype = HRESULT

_shlwapi = OleDLL("shlwapi")

_IStream_Size = _shlwapi.IStream_Size
_IStream_Size.argtypes = [POINTER(IStream), POINTER(ULARGE_INTEGER)]
_IStream_Size.restype = HRESULT

_SHCreateStreamOnFileEx = _shlwapi.SHCreateStreamOnFileEx
_SHCreateStreamOnFileEx.argtypes = [
    LPCWSTR,  # pszFile
    DWORD,  # grfMode
    DWORD,  # dwAttributes
    BOOL,  # fCreate
    POINTER(IStream),  # pstmTemplate
    POINTER(POINTER(IStream)),  # ppstm
]
_SHCreateStreamOnFileEx.restype = HRESULT


def _create_stream_on_hglobal(
    handle: Optional[int] = None, delete_on_release: bool = True
) -> IStream:
    # Create an IStream
    stream = POINTER(IStream)()  # type: ignore
    _CreateStreamOnHGlobal(handle, delete_on_release, byref(stream))
    return stream  # type: ignore


def _create_stream_on_file(
    filepath: Path, mode: int, attr: int, create: bool
) -> IStream:
    stream = POINTER(IStream)()  # type: ignore
    _SHCreateStreamOnFileEx(str(filepath), mode, attr, create, None, byref(stream))
    return stream  # type: ignore


def _get_pwcsname(stat: tagSTATSTG) -> WSTRING:
    return WSTRING.from_address(ctypes.addressof(stat) + tagSTATSTG.pwcsName.offset)


class Test_RemoteWrite(ut.TestCase):
    def test_RemoteWrite(self):
        stream = _create_stream_on_hglobal()
        test_data = b"Some data"
        pv = (c_ubyte * len(test_data)).from_buffer(bytearray(test_data))

        written = stream.RemoteWrite(pv, len(test_data))

        # Verification
        self.assertEqual(written, len(test_data))


class Test_RemoteRead(ut.TestCase):
    def test_RemoteRead(self):
        stream = _create_stream_on_hglobal()
        test_data = b"Some data"
        pv = (c_ubyte * len(test_data)).from_buffer(bytearray(test_data))
        stream.RemoteWrite(pv, len(test_data))

        # Make sure the data actually gets written before trying to read back
        stream.Commit(STGC_DEFAULT)
        # Move the stream back to the beginning
        stream.RemoteSeek(0, STREAM_SEEK_SET)

        buffer_size = 1024

        read_buffer, data_read = stream.RemoteRead(buffer_size)

        # Verification
        self.assertEqual(data_read, len(test_data))
        self.assertEqual(bytearray(read_buffer)[0:data_read], test_data)


class Test_RemoteSeek(ut.TestCase):
    def _create_sample_stream(self) -> IStream:
        stream = _create_stream_on_hglobal()
        test_data = b"spam egg bacon ham"
        pv = (c_ubyte * len(test_data)).from_buffer(bytearray(test_data))
        stream.RemoteWrite(pv, len(test_data))
        stream.Commit(STGC_DEFAULT)
        return stream

    def test_takes_STREAM_SEEK_SET_as_origin(self):
        stream = self._create_sample_stream()
        newpos = stream.RemoteSeek(9, STREAM_SEEK_SET)
        self.assertEqual(newpos, 9)
        buf, read = stream.RemoteRead(1024)
        self.assertEqual(bytearray(buf)[0:read], b"bacon ham")

    def test_takes_STREAM_SEEK_CUR_as_origin(self):
        stream = self._create_sample_stream()
        stream.RemoteSeek(8, STREAM_SEEK_SET)
        newpos = stream.RemoteSeek(7, STREAM_SEEK_CUR)
        self.assertEqual(newpos, 15)
        buf, read = stream.RemoteRead(1024)
        self.assertEqual(bytearray(buf)[0:read], b"ham")

    def test_takes_STREAM_SEEK_END_as_origin(self):
        stream = self._create_sample_stream()
        stream.RemoteSeek(8, STREAM_SEEK_SET)
        newpos = stream.RemoteSeek(-13, STREAM_SEEK_END)
        self.assertEqual(newpos, 5)
        buf, read = stream.RemoteRead(1024)
        self.assertEqual(bytearray(buf)[0:read], b"egg bacon ham")


class Test_SetSize(ut.TestCase):
    def test_SetSize(self):
        stream = _create_stream_on_hglobal()
        stream.SetSize(42)
        pui = pointer(c_ulonglong())
        _IStream_Size(stream, pui)
        self.assertEqual(pui.contents.value, 42)


class Test_RemoteCopyTo(ut.TestCase):
    def test_RemoteCopyTo(self):
        src = _create_stream_on_hglobal()
        dst = _create_stream_on_hglobal()
        test_data = b"parrot"
        pv = (c_ubyte * len(test_data)).from_buffer(bytearray(test_data))
        src_written = src.RemoteWrite(pv, len(test_data))
        src.Commit(STGC_DEFAULT)
        src.RemoteSeek(0, STREAM_SEEK_SET)
        cpy_read, cpy_written = src.RemoteCopyTo(dst, src_written)
        self.assertEqual(cpy_read, len(test_data))
        self.assertEqual(cpy_written, len(test_data))
        dst.Commit(STGC_DEFAULT)
        dst.RemoteSeek(0, STREAM_SEEK_SET)
        dst_buf, dst_read = dst.RemoteRead(1024)
        self.assertEqual(bytearray(dst_buf)[0:dst_read], test_data)


class Test_Stat(ut.TestCase):
    # https://learn.microsoft.com/en-us/windows/win32/api/objidl/nf-objidl-istream-stat
    # https://learn.microsoft.com/en-us/windows/win32/api/objidl/ns-objidl-statstg
    def test_returns_stat_from_no_modified_stream(self):
        stream = _create_stream_on_hglobal()
        stat = stream.Stat(STATFLAG_DEFAULT)
        self.assertIsNone(stat.pwcsName)
        self.assertEqual(stat.type, STGTY_STREAM)
        self.assertEqual(stat.cbSize, 0)
        mt, ct, at = stat.mtime, stat.ctime, stat.atime
        self.assertTrue(mt.dwLowDateTime == ct.dwLowDateTime == at.dwLowDateTime)
        self.assertTrue(mt.dwHighDateTime == ct.dwHighDateTime == at.dwHighDateTime)
        self.assertEqual(stat.grfMode, 0)
        self.assertEqual(stat.grfLocksSupported, 0)
        self.assertEqual(stat.clsid, comtypes.GUID())
        self.assertEqual(stat.grfStateBits, 0)
        name_ptr = _get_pwcsname(stat)
        self.assertIsNone(name_ptr.value)
        malloc = CoGetMalloc()
        self.assertEqual(malloc.DidAlloc(name_ptr), -1)
        del stat  # `pwcsName` is expected to be freed here.
        # `DidAlloc` checks are skipped to avoid using a dangling pointer.


class Test_Clone(ut.TestCase):
    def test_Clone(self):
        orig = _create_stream_on_hglobal()
        test_data = b"spam egg bacon ham"
        pv = (c_ubyte * len(test_data)).from_buffer(bytearray(test_data))
        orig.RemoteWrite(pv, len(test_data))
        orig.Commit(STGC_DEFAULT)
        orig.RemoteSeek(0, STREAM_SEEK_SET)
        new_stm = orig.Clone()
        buf, read = new_stm.RemoteRead(1024)
        self.assertEqual(bytearray(buf)[0:read], test_data)


class Test_LockRegion_UnlockRegion(ut.TestCase):
    def test_cannot_lock_memory_based_stream(self):
        stm = _create_stream_on_hglobal()
        # For memory-backed streams, `LockRegion` and `UnlockRegion` are
        # typically not supported and will return `STG_E_INVALIDFUNCTION`.
        with self.assertRaises(COMError) as cm:
            stm.LockRegion(0, 5, LOCK_EXCLUSIVE)
        self.assertEqual(cm.exception.hresult, STG_E_INVALIDFUNCTION)
        with self.assertRaises(COMError) as cm:
            stm.UnlockRegion(0, 5, LOCK_EXCLUSIVE)
        self.assertEqual(cm.exception.hresult, STG_E_INVALIDFUNCTION)

    def test_can_lock_file_based_stream(self):
        with tempfile.TemporaryDirectory() as t:
            tmpdir = Path(t)
            tmpfile = tmpdir / "lock_test.txt"
            # Create a file-backed stream to enable `LockRegion` support.
            # This implementation maps directly to OS-level file locking,
            # which is not available for memory-based streams.
            stm = _create_stream_on_file(
                tmpfile,
                STGM_READWRITE | STGM_SHARE_DENY_NONE | STGM_CREATE,
                FILE_ATTRIBUTE_NORMAL,
                True,
            )
            stm.SetSize(10)  # Allocate file space
            stm.LockRegion(0, 5, LOCK_EXCLUSIVE)  # Lock the first 5 bytes (0-4)
            # Open a separate file descriptor to simulate concurrent access
            fd = os.open(tmpfile, os.O_RDWR)
            # Writing to the LOCKED region must fail with EACCES
            os.lseek(fd, 0, os.SEEK_SET)
            with self.assertRaises(OSError) as cm:
                os.write(fd, b"ABCDE")
            self.assertEqual(cm.exception.errno, EACCES)
            # Writing to the UNLOCKED region (offset 5+) must succeed
            os.lseek(fd, 5, os.SEEK_SET)
            os.write(fd, b"ABCDE")
            # Cleanup: Close descriptors and release the lock
            os.close(fd)
            stm.UnlockRegion(0, 5, LOCK_EXCLUSIVE)
            stat = stm.Stat(STATFLAG_DEFAULT)
            buf, read = stm.RemoteRead(stat.cbSize)
            # Verify that COM stream content reflects the successful out-of-lock write
            self.assertEqual(bytearray(buf)[0:read], b"\x00\x00\x00\x00\x00ABCDE")
            # Verify that the actual file content on disk matches the expected data
            self.assertEqual(tmpfile.read_bytes(), b"\x00\x00\x00\x00\x00ABCDE")
            name_ptr = _get_pwcsname(stat)
            self.assertEqual(name_ptr.value, stat.pwcsName)
            malloc = CoGetMalloc()
            self.assertEqual(malloc.DidAlloc(name_ptr), 1)
            del stat  # `pwcsName` is expected to be freed here.
            # `DidAlloc` checks are skipped to avoid using a dangling pointer.


# TODO: If there is a standard Windows `IStream` implementation that supports
#       `Revert`, it should be used for testing.
#       https://learn.microsoft.com/en-us/windows/win32/api/objidl/nf-objidl-istream-revert
#
# - For memory-based streams (created by `CreateStreamOnHGlobal`),
#   `IStream::Revert` has no effect because the object "is not transacted"
#   per the specification. All writes are committed immediately to the
#   underlying HGLOBAL.
#   https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-createstreamonhglobal
#
# - `IStream::Revert` is not implemented for the standard Compound File
#   (Structured Storage) implementation. According to official documentation,
#   `Revert` has no effect on these streams.
#   https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-istream#methods


_kernel32 = WinDLL("kernel32")

_GlobalAlloc = _kernel32.GlobalAlloc
_GlobalAlloc.argtypes = (UINT, SIZE_T)
_GlobalAlloc.restype = HGLOBAL

_GlobalFree = _kernel32.GlobalFree
_GlobalFree.argtypes = (HGLOBAL,)
_GlobalFree.restype = HGLOBAL

_GlobalLock = _kernel32.GlobalLock
_GlobalLock.argtypes = (HGLOBAL,)
_GlobalLock.restype = LPVOID

_GlobalUnlock = _kernel32.GlobalUnlock
_GlobalUnlock.argtypes = (HGLOBAL,)
_GlobalUnlock.restype = BOOL

_oleaut32 = WinDLL("oleaut32")

_OleLoadPicture = _oleaut32.OleLoadPicture
_OleLoadPicture.argtypes = (
    POINTER(IStream),  # lpstm
    LONG,  # lSize
    BOOL,  # fSave
    POINTER(comtypes.GUID),  # riid
    POINTER(POINTER(comtypes.IUnknown)),  # ppvObj
)
_OleLoadPicture.restype = HRESULT


class _PICTDESC_BMP(Structure):
    _fields_ = [
        ("hbitmap", HGDIOBJ),
        ("hpal", DWORD),  # COLORREF is DWORD
    ]


class _PICTDESC_WMF(Structure):
    _fields_ = [
        ("hmetafile", HGDIOBJ),  # HMETAFILE
        ("xExt", INT),
        ("yExt", INT),
    ]


class _PICTDESC_EMF(Structure):
    _fields_ = [
        ("hemf", HGDIOBJ),  # HENHMETAFILE
    ]


class _PICTDESC_ICON(Structure):
    _fields_ = [
        ("hicon", HGDIOBJ),  # HICON
    ]


class _PICTDESC_CUR(Structure):
    _fields_ = [
        ("hcur", HGDIOBJ),  # HCURSOR
    ]


class _PICTDESC_DISP(Structure):
    _fields_ = [
        ("lpPicDisp", c_void_p),  # LPPICTUREDISP
    ]


class _PICTDESC_SIZE(Structure):
    _fields_ = [
        ("cx", c_size_t),
        ("cy", c_size_t),
    ]


class PICTDESC_UNION(ctypes.Union):
    _fields_ = [
        ("bmp", _PICTDESC_BMP),
        ("wmf", _PICTDESC_WMF),
        ("emf", _PICTDESC_EMF),
        ("icon", _PICTDESC_ICON),
        ("cur", _PICTDESC_CUR),
        ("disp", _PICTDESC_DISP),
        ("size", _PICTDESC_SIZE),
    ]


class PICTDESC(Structure):
    _fields_ = [
        ("cbSizeofstruct", UINT),
        ("picType", UINT),
        ("u", PICTDESC_UNION),
    ]


_OleCreatePictureIndirect = _oleaut32.OleCreatePictureIndirect
_OleCreatePictureIndirect.argtypes = [
    POINTER(PICTDESC),  # lpPictDesc
    POINTER(comtypes.GUID),  # riid
    BOOL,  # fOwn
    POINTER(POINTER(comtypes.IUnknown)),  # ppvObj
]
_OleCreatePictureIndirect.restype = HRESULT

# Constants for the type of a picture object
PICTYPE_BITMAP = 1

GMEM_FIXED = 0x0000
GMEM_ZEROINIT = 0x0040


@contextlib.contextmanager
def global_alloc(uflags: int, dwbytes: int) -> Iterator[int]:
    """Context manager to allocate and free a global memory handle."""
    handle = _GlobalAlloc(uflags, dwbytes)
    assert handle, "Failed to GlobalAlloc"
    try:
        yield handle
    finally:
        _GlobalFree(handle)


@contextlib.contextmanager
def global_lock(handle: int) -> Iterator[int]:
    """Context manager to lock a global memory handle and obtain a pointer."""
    lp_mem = _GlobalLock(handle)
    assert lp_mem, "Failed to GlobalLock"
    try:
        yield lp_mem
    finally:
        _GlobalUnlock(handle)


def create_24bit_pixel_data(
    red: int,
    green: int,
    blue: int,
    width: int,
    height: int,
) -> bytes:
    # Generates width x height pixel 24-bit BGR BMP binary data with 0 DPI.
    SIZEOF_BITMAPFILEHEADER = 14
    SIZEOF_BITMAPINFOHEADER = 40
    pixel_data = b""
    for _ in range(height):
        # Each row is padded to a 4-byte boundary.
        # For 24bpp, each pixel is 3 bytes (BGR).
        # Row size without padding: width * 3 bytes
        row_size = width * 3
        # Calculate padding bytes (to make row_size a multiple of 4)
        padding_bytes = (4 - (row_size % 4)) % 4
        for _ in range(width):
            # B, G, R
            pixel_data += struct.pack(b"BBB", blue, green, red)
        pixel_data += b"\x00" * padding_bytes
    BITMAP_DATA_OFFSET = SIZEOF_BITMAPFILEHEADER + SIZEOF_BITMAPINFOHEADER
    file_size = BITMAP_DATA_OFFSET + len(pixel_data)
    bmp_header = struct.pack(
        b"<2sIHHI",
        b"BM",  # File type signature "BM"
        file_size,  # Total file size
        0,  # Reserved1
        0,  # Reserved2
        BITMAP_DATA_OFFSET,  # Offset to pixel data
    )
    info_header = struct.pack(
        b"<IiiHHIIiiII",
        SIZEOF_BITMAPINFOHEADER,  # Size of BITMAPINFOHEADER
        width,  # Image width
        height,  # Image height
        1,  # Planes
        24,  # Bits per pixel (for BGR)
        BI_RGB,  # Compression
        len(pixel_data),  # Size of image data
        # Set to 0 DPI (0 px/m) is focusing on pixel data integrity;
        # this ensures environment-independent results and not reliably preserve resolution metadata.
        0,  # X pixels per meter (0 DPI)
        0,  # Y pixels per meter (0 DPI)
        # Setting biClrUsed and biClrImportant to 0 signifies that the bitmap
        # uses the maximum number of colors for the given bit depth (2^24) and
        # that all pixels are essential for rendering.
        0,  # Colors used
        0,  # Colors important
    )
    return bmp_header + info_header + pixel_data


class Test_Picture(ut.TestCase):
    def test_load_from_handle_stream(self):
        width, height = 1, 1
        data = create_24bit_pixel_data(255, 0, 0, width, height)  # Red pixel
        # Allocate global memory with `GMEM_FIXED` (fixed-size) and
        # `GMEM_ZEROINIT` (initialize to zero) and copy BMP data.
        with global_alloc(GMEM_FIXED | GMEM_ZEROINIT, len(data)) as handle:
            with global_lock(handle) as lp_mem:
                ctypes.memmove(lp_mem, data, len(data))
            pstm = _create_stream_on_hglobal(handle, delete_on_release=False)
            # Load picture from the stream
            pic: stdole.IPicture = POINTER(stdole.IPicture)()  # type: ignore
            hr = _OleLoadPicture(
                pstm,
                len(data),  # lSize
                False,  # fSave
                byref(stdole.IPicture._iid_),
                byref(pic),
            )
            self.assertEqual(hr, hresult.S_OK)
            self.assertEqual(pic.Type, PICTYPE_BITMAP)
            pstm.RemoteSeek(0, STREAM_SEEK_SET)
            buf, read = pstm.RemoteRead(len(data))
        self.assertEqual(bytes(buf)[:read], data)

    def test_load_from_buffer_stream(self):
        width, height = 1, 1
        data = create_24bit_pixel_data(0, 255, 0, width, height)  # Green pixel
        srcstm = _create_stream_on_hglobal(delete_on_release=True)
        pv = (c_ubyte * len(data)).from_buffer(bytearray(data))
        srcstm.RemoteWrite(pv, len(data))
        srcstm.Commit(STGC_DEFAULT)
        srcstm.RemoteSeek(0, STREAM_SEEK_SET)
        # Load picture from the stream
        pic: stdole.IPicture = POINTER(stdole.IPicture)()  # type: ignore
        hr = _OleLoadPicture(
            srcstm, len(data), False, byref(stdole.IPicture._iid_), byref(pic)
        )
        self.assertEqual(hr, hresult.S_OK)
        self.assertEqual(pic.Type, PICTYPE_BITMAP)
        with create_image_rendering_dc(0, width, height) as (mem_dc, bits, bmi, _):
            pic.Render(
                mem_dc,
                0,
                0,
                1,
                1,
                0,
                pic.Height,  # start from bottom for bottom-up DIB
                pic.Width,
                -pic.Height,  # negative for top-down rendering in memory
                None,
            )
            # Flush GDI operations to ensure all drawing commands are executed
            # and memory is updated before reading.
            _GdiFlush()
            # Read the pixel data directly from the bits pointer.
            gdi_data = ctypes.string_at(bits, bmi.bmiHeader.biSizeImage)
        # BGR, 1x1 pixel, green (0, 255, 0), in Windows GDI.
        self.assertEqual(gdi_data, b"\x00\xff\x00")
        # Save picture to the stream
        dststm = _create_stream_on_hglobal(delete_on_release=True)
        pic.SaveAsFile(dststm, False)
        dststm.RemoteSeek(0, STREAM_SEEK_SET)
        buf, read = dststm.RemoteRead(dststm.Stat(STATFLAG_DEFAULT).cbSize)
        self.assertEqual(bytes(buf)[:read], data)

    def test_save_created_bitmap_picture(self):
        # BGR, 1x1 pixel, blue (0, 0, 255), in Windows GDI.
        # This is the data that will be directly copied into the DIB section's memory.
        blue_pixel_data = b"\xff\x00\x00"  # Blue (0, 0, 255)
        width, height = 1, 1
        with create_image_rendering_dc(0, width, height) as (_, bits, _, hbm):
            # Copy the raw pixel data into the DIB section's memory
            ctypes.memmove(bits, blue_pixel_data, len(blue_pixel_data))
            # Populate PICTDESC with the HBITMAP from DIB section
            pdesc = PICTDESC()
            pdesc.cbSizeofstruct = ctypes.sizeof(PICTDESC)
            pdesc.picType = PICTYPE_BITMAP
            pdesc.u.bmp.hbitmap = hbm
            pdesc.u.bmp.hpal = 0  # No palette for 24bpp
            # Create IPicture using _OleCreatePictureIndirect
            pic: stdole.IPicture = POINTER(stdole.IPicture)()  # type: ignore
            hr = _OleCreatePictureIndirect(
                byref(pdesc),
                byref(stdole.IPicture._iid_),
                True,  # fOwn: If True, the picture object owns the GDI handle.
                byref(pic),
            )
            self.assertEqual(hr, hresult.S_OK)
            self.assertEqual(pic.Type, PICTYPE_BITMAP)
            dststm = _create_stream_on_hglobal(delete_on_release=True)
            pic.SaveAsFile(dststm, True)
            dststm.RemoteSeek(0, STREAM_SEEK_SET)
            buf, read = dststm.RemoteRead(dststm.Stat(STATFLAG_DEFAULT).cbSize)
        # Save picture to the stream
        self.assertEqual(
            bytes(buf)[:read],
            create_24bit_pixel_data(0, 0, 255, width, height),
        )


if __name__ == "__main__":
    ut.main()
