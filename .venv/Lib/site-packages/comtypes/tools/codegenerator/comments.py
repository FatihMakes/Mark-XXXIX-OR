import io

from comtypes.tools import typedesc


class ComInterfaceBodyImplCommentWriter:
    def __init__(self, stream: io.StringIO):
        self.stream = stream

    def write(self, body: typedesc.ComInterfaceBody) -> None:
        print(
            "################################################################",
            file=self.stream,
        )
        print(f"# code template for {body.itf.name} implementation", file=self.stream)
        print(f"# class {body.itf.name}_Impl(object):", file=self.stream)

        methods = {}
        for m in body.itf.members:
            if isinstance(m, typedesc.ComMethod):
                # m.arguments is a sequence of tuples:
                # (argtype, argname, idlflags, docstring)
                # Some typelibs have unnamed method parameters!
                inargs = [a[1] or "<unnamed>" for a in m.arguments if "out" not in a[2]]
                outargs = [a[1] or "<unnamed>" for a in m.arguments if "out" in a[2]]
                if "propget" in m.idlflags:
                    methods.setdefault(m.name, [0, inargs, outargs, m.doc])[0] |= 1
                elif "propput" in m.idlflags:
                    methods.setdefault(m.name, [0, inargs[:-1], inargs[-1:], m.doc])[
                        0
                    ] |= 2
                else:
                    methods[m.name] = [0, inargs, outargs, m.doc]

        for name, (typ, inargs, outargs, doc) in methods.items():
            if typ == 0:  # method
                print(
                    f"#     def {name}({', '.join(['self'] + inargs)}):",
                    file=self.stream,
                )
                print(f"#         {(doc or '-no docstring-')!r}", file=self.stream)
                print(f"#         #return {', '.join(outargs)}", file=self.stream)
            elif typ == 1:  # propget
                print("#     @property", file=self.stream)
                print(
                    f"#     def {name}({', '.join(['self'] + inargs)}):",
                    file=self.stream,
                )
                print(f"#         {(doc or '-no docstring-')!r}", file=self.stream)
                print(f"#         #return {', '.join(outargs)}", file=self.stream)
            elif typ == 2:  # propput
                print(
                    f"#     def _set({', '.join(['self'] + inargs + outargs)}):",
                    file=self.stream,
                )
                print(f"#         {(doc or '-no docstring-')!r}", file=self.stream)
                print(
                    f"#     {name} = property(fset = _set, doc = _set.__doc__)",
                    file=self.stream,
                )
            elif typ == 3:  # propget + propput
                print(
                    f"#     def _get({', '.join(['self'] + inargs)}):",
                    file=self.stream,
                )
                print(f"#         {(doc or '-no docstring-')!r}", file=self.stream)
                print(f"#         #return {', '.join(outargs)}", file=self.stream)
                print(
                    f"#     def _set({', '.join(['self'] + inargs + outargs)}):",
                    file=self.stream,
                )
                print(f"#         {(doc or '-no docstring-')!r}", file=self.stream)
                print(
                    f"#     {name} = property(_get, _set, doc = _set.__doc__)",
                    file=self.stream,
                )
            else:
                raise RuntimeError("BUG")
            print("#", file=self.stream)
