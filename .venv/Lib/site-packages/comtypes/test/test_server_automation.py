import unittest
from _ctypes import COMError

import comtypes.client
import comtypes.hresult as hresult
from comtypes.automation import IEnumVARIANT
from comtypes.server.automation import VARIANTEnumerator

comtypes.client.GetModule("scrrun.dll")
from comtypes.gen import Scripting as scrrun


class TestVARIANTEnumerator(unittest.TestCase):
    def setUp(self):
        # Create a list of IDispatch objects to enumerate
        dict1 = comtypes.client.CreateObject(
            "Scripting.Dictionary", interface=scrrun.IDictionary
        )
        dict1.Add("key1", "value1")
        dict2 = comtypes.client.CreateObject(
            "Scripting.Dictionary", interface=scrrun.IDictionary
        )
        dict2.Add("key2", "value2")
        dict3 = comtypes.client.CreateObject(
            "Scripting.Dictionary", interface=scrrun.IDictionary
        )
        dict3.Add("key3", "value3")
        self.items = [dict1, dict2, dict3]
        self.enumerator = VARIANTEnumerator(self.items)

    def test_Next_single_item(self):
        enum_variant = self.enumerator.QueryInterface(IEnumVARIANT)
        # Retrieve the first item
        item, fetched = enum_variant.Next(1)
        self.assertEqual(fetched, 1)
        dict1 = item.QueryInterface(scrrun.IDictionary)
        self.assertEqual(dict1.Item("key1"), "value1")
        # Retrieve the second item
        item, fetched = enum_variant.Next(1)
        dict2 = item.QueryInterface(scrrun.IDictionary)
        self.assertEqual(dict2.Item("key2"), "value2")
        # Retrieve the third item
        item, fetched = enum_variant.Next(1)
        self.assertEqual(fetched, 1)
        dict3 = item.QueryInterface(scrrun.IDictionary)
        self.assertEqual(dict3.Item("key3"), "value3")
        # After all items are enumerated, `Next` should return 0 fetched
        item, fetched = enum_variant.Next(1)
        self.assertEqual(fetched, 0)
        self.assertFalse(item)

    def test_Next_multiple_items(self):
        enum_variant = self.enumerator.QueryInterface(IEnumVARIANT)
        # Retrieve all three items at once.
        # We can now call Next(celt) with celt != 1, the call always returns a
        # list:
        item1, item2, item3 = enum_variant.Next(3)
        dict1 = item1.QueryInterface(scrrun.IDictionary)
        self.assertEqual(dict1.Item("key1"), "value1")
        dict2 = item2.QueryInterface(scrrun.IDictionary)
        self.assertEqual(dict2.Item("key2"), "value2")
        dict3 = item3.QueryInterface(scrrun.IDictionary)
        self.assertEqual(dict3.Item("key3"), "value3")
        # After all items are enumerated, Next should return 0 fetched
        item, fetched = enum_variant.Next(1)
        self.assertEqual(fetched, 0)
        self.assertFalse(item)

    def test_Skip(self):
        enum_variant = self.enumerator.QueryInterface(IEnumVARIANT)
        # Explicitly reset the enumerator, though it should be fresh
        self.assertEqual(enum_variant.Reset(), hresult.S_OK)
        # Skip zero items, should return S_OK
        self.assertEqual(enum_variant.Skip(0), hresult.S_OK)
        # Skip the first item
        self.assertEqual(enum_variant.Skip(1), hresult.S_OK)
        # Next should return the second item
        item, fetched = enum_variant.Next(1)
        self.assertEqual(fetched, 1)
        dict2 = item.QueryInterface(scrrun.IDictionary)
        self.assertEqual(dict2.Item("key2"), "value2")
        # Skip remaining items (1 items available, but skip 2)
        self.assertEqual(enum_variant.Skip(2), hresult.S_FALSE)
        # Next should now return 0 fetched
        item, fetched = enum_variant.Next(1)
        self.assertEqual(fetched, 0)
        self.assertFalse(item)

    def test_Reset(self):
        enum_variant = self.enumerator.QueryInterface(IEnumVARIANT)
        # Get some items
        item, fetched = enum_variant.Next(1)
        self.assertEqual(item.QueryInterface(scrrun.IDictionary).Item("key1"), "value1")
        item, fetched = enum_variant.Next(1)
        self.assertEqual(item.QueryInterface(scrrun.IDictionary).Item("key2"), "value2")
        # Reset the enumerator
        hr = enum_variant.Reset()
        self.assertEqual(hr, hresult.S_OK)
        # Next should return the first item again
        item, fetched = enum_variant.Next(1)
        self.assertEqual(fetched, 1)
        # Verify the content of the first dictionary
        self.assertEqual(item.QueryInterface(scrrun.IDictionary).Item("key1"), "value1")

    def test_Clone(self):
        enum_variant = self.enumerator.QueryInterface(IEnumVARIANT)
        # Clone is not implemented in `VARIANTEnumerator`.
        with self.assertRaises(COMError) as cm:
            enum_variant.Clone()
        self.assertEqual(cm.exception.hresult, hresult.E_NOTIMPL)

    def test_dunder_iter(self):
        enum_variant = self.enumerator.QueryInterface(IEnumVARIANT)
        # Ensure the enumerator is reset before iterating
        enum_variant.Reset()
        dict1, dict2, dict3 = [
            i.QueryInterface(scrrun.IDictionary) for i in enum_variant
        ]
        self.assertEqual(dict1["key1"], "value1")
        self.assertEqual(dict2["key2"], "value2")
        self.assertEqual(dict3["key3"], "value3")

    def test_dunder_getitem(self):
        enum_variant = self.enumerator.QueryInterface(IEnumVARIANT)
        enum_variant.Reset()
        # Directly access items by index
        dict1 = enum_variant[0].QueryInterface(scrrun.IDictionary)
        self.assertEqual(dict1["key1"], "value1")
        dict2 = enum_variant[1].QueryInterface(scrrun.IDictionary)
        self.assertEqual(dict2["key2"], "value2")
        dict3 = enum_variant[2].QueryInterface(scrrun.IDictionary)
        self.assertEqual(dict3["key3"], "value3")
        # Test index out of bounds
        with self.assertRaises(IndexError):
            _ = enum_variant[len(self.items)]
