from ctypes import POINTER, Structure, c_ulong
from typing import TYPE_CHECKING
from typing import Union as _UnionT

from comtypes import COMMETHOD, GUID, HRESULT, IUnknown

if TYPE_CHECKING:
    from ctypes import _CArgObject, _Pointer

    from comtypes import hints  # noqa  # type: ignore

    REFIID = _UnionT[_Pointer[GUID], _CArgObject]

_GUID = GUID


class tagCONNECTDATA(Structure):
    _fields_ = [
        ("pUnk", POINTER(IUnknown)),
        ("dwCookie", c_ulong),
    ]


CONNECTDATA = tagCONNECTDATA

################################################################


class IConnectionPointContainer(IUnknown):
    _iid_ = GUID("{B196B284-BAB4-101A-B69C-00AA00341D07}")
    _idlflags_ = []

    if TYPE_CHECKING:

        def EnumConnectionPoints(self) -> "IEnumConnectionPoints": ...
        def FindConnectionPoint(self, riid: REFIID) -> "IConnectionPoint": ...


class IConnectionPoint(IUnknown):
    _iid_ = GUID("{B196B286-BAB4-101A-B69C-00AA00341D07}")
    _idlflags_ = []

    if TYPE_CHECKING:

        def GetConnectionPointContainer(self) -> IConnectionPointContainer: ...
        def Advise(self, pUnkSink: IUnknown) -> int: ...
        def Unadvise(self, dwCookie: int) -> hints.Hresult: ...
        def EnumConnections(self) -> "IEnumConnections": ...


class IEnumConnections(IUnknown):
    _iid_ = GUID("{B196B287-BAB4-101A-B69C-00AA00341D07}")
    _idlflags_ = []

    if TYPE_CHECKING:

        def Next(self, cConnections: int) -> tuple[tagCONNECTDATA, int]: ...
        def Skip(self, cConnections: int) -> hints.Hresult: ...
        def Reset(self) -> hints.Hresult: ...
        def Clone(self) -> "IEnumConnections": ...

    def __iter__(self):
        return self

    def __next__(self):
        cp, fetched = self.Next(1)
        if fetched == 0:
            raise StopIteration
        return cp


class IEnumConnectionPoints(IUnknown):
    _iid_ = GUID("{B196B285-BAB4-101A-B69C-00AA00341D07}")
    _idlflags_ = []

    if TYPE_CHECKING:

        def Next(self, cConnections: int) -> tuple[IConnectionPoint, int]: ...
        def Skip(self, cConnections: int) -> hints.Hresult: ...
        def Reset(self) -> hints.Hresult: ...
        def Clone(self) -> "IEnumConnectionPoints": ...

    def __iter__(self):
        return self

    def __next__(self):
        cp, fetched = self.Next(1)
        if fetched == 0:
            raise StopIteration
        return cp


################################################################

IConnectionPointContainer._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        "EnumConnectionPoints",
        (["out"], POINTER(POINTER(IEnumConnectionPoints)), "ppEnum"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "FindConnectionPoint",
        (["in"], POINTER(_GUID), "riid"),
        (["out"], POINTER(POINTER(IConnectionPoint)), "ppCP"),
    ),
]

IConnectionPoint._methods_ = [
    COMMETHOD([], HRESULT, "GetConnectionInterface", (["out"], POINTER(_GUID), "pIID")),
    COMMETHOD(
        [],
        HRESULT,
        "GetConnectionPointContainer",
        (["out"], POINTER(POINTER(IConnectionPointContainer)), "ppCPC"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "Advise",
        (["in"], POINTER(IUnknown), "pUnkSink"),
        (["out"], POINTER(c_ulong), "pdwCookie"),
    ),
    COMMETHOD([], HRESULT, "Unadvise", (["in"], c_ulong, "dwCookie")),
    COMMETHOD(
        [],
        HRESULT,
        "EnumConnections",
        (["out"], POINTER(POINTER(IEnumConnections)), "ppEnum"),
    ),
]

IEnumConnections._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        "Next",
        (["in"], c_ulong, "cConnections"),
        (["out"], POINTER(tagCONNECTDATA), "rgcd"),
        (["out"], POINTER(c_ulong), "pcFetched"),
    ),
    COMMETHOD([], HRESULT, "Skip", (["in"], c_ulong, "cConnections")),
    COMMETHOD([], HRESULT, "Reset"),
    COMMETHOD(
        [], HRESULT, "Clone", (["out"], POINTER(POINTER(IEnumConnections)), "ppEnum")
    ),
]

IEnumConnectionPoints._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        "Next",
        (["in"], c_ulong, "cConnections"),
        (["out"], POINTER(POINTER(IConnectionPoint)), "ppCP"),
        (["out"], POINTER(c_ulong), "pcFetched"),
    ),
    COMMETHOD([], HRESULT, "Skip", (["in"], c_ulong, "cConnections")),
    COMMETHOD([], HRESULT, "Reset"),
    COMMETHOD(
        [],
        HRESULT,
        "Clone",
        (["out"], POINTER(POINTER(IEnumConnectionPoints)), "ppEnum"),
    ),
]
