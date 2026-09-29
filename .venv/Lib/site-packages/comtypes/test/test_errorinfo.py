import unittest as ut

from comtypes import errorinfo, shelllink
from comtypes import hresult as hres


class Test_GetErrorInfo(ut.TestCase):
    def test_error_has_been_set(self):
        self.assertIsNone(errorinfo.GetErrorInfo())
        errmsg = "sample unexpected error message for tests"
        errcode = hres.E_UNEXPECTED
        helpcontext = 123
        hr = errorinfo.ReportError(
            errmsg,
            shelllink.IShellLinkW._iid_,
            str(shelllink.ShellLink._reg_clsid_),
            helpfile="help.chm",
            helpcontext=helpcontext,
            hresult=errcode,
        )
        self.assertEqual(errcode, hr)
        pei = errorinfo.GetErrorInfo()
        self.assertIsNotNone(pei)
        assert pei is not None  # for static type guard
        self.assertEqual(shelllink.IShellLinkW._iid_, pei.GetGUID())
        self.assertEqual("lnkfile", pei.GetSource())
        self.assertEqual(errmsg, pei.GetDescription())
        self.assertEqual("help.chm", pei.GetHelpFile())
        self.assertEqual(helpcontext, pei.GetHelpContext())
        # Calling `GetErrorInfo` clears the error state for the thread.
        # Therefore, `None` is returned in the second call.
        self.assertIsNone(errorinfo.GetErrorInfo())

    def test_without_optional_args(self):
        self.assertIsNone(errorinfo.GetErrorInfo())
        errmsg = "sample unexpected error message for tests"
        hr = errorinfo.ReportError(errmsg, shelllink.IShellLinkW._iid_)
        self.assertEqual(hres.DISP_E_EXCEPTION, hr)
        pei = errorinfo.GetErrorInfo()
        self.assertIsNotNone(pei)
        assert pei is not None  # for static type guard
        self.assertEqual(shelllink.IShellLinkW._iid_, pei.GetGUID())
        self.assertIsNone(pei.GetSource())
        self.assertEqual(errmsg, pei.GetDescription())
        self.assertIsNone(pei.GetHelpFile())
        self.assertEqual(0, pei.GetHelpContext())

    def test_error_has_not_been_set(self):
        self.assertIsNone(errorinfo.GetErrorInfo())
        pei = errorinfo.GetErrorInfo()
        self.assertIsNone(pei)


def raise_runtime_error():
    _raise_runtime_error()


def _raise_runtime_error():
    raise RuntimeError("for testing")


class Test_ReportException(ut.TestCase):
    def test_without_stacklevel(self):
        self.assertIsNone(errorinfo.GetErrorInfo())
        iid = shelllink.IShellLinkW._iid_
        try:
            raise_runtime_error()
        except RuntimeError:
            hr = errorinfo.ReportException(hres.E_UNEXPECTED, iid)
        self.assertEqual(hres.E_UNEXPECTED, hr)
        pei = errorinfo.GetErrorInfo()
        self.assertIsNotNone(pei)
        assert pei is not None  # for static type guard
        self.assertEqual(shelllink.IShellLinkW._iid_, pei.GetGUID())
        self.assertIsNone(pei.GetSource())
        self.assertEqual("<class 'RuntimeError'>: for testing", pei.GetDescription())
        self.assertIsNone(pei.GetHelpFile())
        self.assertEqual(0, pei.GetHelpContext())
        self.assertIsNone(errorinfo.GetErrorInfo())

    def test_with_stacklevel(self):
        self.assertIsNone(errorinfo.GetErrorInfo())
        stem = "<class 'RuntimeError'>: for testing"
        iid = shelllink.IShellLinkW._iid_
        for slv, text in [
            # XXX: If the codebase changes, the line where functions or
            # methods are defined will change, meaning this test is brittle.
            (0, f"{stem} ({__name__}, line 96)"),
            (1, f"{stem} ({__name__}, line 55)"),
            (2, f"{stem} ({__name__}, line 59)"),
        ]:
            with self.subTest(text=text):
                try:
                    raise_runtime_error()
                except RuntimeError:
                    errorinfo.ReportException(hres.E_UNEXPECTED, iid, stacklevel=slv)
                pei = errorinfo.GetErrorInfo()
                assert pei is not None  # for static type guard
                self.assertEqual(text, pei.GetDescription())
                self.assertIsNone(errorinfo.GetErrorInfo())

    def test_with_over_stacklevel(self):
        self.assertIsNone(errorinfo.GetErrorInfo())
        iid = shelllink.IShellLinkW._iid_
        try:
            raise_runtime_error()
        except RuntimeError:
            with self.assertRaises(ValueError):
                errorinfo.ReportException(hres.E_UNEXPECTED, iid, stacklevel=4)

    def test_with_no_error_and_zero_stacklevel(self):
        self.assertIsNone(errorinfo.GetErrorInfo())
        iid = shelllink.IShellLinkW._iid_
        with self.assertRaises(ValueError):
            errorinfo.ReportException(hres.E_UNEXPECTED, iid, stacklevel=0)
