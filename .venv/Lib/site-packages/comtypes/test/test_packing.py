import unittest

from comtypes.tools import typedesc
from comtypes.tools.codegenerator.packing import PackingError, calc_packing


# Sizes, alignments and offsets are expressed in bits, matching the values
# produced by ``comtypes.tools.tlbparser`` (e.g. a 32-bit ``int``).
def _make_field(name, size, align, offset):
    typ = typedesc.FundamentalType("int", size, align)
    return typedesc.Field(name, typ, None, offset)


class CalcPackingTest(unittest.TestCase):
    def test_returns_none_for_default_packing(self):
        # A naturally laid out single-field struct needs no explicit packing.
        field = _make_field("a", 32, 32, 0)
        struct = typedesc.Structure(
            "Good", align=32, members=[field], bases=[], size=32
        )
        self.assertIsNone(calc_packing(struct, [field]))

    def test_incomplete_struct_returns_none(self):
        field = _make_field("a", 32, 32, 0)
        struct = typedesc.Structure(
            "Incomplete", align=32, members=[field], bases=[], size=None
        )
        self.assertIsNone(calc_packing(struct, [field]))

    def test_raises_packing_error_with_details_when_layout_is_inconsistent(self):
        # The declared field offset does not match the computed layout, so every
        # packing attempt raises ``PackingError`` and ``calc_packing`` must
        # re-raise with the underlying reason.
        #
        # Regression test for gh-937: the final ``raise`` referenced the
        # ``except ... as`` target after it had been cleared, raising
        # ``UnboundLocalError`` and masking the real ``PackingError``.
        field = _make_field("x", 32, 32, 64)
        struct = typedesc.Structure("Bad", align=32, members=[field], bases=[], size=96)
        with self.assertRaises(PackingError) as ctx:
            calc_packing(struct, [field])
        message = str(ctx.exception)
        self.assertIn("PACKING FAILED", message)
        # The original failure reason must be preserved, not lost.
        self.assertIn("field x offset", message)


if __name__ == "__main__":
    unittest.main()
