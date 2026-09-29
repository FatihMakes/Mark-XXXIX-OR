import doctest
import unittest as ut

import comtypes.hresult


class Test_MAKE_HRESULT(ut.TestCase):
    def test(self):
        for sev, fac, code, hr in [
            (0x0000, 0x0000, 0x0000, 0),
            (0x0001, 0x0000, 0x0000, -2147483648),
            (0x0000, 0x0001, 0x0000, 65536),
            (0x0000, 0x0000, 0x0001, 1),
            (0x0001, 0xFFFF, 0xFFFF, -1),
            (0x0000, 0xFFFF, 0xFFFF, -1),
            (0x0001, 0x0000, 0x0001, -2147483647),
            (0x0001, 0x0001, 0x0001, -2147418111),
            (0x0000, 0x0001, 0xFFFF, 131071),
            (0x0001, 0xFFFF, 0x0000, -65536),
            (0x0001, 0x0000, 0xFFFF, -2147418113),
        ]:
            with self.subTest(sev=sev, fac=fac, code=code, hr=hr):
                self.assertEqual(comtypes.hresult.MAKE_HRESULT(sev, fac, code), hr)


ERROR_OUTOFMEMORY = 14  # 0xE
ERROR_INVALID_PARAMETER = 87  # 0x57
RPC_S_SERVER_UNAVAILABLE = 1722  # 0x6BA


class Test_HRESULT_FROM_WIN32(ut.TestCase):
    def test(self):
        for w32, hr in [
            (ERROR_OUTOFMEMORY, comtypes.hresult.E_OUTOFMEMORY),
            (ERROR_INVALID_PARAMETER, comtypes.hresult.E_INVALIDARG),
            (RPC_S_SERVER_UNAVAILABLE, comtypes.hresult.RPC_S_SERVER_UNAVAILABLE),
            (-1, -1),
            (0, -2147024896),
            (1, -2147024895),
            (0xFFFF - 3, -2146959364),
            (0xFFFF - 2, -2146959363),
            (0xFFFF - 1, -2146959362),
            (0xFFFF + 0, -2146959361),
            (0xFFFF + 1, -2147024896),
            (0xFFFF + 2, -2147024895),
            (0xFFFF + 3, -2147024894),
        ]:
            with self.subTest(w32=w32, hr=hr):
                self.assertEqual(comtypes.hresult.HRESULT_FROM_WIN32(w32), hr)


class Test_signed32bithex_to_int(ut.TestCase):
    def test(self):
        for val, expected in [
            ("0x00000000", comtypes.hresult.S_OK),
            ("0x00000001", comtypes.hresult.S_FALSE),
            ("0x8000FFFF", comtypes.hresult.E_UNEXPECTED),
            ("0x80004002", comtypes.hresult.E_NOINTERFACE),
            # boundary values
            ("0x7FFFFFFF", 2147483647),
            ("0x80000000", -2147483648),
            ("0xFFFFFFFF", -1),
        ]:
            with self.subTest(val=val, expected=expected):
                self.assertEqual(comtypes.hresult.signed32bithex_to_int(val), expected)


class Test_int_to_signed32bithex(ut.TestCase):
    def test(self):
        for val, expected in [
            (comtypes.hresult.S_OK, "0x00000000"),
            (comtypes.hresult.S_FALSE, "0x00000001"),
            (comtypes.hresult.E_UNEXPECTED, "0x8000FFFF"),
            (comtypes.hresult.E_NOINTERFACE, "0x80004002"),
        ]:
            with self.subTest(val=val, expected=expected):
                self.assertEqual(comtypes.hresult.int_to_signed32bithex(val), expected)


class DocTest(ut.TestCase):
    def test(self):
        doctest.testmod(
            comtypes.hresult,
            verbose=False,
            optionflags=doctest.ELLIPSIS,
            raise_on_error=True,
        )
