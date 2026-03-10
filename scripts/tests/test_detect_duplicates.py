#!/usr/bin/env python3
"""
Unit tests for detect_duplicates.py

Run from the scripts/ directory:
    python3 -m pytest tests/test_detect_duplicates.py -v
    python3 -m unittest tests.test_detect_duplicates -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from detect_duplicates import (
    parse_date,
    field_count,
    is_duplicate,
    merge_pair,
    detect_recurring,
    run_detection,
    VENDOR_THRESHOLD,
    AMOUNT_TOLERANCE,
    DATE_WINDOW_DAYS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _tx(vendor="OpenAI", amount=49.00, date="2025-03-15", **kwargs):
    """Build a minimal transaction dict for testing."""
    base = {
        "vendor": vendor,
        "amount": amount,
        "transaction_date": date,
        "receipt_matched": False,
        "source": "Bank Import",
        "category": None,
        "notes": "",
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------
class TestParseDate(unittest.TestCase):
    def test_iso_format(self):
        dt = parse_date("2025-03-15")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 3)
        self.assertEqual(dt.day, 15)

    def test_slash_mdy_four_digit(self):
        dt = parse_date("03/15/2025")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2025)

    def test_slash_mdy_two_digit(self):
        dt = parse_date("03/15/25")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2025)

    def test_invalid_returns_none(self):
        self.assertIsNone(parse_date("not-a-date"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_date(""))


# ---------------------------------------------------------------------------
# field_count
# ---------------------------------------------------------------------------
class TestFieldCount(unittest.TestCase):
    def test_counts_populated_fields(self):
        tx = {"vendor": "OpenAI", "amount": 49.0, "notes": "", "category": None}
        self.assertEqual(field_count(tx), 2)  # vendor + amount; notes and category excluded

    def test_false_not_counted(self):
        tx = {"receipt_matched": False, "vendor": "X"}
        self.assertEqual(field_count(tx), 1)  # only vendor; False is excluded

    def test_true_counted(self):
        tx = {"receipt_matched": True, "vendor": "X"}
        self.assertEqual(field_count(tx), 2)

    def test_empty_dict(self):
        self.assertEqual(field_count({}), 0)


# ---------------------------------------------------------------------------
# is_duplicate
# ---------------------------------------------------------------------------
class TestIsDuplicate(unittest.TestCase):
    def test_exact_match(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.00, "2025-03-15")
        is_dup, reason = is_duplicate(t1, t2)
        self.assertTrue(is_dup)
        self.assertIn("Vendor match", reason)

    def test_same_day_same_amount(self):
        t1 = _tx("Canva", 16.00, "2025-03-10")
        t2 = _tx("Canva", 16.00, "2025-03-10")
        is_dup, _ = is_duplicate(t1, t2)
        self.assertTrue(is_dup)

    def test_different_amount_not_duplicate(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 99.00, "2025-03-15")
        is_dup, _ = is_duplicate(t1, t2)
        self.assertFalse(is_dup)

    def test_amount_within_tolerance(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.01, "2025-03-15")  # within AMOUNT_TOLERANCE ($0.02)
        is_dup, _ = is_duplicate(t1, t2)
        self.assertTrue(is_dup)

    def test_amount_exceeds_tolerance(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.05, "2025-03-15")  # exceeds AMOUNT_TOLERANCE
        is_dup, _ = is_duplicate(t1, t2)
        self.assertFalse(is_dup)

    def test_date_within_window(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.00, "2025-03-17")  # 2 days apart, within DATE_WINDOW_DAYS (3)
        is_dup, _ = is_duplicate(t1, t2)
        self.assertTrue(is_dup)

    def test_date_outside_window(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.00, "2025-03-20")  # 5 days apart, outside DATE_WINDOW_DAYS
        is_dup, _ = is_duplicate(t1, t2)
        self.assertFalse(is_dup)

    def test_different_vendor_not_duplicate(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("Canva", 49.00, "2025-03-15")
        is_dup, _ = is_duplicate(t1, t2)
        self.assertFalse(is_dup)

    def test_vendor_case_insensitive_match(self):
        # One record might arrive all-caps from a bank CSV, the other title-cased
        # from an email receipt. Both token sets are identical when lowercased → 100% match.
        t1 = _tx("OPENAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.00, "2025-03-15")
        is_dup, _ = is_duplicate(t1, t2)
        self.assertTrue(is_dup)

    def test_empty_vendor_not_duplicate(self):
        t1 = _tx("", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.00, "2025-03-15")
        is_dup, _ = is_duplicate(t1, t2)
        self.assertFalse(is_dup)

    def test_missing_date_not_duplicate(self):
        t1 = _tx("OpenAI", 49.00, "")
        t2 = _tx("OpenAI", 49.00, "2025-03-15")
        is_dup, _ = is_duplicate(t1, t2)
        self.assertFalse(is_dup)

    def test_reason_contains_vendor_score(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.00, "2025-03-15")
        _, reason = is_duplicate(t1, t2)
        self.assertIn("100%", reason)  # exact vendor match = 100

    def test_reason_contains_amount(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.00, "2025-03-15")
        _, reason = is_duplicate(t1, t2)
        self.assertIn("49.00", reason)

    def test_reason_contains_date_diff(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.00, "2025-03-16")
        _, reason = is_duplicate(t1, t2)
        self.assertIn("1 days", reason)

    def test_thresholds_exported(self):
        # Confirm constants are accessible and sane
        self.assertGreater(VENDOR_THRESHOLD, 50)
        self.assertLess(AMOUNT_TOLERANCE, 1.0)
        self.assertGreater(DATE_WINDOW_DAYS, 0)


# ---------------------------------------------------------------------------
# merge_pair
# ---------------------------------------------------------------------------
class TestMergePair(unittest.TestCase):
    def test_winner_has_receipt(self):
        # Transaction with receipt_matched=True should win
        t_with_receipt = _tx("OpenAI", 49.00, "2025-03-15", receipt_matched=True)
        t_without = _tx("OpenAI", 49.00, "2025-03-15", receipt_matched=False)
        merged = merge_pair(t_without, t_with_receipt, "test reason")
        self.assertTrue(merged["receipt_matched"])

    def test_email_source_wins_over_bank_import(self):
        # Valid source values per SKILL.md schema: "Bank Import", "Email Receipt",
        # "Photo Upload", "Manual". The priority function checks for "Email Receipt"
        # specifically — using any other string will not get the +10 priority bonus.
        t_bank  = _tx("OpenAI", 49.00, "2025-03-15", source="Bank Import")
        t_email = _tx("OpenAI", 49.00, "2025-03-15", source="Email Receipt")
        merged = merge_pair(t_bank, t_email, "test reason")
        self.assertEqual(merged["source"], "Email Receipt")

    def test_missing_fields_filled_from_loser(self):
        t_winner = _tx("OpenAI", 49.00, "2025-03-15", category=None)
        t_loser = _tx("OpenAI", 49.00, "2025-03-15", category="software_subscriptions")
        merged = merge_pair(t_winner, t_loser, "test reason")
        self.assertEqual(merged["category"], "software_subscriptions")

    def test_notes_combined(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15", notes="Monthly API")
        t2 = _tx("OpenAI", 49.00, "2025-03-15", notes="")
        merged = merge_pair(t1, t2, "test reason")
        self.assertIn("Monthly API", merged["notes"])
        self.assertIn("AUTO-MERGED", merged["notes"])

    def test_auto_merge_tag_always_present(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.00, "2025-03-15")
        merged = merge_pair(t1, t2, "some reason")
        self.assertIn("AUTO-MERGED", merged["notes"])

    def test_loser_source_appended_to_notes(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15", source="Bank Import")
        t2 = _tx("OpenAI", 49.00, "2025-03-15", source="Email Receipt")
        # Email Receipt has higher priority (+10); bank becomes the loser
        merged = merge_pair(t1, t2, "test reason")
        self.assertIn("Duplicate source", merged["notes"])

    def test_returns_dict(self):
        t1 = _tx("OpenAI", 49.00, "2025-03-15")
        t2 = _tx("OpenAI", 49.00, "2025-03-15")
        merged = merge_pair(t1, t2, "reason")
        self.assertIsInstance(merged, dict)


# ---------------------------------------------------------------------------
# detect_recurring
# ---------------------------------------------------------------------------
class TestDetectRecurring(unittest.TestCase):
    def _monthly_series(self, vendor, amount, start_month=1, count=3):
        """Generate monthly transactions ~30 days apart."""
        txns = []
        for i in range(count):
            month = start_month + i
            date = f"2025-{month:02d}-15"
            txns.append(_tx(vendor, amount, date))
        return txns

    def test_monthly_series_flagged(self):
        txns = self._monthly_series("Canva", 16.00, start_month=1, count=3)
        result = detect_recurring(txns)
        flagged = [t for t in result if t.get("_recurring")]
        self.assertEqual(len(flagged), 3)

    def test_single_transaction_not_flagged(self):
        txns = [_tx("Canva", 16.00, "2025-03-15")]
        result = detect_recurring(txns)
        self.assertFalse(any(t.get("_recurring") for t in result))

    def test_close_dates_not_flagged_as_recurring(self):
        # Two transactions 5 days apart are NOT recurring (< 25 day gap)
        txns = [
            _tx("Canva", 16.00, "2025-03-01"),
            _tx("Canva", 16.00, "2025-03-06"),
        ]
        result = detect_recurring(txns)
        self.assertFalse(any(t.get("_recurring") for t in result))

    def test_different_amounts_not_grouped(self):
        # Two transactions same vendor but different amounts — not the same recurring charge
        txns = [
            _tx("Canva", 16.00, "2025-01-15"),
            _tx("Canva", 99.00, "2025-02-15"),
        ]
        result = detect_recurring(txns)
        self.assertFalse(any(t.get("_recurring") for t in result))


# ---------------------------------------------------------------------------
# run_detection (integration)
# ---------------------------------------------------------------------------
class TestRunDetection(unittest.TestCase):
    def test_no_duplicates(self):
        txns = [
            _tx("OpenAI", 49.00, "2025-03-01"),
            _tx("Canva", 16.00, "2025-03-05"),
            _tx("Notion", 10.00, "2025-03-10"),
        ]
        result = run_detection(txns)
        self.assertEqual(result["stats"]["duplicates_merged"], 0)
        self.assertEqual(len(result["clean"]), 3)
        self.assertEqual(len(result["duplicates"]), 0)

    def test_exact_duplicate_merged(self):
        txns = [
            _tx("OpenAI", 49.00, "2025-03-15"),
            _tx("OpenAI", 49.00, "2025-03-15"),  # exact duplicate
        ]
        result = run_detection(txns)
        self.assertEqual(len(result["clean"]), 1)
        self.assertEqual(result["stats"]["duplicates_merged"], 1)
        self.assertEqual(result["stats"]["output_count"], 1)

    def test_near_duplicate_within_window_merged(self):
        txns = [
            _tx("OpenAI", 49.00, "2025-03-15"),
            _tx("OpenAI", 49.00, "2025-03-17"),  # 2 days apart
        ]
        result = run_detection(txns)
        self.assertEqual(len(result["clean"]), 1)

    def test_far_duplicate_not_merged(self):
        txns = [
            _tx("OpenAI", 49.00, "2025-03-01"),
            _tx("OpenAI", 49.00, "2025-03-10"),  # 9 days apart, outside window
        ]
        result = run_detection(txns)
        self.assertEqual(len(result["clean"]), 2)

    def test_receipt_kept_after_merge(self):
        t_no_receipt = _tx("OpenAI", 49.00, "2025-03-15", receipt_matched=False)
        t_with_receipt = _tx("OpenAI", 49.00, "2025-03-15", receipt_matched=True)
        result = run_detection([t_no_receipt, t_with_receipt])
        self.assertTrue(result["clean"][0]["receipt_matched"])

    def test_recurring_stripped_from_clean(self):
        # Recurring flag is internal; _recurring must NOT appear on output transactions
        txns = [
            _tx("Canva", 16.00, "2025-01-15"),
            _tx("Canva", 16.00, "2025-02-15"),
            _tx("Canva", 16.00, "2025-03-15"),
        ]
        result = run_detection(txns)
        for tx in result["clean"]:
            self.assertNotIn("_recurring", tx)

    def test_recurring_counted_in_stats(self):
        txns = [
            _tx("Canva", 16.00, "2025-01-15"),
            _tx("Canva", 16.00, "2025-02-15"),
            _tx("Canva", 16.00, "2025-03-15"),
        ]
        result = run_detection(txns)
        self.assertGreater(result["stats"]["recurring_flagged"], 0)

    def test_stats_keys_present(self):
        result = run_detection([_tx()])
        expected_keys = {
            "input_count", "output_count",
            "duplicates_merged", "duplicate_groups", "recurring_flagged",
        }
        self.assertEqual(set(result["stats"].keys()), expected_keys)

    def test_output_keys_present(self):
        result = run_detection([_tx()])
        self.assertIn("clean", result)
        self.assertIn("duplicates", result)
        self.assertIn("stats", result)

    def test_empty_input(self):
        result = run_detection([])
        self.assertEqual(result["stats"]["input_count"], 0)
        self.assertEqual(result["stats"]["output_count"], 0)
        self.assertEqual(result["clean"], [])

    def test_single_transaction_passes_through(self):
        tx = _tx("OpenAI", 49.00, "2025-03-15")
        result = run_detection([tx])
        self.assertEqual(len(result["clean"]), 1)
        self.assertEqual(result["clean"][0]["vendor"], "OpenAI")

    def test_three_way_duplicate(self):
        # Three identical records (e.g., bank import + email receipt + manual entry)
        txns = [
            _tx("OpenAI", 49.00, "2025-03-15"),
            _tx("OpenAI", 49.00, "2025-03-15"),
            _tx("OpenAI", 49.00, "2025-03-15"),
        ]
        result = run_detection(txns)
        # All three should collapse into one
        self.assertEqual(len(result["clean"]), 1)
        self.assertEqual(result["stats"]["duplicates_merged"], 2)

    def test_input_count_matches(self):
        txns = [_tx() for _ in range(5)]
        result = run_detection(txns)
        self.assertEqual(result["stats"]["input_count"], 5)

    def test_duplicate_group_structure(self):
        txns = [
            _tx("OpenAI", 49.00, "2025-03-15"),
            _tx("OpenAI", 49.00, "2025-03-15"),
        ]
        result = run_detection(txns)
        self.assertEqual(len(result["duplicates"]), 1)
        group = result["duplicates"][0]
        self.assertIn("kept", group)
        self.assertIn("merged", group)
        self.assertIn("reasons", group)

    def test_non_duplicate_different_amount(self):
        txns = [
            _tx("OpenAI", 49.00, "2025-03-15"),
            _tx("OpenAI", 99.00, "2025-03-15"),
        ]
        result = run_detection(txns)
        self.assertEqual(len(result["clean"]), 2)

    def test_non_duplicate_different_vendor(self):
        txns = [
            _tx("OpenAI", 49.00, "2025-03-15"),
            _tx("Anthropic", 49.00, "2025-03-15"),
        ]
        result = run_detection(txns)
        self.assertEqual(len(result["clean"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
