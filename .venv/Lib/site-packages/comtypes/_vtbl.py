import logging
from _ctypes import COMError
from collections.abc import Callable, Iterator, Sequence
from ctypes import WINFUNCTYPE, Structure, c_void_p
from typing import TYPE_CHECKING, Any, Optional
from typing import Union as _UnionT

import comtypes
from comtypes import GUID, IUnknown, hresult
from comtypes._memberspec import (
    DISPATCH_METHOD,
    DISPATCH_PROPERTYGET,
    DISPATCH_PROPERTYPUT,
    DISPATCH_PROPERTYPUTREF,
    _encode_idl,
)
from comtypes.errorinfo import ReportError, ReportException

if TYPE_CHECKING:
    from ctypes import _FuncPointer

    from comtypes import hints  # type: ignore
    from comtypes._memberspec import _ComIdlFlags, _DispIdlFlags, _DispMemberSpec

logger = logging.getLogger(__name__)
_debug = logger.debug
_warning = logger.warning
_error = logger.error


class E_NotImplemented(Exception):
    """COM method is not implemented"""


def HRESULT_FROM_WIN32(errcode: Optional[int]) -> int:
    "Convert a Windows error code into a HRESULT value."
    if errcode is None:
        return 0x80000000
    if errcode & 0x80000000:
        return errcode
    return (errcode & 0xFFFF) | 0x80070000


def winerror(exc: Exception) -> int:
    """Return the windows error code from a WindowsError or COMError
    instance."""
    if isinstance(exc, COMError):
        return exc.hresult
    elif isinstance(exc, WindowsError):
        code = exc.winerror
        if isinstance(code, int):
            return code
        # Sometimes, a WindowsError instance has no error code.  An access
        # violation raised by ctypes has only text, for example.  In this
        # cases we return a generic error code.
        return hresult.E_FAIL
    raise TypeError(
        f"Expected comtypes.COMERROR or WindowsError instance, got {type(exc).__name__}"
    )


def _do_implement(interface_name: str, method_name: str) -> Callable[..., int]:
    def _not_implemented(*args):
        """Return E_NOTIMPL because the method is not implemented."""
        _debug("unimplemented method %s_%s called", interface_name, method_name)
        return hresult.E_NOTIMPL

    return _not_implemented


def catch_errors(
    obj: "hints.COMObject",
    mth: Callable[..., Any],
    paramflags: Optional[tuple["hints.ParamFlagType", ...]],
    interface: type[IUnknown],
    mthname: str,
) -> Callable[..., Any]:
    clsid = getattr(obj, "_reg_clsid_", None)

    def call_with_this(*args, **kw):
        try:
            result = mth(*args, **kw)
        except comtypes.ReturnHRESULT as err:
            (hr, text) = err.args
            return ReportError(text, iid=interface._iid_, clsid=clsid, hresult=hr)
        except (OSError, COMError) as details:
            _error(
                "Exception in %s.%s implementation:",
                interface.__name__,
                mthname,
                exc_info=True,
            )
            return HRESULT_FROM_WIN32(winerror(details))
        except E_NotImplemented:
            _warning("Unimplemented method %s.%s called", interface.__name__, mthname)
            return hresult.E_NOTIMPL
        except:
            _error(
                "Exception in %s.%s implementation:",
                interface.__name__,
                mthname,
                exc_info=True,
            )
            return ReportException(hresult.E_FAIL, interface._iid_, clsid=clsid)
        if result is None:
            return hresult.S_OK
        return result

    if paramflags is None:
        has_outargs = False
    else:
        has_outargs = bool([x[0] for x in paramflags if x[0] & 2])
    call_with_this.has_outargs = has_outargs
    return call_with_this


################################################################


