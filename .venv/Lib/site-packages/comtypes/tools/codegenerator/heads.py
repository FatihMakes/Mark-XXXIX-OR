import io
from collections.abc import Sequence
from typing import Optional

from comtypes.tools import typedesc
from comtypes.tools.codegenerator import typeannotator


def _to_docstring(orig: str, depth: int = 1) -> str:
    # increasing `depth` by one increases indentation by one
    indent = "    " * depth
    # some chars are replaced to avoid causing a `SyntaxError`
    repled = orig.replace("\\", r"\\").replace('"', r"'")
    return f'{indent}"""{repled}"""'


class StructureHeadWriter:
    def __init__(self, stream: io.StringIO) -> None:
        self.stream = stream

    def write(self, head: typedesc.StructureHead, basenames: Sequence[str]) -> None:
        if head.struct.location:
            print(f"# {head.struct.location}", file=self.stream)
        if basenames:
            method_names = [
                m.name for m in head.struct.members if type(m) is typedesc.Method
            ]
            print(
                f"class {head.struct.name}({', '.join(basenames)}):",
                file=self.stream,
            )
            print(
                "    _iid_ = GUID('{}') # please look up iid and fill in!",
                file=self.stream,
            )
            if "Enum" in method_names:
                print("    def __iter__(self):", file=self.stream)
                print("        return self.Enum()", file=self.stream)
            elif method_names == "Next Skip Reset Clone".split():
                print("    def __iter__(self):", file=self.stream)
                print("        return self", file=self.stream)
                print(file=self.stream)
                print("    def next(self):", file=self.stream)
                print("         arr, fetched = self.Next(1)", file=self.stream)
                print("         if fetched == 0:", file=self.stream)
                print("             raise StopIteration", file=self.stream)
                print("         return arr[0]", file=self.stream)

        else:
            methods = [m for m in head.struct.members if type(m) is typedesc.Method]

            if methods:
                # Hm. We cannot generate code for IUnknown...
                print("assert 0, 'cannot generate code for IUnknown'", file=self.stream)
                print(f"class {head.struct.name}(_com_interface):", file=self.stream)
                print("    pass", file=self.stream)
            elif type(head.struct) is typedesc.Structure:
                print(f"class {head.struct.name}(Structure):", file=self.stream)
                if hasattr(head.struct, "_recordinfo_"):
                    print(
                        f"    _recordinfo_ = {head.struct._recordinfo_!r}",
                        file=self.stream,
                    )
                else:
                    print("    pass", file=self.stream)
            elif type(head.struct) is typedesc.Union:
                print(f"class {head.struct.name}(Union):", file=self.stream)
                print("    pass", file=self.stream)


class LibraryHeadWriter:
    def __init__(self, stream: io.StringIO) -> None:
        self.stream = stream

    def write(self, lib: typedesc.TypeLib) -> None:
        # Hm, in user code we have to write:
        # class MyServer(COMObject, ...):
        #     _com_interfaces_ = [MyTypeLib.IInterface]
        #     _reg_typelib_ = MyTypeLib.Library._reg_typelib_
        #                               ^^^^^^^
        # Should the '_reg_typelib_' attribute be at top-level in the
        # generated code, instead as being an attribute of the
        # 'Library' symbol?
        print("class Library(object):", file=self.stream)
        if lib.doc:
            print(_to_docstring(lib.doc), file=self.stream)

        if lib.name:
            print(f"    name = {lib.name!r}", file=self.stream)

        print(
            f"    _reg_typelib_ = ({lib.guid!r}, {lib.major!r}, {lib.minor!r})",
            file=self.stream,
        )


class CoClassHeadWriter:
    def __init__(self, stream: io.StringIO, filename: Optional[str]) -> None:
        self.stream = stream
        self.filename = filename

    def write(self, coclass: typedesc.CoClass) -> None:
        print(f"class {coclass.name}(CoClass):", file=self.stream)
        if coclass.doc:
            print(_to_docstring(coclass.doc), file=self.stream)
        print(f"    _reg_clsid_ = GUID({coclass.clsid!r})", file=self.stream)
        print(f"    _idlflags_ = {coclass.idlflags}", file=self.stream)
        if self.filename is not None:
            print("    _typelib_path_ = typelib_path", file=self.stream)
        # X print
        # >> self.stream, "POINTER(%s).__ctypes_from_outparam__ = wrap" % coclass.name

        libid = coclass.tlibattr.guid
        wMajor, wMinor = coclass.tlibattr.wMajorVerNum, coclass.tlibattr.wMinorVerNum
        print(
            f"    _reg_typelib_ = ({str(libid)!r}, {wMajor}, {wMinor})",
            file=self.stream,
        )


class ComInterfaceHeadWriter:
    def __init__(self, stream: io.StringIO) -> None:
        self.stream = stream

    def _is_enuminterface(self, itf: typedesc.ComInterface) -> bool:
        # Check if this is an IEnumXXX interface
        if not itf.name.startswith("IEnum"):
            return False
        member_names = [mth.name for mth in itf.members]
        for name in ("Next", "Skip", "Reset", "Clone"):
            if name not in member_names:
                return False
        return True

    def write(self, head: typedesc.ComInterfaceHead, basename: str) -> None:
        if head.itf.base is None:
            # we don't beed to generate IUnknown
            return

        print(f"class {head.itf.name}({basename}):", file=self.stream)
        if head.itf.doc:
            print(_to_docstring(head.itf.doc), file=self.stream)

        print("    _case_insensitive_ = True", file=self.stream)
        print(f"    _iid_ = GUID({head.itf.iid!r})", file=self.stream)
        print(f"    _idlflags_ = {head.itf.idlflags}", file=self.stream)

        if self._is_enuminterface(head.itf):
            print(file=self.stream)
            print("    def __iter__(self):", file=self.stream)
            print("        return self", file=self.stream)
            print(file=self.stream)

            print("    def __next__(self):", file=self.stream)
            print("        item, fetched = self.Next(1)", file=self.stream)
            print("        if fetched:", file=self.stream)
            print("            return item", file=self.stream)
            print("        raise StopIteration", file=self.stream)
            print(file=self.stream)

            print("    def __getitem__(self, index):", file=self.stream)
            print("        self.Reset()", file=self.stream)
            print("        self.Skip(index)", file=self.stream)
            print("        item, fetched = self.Next(1)", file=self.stream)
            print("        if fetched:", file=self.stream)
            print("            return item", file=self.stream)
            print("        raise IndexError(index)", file=self.stream)

        annotations = typeannotator.ComInterfaceMembersAnnotator(head.itf).generate()
        if annotations:
            print(file=self.stream)
            print("    if TYPE_CHECKING:  # commembers", file=self.stream)
            print(annotations, file=self.stream)


class DispInterfaceHeadWriter:
    def __init__(self, stream: io.StringIO) -> None:
        self.stream = stream

    def write(self, head: typedesc.DispInterfaceHead, basename: str) -> None:
        print(f"class {head.itf.name}({basename}):", file=self.stream)
        if head.itf.doc:
            print(_to_docstring(head.itf.doc), file=self.stream)
        print("    _case_insensitive_ = True", file=self.stream)
        print(f"    _iid_ = GUID({head.itf.iid!r})", file=self.stream)
        print(f"    _idlflags_ = {head.itf.idlflags}", file=self.stream)
        print("    _methods_ = []", file=self.stream)

        annotations = typeannotator.DispInterfaceMembersAnnotator(head.itf).generate()
        if annotations:
            print(file=self.stream)
            print("    if TYPE_CHECKING:  # dispmembers", file=self.stream)
            print(annotations, file=self.stream)
