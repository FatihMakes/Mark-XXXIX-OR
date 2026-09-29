import unittest
from ctypes import c_void_p

from comtypes import IUnknown


class Test(unittest.TestCase):
    def test_subinterface(self):
        class ISub(IUnknown):
            pass

    def test_subclass(self):
        class X(c_void_p):
            pass