def hack(
    inst: "hints.COMObject",
    mth: Callable[..., Any],
    paramflags: Optional[tuple["hints.ParamFlagType", ...]],
    interface: type[IUnknown],
    mthname: str,
) -> Callable[..., Any]:
    if paramflags is None:
        return catch_errors(inst, mth, paramflags, interface, mthname)
    code = mth.__code__
    if code.co_varnames[1:2] == ("this",):
        return catch_errors(inst, mth, paramflags, interface, mthname)
    dirflags = [f[0] for f in paramflags]
    # An argument is an input arg either if flags are NOT set in the
    # idl file, or if the flags contain 'in'. In other words, the
    # direction flag is either exactly '0' or has the '1' bit set:
    # Output arguments have flag '2'

    args_out_idx = []
    args_in_idx = []
    for i, a in enumerate(dirflags):
        if a & 2:
            args_out_idx.append(i)
        if a & 1 or a == 0:
            args_in_idx.append(i)
    args_out = len(args_out_idx)

    ## XXX Remove this:
    # if args_in != code.co_argcount - 1:
    #     return catch_errors(inst, mth, interface, mthname)

    clsid = getattr(inst, "_reg_clsid_", None)

    def call_without_this(this, *args):
        # Method implementations could check for and return E_POINTER
        # themselves.  Or an error will be raised when
        # 'outargs[i][0] = value' is executed.
        # for a in outargs:
        #     if not a:
        #         return E_POINTER

        # make argument list for handler by index array built above
        inargs = []
        for a in args_in_idx:
            inargs.append(args[a])
        try:
            result = mth(*inargs)
            if args_out == 1:
                args[args_out_idx[0]][0] = result
            elif args_out != 0:
                if len(result) != args_out:
                    msg = f"Method should have returned a {args_out}-tuple"
                    raise ValueError(msg)
                for i, value in enumerate(result):
                    args[args_out_idx[i]][0] = value
        except comtypes.ReturnHRESULT as err:
            (hr, text) = err.args
            return ReportError(text, iid=interface._iid_, clsid=clsid, hresult=hr)
        except COMError as err:
            (hr, text, details) = err.args
            _error(
                "Exception in %s.%s implementation:",
                interface.__name__,
                mthname,
                exc_info=True,
            )
            try:
                descr, source, helpfile, helpcontext, progid = details
            except (ValueError, TypeError):
                msg = str(details)
            else:
                msg = f"{source}: {descr}"
            hr = HRESULT_FROM_WIN32(hr)
            return ReportError(msg, iid=interface._iid_, clsid=clsid, hresult=hr)
        except OSError as details:
            _error(
                "Exception in %s.%s implementation:",
                interface.__name__,
                mthname,
                exc_info=True,
            )
            hr = HRESULT_FROM_WIN32(winerror(details))
            return ReportException(hr, interface._iid_, clsid=clsid)
        except E_NotImplemented:
            _warning("Unimplemented method %s.%s called", interface.__name__, mthname)
            return hresult.E_NOTIMPL
        except:
            _error(
                "Exception in %s.%s implementation:",
                interface.__name__,
                mthname,
                exc_info=True,
            )
            return ReportException(hresult.E_FAIL, interface._iid_, clsid=clsid)
        return hresult.S_OK

    if args_out:
        call_without_this.has_outargs = True
    return call_without_this


