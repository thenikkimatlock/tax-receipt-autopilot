#!/usr/bin/env python3
"""
Unit tests for monthly_reminder.py

Run from the scripts/ directory:
    python3 -m pytest tests/test_monthly_reminder.py -v
    python3 -m unittest tests.test_monthly_reminder -v
"""

import sys
import json
import tempfile
import os
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from monthly_reminder import (
    parse_date,
    get_deductible_pct,
    check_reminder,
    full_audit,
    monthly_summary,
    _get_missing_months,
    _get_missing_months_by_account,
    STATEMENT_OVERDUE_DAYS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _tx(vendor="OpenAI", amount=49.00, date_str="2026-03-15",
        category="software_subscriptions", biz="business",
        deductible=True, deductible_pct=100,
        receipt=False, review=False, source="Bank Import", **kwargs):
    base = {
        "vendor": vendor,
        "amount": amount,
        "transaction_date": date_str,
        "category": category,
        "business_or_personal": biz,
        "deductible": deductible,
        "deductible_pct": deductible_pct,
        "receipt_matched": receipt,
        "review_required": review,
        "source": source,
        "notes": "",
    }
    base.update(kwargs)
    return base


def _write_snooze(days_from_now: int) -> Path:
    """Write a snooze file that expires N days from now."""
    snooze_path = Path(tempfile.mktemp(suffix=".json"))
    until = date.today() + timedelta(days=days_from_now)
    with open(snooze_path, "w") as f:
        json.dump({"until": str(until)}, f)
    return snooze_path


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------
class TestParseDate(unittest.TestCase):
    def test_iso_format(self):
        d = parse_date("2026-03-15")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2026)

    def test_slash_mdy(self):
        d = parse_date("03/15/2026")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2026)

    def test_invalid_returns_none(self):
        self.assertIsNone(parse_date("not-a-date"))

    def test_empty_returns_none(self):
        self.assertIsNone(parse_date(""))


# ---------------------------------------------------------------------------
# get_deductible_pct (monthly_reminder version)
# ---------------------------------------------------------------------------
class TestGetDeductiblePct(unittest.TestCase):
    def test_fully_deductible(self):
        self.assertEqual(get_deductible_pct({"deductible": True, "deductible_pct": 100}), 100)

    def test_meals_50(self):
        self.assertEqual(get_deductible_pct({"deductible": True, "deductible_pct": 50}), 50)

    def test_not_deductible(self):
        self.assertEqual(get_deductible_pct({"deductible": False}), 0)

    def test_missing_pct_defaults_to_100_when_deductible(self):
        self.assertEqual(get_deductible_pct({"deductible": True}), 100)


