from ctypes import Structure, Union, byref, windll
from ctypes.wintypes import DWORD, LONG, LPWSTR, ULARGE_INTEGER, VARIANT_BOOL, WORD

from comtypes import GUID
from comtypes.automation import VARTYPE, VT_BOOL, VT_CLSID, VT_LPWSTR, VT_UI4


class PROPVARIANT_UNION(Union):
    _fields_ = [
        ("lVal", LONG),
        ("uhVal", ULARGE_INTEGER),
        ("boolVal", VARIANT_BOOL),
        ("pwszVal", LPWSTR),
        ("puuid", GUID),
    ]


class PROPVARIANT(Structure):
    _fields_ = [
        ("vt", VARTYPE),
        ("reserved1", WORD),
        ("reserved2", WORD),
        ("reserved3", WORD),
        ("union", PROPVARIANT_UNION),
    ]

    def GetValue(self):
        vt = self.vt
        if vt == VT_BOOL:
            return self.union.boolVal != 0
        elif vt == VT_LPWSTR:
            # Try multiple access patterns for comtypes compatibility
            # Pattern 1: Direct union access
            result = getattr(self.union, "pwszVal", None)
            if result is not None:
                return result
            # Pattern 2: Nested value object
            value_obj = getattr(self, "value", None)
            if value_obj is not None:
                result = getattr(value_obj, "pwszVal", None)
                if result is not None:
                    return result
            # Pattern 3: Anonymous union access
            result = getattr(self, "pwszVal", None)
            if result is not None:
                return result
            # Pattern 4: Data object access
            data_obj = getattr(self, "data", None)
            if data_obj is not None:
                result = getattr(data_obj, "pwszVal", None)
                if result is not None:
                    return result
            return None
        elif vt == VT_UI4:
            return self.union.lVal
        elif vt == VT_CLSID:
            return
        else:
            return "%s:?" % (vt)

    def clear(self):
        windll.ole32.PropVariantClear(byref(self))


class PROPERTYKEY(Structure):
    _fields_ = [
        ("fmtid", GUID),
        ("pid", DWORD),
    ]

    def __str__(self):
        return "%s %s" % (self.fmtid, self.pid)