class _MethodFinder:
    def __init__(self, inst: "hints.COMObject") -> None:
        self.inst = inst
        # map lower case names to names with correct spelling.
        self.names = dict([(n.lower(), n) for n in dir(inst)])

    def get_impl(
        self,
        interface: type[IUnknown],
        mthname: str,
        paramflags: Optional[tuple["hints.ParamFlagType", ...]],
        idlflags: _UnionT["_ComIdlFlags", "_DispIdlFlags"],
    ) -> Callable[..., Any]:
        mth = self.find_impl(interface, mthname, paramflags, idlflags)
        if mth is None:
            return _do_implement(interface.__name__, mthname)
        return hack(self.inst, mth, paramflags, interface, mthname)

    def find_method(self, fq_name: str, mthname: str) -> Callable[..., Any]:
        # Try to find a method, first with the fully qualified name
        # ('IUnknown_QueryInterface'), if that fails try the simple
        # name ('QueryInterface')
        try:
            return getattr(self.inst, fq_name)
        except AttributeError:
            pass
        return getattr(self.inst, mthname)

    def find_impl(
        self,
        interface: type[IUnknown],
        mthname: str,
        paramflags: Optional[tuple["hints.ParamFlagType", ...]],
        idlflags: _UnionT["_ComIdlFlags", "_DispIdlFlags"],
    ) -> Optional[Callable[..., Any]]:
        fq_name = f"{interface.__name__}_{mthname}"
        if interface._case_insensitive_:
            # simple name, like 'QueryInterface'
            mthname = self.names.get(mthname.lower(), mthname)
            # qualified name, like 'IUnknown_QueryInterface'
            fq_name = self.names.get(fq_name.lower(), fq_name)

        try:
            return self.find_method(fq_name, mthname)
        except AttributeError:
            pass
        propname = mthname[5:]  # strip the '_get_' or '_set' prefix
        if interface._case_insensitive_:
            propname = self.names.get(propname.lower(), propname)
        # propput and propget is done with 'normal' attribute access,
        # but only for COM properties that do not take additional
        # arguments:

        if "propget" in idlflags and len(paramflags) == 1:
            return self.getter(propname)
        if "propput" in idlflags and len(paramflags) == 1:
            return self.setter(propname)
        _debug("%r: %s.%s not implemented", self.inst, interface.__name__, mthname)
        return None

    def setter(self, propname: str) -> Callable[[Any], Any]:
        #
        def set(self, value):
            try:
                # XXX this may not be correct is the object implements
                # _get_PropName but not _set_PropName
                setattr(self, propname, value)
            except AttributeError:
                raise E_NotImplemented()

        return comtypes.instancemethod(set, self.inst, type(self.inst))

    def getter(self, propname: str) -> Callable[[], Any]:
        def get(self):
            try:
                return getattr(self, propname)
            except AttributeError:
                raise E_NotImplemented()

        return comtypes.instancemethod(get, self.inst, type(self.inst))


def _create_vtbl_type(
    fields: tuple[tuple[str, type["_FuncPointer"]], ...], itf: type[IUnknown]
) -> type[Structure]:
    try:
        return _vtbl_types[fields]
    except KeyError:

        class Vtbl(Structure):
            _fields_ = fields

        Vtbl.__name__ = f"Vtbl_{itf.__name__}"
        _vtbl_types[fields] = Vtbl
        return Vtbl


# Ugh. Another type cache to avoid leaking types.
_vtbl_types: dict[tuple[tuple[str, type["_FuncPointer"]], ...], type[Structure]] = {}

################################################################


def create_vtbl_mapping(
    itf: type[IUnknown], finder: _MethodFinder
) -> tuple[Sequence[GUID], Structure]:
    methods: list[Callable[..., Any]] = []  # method implementations
    fields: list[tuple[str, type["_FuncPointer"]]] = []  # virtual function table
    iids: list[GUID] = []  # interface identifiers.
    for interface in _walk_itf_bases(itf):
        iids.append(interface._iid_)
        for m in interface._methods_:
            proto = WINFUNCTYPE(m.restype, c_void_p, *m.argtypes)
            fields.append((m.name, proto))
            mth = finder.get_impl(interface, m.name, m.paramflags, m.idlflags)
            methods.append(proto(mth))
    Vtbl = _create_vtbl_type(tuple(fields), itf)
    vtbl = Vtbl(*methods)
    return (iids, vtbl)


def _walk_itf_bases(itf: type[IUnknown]) -> Iterator[type[IUnknown]]:
    """Iterates over interface inheritance in reverse order to build the
    virtual function table, and leave out the 'object' base class.
    """
    yield from itf.__mro__[-2::-1]