# ---------------------------------------------------------------------------
# full_audit — contractor 1099 threshold uses LEDGER YEAR not today's year
# ---------------------------------------------------------------------------
class TestContractorThresholdYear(unittest.TestCase):
    """
    This tests the bug fix: contractor threshold must use the ledger's tax year,
    not the current calendar year. A 2025 ledger audited in 2026 must use the
    2025 $600 threshold, not 2026's $2,000 threshold.
    """

    def test_2025_ledger_uses_600_threshold(self):
        """$550 contractor in a 2025 ledger should trigger a warning (>= 80% of $600 = $480)."""
        txns = [_tx("Freelancer Jane", 550.0, "2025-06-15",
                    category="contractor_payments")]
        result = full_audit(txns)
        self.assertGreater(
            len(result["contractor_warnings"]), 0,
            "Expected 1099 warning for $550 in a 2025 ledger (threshold $600, 80% = $480)"
        )

    def test_2026_ledger_uses_2000_threshold(self):
        """$550 contractor in a 2026 ledger should NOT warn ($550 < 80% of $2,000 = $1,600)."""
        txns = [_tx("Freelancer Jane", 550.0, "2026-06-15",
                    category="contractor_payments")]
        result = full_audit(txns)
        self.assertEqual(
            len(result["contractor_warnings"]), 0,
            "No warning expected for $550 in a 2026 ledger (threshold $2,000, 80% = $1,600)"
        )

    def test_2026_ledger_warns_at_1800(self):
        """$1,800 contractor in a 2026 ledger SHOULD warn (>= 80% of $2,000 = $1,600)."""
        txns = [_tx("Freelancer Jane", 1800.0, "2026-06-15",
                    category="contractor_payments")]
        result = full_audit(txns)
        self.assertGreater(
            len(result["contractor_warnings"]), 0,
            "Expected warning for $1,800 in a 2026 ledger (threshold $2,000, 80% = $1,600)"
        )

    def test_2025_ledger_no_warning_below_threshold(self):
        """$400 contractor in 2025 should NOT warn ($400 < 80% of $600 = $480)."""
        txns = [_tx("Freelancer Jane", 400.0, "2025-06-15",
                    category="contractor_payments")]
        result = full_audit(txns)
        self.assertEqual(
            len(result["contractor_warnings"]), 0,
            "No warning expected for $400 in a 2025 ledger (80% of $600 = $480)"
        )

    def test_threshold_stored_on_warning_record(self):
        """The warning record should store the correct threshold for the ledger year."""
        txns = [_tx("Freelancer Jane", 550.0, "2025-06-15",
                    category="contractor_payments")]
        result = full_audit(txns)
        self.assertEqual(len(result["contractor_warnings"]), 1)
        self.assertAlmostEqual(result["contractor_warnings"][0]["threshold"], 600.0)

    def test_mixed_year_ledger_uses_max_year(self):
        """
        If a ledger spans 2025 and 2026 (e.g. prior year being amended),
        max year wins. $550 contractor dated 2025 with 2026 txns present
        should use 2026 threshold → no warning.
        """
        txns = [
            _tx("OpenAI", 49.0, "2026-01-15"),           # 2026 txn pulls max year to 2026
            _tx("Freelancer Jane", 550.0, "2025-12-15",
                category="contractor_payments"),           # $550 < 80% of $2,000 = $1,600
        ]
        result = full_audit(txns)
        self.assertEqual(
            len(result["contractor_warnings"]), 0,
            "With 2026 txns present, ledger_year=2026 → $550 should not warn"
        )

    def test_empty_ledger_does_not_crash(self):
        """Empty ledger should not raise on threshold calculation."""
        result = full_audit([])
        self.assertEqual(result["total_transactions"], 0)
        self.assertEqual(result["contractor_warnings"], [])


# ---------------------------------------------------------------------------
# full_audit — health score
# ---------------------------------------------------------------------------
class TestHealthScore(unittest.TestCase):
    def test_perfect_ledger_scores_100(self):
        txns = [_tx(receipt=True, review=False, deductible=True, deductible_pct=100)]
        result = full_audit(txns)
        self.assertEqual(result["health_score"], 100)

    def test_all_missing_receipts_scores_low(self):
        txns = [_tx(receipt=False, biz="business") for _ in range(10)]
        result = full_audit(txns)
        # 100% missing receipts → 40-point penalty on all → score = 60
        self.assertLess(result["health_score"], 70)

    def test_health_score_capped_at_100(self):
        result = full_audit([_tx(receipt=True)])
        self.assertLessEqual(result["health_score"], 100)

    def test_health_score_floored_at_0(self):
        txns = [_tx(receipt=False, review=True, biz="mixed") for _ in range(10)]
        result = full_audit(txns)
        self.assertGreaterEqual(result["health_score"], 0)

    def test_health_score_in_result(self):
        result = full_audit([_tx()])
        self.assertIn("health_score", result)

    def test_health_score_proportional_to_missing_receipts(self):
        # 5 txns, 2 missing receipts → 40% missing → 16-point penalty → ~84
        txns = [
            _tx(receipt=True), _tx(receipt=True), _tx(receipt=True),
            _tx(receipt=False), _tx(receipt=False),
        ]
        result = full_audit(txns)
        self.assertLess(result["health_score"], 100)
        self.assertGreater(result["health_score"], 75)


