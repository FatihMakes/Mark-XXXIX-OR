import ctypes
from ctypes import HRESULT, POINTER
from ctypes.wintypes import BOOL, DWORD, LPCWSTR

from comtypes import COMMETHOD, GUID, IUnknown

from pycaw.api.mmdeviceapi import PROPERTYKEY
from pycaw.api.mmdeviceapi.depend import PROPVARIANT


class IPolicyConfig(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
    _methods_ = (
        COMMETHOD([], HRESULT, "Unused1"),
        COMMETHOD([], HRESULT, "Unused2"),
        COMMETHOD([], HRESULT, "Unused3"),
        COMMETHOD([], HRESULT, "Unused4"),
        COMMETHOD([], HRESULT, "Unused5"),
        COMMETHOD([], HRESULT, "Unused6"),
        COMMETHOD([], HRESULT, "Unused7"),
        COMMETHOD([], HRESULT, "Unused8"),
        COMMETHOD(
            [],
            HRESULT,
            "GetPropertyValue",
            (["in"], LPCWSTR, "pwstrDeviceId"),
            (["in"], POINTER(PROPERTYKEY), "pKey"),
            (["out"], POINTER(PROPVARIANT), "pValue"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetPropertyValue",
            (["in"], LPCWSTR, "pwstrDeviceId"),
            (["in"], POINTER(PROPERTYKEY), "pKey"),
            (["in"], POINTER(PROPVARIANT), "pValue"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetDefaultEndpoint",
            (["in"], LPCWSTR, "pwstrDeviceId"),
            (["in"], DWORD, "role"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetEndpointVisibility",
            (["in"], LPCWSTR, "pwstrDeviceId"),
            (["in"], BOOL, "bVisible"),
        ),
    )


class IPolicyConfigVista(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID("{568B9108-44BF-40B4-9006-86AFE5B5A620}")
    _methods_ = (
        COMMETHOD(
            [],
            HRESULT,
            "GetMixFormat",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["out"], POINTER(ctypes.c_void_p), "ppFormat"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetDeviceFormat",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["in"], BOOL, "bDefault"),
            (["out"], POINTER(ctypes.c_void_p), "ppFormat"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetDeviceFormat",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["in"], ctypes.c_void_p, "pEndpointFormat"),
            (["in"], ctypes.c_void_p, "mixFormat"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetProcessingPeriod",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["in"], BOOL, "bDefault"),
            (["out"], POINTER(ctypes.c_longlong), "pmftDefaultPeriod"),
            (["out"], POINTER(ctypes.c_longlong), "pmftMinimumPeriod"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetProcessingPeriod",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["in"], POINTER(ctypes.c_longlong), "pmftPeriod"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetShareMode",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["out"], POINTER(ctypes.c_void_p), "pMode"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetShareMode",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["in"], ctypes.c_void_p, "mode"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetPropertyValue",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["in"], POINTER(ctypes.c_void_p), "key"),
            (["out"], POINTER(ctypes.c_void_p), "pv"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetPropertyValue",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["in"], POINTER(ctypes.c_void_p), "key"),
            (["in"], POINTER(ctypes.c_void_p), "pv"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetDefaultEndpoint",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["in"], DWORD, "role"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetEndpointVisibility",
            (["in"], LPCWSTR, "wszDeviceId"),
            (["in"], BOOL, "bVisible"),
        ),
    )
