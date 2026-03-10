#!/usr/bin/env python3
"""
Unit tests for export_ledger.py

Run from the scripts/ directory:
    python3 -m pytest tests/test_export_ledger.py -v
    python3 -m unittest tests.test_export_ledger -v
"""

import sys
import tempfile
import os
import json
import csv
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from export_ledger import (
    get_deductible_pct,
    format_amount,
    load_transactions,
    generate_export,
    CATEGORY_META,
    DEPRECIATION_FLAG,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _tx(vendor="OpenAI", amount=49.00, date="2026-03-15", category="software_subscriptions",
        biz="business", deductible=True, deductible_pct=100, receipt=False,
        review=False, review_reason="", **kwargs):
    """Build a minimal transaction dict for testing."""
    base = {
        "vendor": vendor,
        "amount": amount,
        "transaction_date": date,
        "category": category,
        "business_or_personal": biz,
        "deductible": deductible,
        "deductible_pct": deductible_pct,
        "receipt_matched": receipt,
        "review_required": review,
        "review_reason": review_reason,
        "source": "Bank Import",
        "notes": "",
    }
    base.update(kwargs)
    return base


def _meal(vendor="Chipotle", amount=42.00, date="2026-03-20"):
    """Build a 50% deductible meals_entertainment transaction."""
    return _tx(vendor=vendor, amount=amount, date=date,
               category="meals_entertainment", deductible=True, deductible_pct=50,
               notes="50% deductible. Business purpose: Client lunch. Attendees: Jane.")


def _write_ledger(txns):
    """Write a list of transactions to a temp JSON file, return path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(txns, f)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# get_deductible_pct
# ---------------------------------------------------------------------------
class TestGetDeductiblePct(unittest.TestCase):
    def test_fully_deductible_no_pct_field(self):
        # deductible=True with no deductible_pct → defaults to 100
        tx = {"deductible": True}
        self.assertEqual(get_deductible_pct(tx), 100)

    def test_fully_deductible_explicit_100(self):
        tx = {"deductible": True, "deductible_pct": 100}
        self.assertEqual(get_deductible_pct(tx), 100)

    def test_meals_50_pct(self):
        tx = {"deductible": True, "deductible_pct": 50}
        self.assertEqual(get_deductible_pct(tx), 50)

    def test_not_deductible(self):
        tx = {"deductible": False, "deductible_pct": 100}
        self.assertEqual(get_deductible_pct(tx), 0)

    def test_deductible_false_no_pct(self):
        tx = {"deductible": False}
        self.assertEqual(get_deductible_pct(tx), 0)

    def test_deductible_string_true(self):
        # Some older records may have stored "true" as a string
        tx = {"deductible": "true", "deductible_pct": 80}
        self.assertEqual(get_deductible_pct(tx), 80)

    def test_deductible_string_false(self):
        tx = {"deductible": "false", "deductible_pct": 80}
        self.assertEqual(get_deductible_pct(tx), 0)

    def test_pct_clamped_above_100(self):
        tx = {"deductible": True, "deductible_pct": 150}
        self.assertEqual(get_deductible_pct(tx), 100)

    def test_pct_clamped_below_0(self):
        tx = {"deductible": True, "deductible_pct": -10}
        self.assertEqual(get_deductible_pct(tx), 0)

    def test_pct_none_defaults_to_100(self):
        tx = {"deductible": True, "deductible_pct": None}
        self.assertEqual(get_deductible_pct(tx), 100)

    def test_pct_invalid_string_defaults_to_100(self):
        # get_deductible_pct() returns 100 for non-numeric strings as a fallback.
        # This is intentional export-script behavior — it does not crash on legacy or
        # manually-edited data. SKILL.md Step 6 now blocks invalid deductible_pct at
        # write time (rejects strings, sets 0 + review_required: true). Any "partial"
        # in the ledger therefore indicates a pre-validation write or manual edit.
        # This test documents the existing fallback; it does not represent valid data.
        tx = {"deductible": True, "deductible_pct": "partial"}
        self.assertEqual(get_deductible_pct(tx), 100)

    def test_missing_deductible_field_treated_as_false(self):
        # No deductible key at all → treat as non-deductible
        tx = {"deductible_pct": 100}
        self.assertEqual(get_deductible_pct(tx), 0)

    def test_zero_pct_on_deductible_true(self):
        # Explicitly set to 0 (review_required pending % confirmation)
        tx = {"deductible": True, "deductible_pct": 0}
        self.assertEqual(get_deductible_pct(tx), 0)


# ---------------------------------------------------------------------------
# format_amount
# ---------------------------------------------------------------------------
class TestFormatAmount(unittest.TestCase):
    def test_whole_number(self):
        self.assertEqual(format_amount(100), "$100.00")

    def test_two_decimals(self):
        self.assertEqual(format_amount(49.99), "$49.99")

    def test_thousands_separator(self):
        self.assertEqual(format_amount(1234.56), "$1,234.56")

    def test_zero(self):
        self.assertEqual(format_amount(0), "$0.00")

    def test_none_returns_zero(self):
        self.assertEqual(format_amount(None), "$0.00")

    def test_string_input(self):
        self.assertEqual(format_amount("47.50"), "$47.50")


# ---------------------------------------------------------------------------
# load_transactions
# ---------------------------------------------------------------------------
class TestLoadTransactions(unittest.TestCase):
    def test_loads_plain_array(self):
        txns = [_tx(), _tx("Canva", 16.00)]
        path = _write_ledger(txns)
        try:
            loaded = load_transactions(path)
            self.assertEqual(len(loaded), 2)
        finally:
            os.unlink(path)

    def test_loads_from_detect_duplicates_output(self):
        # detect_duplicates.py wraps output in {"clean": [...], "duplicates": [...]}
        data = {"clean": [_tx(), _tx("Canva", 16.00)], "duplicates": [], "stats": {}}
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, f)
        f.close()
        try:
            loaded = load_transactions(f.name)
            self.assertEqual(len(loaded), 2)
        finally:
            os.unlink(f.name)

    def test_raises_on_unrecognized_format(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump({"something_unexpected": 42}, f)
        f.close()
        try:
            with self.assertRaises(ValueError):
                load_transactions(f.name)
        finally:
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# generate_export — integration (writes real files, reads them back)
# ---------------------------------------------------------------------------
class TestGenerateExport(unittest.TestCase):
    def setUp(self):
        self.output_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def _run_export(self, txns, income=None, mileage=None):
        return generate_export(
            txns,
            year="2026",
            business_name="Test LLC",
            output_dir=self.output_dir,
            income_records=income,
            mileage_records=mileage,
        )

    def _read_csv(self, filename):
        path = self.output_dir / filename
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    # --- personal transactions are excluded ---
    def test_personal_transactions_excluded_from_full(self):
        txns = [
            _tx("OpenAI", 49.00, biz="business"),
            _tx("Netflix", 15.99, biz="personal", category="personal"),
        ]
        result = self._run_export(txns)
        self.assertEqual(result["full_count"], 1)

    # --- meals 50% rule ---
    def test_meals_deductible_amount_is_50_pct(self):
        txns = [_meal("Chipotle", 100.00)]
        result = self._run_export(txns)
        # Grand deductible should be $50, not $100
        self.assertAlmostEqual(result["grand_deductible"], 50.00, places=2)

    def test_meals_appear_in_full_csv_with_correct_pct(self):
        txns = [_meal("Chipotle", 100.00)]
        self._run_export(txns)
        rows = self._read_csv("tax-export-2026-Test-LLC-full.csv")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Deductible %"], "50%")
        self.assertEqual(rows[0]["Deductible Amount"], "$50.00")

    # --- flagged transactions ---
    def test_flagged_transactions_in_flagged_csv(self):
        txns = [
            _tx("Vendor A", 100.00, review=True, review_reason="Mixed use"),
            _tx("Vendor B", 50.00, review=False),
        ]
        result = self._run_export(txns)
        self.assertEqual(result["flagged_count"], 1)
        flagged_rows = self._read_csv("tax-export-2026-Test-LLC-flagged.csv")
        self.assertEqual(len(flagged_rows), 1)
        self.assertEqual(flagged_rows[0]["Vendor"], "Vendor A")

    # --- missing receipts ---
    def test_missing_receipts_csv(self):
        txns = [
            _tx("OpenAI", 49.00, receipt=False),
            _tx("Canva", 16.00, receipt=True),
        ]
        result = self._run_export(txns)
        self.assertEqual(result["missing_count"], 1)
        missing_rows = self._read_csv("tax-export-2026-Test-LLC-missing-receipts.csv")
        self.assertEqual(len(missing_rows), 1)
        self.assertEqual(missing_rows[0]["Vendor"], "OpenAI")

    # --- grand totals ---
    def test_grand_total_calculation(self):
        txns = [
            _tx("OpenAI", 49.00, deductible=True, deductible_pct=100),
            _tx("Meta Ads", 150.00, category="marketing_advertising",
                deductible=True, deductible_pct=100),
        ]
        result = self._run_export(txns)
        self.assertAlmostEqual(result["grand_total"], 199.00, places=2)
        self.assertAlmostEqual(result["grand_deductible"], 199.00, places=2)

    def test_grand_total_with_mixed_deductibility(self):
        txns = [
            _tx("OpenAI", 100.00, deductible=True, deductible_pct=100),
            _tx("Chipotle", 100.00, category="meals_entertainment",
                deductible=True, deductible_pct=50),
            _tx("Netflix", 15.99, biz="personal", category="personal",
                deductible=False, deductible_pct=0),
        ]
        result = self._run_export(txns)
        # Personal excluded from grand_total (only business txns count)
        self.assertAlmostEqual(result["grand_total"], 200.00, places=2)
        # $100 @ 100% + $100 @ 50% = $150 deductible
        self.assertAlmostEqual(result["grand_deductible"], 150.00, places=2)

    # --- output file count ---
    def test_five_files_created_without_income_or_mileage(self):
        txns = [_tx()]
        result = self._run_export(txns)
        self.assertEqual(result["files_created"], 5)

    def test_six_files_with_income(self):
        txns = [_tx()]
        income = [{"date": "2026-03-01", "source": "Stripe", "payer": "Client A",
                   "amount": 500.00, "form_1099": False, "notes": ""}]
        result = self._run_export(txns, income=income)
        self.assertEqual(result["files_created"], 6)

    def test_seven_files_with_income_and_mileage(self):
        txns = [_tx()]
        income = [{"date": "2026-03-01", "source": "Stripe", "payer": "Client A",
                   "amount": 500.00, "form_1099": False, "notes": ""}]
        mileage = [{"date": "2026-03-05", "start_location": "Home", "end_location": "Office",
                    "business_purpose": "Client meeting", "miles": 12.0,
                    "rate_per_mile": 0.725, "deductible_amount": 8.70, "notes": ""}]
        result = self._run_export(txns, income=income, mileage=mileage)
        self.assertEqual(result["files_created"], 7)

    # --- mileage deduction ---
    def test_mileage_deduction_totaled_correctly(self):
        mileage = [
            {"date": "2026-03-01", "start_location": "Home", "end_location": "Client",
             "business_purpose": "Meeting", "miles": 10.0,
             "rate_per_mile": 0.725, "deductible_amount": 7.25, "notes": ""},
            {"date": "2026-03-15", "start_location": "Home", "end_location": "Post Office",
             "business_purpose": "Ship product", "miles": 5.0,
             "rate_per_mile": 0.725, "deductible_amount": 3.625, "notes": ""},
        ]
        result = self._run_export([_tx()], mileage=mileage)
        self.assertAlmostEqual(result["total_miles"], 15.0, places=1)
        self.assertAlmostEqual(result["mileage_deduction"], 10.875, places=2)

    # --- income total ---
    def test_income_gross_total(self):
        income = [
            {"date": "2026-01-15", "source": "Stripe", "payer": "Client A",
             "amount": 1000.00, "form_1099": False, "notes": ""},
            {"date": "2026-02-15", "source": "PayPal", "payer": "Client B",
             "amount": 500.00, "form_1099": True, "notes": ""},
        ]
        result = self._run_export([_tx()], income=income)
        self.assertAlmostEqual(result["gross_income"], 1500.00, places=2)

    def _read_cover(self, path):
        """Read a cover note using locale encoding (export_ledger writes with open() default)."""
        with open(path, encoding="locale", errors="replace") as f:
            return f.read()

    # --- cover note ---
    def test_cover_note_created(self):
        self._run_export([_tx()])
        cover_path = self.output_dir / "tax-export-2026-Test-LLC-cover-note.txt"
        self.assertTrue(cover_path.exists())
        content = self._read_cover(cover_path)
        self.assertIn("Test LLC", content)
        self.assertIn("2026", content)

    def test_cover_note_mentions_meals_limitation_when_present(self):
        txns = [_meal("Chipotle", 80.00)]
        self._run_export(txns)
        cover = self._read_cover(self.output_dir / "tax-export-2026-Test-LLC-cover-note.txt")
        self.assertIn("50%", cover)
        self.assertIn("TCJA", cover)

    def test_cover_note_contractor_threshold_2026(self):
        # 2026 export should state $2,000 1099-NEC threshold
        txns = [_tx("Freelancer Jane", 3000.00, category="contractor_payments")]
        self._run_export(txns)
        cover = self._read_cover(self.output_dir / "tax-export-2026-Test-LLC-cover-note.txt")
        self.assertIn("$2,000", cover)

    def test_cover_note_contractor_threshold_2025(self):
        # 2025 export should state $600 1099-NEC threshold
        out_2025 = self.output_dir / "2025"
        generate_export(
            [_tx("Freelancer Jane", 3000.00, category="contractor_payments",
                 date="2025-06-15")],
            year="2025",
            business_name="Test LLC",
            output_dir=out_2025,
        )
        cover = self._read_cover(out_2025 / "tax-export-2025-Test-LLC-cover-note.txt")
        self.assertIn("$600", cover)

    # --- summary CSV ---
    def test_summary_csv_has_grand_total_row(self):
        txns = [_tx("OpenAI", 49.00), _tx("Canva", 16.00)]
        self._run_export(txns)
        rows = self._read_csv("tax-export-2026-Test-LLC-summary.csv")
        categories = [r["Category"] for r in rows]
        self.assertIn("GRAND TOTAL", categories)

    def test_summary_csv_schedule_references(self):
        txns = [
            _tx("OpenAI", 49.00, category="software_subscriptions"),
            _tx("Meta Ads", 150.00, category="marketing_advertising"),
        ]
        self._run_export(txns)
        rows = self._read_csv("tax-export-2026-Test-LLC-summary.csv")
        by_cat = {r["Category"]: r for r in rows if r["Schedule Reference"]}
        self.assertIn("Sch C Line 18", by_cat.get("Software & Subscriptions", {}).get("Schedule Reference", ""))
        self.assertIn("Sch C Line 8", by_cat.get("Marketing & Advertising", {}).get("Schedule Reference", ""))

    # --- full CSV column headers ---
    def test_full_csv_has_required_columns(self):
        self._run_export([_tx()])
        rows = self._read_csv("tax-export-2026-Test-LLC-full.csv")
        required = {"Date", "Vendor", "Amount", "Category", "Deductible %",
                    "Deductible Amount", "Receipt Matched", "Review Required"}
        self.assertTrue(required.issubset(set(rows[0].keys())))


# ---------------------------------------------------------------------------
# CATEGORY_META completeness
# ---------------------------------------------------------------------------
class TestCategoryMeta(unittest.TestCase):
    EXPECTED_CATEGORIES = [
        "software_subscriptions", "marketing_advertising", "office_supplies",
        "equipment", "travel", "vehicle_mileage", "meals_entertainment",
        "professional_services", "utilities", "rent_lease", "education_training",
        "contractor_payments", "insurance", "bank_fees", "home_office",
        "other_business", "personal",
    ]

    def test_all_categories_present(self):
        for cat in self.EXPECTED_CATEGORIES:
            self.assertIn(cat, CATEGORY_META, f"Missing category: {cat}")

    def test_each_category_has_display_and_schedule(self):
        for cat, meta in CATEGORY_META.items():
            self.assertIn("display", meta, f"{cat} missing display name")
            self.assertIn("schedule", meta, f"{cat} missing schedule reference")

    def test_equipment_in_depreciation_flag(self):
        self.assertIn("equipment", DEPRECIATION_FLAG)


if __name__ == "__main__":
    unittest.main(verbosity=2)