# ---------------------------------------------------------------------------
# full_audit — issue detection
# ---------------------------------------------------------------------------
class TestAuditIssueDetection(unittest.TestCase):
    def test_detects_missing_receipts(self):
        txns = [_tx(receipt=False, biz="business"), _tx(receipt=True)]
        result = full_audit(txns)
        self.assertEqual(result["stats"]["missing_receipts"], 1)
        self.assertEqual(len(result["missing_receipts"]), 1)

    def test_personal_not_counted_as_missing_receipt(self):
        txns = [_tx(receipt=False, biz="personal", category="personal")]
        result = full_audit(txns)
        self.assertEqual(result["stats"]["missing_receipts"], 0)

    def test_detects_flagged_transactions(self):
        txns = [_tx(review=True, review_reason="Check this")]
        result = full_audit(txns)
        self.assertEqual(result["stats"]["flagged"], 1)
        self.assertEqual(result["flagged_transactions"][0]["reason"], "Check this")

    def test_detects_uncategorized(self):
        txns = [_tx(category=None)]
        result = full_audit(txns)
        self.assertEqual(result["stats"]["uncategorized"], 1)

    def test_detects_mixed_use(self):
        txns = [_tx(biz="mixed")]
        result = full_audit(txns)
        self.assertEqual(result["stats"]["mixed_use"], 1)

    def test_detects_large_equipment(self):
        txns = [_tx("Apple", 2600.00, category="equipment")]
        result = full_audit(txns)
        self.assertEqual(result["stats"]["large_equipment"], 1)

    def test_equipment_under_2500_not_flagged(self):
        txns = [_tx("Keyboard", 200.00, category="equipment")]
        result = full_audit(txns)
        self.assertEqual(result["stats"]["large_equipment"], 0)

    def test_meals_without_notes_detected(self):
        txns = [_tx(category="meals_entertainment", notes="")]
        result = full_audit(txns)
        self.assertEqual(result["stats"]["meals_no_notes"], 1)

    def test_meals_with_notes_not_flagged(self):
        txns = [_tx(category="meals_entertainment",
                    notes="50% deductible. Business purpose: client. Attendees: Jane.")]
        result = full_audit(txns)
        self.assertEqual(result["stats"]["meals_no_notes"], 0)

    def test_audit_result_keys_present(self):
        result = full_audit([_tx()])
        expected = {
            "audit_date", "total_transactions", "health_score", "issues",
            "missing_receipts", "flagged_transactions", "uncategorized",
            "mixed_use_items", "large_equipment", "contractor_warnings",
            "contractors_missing_w9", "meals_needing_notes", "mileage_log_issues",
            "stats",
        }
        self.assertTrue(expected.issubset(set(result.keys())))


