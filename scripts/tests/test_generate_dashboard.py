"""
Tests for generate_dashboard.compute_data() and render_html().

Run from the scripts/ directory:
    python -m pytest tests/test_generate_dashboard.py -v
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import generate_dashboard as gd  # noqa: E402

# ── Fixtures ─────────────────────────────────────────────────────────────────

MINIMAL_CONFIG = {
    "business_name": "Test Co",
    "tax_year": "2025",
    "entity_type": "sole_prop",
}


def make_tx(
    amount=100.0,
    category="software_subscriptions",
    deductible=True,
    deductible_pct=100,
    date="2025-03-15",
    vendor="Canva",
    receipt_matched=False,
    review_required=False,
):
    return {
        "amount": amount,
        "category": category,
        "deductible": deductible,
        "deductible_pct": deductible_pct,
        "transaction_date": date,
        "vendor": vendor,
        "receipt_matched": receipt_matched,
        "review_required": review_required,
    }


def make_income(amount=500.0, category="affiliate_commission", date="2025-03-10", source="ClickBank"):
    return {"amount": amount, "category": category, "date": date, "source": source}


def make_mileage(miles=10.0, round_trip=False, date="2025-03-20", purpose="Client meeting"):
    return {
        "miles": miles,
        "round_trip": round_trip,
        "date": date,
        "business_purpose": purpose,
        "start_location": "Home",
        "end_location": "Office",
    }


# ── compute_data: empty inputs ────────────────────────────────────────────────

class TestComputeDataEmpty(unittest.TestCase):

    def test_empty_inputs_zero_totals(self):
        data = gd.compute_data(MINIMAL_CONFIG, [], [], [])
        s = data["summary"]
        self.assertEqual(s["total_expenses"], 0.0)
        self.assertEqual(s["deductible_total"], 0.0)
        self.assertEqual(s["income_total"], 0.0)
        self.assertEqual(s["tx_count"], 0)
        self.assertEqual(s["income_count"], 0)
        self.assertEqual(s["mileage_count"], 0)
        self.assertEqual(s["missing_receipts"], 0)
        self.assertEqual(s["review_required"], 0)

    def test_meta_fields_populated(self):
        data = gd.compute_data(MINIMAL_CONFIG, [], [], [])
        meta = data["meta"]
        self.assertEqual(meta["tax_year"], "2025")
        self.assertEqual(meta["business_name"], "Test Co")
        self.assertIn("generated", meta)

    def test_no_alerts_on_empty_ledger(self):
        data = gd.compute_data(MINIMAL_CONFIG, [], [], [])
        self.assertEqual(data["alerts"], [])


# ── compute_data: mileage rate lookup ─────────────────────────────────────────

class TestMileageRateLookup(unittest.TestCase):

    def test_rate_2025(self):
        data = gd.compute_data(MINIMAL_CONFIG, [], [], [])
        self.assertEqual(data["meta"]["mileage_rate"], 0.70)

    def test_rate_2026(self):
        cfg = {**MINIMAL_CONFIG, "tax_year": "2026"}
        data = gd.compute_data(cfg, [], [], [])
        self.assertEqual(data["meta"]["mileage_rate"], 0.725)

    def test_unknown_year_defaults_to_070(self):
        cfg = {**MINIMAL_CONFIG, "tax_year": "2099"}
        data = gd.compute_data(cfg, [], [], [])
        self.assertEqual(data["meta"]["mileage_rate"], 0.70)


# ── compute_data: expense totals ──────────────────────────────────────────────

class TestExpenseTotals(unittest.TestCase):

    def test_single_fully_deductible_transaction(self):
        tx = make_tx(amount=200.0, deductible=True, deductible_pct=100)
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        s = data["summary"]
        self.assertEqual(s["total_expenses"], 200.0)
        self.assertEqual(s["deductible_total"], 200.0)

    def test_non_deductible_transaction(self):
        tx = make_tx(amount=50.0, deductible=False, category="personal")
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        s = data["summary"]
        self.assertEqual(s["total_expenses"], 50.0)
        self.assertEqual(s["deductible_total"], 0.0)

    def test_fifty_percent_deductible_meals(self):
        tx = make_tx(amount=100.0, deductible=True, deductible_pct=50, category="meals_entertainment")
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        s = data["summary"]
        self.assertEqual(s["total_expenses"], 100.0)
        self.assertEqual(s["deductible_total"], 50.0)

    def test_multiple_transactions_sum_correctly(self):
        txs = [
            make_tx(amount=100.0, deductible=True, deductible_pct=100),
            make_tx(amount=200.0, deductible=True, deductible_pct=100, date="2025-04-10"),
            make_tx(amount=50.0, deductible=False, category="personal"),
        ]
        data = gd.compute_data(MINIMAL_CONFIG, txs, [], [])
        s = data["summary"]
        self.assertEqual(s["total_expenses"], 350.0)
        self.assertEqual(s["deductible_total"], 300.0)
        self.assertEqual(s["tx_count"], 3)


# ── compute_data: receipt and review flags ────────────────────────────────────

class TestReceiptAndReviewFlags(unittest.TestCase):

    def test_unmatched_receipt_counted_as_missing(self):
        tx = make_tx(receipt_matched=False, review_required=False)
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        self.assertEqual(data["summary"]["missing_receipts"], 1)

    def test_matched_receipt_not_missing(self):
        tx = make_tx(receipt_matched=True)
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        self.assertEqual(data["summary"]["missing_receipts"], 0)

    def test_review_required_counted(self):
        tx = make_tx(review_required=True, receipt_matched=True)
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        self.assertEqual(data["summary"]["review_required"], 1)

    def test_receipt_status_field_on_transaction(self):
        matched = make_tx(receipt_matched=True)
        data = gd.compute_data(MINIMAL_CONFIG, [matched], [], [])
        self.assertEqual(data["transactions"][0]["receipt_status"], "matched")

    def test_review_status_overrides_missing(self):
        # review_required=True, receipt_matched=False → status should be "review"
        tx = make_tx(receipt_matched=False, review_required=True)
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        self.assertEqual(data["transactions"][0]["receipt_status"], "review")


# ── compute_data: income ──────────────────────────────────────────────────────

class TestIncome(unittest.TestCase):

    def test_income_total(self):
        inc = make_income(amount=1000.0)
        data = gd.compute_data(MINIMAL_CONFIG, [], [inc], [])
        self.assertEqual(data["summary"]["income_total"], 1000.0)
        self.assertEqual(data["summary"]["income_count"], 1)

    def test_income_by_category(self):
        inc = make_income(amount=500.0, category="affiliate_commission")
        data = gd.compute_data(MINIMAL_CONFIG, [], [inc], [])
        self.assertIn("affiliate_commission", data["income_by_category"])
        self.assertEqual(data["income_by_category"]["affiliate_commission"]["total"], 500.0)


# ── compute_data: mileage ─────────────────────────────────────────────────────

class TestMileage(unittest.TestCase):

    def test_one_way_mileage_deduction(self):
        mi = make_mileage(miles=10.0, round_trip=False)
        data = gd.compute_data(MINIMAL_CONFIG, [], [], [mi])
        s = data["summary"]
        self.assertEqual(s["mileage_miles"], 10.0)
        self.assertAlmostEqual(s["mileage_deduction"], 7.0, places=2)  # 10 * 0.70

    def test_round_trip_doubles_miles(self):
        mi = make_mileage(miles=10.0, round_trip=True)
        data = gd.compute_data(MINIMAL_CONFIG, [], [], [mi])
        s = data["summary"]
        self.assertEqual(s["mileage_miles"], 20.0)
        self.assertAlmostEqual(s["mileage_deduction"], 14.0, places=2)  # 20 * 0.70

    def test_mileage_record_fields(self):
        mi = make_mileage(miles=5.0, purpose="Post office run")
        data = gd.compute_data(MINIMAL_CONFIG, [], [], [mi])
        rec = data["mileage_records"][0]
        self.assertEqual(rec["miles"], 5.0)
        self.assertEqual(rec["purpose"], "Post office run")


# ── compute_data: category grouping ──────────────────────────────────────────

class TestCategoryGrouping(unittest.TestCase):

    def test_by_category_aggregates_same_category(self):
        txs = [
            make_tx(amount=100.0, category="software_subscriptions"),
            make_tx(amount=50.0, category="software_subscriptions", date="2025-04-01"),
        ]
        data = gd.compute_data(MINIMAL_CONFIG, txs, [], [])
        cat = data["by_category"]["software_subscriptions"]
        self.assertEqual(cat["total"], 150.0)
        self.assertEqual(cat["count"], 2)

    def test_category_label_populated(self):
        tx = make_tx(category="marketing_advertising")
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        label = data["by_category"]["marketing_advertising"]["label"]
        self.assertEqual(label, "Marketing & Advertising")

    def test_deductible_amount_per_category(self):
        tx = make_tx(amount=200.0, category="office_supplies", deductible=True, deductible_pct=100)
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        cat = data["by_category"]["office_supplies"]
        self.assertEqual(cat["deductible"], 200.0)


# ── compute_data: by_month grouping ──────────────────────────────────────────

class TestByMonth(unittest.TestCase):

    def test_month_key_format(self):
        tx = make_tx(date="2025-06-15")
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        self.assertIn("2025-06", data["by_month"])

    def test_all_months_sorted(self):
        txs = [
            make_tx(date="2025-06-01"),
            make_tx(date="2025-03-01"),
            make_tx(date="2025-09-01"),
        ]
        data = gd.compute_data(MINIMAL_CONFIG, txs, [], [])
        self.assertEqual(data["all_months"], sorted(data["all_months"]))

    def test_invalid_date_excluded_from_by_month(self):
        tx = make_tx(date="not-a-date")
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        # Transaction should still appear in totals but not in by_month
        self.assertEqual(data["summary"]["total_expenses"], 100.0)
        self.assertEqual(data["by_month"], {})


# ── compute_data: quarterly tax estimate ─────────────────────────────────────

class TestQuarterlyEstimate(unittest.TestCase):

    def test_se_tax_positive_when_profitable(self):
        inc = make_income(amount=10000.0)
        data = gd.compute_data(MINIMAL_CONFIG, [], [inc], [])
        self.assertGreater(data["summary"]["se_tax_est"], 0)

    def test_zero_tax_when_no_income(self):
        data = gd.compute_data(MINIMAL_CONFIG, [], [], [])
        self.assertEqual(data["summary"]["se_tax_est"], 0.0)
        self.assertEqual(data["summary"]["fed_income_est"], 0.0)

    def test_mileage_deduction_reduces_net_profit(self):
        inc = make_income(amount=1000.0)
        mi = make_mileage(miles=100.0)  # 100 * 0.70 = $70 deduction
        data = gd.compute_data(MINIMAL_CONFIG, [], [inc], [mi])
        self.assertAlmostEqual(data["summary"]["net_profit"], 930.0, places=2)

    def test_ledger_deductions_reduce_net_profit(self):
        inc = make_income(amount=1000.0)
        tx = make_tx(amount=200.0, deductible=True, deductible_pct=100)
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [inc], [])
        self.assertAlmostEqual(data["summary"]["net_profit"], 800.0, places=2)


# ── compute_data: alerts ──────────────────────────────────────────────────────

class TestAlerts(unittest.TestCase):

    def test_missing_receipt_triggers_warning(self):
        tx = make_tx(receipt_matched=False)
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        types = [a["type"] for a in data["alerts"]]
        self.assertIn("warning", types)

    def test_no_income_with_expenses_triggers_info(self):
        tx = make_tx(amount=100.0)
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        msgs = [a["msg"] for a in data["alerts"]]
        self.assertTrue(any("No income" in m for m in msgs))

    def test_mileage_alert_present_when_miles_logged(self):
        mi = make_mileage(miles=50.0)
        data = gd.compute_data(MINIMAL_CONFIG, [], [], [mi])
        msgs = [a["msg"] for a in data["alerts"]]
        self.assertTrue(any("Mileage" in m for m in msgs))

    def test_review_required_triggers_warning(self):
        tx = make_tx(review_required=True, receipt_matched=True)
        data = gd.compute_data(MINIMAL_CONFIG, [tx], [], [])
        types = [a["type"] for a in data["alerts"]]
        self.assertIn("warning", types)


# ── render_html ───────────────────────────────────────────────────────────────

class TestRenderHtml(unittest.TestCase):

    def _data(self):
        return gd.compute_data(MINIMAL_CONFIG, [], [], [])

    def test_returns_html_string(self):
        html = gd.render_html(self._data())
        self.assertIsInstance(html, str)
        self.assertTrue(html.strip().startswith("<!DOCTYPE html>"))

    def test_tax_year_substituted(self):
        html = gd.render_html(self._data())
        self.assertNotIn("{{TAX_YEAR}}", html)
        self.assertIn("2025", html)

    def test_generated_timestamp_substituted(self):
        html = gd.render_html(self._data())
        self.assertNotIn("{{GENERATED}}", html)

    def test_data_json_substituted(self):
        html = gd.render_html(self._data())
        self.assertNotIn("%%DATA_JSON%%", html)

    def test_no_leftover_placeholder_tokens(self):
        html = gd.render_html(self._data())
        self.assertNotIn("{{TAX_YEAR}}", html)
        self.assertNotIn("{{GENERATED}}", html)
        self.assertNotIn("%%DATA_JSON%%", html)

    def test_data_json_is_parseable_in_output(self):
        data = self._data()
        html = gd.render_html(data)
        marker = "const DATA = "
        self.assertIn(marker, html)
        idx = html.index(marker) + len(marker)
        end = html.index(";", idx)
        parsed = json.loads(html[idx:end])
        self.assertIn("meta", parsed)
        self.assertIn("summary", parsed)
        self.assertIn("transactions", parsed)

    def test_data_json_contains_correct_tax_year(self):
        data = self._data()
        html = gd.render_html(data)
        marker = "const DATA = "
        idx = html.index(marker) + len(marker)
        end = html.index(";", idx)
        parsed = json.loads(html[idx:end])
        self.assertEqual(parsed["meta"]["tax_year"], "2025")

    def test_missing_template_raises_file_not_found(self):
        original = gd._TEMPLATE_PATH
        gd._TEMPLATE_PATH = Path("/nonexistent/path/dashboard.html")
        try:
            with self.assertRaises(FileNotFoundError) as ctx:
                gd.render_html(self._data())
            self.assertIn("dashboard.html", str(ctx.exception))
        finally:
            gd._TEMPLATE_PATH = original

    def test_error_message_includes_guidance(self):
        original = gd._TEMPLATE_PATH
        gd._TEMPLATE_PATH = Path("/nonexistent/path/dashboard.html")
        try:
            with self.assertRaises(FileNotFoundError) as ctx:
                gd.render_html(self._data())
            self.assertIn("scripts/templates/dashboard.html", str(ctx.exception))
        finally:
            gd._TEMPLATE_PATH = original


# ── Tax estimate: real brackets + deductions ─────────────────────────────────

class TestImprovedTaxEstimate(unittest.TestCase):
    """Verify the improved income tax estimate applies proper deductions."""

    def test_low_income_zero_fed_tax_after_deductions(self):
        # $5,000 net profit: SE tax ~$706, SE deduction ~$353, QBID ~$1,000,
        # std deduction $15,750 → taxable income is negative → fed_income_est == 0
        config = {"business_name": "Test Co", "tax_year": "2025", "entity_type": "sole_prop"}
        inc = make_income(amount=5000.0)
        data = gd.compute_data(config, [], [inc], [])
        s = data["summary"]
        self.assertEqual(s["fed_income_est"], 0.0)
        self.assertGreater(s["se_tax_est"], 0.0)  # SE tax still applies

    def test_high_income_uses_marginal_brackets(self):
        # $100,000 net profit: after deductions, taxable income > 0 → real bracket applied
        config = {"business_name": "Test Co", "tax_year": "2025", "entity_type": "sole_prop"}
        inc = make_income(amount=100_000.0)
        data = gd.compute_data(config, [], [inc], [])
        s = data["summary"]
        self.assertGreater(s["fed_income_est"], 0.0)
        # Flat 12% of $100k would be $12,000 — with deductions the real answer is lower
        self.assertLess(s["fed_income_est"], 12_000.0)

    def test_2026_brackets_applied_when_tax_year_2026(self):
        config = {"business_name": "Test Co", "tax_year": "2026", "entity_type": "sole_prop"}
        inc = make_income(amount=100_000.0)
        data = gd.compute_data(config, [], [inc], [])
        s = data["summary"]
        # 2026 std deduction is $16,100 (vs $15,750 for 2025) → slightly lower taxable income
        # We just verify the estimate is positive and the config was accepted
        self.assertGreater(s["total_tax_est"], 0.0)


if __name__ == "__main__":
    unittest.main()
