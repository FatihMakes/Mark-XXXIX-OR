import struct
import tempfile
import unittest as ut
from ctypes import WinDLL, addressof, cast, create_string_buffer, string_at
from ctypes.wintypes import BOOL
from pathlib import Path

import comtypes.hresult
from comtypes import GUID, CoCreateInstance, shelllink
from comtypes.malloc import CoGetMalloc, _CoTaskMemFree
from comtypes.persist import IPersistFile
from comtypes.shelllink import LPITEMIDLIST as PIDLIST_ABSOLUTE

CLSID_ShellLink = GUID("{00021401-0000-0000-C000-000000000046}")

_shell32 = WinDLL("shell32")

# https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-ilisequal
_ILIsEqual = _shell32.ILIsEqual
_ILIsEqual.argtypes = [PIDLIST_ABSOLUTE, PIDLIST_ABSOLUTE]
_ILIsEqual.restype = BOOL


class Test_IShellLinkA(ut.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp_dir = Path(td.name)
        self.src_file = (self.tmp_dir / "src.txt").resolve()
        self.src_file.touch()

    def _create_shortcut(self) -> shelllink.IShellLinkA:
        return CoCreateInstance(CLSID_ShellLink, interface=shelllink.IShellLinkA)

    def test_set_and_get_path(self):
        shortcut = self._create_shortcut()
        pf = shortcut.QueryInterface(IPersistFile)
        self.assertEqual(pf.IsDirty(), comtypes.hresult.S_FALSE)
        shortcut.SetPath(str(self.src_file).encode("utf-8"))
        self.assertEqual(pf.IsDirty(), comtypes.hresult.S_OK)
        self.assertEqual(
            shortcut.GetPath(shelllink.SLGP_UNCPRIORITY),
            str(self.src_file).encode("utf-8"),
        )
        lnk_file = (self.tmp_dir / "new.lnk").resolve()
        self.assertFalse(lnk_file.exists())
        pf.Save(str(lnk_file), True)
        self.assertTrue(lnk_file.exists())
        self.assertEqual(pf.GetCurFile(), str(lnk_file))

    def test_set_and_get_working_directory(self):
        shortcut = self._create_shortcut()
        shortcut.SetWorkingDirectory(str(self.tmp_dir).encode("utf-8"))
        self.assertEqual(
            shortcut.GetWorkingDirectory(), str(self.tmp_dir).encode("utf-8")
        )

    def test_set_and_get_arguments(self):
        shortcut = self._create_shortcut()
        shortcut.SetArguments(b"-f")
        self.assertEqual(shortcut.GetArguments(), b"-f")

    def test_set_and_get_hotkey(self):
        hotkey = shelllink.HOTKEYF_ALT | shelllink.HOTKEYF_CONTROL
        shortcut = self._create_shortcut()
        shortcut.Hotkey = hotkey
        self.assertEqual(shortcut.Hotkey, hotkey)

    def test_set_and_get_showcmd(self):
        shortcut = self._create_shortcut()
        shortcut.ShowCmd = shelllink.SW_SHOWMAXIMIZED
        self.assertEqual(shortcut.ShowCmd, shelllink.SW_SHOWMAXIMIZED)

    def test_set_and_get_icon_location(self):
        shortcut = self._create_shortcut()
        shortcut.SetIconLocation(str(self.src_file).encode("utf-8"), 1)
        icon_path, index = shortcut.GetIconLocation()
        self.assertEqual(icon_path, str(self.src_file).encode("utf-8"))
        self.assertEqual(index, 1)

    def test_set_and_get_idlist(self):
        # Create a manual PIDL for testing.
        # In reality, the `abID` portion contains Shell namespace identifiers.
        # (e.g. file system item IDs, special folder tokens, virtual folder
        # GUIDs, etc.)
        # These IDs are referenced/used by Shell folders to identify and locate
        # specific items in the namespace.
        data = b"\xde\xad\xbe\xef"  # dummy test data (meaningless in real use).
        cb = len(data) + 2
        # ITEMIDLIST format:
        # - little-endian ('<')
        # - cb as 16-bit unsigned integer ('H')
        # - data bytes of length ('{len(data)}s')
        # - terminator as 16-bit unsigned integer ('H')
        raw_pidl = struct.pack(f"<H{len(data)}sH", cb, data, 0)
        in_pidl = cast(create_string_buffer(raw_pidl), shelllink.LPCITEMIDLIST)
        shortcut = self._create_shortcut()
        shortcut.SetIDList(in_pidl)
        # Get it back and verify.
        out_pidl = shortcut.GetIDList()
        idlist = out_pidl.contents
        self.assertEqual(idlist.mkid.cb, cb)
        # Access the raw data from the pointer.
        self.assertEqual(string_at(addressof(idlist.mkid.abID), len(data)), data)
        self.assertTrue(_ILIsEqual(in_pidl, out_pidl))
        malloc = CoGetMalloc()
        # Verify that the input PIDL is not COM-allocated memory.
        self.assertFalse(malloc.DidAlloc(in_pidl))
        # Verify that the output PIDL IS COM-allocated memory, requiring
        # `CoTaskMemFree` for proper deallocation.
        self.assertTrue(malloc.DidAlloc(out_pidl))
        _CoTaskMemFree(out_pidl)


class Test_IShellLinkW(ut.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp_dir = Path(td.name)
        self.src_file = (self.tmp_dir / "src.txt").resolve()
        self.src_file.touch()

    def _create_shortcut(self) -> shelllink.IShellLinkW:
        return CoCreateInstance(CLSID_ShellLink, interface=shelllink.IShellLinkW)

    def test_set_and_get_path(self):
        shortcut = self._create_shortcut()
        pf = shortcut.QueryInterface(IPersistFile)
        self.assertEqual(pf.IsDirty(), comtypes.hresult.S_FALSE)
        shortcut.SetPath(str(self.src_file))
        self.assertEqual(pf.IsDirty(), comtypes.hresult.S_OK)
        self.assertEqual(
            shortcut.GetPath(shelllink.SLGP_UNCPRIORITY),
            str(self.src_file),
        )
        lnk_file = (self.tmp_dir / "new.lnk").resolve()
        self.assertFalse(lnk_file.exists())
        pf.Save(str(lnk_file), True)
        self.assertTrue(lnk_file.exists())
        self.assertEqual(pf.GetCurFile(), str(lnk_file))

    def test_set_and_get_description(self):
        shortcut = self._create_shortcut()
        shortcut.SetDescription("sample")
        self.assertEqual(shortcut.GetDescription(), "sample")

    def test_set_and_get_working_directory(self):
        shortcut = self._create_shortcut()
        shortcut.SetWorkingDirectory(str(self.tmp_dir))
        self.assertEqual(shortcut.GetWorkingDirectory(), str(self.tmp_dir))

    def test_set_and_get_arguments(self):
        shortcut = self._create_shortcut()
        shortcut.SetArguments("-f")
        self.assertEqual(shortcut.GetArguments(), "-f")

    def test_set_and_get_hotkey(self):
        hotkey = shelllink.HOTKEYF_ALT | shelllink.HOTKEYF_CONTROL
        shortcut = self._create_shortcut()
        shortcut.Hotkey = hotkey
        self.assertEqual(shortcut.Hotkey, hotkey)

    def test_set_and_get_showcmd(self):
        shortcut = self._create_shortcut()
        shortcut.ShowCmd = shelllink.SW_SHOWMAXIMIZED
        self.assertEqual(shortcut.ShowCmd, shelllink.SW_SHOWMAXIMIZED)

    def test_set_and_get_icon_location(self):
        shortcut = self._create_shortcut()
        shortcut.SetIconLocation(str(self.src_file), 1)
        icon_path, index = shortcut.GetIconLocation()
        self.assertEqual(icon_path, str(self.src_file))
        self.assertEqual(index, 1)

    def test_set_and_get_idlist(self):
        # Create a manual PIDL for testing.
        # In reality, the `abID` portion contains Shell namespace identifiers.
        # (e.g. file system item IDs, special folder tokens, virtual folder
        # GUIDs, etc.)
        # These IDs are referenced/used by Shell folders to identify and locate
        # specific items in the namespace.
        data = b"\xca\xfe\xba\xbe"  # dummy test data (meaningless in real use).
        cb = len(data) + 2
        # ITEMIDLIST format:
        # - little-endian ('<')
        # - cb as 16-bit unsigned integer ('H')
        # - data bytes of length ('{len(data)}s')
        # - terminator as 16-bit unsigned integer ('H')
        raw_pidl = struct.pack(f"<H{len(data)}sH", cb, data, 0)
        in_pidl = cast(create_string_buffer(raw_pidl), shelllink.LPCITEMIDLIST)
        # Set pidl.
        shortcut = self._create_shortcut()
        shortcut.SetIDList(in_pidl)
        # Get it back and verify.
        out_pidl = shortcut.GetIDList()
        idlist = out_pidl.contents
        self.assertEqual(idlist.mkid.cb, cb)
        # Access the raw data from the pointer.
        self.assertEqual(string_at(addressof(idlist.mkid.abID), len(data)), data)
        self.assertTrue(_ILIsEqual(in_pidl, out_pidl))
        malloc = CoGetMalloc()
        # Verify that the input PIDL is not COM-allocated memory.
        self.assertFalse(malloc.DidAlloc(in_pidl))
        # Verify that the output PIDL IS COM-allocated memory, requiring
        # `CoTaskMemFree` for proper deallocation.
        self.assertTrue(malloc.DidAlloc(out_pidl))
        _CoTaskMemFree(out_pidl)
