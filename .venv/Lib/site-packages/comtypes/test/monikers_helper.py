from ctypes import HRESULT, POINTER, OleDLL, c_wchar_p
from ctypes.wintypes import DWORD

from comtypes import GUID, IUnknown

# https://learn.microsoft.com/en-us/windows/win32/api/objidl/ne-objidl-mksys
MKSYS_GENERICCOMPOSITE = 1
MKSYS_FILEMONIKER = 2
MKSYS_ANTIMONIKER = 3
MKSYS_ITEMMONIKER = 4
MKSYS_POINTERMONIKER = 5
MKSYS_CLASSMONIKER = 7
MKSYS_OBJREFMONIKER = 8

CLSID_CompositeMoniker = GUID("{00000309-0000-0000-c000-000000000046}")
CLSID_FileMoniker = GUID("{00000303-0000-0000-C000-000000000046}")
CLSID_AntiMoniker = GUID("{00000305-0000-0000-c000-000000000046}")
CLSID_ItemMoniker = GUID("{00000304-0000-0000-c000-000000000046}")
CLSID_PointerMoniker = GUID("{00000306-0000-0000-c000-000000000046}")
CLSID_ClassMoniker = GUID("{0000031A-0000-0000-C000-000000000046}")
CLSID_ObjrefMoniker = GUID("{00000327-0000-0000-c000-000000000046}")

ROTFLAGS_ALLOWANYCLIENT = 1

LPOLESTR = LPCOLESTR = c_wchar_p

_ole32 = OleDLL("ole32")

_CreateGenericComposite = _ole32.CreateGenericComposite
_CreateGenericComposite.argtypes = [
    POINTER(IUnknown),  # pmkFirst
    POINTER(IUnknown),  # pmkRest
    POINTER(POINTER(IUnknown)),  # ppmkComposite
]
_CreateGenericComposite.restype = HRESULT

_CreateFileMoniker = _ole32.CreateFileMoniker
_CreateFileMoniker.argtypes = [LPCOLESTR, POINTER(POINTER(IUnknown))]
_CreateFileMoniker.restype = HRESULT

_CreateAntiMoniker = _ole32.CreateAntiMoniker
_CreateAntiMoniker.argtypes = [POINTER(POINTER(IUnknown))]
_CreateAntiMoniker.restype = HRESULT

_CreateItemMoniker = _ole32.CreateItemMoniker
_CreateItemMoniker.argtypes = [LPCOLESTR, LPCOLESTR, POINTER(POINTER(IUnknown))]
_CreateItemMoniker.restype = HRESULT

_CreatePointerMoniker = _ole32.CreatePointerMoniker
_CreatePointerMoniker.argtypes = [POINTER(IUnknown), POINTER(POINTER(IUnknown))]
_CreatePointerMoniker.restype = HRESULT

_CreateClassMoniker = _ole32.CreateClassMoniker
_CreateClassMoniker.argtypes = [POINTER(GUID), POINTER(POINTER(IUnknown))]
_CreateClassMoniker.restype = HRESULT

_CreateObjrefMoniker = _ole32.CreateObjrefMoniker
_CreateObjrefMoniker.argtypes = [POINTER(IUnknown), POINTER(POINTER(IUnknown))]
_CreateObjrefMoniker.restype = HRESULT

_CreateBindCtx = _ole32.CreateBindCtx
_CreateBindCtx.argtypes = [DWORD, POINTER(POINTER(IUnknown))]
_CreateBindCtx.restype = HRESULT

_GetRunningObjectTable = _ole32.GetRunningObjectTable
_GetRunningObjectTable.argtypes = [DWORD, POINTER(POINTER(IUnknown))]
_GetRunningObjectTable.restype = HRESULT

# Common COM Errors from Moniker/Binding Context operations
MK_E_NOINVERSE = -2147221012  # 0x800401EC
MK_E_NEEDGENERIC = -2147221022  # 0x800401E2
MK_E_SYNTAX = -2147221020  # 0x800401E4
MK_E_UNAVAILABLE = -2147221021  # 0x800401E3
