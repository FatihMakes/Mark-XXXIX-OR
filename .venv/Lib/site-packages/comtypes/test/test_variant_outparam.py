import unittest as ut

from comtypes import automation, typeinfo
from comtypes.client import CoGetObject


# WMI has dual interfaces.
# Some methods/properties have "[out] POINTER(VARIANT)" parameters.
# This test checks that these parameters are returned as strings:
# that's what VARIANT.__ctypes_from_outparam__ does.
class TestWMI(ut.TestCase):
    def test_wmi(self):
        wmi: "WbemScripting.ISWbemServices" = CoGetObject("winmgmts:")
        disks = wmi.InstancesOf("Win32_LogicalDisk")

        # There are different typelibs installed for WMI on win2k and winXP.
        # WbemScripting refers to their guid:
        #   Win2k:
        #     import comtypes.gen._565783C6_CB41_11D1_8B02_00600806D9B6_0_1_1 as mod
        #   WinXP:
        #     import comtypes.gen._565783C6_CB41_11D1_8B02_00600806D9B6_0_1_2 as mod
        # So, the one that's referenced onm WbemScripting will be used, whether the
        # actual typelib is available or not.  XXX
        from comtypes.gen import WbemScripting

        self.assertTrue(hasattr(WbemScripting, "wbemPrivilegeCreateToken"))

        for item in disks:
            # obj[index] is forwarded to obj.Item(index)
            item: "WbemScripting.ISWbemObject"
            a = item.Properties_["Caption"].Value
            b = item.Properties_.Item("Caption").Value
            c = item.Properties_("Caption").Value
            self.assertEqual(a, b)
            self.assertEqual(a, c)
            self.assertTrue(isinstance(a, str))
            self.assertTrue(isinstance(b, str))
            self.assertTrue(isinstance(c, str))
            # Verify parameter types from the interface type.
            dispti = item.Properties_["Caption"].GetTypeInfo(0)
            # GetRefTypeOfImplType(-1) returns the custom portion
            # of a dispinterface, if it is dual
            # See https://learn.microsoft.com/en-us/windows/win32/api/oaidl/nf-oaidl-itypeinfo-getreftypeofimpltype#remarks
            dualti = dispti.GetRefTypeInfo(dispti.GetRefTypeOfImplType(-1))
            # .Value is a property with "[out] POINTER(VARIANT)" parameter.
            fd = dualti.GetFuncDesc(0)
            names = dualti.GetNames(fd.memid, fd.cParams + 1)
            self.assertEqual(names, ["Value", "varValue"])
            edesc = fd.lprgelemdescParam[0]
            self.assertEqual(
                edesc._.paramdesc.wParamFlags,
                typeinfo.PARAMFLAG_FOUT | typeinfo.PARAMFLAG_FRETVAL,
            )
            tdesc = edesc.tdesc
            self.assertEqual(tdesc.vt, automation.VT_PTR)
            self.assertEqual(tdesc._.lptdesc[0].vt, automation.VT_VARIANT)
            result = {}
            for prop in item.Properties_:
                prop: "WbemScripting.ISWbemProperty"
                self.assertTrue(isinstance(prop.Name, str))
                result[prop.Name] = prop.Value
                # print "\t", (prop.Name, prop.Value)
            self.assertEqual(len(item.Properties_), item.Properties_.Count)
            self.assertEqual(len(item.Properties_), len(result))
            self.assertTrue(isinstance(item.Properties_["Description"].Value, str))
        # len(obj) is forwared to obj.Count
        self.assertEqual(len(disks), disks.Count)


if __name__ == "__main__":
    ut.main()