# ---------------------------------------------------------------------------
# monthly_summary
# ---------------------------------------------------------------------------
class TestMonthlySummary(unittest.TestCase):
    def test_filters_by_month(self):
        txns = [
            _tx("OpenAI", 49.00, "2026-03-15"),
            _tx("Canva", 16.00, "2026-04-01"),  # different month
        ]
        result = monthly_summary(txns, month="2026-03")
        self.assertEqual(result["transaction_count"], 1)

    def test_total_expenses(self):
        txns = [_tx("OpenAI", 49.00, "2026-03-15"), _tx("Canva", 16.00, "2026-03-10")]
        result = monthly_summary(txns, month="2026-03")
        self.assertAlmostEqual(result["total_expenses"], 65.00, places=2)

    def test_deductible_total_50pct_meals(self):
        txns = [_tx("Chipotle", 100.00, "2026-03-20", category="meals_entertainment",
                    deductible=True, deductible_pct=50)]
        result = monthly_summary(txns, month="2026-03")
        self.assertAlmostEqual(result["deductible_total"], 50.00, places=2)

    def test_personal_excluded(self):
        txns = [
            _tx("OpenAI", 49.00, "2026-03-15", biz="business"),
            _tx("Netflix", 15.99, "2026-03-20", biz="personal", category="personal"),
        ]
        result = monthly_summary(txns, month="2026-03")
        self.assertEqual(result["transaction_count"], 1)

    def test_by_category_breakdown(self):
        txns = [
            _tx("OpenAI", 49.00, "2026-03-15", category="software_subscriptions"),
            _tx("Meta Ads", 150.00, "2026-03-20", category="marketing_advertising"),
        ]
        result = monthly_summary(txns, month="2026-03")
        self.assertIn("software_subscriptions", result["by_category"])
        self.assertIn("marketing_advertising", result["by_category"])

    def test_missing_receipts_count(self):
        txns = [
            _tx("OpenAI", 49.00, "2026-03-15", receipt=False),
            _tx("Canva", 16.00, "2026-03-10", receipt=True),
        ]
        result = monthly_summary(txns, month="2026-03")
        self.assertEqual(result["missing_receipts"], 1)

    def test_ytd_deductible_spans_full_year(self):
        txns = [
            _tx("OpenAI", 49.00, "2026-01-15", deductible=True, deductible_pct=100),
            _tx("Canva", 16.00, "2026-02-10", deductible=True, deductible_pct=100),
            _tx("Meta Ads", 100.00, "2026-03-20", deductible=True, deductible_pct=100),
        ]
        result = monthly_summary(txns, month="2026-03")
        self.assertAlmostEqual(result["ytd_deductible"], 165.00, places=2)

    def test_month_income_sum(self):
        txns = [_tx()]
        income = [
            {"date": "2026-03-01", "amount": 500.00},
            {"date": "2026-03-15", "amount": 250.00},
            {"date": "2026-04-01", "amount": 1000.00},  # different month
        ]
        result = monthly_summary(txns, month="2026-03", income_records=income)
        self.assertAlmostEqual(result["month_income"], 750.00, places=2)

    def test_result_keys_present(self):
        result = monthly_summary([_tx()], month="2026-03")
        expected = {
            "month", "transaction_count", "total_expenses", "deductible_total",
            "by_category", "missing_receipts", "flagged", "ytd_deductible",
            "month_income", "ytd_income", "month_miles", "month_mileage_deduction",
        }
        self.assertTrue(expected.issubset(set(result.keys())))


# ---------------------------------------------------------------------------
# check_reminder
# ---------------------------------------------------------------------------
class TestCheckReminder(unittest.TestCase):
    def test_no_bank_imports_needs_reminder(self):
        txns = [_tx(source="Photo Upload")]  # no Bank Import source
        result = check_reminder(txns, Path(tempfile.mktemp()))
        self.assertTrue(result["reminder_needed"])

    def test_recent_import_no_reminder(self):
        today_str = date.today().strftime("%Y-%m-%d")
        txns = [_tx(source="Bank Import", date_str=today_str)]
        result = check_reminder(txns, Path(tempfile.mktemp()))
        self.assertFalse(result["reminder_needed"])

    def test_overdue_import_triggers_reminder(self):
        old_date = (date.today() - timedelta(days=STATEMENT_OVERDUE_DAYS + 5)).strftime("%Y-%m-%d")
        txns = [_tx(source="Bank Import", date_str=old_date)]
        result = check_reminder(txns, Path(tempfile.mktemp()))
        self.assertTrue(result["reminder_needed"])

    def test_snooze_suppresses_reminder(self):
        old_date = (date.today() - timedelta(days=STATEMENT_OVERDUE_DAYS + 5)).strftime("%Y-%m-%d")
        txns = [_tx(source="Bank Import", date_str=old_date)]
        snooze_path = _write_snooze(days_from_now=3)  # snoozed for 3 more days
        try:
            result = check_reminder(txns, snooze_path)
            self.assertFalse(result["reminder_needed"])
        finally:
            snooze_path.unlink(missing_ok=True)

    def test_expired_snooze_allows_reminder(self):
        old_date = (date.today() - timedelta(days=STATEMENT_OVERDUE_DAYS + 5)).strftime("%Y-%m-%d")
        txns = [_tx(source="Bank Import", date_str=old_date)]
        snooze_path = _write_snooze(days_from_now=-1)  # snooze expired yesterday
        try:
            result = check_reminder(txns, snooze_path)
            self.assertTrue(result["reminder_needed"])
        finally:
            snooze_path.unlink(missing_ok=True)

    def test_empty_ledger_triggers_reminder(self):
        result = check_reminder([], Path(tempfile.mktemp()))
        self.assertTrue(result["reminder_needed"])


