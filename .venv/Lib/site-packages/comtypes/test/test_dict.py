"""Use Scripting.Dictionary to test the lazybind and the generated modules."""

import unittest

from comtypes import typeinfo
from comtypes.automation import VARIANT
from comtypes.client import CreateObject, GetModule
from comtypes.client.lazybind import Dispatch

GetModule("scrrun.dll")
import comtypes.gen.Scripting as scrrun


class Test(unittest.TestCase):
    def test_dynamic(self):
        d = CreateObject("Scripting.Dictionary", dynamic=True)
        self.assertEqual(type(d), Dispatch)

        # Count is a normal propget, no propput
        self.assertEqual(d.Count, 0)
        with self.assertRaises(AttributeError):
            d.Count = -1

        # HashVal is a 'named' propget, no propput
        # HashVal is a 'hidden' member and used internally.
        ##d.HashVal

        # Add(Key, Item) -> None
        self.assertEqual(d.Add("one", 1), None)
        self.assertEqual(d.Count, 1)

        # RemoveAll() -> None
        self.assertEqual(d.RemoveAll(), None)
        self.assertEqual(d.Count, 0)

        # CompareMode: propget, propput
        # (Can only be set when dict is empty!)
        # Verify that the default is BinaryCompare.
        self.assertEqual(d.CompareMode, scrrun.BinaryCompare)
        d.CompareMode = scrrun.TextCompare
        self.assertEqual(d.CompareMode, scrrun.TextCompare)
        d.CompareMode = scrrun.BinaryCompare

        # Exists(key) -> bool
        self.assertEqual(d.Exists(42), False)
        d.Add(42, "foo")
        self.assertEqual(d.Exists(42), True)

        # Keys() -> array
        # Items() -> array
        self.assertEqual(d.Keys(), (42,))
        self.assertEqual(d.Items(), ("foo",))
        d.Remove(42)
        self.assertEqual(d.Exists(42), False)
        self.assertEqual(d.Keys(), ())
        self.assertEqual(d.Items(), ())

        # Item[key] : propget
        d.Add(42, "foo")
        self.assertEqual(d.Item[42], "foo")

        d.Add("spam", "bar")
        self.assertEqual(d.Item["spam"], "bar")

        # Item[key] = value: propput, propputref
        d.Item["key"] = "value"
        self.assertEqual(d.Item["key"], "value")
        d.Item[42] = 73, 48
        self.assertEqual(d.Item[42], (73, 48))

        ################################################################
        # part 2, testing propput and propputref

        s = CreateObject("Scripting.Dictionary", dynamic=True)
        s.CompareMode = scrrun.DatabaseCompare

        # This calls propputref, since we assign an Object
        d.Item["object"] = s
        # This calls propput, since we assign a Value
        d.Item["value"] = s.CompareMode

        self.assertEqual(d.Item["object"], s)
        self.assertEqual(d.Item["object"].CompareMode, scrrun.DatabaseCompare)
        self.assertEqual(d.Item["value"], scrrun.DatabaseCompare)

        # Changing a property of the object
        s.CompareMode = scrrun.BinaryCompare
        self.assertEqual(d.Item["object"], s)
        self.assertEqual(d.Item["object"].CompareMode, scrrun.BinaryCompare)
        self.assertEqual(d.Item["value"], scrrun.DatabaseCompare)

        # This also calls propputref since we assign an Object
        d.Item["var"] = VARIANT(s)
        self.assertEqual(d.Item["var"], s)

        # iter(d)
        self.assertEqual(d.Keys(), tuple(x for x in d))

        # d[key] = value
        # d[key] -> value
        d["blah"] = "blarg"
        self.assertEqual(d["blah"], "blarg")
        # d(key) -> value
        self.assertEqual(d("blah"), "blarg")

    def test_static(self):
        d = CreateObject(scrrun.Dictionary, interface=scrrun.IDictionary)
        # This confirms that the Dictionary is a dual interface.
        ti = d.GetTypeInfo(0)
        self.assertTrue(ti.GetTypeAttr().wTypeFlags & typeinfo.TYPEFLAG_FDUAL)
        # Count is a normal propget, no propput
        self.assertEqual(d.Count, 0)
        with self.assertRaises(AttributeError):
            d.Count = -1  # type: ignore
        # Dual interfaces call COM methods that support named arguments.
        d.Add("spam", "foo")
        d.Add("egg", Item="bar")
        self.assertEqual(d.Count, 2)
        d.Add(Key="ham", Item="baz")
        self.assertEqual(len(d), 3)
        d.Add(Item="qux", Key="toast")
        d.Item["beans"] = "quux"
        d["bacon"] = "corge"
        self.assertEqual(d("spam"), "foo")
        self.assertEqual(d.Item["egg"], "bar")
        self.assertEqual(d["ham"], "baz")
        self.assertEqual(d("toast"), "qux")
        self.assertEqual(d.Item("beans"), "quux")
        self.assertEqual(d("bacon"), "corge")
        # NOTE: Named parameters are not yet implemented for the named property.
        # See https://github.com/enthought/comtypes/issues/371
        # TODO: After named parameters are supported, this will become a test to
        # assert the return value.
        with self.assertRaises(TypeError):
            d.Item(Key="spam")
        with self.assertRaises(TypeError):
            d(Key="egg")


if __name__ == "__main__":
    unittest.main()