def create_dispimpl(
    itf: type[IUnknown], finder: _MethodFinder
) -> dict[tuple[comtypes.dispid, int], Callable[..., Any]]:
    dispimpl: dict[tuple[comtypes.dispid, int], Callable[..., Any]] = {}
    for m in itf._disp_methods_:
        #################
        # What we have:
        #
        # restypes is a ctypes type or None
        # argspec is seq. of (['in'], paramtype, paramname) tuples (or
        # lists?)
        #################
        # What we need:
        #
        # idlflags must contain 'propget', 'propset' and so on:
        # Must be constructed by converting disptype
        #
        # paramflags must be a sequence
        # of (F_IN|F_OUT|F_RETVAL, paramname[, default-value]) tuples
        #################

        if m.what == "DISPMETHOD":
            dispimpl.update(_make_dispmthentry(itf, finder, m))
        elif m.what == "DISPPROPERTY":
            dispimpl.update(_make_disppropentry(itf, finder, m))
    return dispimpl


def _make_dispmthentry(
    itf: type[IUnknown], finder: _MethodFinder, m: "_DispMemberSpec"
) -> Iterator[tuple[tuple[comtypes.dispid, int], Callable[..., Any]]]:
    if "propget" in m.idlflags:
        invkind = DISPATCH_PROPERTYGET
        mthname = f"_get_{m.name}"
    elif "propput" in m.idlflags:
        invkind = DISPATCH_PROPERTYPUT
        mthname = f"_set_{m.name}"
    elif "propputref" in m.idlflags:
        invkind = DISPATCH_PROPERTYPUTREF
        mthname = f"_setref_{m.name}"
    else:
        invkind = DISPATCH_METHOD
        if m.restype:
            argspec = m.argspec + ((["out"], m.restype, ""),)
        else:
            argspec = m.argspec
        mthname = m.name
    yield from _make_dispentry(finder, itf, mthname, m.idlflags, argspec, invkind)


def _make_disppropentry(
    itf: type[IUnknown], finder: _MethodFinder, m: "_DispMemberSpec"
) -> Iterator[tuple[tuple[comtypes.dispid, int], Callable[..., Any]]]:
    if m.restype:
        # DISPPROPERTY have implicit "out"
        argspec = m.argspec + ((["out"], m.restype, ""),)
    else:
        argspec = m.argspec
    yield from _make_dispentry(
        finder, itf, f"_get_{m.name}", m.idlflags, argspec, DISPATCH_PROPERTYGET
    )
    if "readonly" not in m.idlflags:
        yield from _make_dispentry(
            finder, itf, f"_set_{m.name}", m.idlflags, argspec, DISPATCH_PROPERTYPUT
        )
        # Add DISPATCH_PROPERTYPUTREF also?


def _make_dispentry(
    finder: _MethodFinder,
    interface: type[IUnknown],
    mthname: str,
    idlflags: "_DispIdlFlags",
    argspec: tuple["hints.ArgSpecElmType", ...],
    invkind: int,
) -> Iterator[tuple[tuple[comtypes.dispid, int], Callable[..., Any]]]:
    # We build a _dispmap_ entry now that maps invkind and dispid to
    # implementations that the finder finds; IDispatch_Invoke will later call it.
    paramflags = tuple(((_encode_idl(x[0]), x[1]) + tuple(x[3:])) for x in argspec)
    # XXX can the dispid be at a different index?  Check codegenerator.
    dispid = idlflags[0]
    impl = finder.get_impl(interface, mthname, paramflags, idlflags)  # type: ignore
    yield ((dispid, invkind), impl)  # type: ignore
    # invkind is really a set of flags; we allow both DISPATCH_METHOD and
    # DISPATCH_PROPERTYGET (win32com uses this, maybe other languages too?)
    if invkind in (DISPATCH_METHOD, DISPATCH_PROPERTYGET):
        yield ((dispid, DISPATCH_METHOD | DISPATCH_PROPERTYGET), impl)  # type: ignore
