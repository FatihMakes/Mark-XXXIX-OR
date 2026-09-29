import contextlib
import time
import unittest

import comtypes
import comtypes.client

with contextlib.redirect_stdout(None):  # supress warnings
    comtypes.client.GetModule("msvidctl.dll")
from comtypes.gen import MSVidCtlLib as msvidctl

try:
    # pass Word libUUID
    comtypes.client.GetModule(("{00020905-0000-0000-C000-000000000046}",))
    IMPORT_WORD_FAILED = False
except (ImportError, OSError):
    IMPORT_WORD_FAILED = True


################################################################
#
# TODO:
#
# It seems bad that only external test like this
# can verify the behavior of `comtypes` implementation.
# Find a different built-in win32 API to use.
#
################################################################


@unittest.skipIf(IMPORT_WORD_FAILED, "This depends on Word.")
class Test_Word(unittest.TestCase):
    def setUp(self):
        try:
            comtypes.client.GetActiveObject("Word.Application")
        except OSError:
            pass
        else:
            # seems word is running, we cannot test this.
            self.fail("MSWord is running, cannot test")
        # create a WORD instance
        self.w1 = comtypes.client.CreateObject("Word.Application")

    def tearDown(self):
        if hasattr(self, "w1"):
            self.w1.Quit()
            del self.w1

    def test(self):
        # connect to the running instance
        w1 = self.w1
        w2 = comtypes.client.GetActiveObject("Word.Application")

        # check if they are referring to the same object
        self.assertEqual(
            w1.QueryInterface(comtypes.IUnknown), w2.QueryInterface(comtypes.IUnknown)
        )

        w1.Quit()
        del self.w1

        time.sleep(1)

        with self.assertRaises(comtypes.COMError) as arc:
            w2.Visible

        err = arc.exception
        variables = err.hresult, err.text, err.details
        self.assertEqual(variables, err.args)
        with self.assertRaises(WindowsError):
            comtypes.client.GetActiveObject("Word.Application")


class Test_MSVidCtlLib(unittest.TestCase):
    def test_register_and_revoke(self):
        CLSID_MSVidCtl = msvidctl.MSVidCtl._reg_clsid_
        vidctl = comtypes.client.CreateObject(msvidctl.MSVidCtl)
        with self.assertRaises(WindowsError):
            comtypes.client.GetActiveObject(msvidctl.MSVidCtl)
        handle = comtypes.client.RegisterActiveObject(vidctl, msvidctl.MSVidCtl)
        with self.assertRaises(ValueError):
            comtypes.client.GetActiveObject(
                CLSID_MSVidCtl,
                interface=msvidctl.IMSVidCtl,
                dynamic=True,  # type: ignore
            )
        activeobj = comtypes.client.GetActiveObject(msvidctl.MSVidCtl)
        self.assertEqual(vidctl, activeobj)
        dynamicobj = comtypes.client.GetActiveObject(CLSID_MSVidCtl, dynamic=True)
        self.assertIsInstance(dynamicobj, comtypes.client.lazybind.Dispatch)
        self.assertEqual(hash(vidctl), hash(dynamicobj))
        comtypes.client.RevokeActiveObject(handle)
        with self.assertRaises(WindowsError):
            comtypes.client.GetActiveObject(msvidctl.MSVidCtl)


if __name__ == "__main__":
    unittest.main()
