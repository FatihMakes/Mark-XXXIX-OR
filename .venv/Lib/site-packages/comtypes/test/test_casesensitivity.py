import contextlib
import unittest

from comtypes.client import GetModule

with contextlib.redirect_stdout(None):  # supress warnings
    GetModule("msvidctl.dll")
from comtypes.gen import MSVidCtlLib as msvidctl


class TestCase(unittest.TestCase):
    def test(self):
        # IDispatch(IUnknown)
        # IMSVidDevice(IDispatch)
        # IMSVidInputDevice(IMSVidDevice)
        # IMSVidPlayback(IMSVidOutputDevice)

        self.assertTrue(issubclass(msvidctl.IMSVidPlayback, msvidctl.IMSVidInputDevice))
        self.assertTrue(issubclass(msvidctl.IMSVidInputDevice, msvidctl.IMSVidDevice))

        # names in the base class __map_case__ must also appear in the
        # subclass.
        for name in msvidctl.IMSVidDevice.__map_case__:
            self.assertIn(name, msvidctl.IMSVidInputDevice.__map_case__)
            self.assertIn(name, msvidctl.IMSVidPlayback.__map_case__)

        for name in msvidctl.IMSVidInputDevice.__map_case__:
            self.assertIn(name, msvidctl.IMSVidPlayback.__map_case__)


if __name__ == "__main__":
    unittest.main()
