import logging
from _ctypes import COMError
from typing import Any, Optional

import comtypes
import comtypes.client.dynamic
from comtypes import GUID, IUnknown, automation, typeinfo
from comtypes.client._generate import GetModule

logger = logging.getLogger(__name__)


def wrap_outparam(punk: Any) -> Any:
    logger.debug("wrap_outparam(%s)", punk)
    if not punk:
        return None
    if punk.__com_interface__ == automation.IDispatch:
        return GetBestInterface(punk)
    return punk


def GetBestInterface(punk: Any) -> Any:
    """Try to QueryInterface a COM pointer to the 'most useful'
    interface.

    Get type information for the provided object, either via
    IDispatch.GetTypeInfo(), or via IProvideClassInfo.GetClassInfo().
    Generate a wrapper module for the typelib, and QI for the
    interface found.
    """
    if not punk:  # NULL COM pointer
        return punk  # or should we return None?
    # find the typelib and the interface name
    logger.debug("GetBestInterface(%s)", punk)
    try:
        try:
            pci = punk.QueryInterface(typeinfo.IProvideClassInfo)
            logger.debug("Does implement IProvideClassInfo")
        except COMError:
            # Some COM objects support IProvideClassInfo2, but not IProvideClassInfo.
            # These objects are broken, but we support them anyway.
            logger.debug(
                "Does NOT implement IProvideClassInfo, trying IProvideClassInfo2"
            )
            pci = punk.QueryInterface(typeinfo.IProvideClassInfo2)
            logger.debug("Does implement IProvideClassInfo2")
        tinfo = pci.GetClassInfo()  # TypeInfo for the CoClass
        # find the interface marked as default
        ta = tinfo.GetTypeAttr()
        for index in range(ta.cImplTypes):
            if tinfo.GetImplTypeFlags(index) == 1:
                break
        else:
            if ta.cImplTypes != 1:
                # Hm, should we use dynamic now?
                raise TypeError("No default interface found")
            # Only one interface implemented, use that (even if
            # not marked as default).
            index = 0
        href = tinfo.GetRefTypeOfImplType(index)
        tinfo = tinfo.GetRefTypeInfo(href)
    except COMError:
        logger.debug("Does NOT implement IProvideClassInfo/IProvideClassInfo2")
        try:
            pdisp = punk.QueryInterface(automation.IDispatch)
        except COMError:
            logger.debug("No Dispatch interface: %s", punk)
            return punk
        try:
            tinfo = pdisp.GetTypeInfo(0)
        except COMError:
            pdisp = comtypes.client.dynamic.Dispatch(pdisp)
            logger.debug("IDispatch.GetTypeInfo(0) failed: %s" % pdisp)
            return pdisp
    typeattr = tinfo.GetTypeAttr()
    logger.debug("Default interface is %s", typeattr.guid)
    try:
        punk.QueryInterface(IUnknown, typeattr.guid)
    except COMError:
        logger.debug("Does not implement default interface, returning dynamic object")
        return comtypes.client.dynamic.Dispatch(punk)

    itf_name = tinfo.GetDocumentation(-1)[0]  # interface name
    tlib = tinfo.GetContainingTypeLib()[0]  # typelib

    # import the wrapper, generating it on demand
    mod = GetModule(tlib)
    # Python interface class
    interface = getattr(mod, itf_name)
    logger.debug("Implements default interface from typeinfo %s", interface)
    # QI for this interface
    # XXX
    # What to do if this fails?
    # In the following example the engine.Eval() call returns
    # such an object.
    #
    # engine = CreateObject("MsScriptControl.ScriptControl")
    # engine.Language = "JScript"
    # engine.Eval("[1, 2, 3]")
    #
    # Could the above code, as an optimization, check that QI works,
    # *before* generating the wrapper module?
    result = punk.QueryInterface(interface)
    logger.debug("Final result is %s", result)
    return result


def _manage(
    obj: Any, clsid: Optional[GUID], interface: Optional[type[IUnknown]]
) -> Any:
    obj.__dict__["__clsid"] = str(clsid)
    if interface is None:
        obj = GetBestInterface(obj)
    return obj
