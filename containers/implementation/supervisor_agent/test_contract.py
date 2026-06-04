import unittest

from containers.implementation.supervisor_agent.contract import (
    classify_gap,
    filter_user_gap_messages,
    should_ask_user,
)


class SupervisorContractTest(unittest.TestCase):
    def test_pipeline_fail_not_ask_user(self) -> None:
        msg = "Internal corpus_merge KeyError in pipeline"
        self.assertEqual(classify_gap(msg), "pipeline_fail")
        self.assertFalse(should_ask_user([msg]))

    def test_empty_row_is_user_gap(self) -> None:
        msg = "Row 3: empty required value for 'supplier_name'"
        self.assertEqual(classify_gap(msg), "user_gap")
        self.assertTrue(should_ask_user([msg]))

    def test_naming_series_auto_fix(self) -> None:
        msg = "Missing naming_series — apply KB default"
        self.assertEqual(classify_gap(msg), "auto_fix")

    def test_filter_user_gap_messages(self) -> None:
        msgs = [
            "Row 1: empty required value for 'item_code'",
            "Internal traceback in graph resolver",
        ]
        filtered = filter_user_gap_messages(msgs)
        self.assertEqual(len(filtered), 1)
        self.assertIn("empty required value", filtered[0])


if __name__ == "__main__":
    unittest.main()
