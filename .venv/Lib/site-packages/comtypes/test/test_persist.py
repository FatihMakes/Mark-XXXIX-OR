import tempfile
import unittest as ut
from _ctypes import COMError
from pathlib import Path

from comtypes import GUID, CoCreateInstance, IPersist, hresult, persist
from comtypes.automation import VARIANT

CLSID_ShellLink = GUID("{00021401-0000-0000-C000-000000000046}")


class Test_IPersist(ut.TestCase):
    def test_GetClassID(self):
        p = CoCreateInstance(CLSID_ShellLink).QueryInterface(IPersist)
        self.assertEqual(p.GetClassID(), CLSID_ShellLink)


class Test_IPersistFile(ut.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp_dir = Path(td.name)

    def _create_pf(self) -> persist.IPersistFile:
        return CoCreateInstance(CLSID_ShellLink).QueryInterface(persist.IPersistFile)

    def test_load(self):
        pf = self._create_pf()
        tgt_file = (self.tmp_dir / "tgt.txt").resolve()
        tgt_file.touch()
        pf.Load(str(tgt_file), persist.STGM_DIRECT)
        self.assertEqual(pf.GetCurFile(), str(tgt_file))

    def test_save(self):
        pf = self._create_pf()
        tgt_file = self.tmp_dir / "tgt.txt"
        self.assertFalse(tgt_file.exists())
        pf.Save(str(tgt_file), True)
        self.assertEqual(pf.GetCurFile(), str(tgt_file))
        self.assertTrue(tgt_file.exists())


class Test_DictPropertyBag(ut.TestCase):
    def create_itf_ptr(self) -> persist.IPropertyBag:
        # Create a DictPropertyBag instance with some initial values
        impl = persist.DictPropertyBag(Key1="value1", Key2=123, Key3=True)
        # Get the IPropertyBag interface pointer
        itf = impl.QueryInterface(persist.IPropertyBag)
        return itf

    def test_read_existing_properties(self):
        itf = self.create_itf_ptr()
        self.assertEqual(itf.Read("Key1", VARIANT(), None), "value1")
        self.assertEqual(itf.Read("Key2", VARIANT(), None), 123)
        self.assertEqual(itf.Read("Key3", VARIANT(), None), True)

    def test_write_new_property(self):
        itf = self.create_itf_ptr()
        itf.Write("Key4", "new_value")
        self.assertEqual(itf.Read("Key4", VARIANT(), None), "new_value")

    def test_update_existing_property(self):
        itf = self.create_itf_ptr()
        itf.Write("Key1", "updated_value")
        self.assertEqual(itf.Read("Key1", VARIANT(), None), "updated_value")

    def test_read_non_existent_property(self):
        itf = self.create_itf_ptr()
        with self.assertRaises(COMError) as cm:
            itf.Read("NonExistentProp", VARIANT(), None)
        self.assertEqual(cm.exception.hresult, hresult.E_INVALIDARG)
