import unittest

from containers.implementation.shared.doctype_resolver import (
    normalize_doctype_name,
    resolve_doctype,
    strip_annotations,
)


class DoctypeResolverTest(unittest.TestCase):
    def test_strip_parenthetical_annotation(self) -> None:
        raw = "Stock Entry (Issue, Transfer, Manufacture)"
        self.assertEqual(strip_annotations(raw), "Stock Entry")
        self.assertEqual(normalize_doctype_name(raw), "stock entry")

    def test_resolve_stock_entry_alias(self) -> None:
        self.assertEqual(
            resolve_doctype("Stock Entry (Issue, Transfer, Manufacture)"),
            "Stock Entry",
        )


if __name__ == "__main__":
    unittest.main()