# ---------------------------------------------------------------------------
# _get_missing_months
# ---------------------------------------------------------------------------
class TestGetMissingMonths(unittest.TestCase):
    def test_no_gaps_returns_empty(self):
        # Transactions covering Jan, Feb, Mar 2026 with no gaps through current month
        # (Since we can't control today's date, create txns through this month)
        today = date.today()
        txns = []
        y, m = 2026, 1
        while (y, m) <= (today.year, today.month):
            txns.append(_tx(source="Bank Import",
                            date_str=f"{y}-{m:02d}-15"))
            m += 1
            if m > 12:
                m = 1
                y += 1
        missing = _get_missing_months(txns)
        self.assertEqual(missing, [])

    def test_gap_detected(self):
        # Jan and Mar present, Feb missing
        txns = [
            _tx(source="Bank Import", date_str="2026-01-15"),
            _tx(source="Bank Import", date_str="2026-03-15"),
        ]
        missing = _get_missing_months(txns)
        self.assertIn("February 2026", missing)

    def test_no_bank_imports_returns_current_month(self):
        txns = [_tx(source="Photo Upload")]
        missing = _get_missing_months(txns)
        self.assertEqual(len(missing), 1)

    def test_empty_ledger_returns_current_month(self):
        missing = _get_missing_months([])
        self.assertEqual(len(missing), 1)


# ---------------------------------------------------------------------------
# _get_missing_months_by_account
# ---------------------------------------------------------------------------
class TestGetMissingMonthsByAccount(unittest.TestCase):

    def test_no_bank_imports_returns_empty_dict(self):
        txns = [_tx(source="Photo Upload")]
        result = _get_missing_months_by_account(txns)
        self.assertEqual(result, {})

    def test_empty_ledger_returns_empty_dict(self):
        result = _get_missing_months_by_account([])
        self.assertEqual(result, {})

    def test_single_account_gap_detected(self):
        # Chase: Jan and Mar present, Feb missing
        txns = [
            _tx(source="Bank Import", date_str="2026-01-15", account="Chase Checking"),
            _tx(source="Bank Import", date_str="2026-03-15", account="Chase Checking"),
        ]
        result = _get_missing_months_by_account(txns)
        self.assertIn("Chase Checking", result)
        self.assertIn("February 2026", result["Chase Checking"])

    def test_multiple_accounts_tracked_independently(self):
        # Chase: continuous Jan-Mar. Amex: Jan only, Feb missing.
        txns = [
            _tx(source="Bank Import", date_str="2026-01-15", account="Chase"),
            _tx(source="Bank Import", date_str="2026-02-15", account="Chase"),
            _tx(source="Bank Import", date_str="2026-03-15", account="Chase"),
            _tx(source="Bank Import", date_str="2026-01-20", account="Amex"),
        ]
        result = _get_missing_months_by_account(txns)
        self.assertIn("Chase", result)
        self.assertIn("Amex", result)
        # Amex missing Feb 2026 at minimum
        self.assertIn("February 2026", result["Amex"])
        # Chase Jan-Mar: no gaps within that window
        chase_missing = result["Chase"]
        self.assertNotIn("January 2026", chase_missing)
        self.assertNotIn("February 2026", chase_missing)
        self.assertNotIn("March 2026", chase_missing)

    def test_no_account_field_groups_under_empty_string(self):
        # Transactions without an 'account' key should appear under "" key
        txns = [
            {"vendor": "OpenAI", "amount": 20, "transaction_date": "2026-01-15",
             "source": "Bank Import"},
            {"vendor": "Canva", "amount": 16, "transaction_date": "2026-03-10",
             "source": "Bank Import"},
        ]
        result = _get_missing_months_by_account(txns)
        self.assertIn("", result)
        self.assertIn("February 2026", result[""])


if __name__ == "__main__":
    unittest.main(verbosity=2)
