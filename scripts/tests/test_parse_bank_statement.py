#!/usr/bin/env python3
"""
Unit tests for parse_bank_statement.py

Run from the scripts/ directory:
    python3 -m pytest tests/test_parse_bank_statement.py -v
    python3 -m unittest tests.test_parse_bank_statement -v
"""

import csv
import io
import sys
import tempfile
import os
import unittest
from pathlib import Path

# Allow importing from parent scripts/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))
from parse_bank_statement import (
    normalize_vendor,
    parse_amount,
    parse_date,
    find_column,
    parse_csv,
    BANK_COLUMN_MAPS,
)


# ---------------------------------------------------------------------------
# Helper: write a CSV string to a temp file, return path
# ---------------------------------------------------------------------------
def _write_temp_csv(content: str) -> str:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    )
    f.write(content)
    f.close()
    return f.name


class TestNormalizeVendor(unittest.TestCase):
    # --- exact pattern matches ---
    def test_amazon_mktp(self):
        self.assertEqual(normalize_vendor("AMZN MKTP US*1A2B3C4D"), "Amazon")

    def test_amazon_com(self):
        self.assertEqual(normalize_vendor("AMAZON.COM*AB12CD34"), "Amazon")

    def test_aws(self):
        self.assertEqual(normalize_vendor("AMAZON WEB SERVICES"), "Amazon Web Services")

    def test_paypal_with_merchant(self):
        result = normalize_vendor("PAYPAL *STARBUCKS")
        self.assertEqual(result, "PayPal - Starbucks")

    def test_square_pos(self):
        # "SQ *COFFEE SHOP" → strips "SQ *" prefix, returns title-cased merchant
        result = normalize_vendor("SQ *COFFEE SHOP")
        self.assertEqual(result, "Coffee Shop")

    def test_meta_ads(self):
        self.assertEqual(normalize_vendor("META *ADS 123456"), "Meta Ads")

    def test_facebook_ads(self):
        self.assertEqual(normalize_vendor("FACEBK *ADS PAYMENT"), "Meta Ads")

    def test_google_workspace(self):
        self.assertEqual(normalize_vendor("GOOGLE *GSUITE_ACME"), "Google Workspace")

    def test_openai(self):
        self.assertEqual(normalize_vendor("OPENAI *API"), "OpenAI")

    def test_anthropic(self):
        self.assertEqual(normalize_vendor("ANTHROPIC INC CHARGE"), "Anthropic")

    def test_canva(self):
        self.assertEqual(normalize_vendor("CANVA* SUBSCRIPTION"), "Canva")

    def test_canva_no_asterisk(self):
        self.assertEqual(normalize_vendor("CANVA PTY LTD"), "Canva")

    def test_fiverr(self):
        self.assertEqual(normalize_vendor("FIVERR COM"), "Fiverr")

    def test_upwork(self):
        self.assertEqual(normalize_vendor("UPWORK ESCROW INC"), "Upwork")

    def test_gohighlevel(self):
        self.assertEqual(normalize_vendor("GOHIGHLEVEL MONTHLY"), "GoHighLevel")

    def test_highlevel(self):
        self.assertEqual(normalize_vendor("HIGHLEVEL SUBSCRIPTION"), "GoHighLevel")

    def test_make_com(self):
        self.assertEqual(normalize_vendor("MAKE.COM"), "Make.com")

    def test_integromat(self):
        self.assertEqual(normalize_vendor("INTEGROMAT PLAN"), "Make.com")

    def test_verizon(self):
        self.assertEqual(normalize_vendor("VZWRLSS*BILL"), "Verizon Wireless")

    # --- fallback: unknown vendor gets title-cased ---
    def test_fallback_titlecase(self):
        result = normalize_vendor("SOME RANDOM VENDOR INC")
        self.assertEqual(result, "Some Random Vendor Inc")

    def test_fallback_strips_hash_suffix(self):
        # Characters after # or * should be stripped in fallback
        result = normalize_vendor("UNKNOWN VENDOR #9871")
        self.assertNotIn("#", result)

    # --- case insensitivity ---
    def test_lowercase_input(self):
        # Patterns use IGNORECASE — lowercase input should still match
        self.assertEqual(normalize_vendor("openai subscription"), "OpenAI")

    def test_mixed_case_input(self):
        self.assertEqual(normalize_vendor("Notion Inc"), "Notion")

    # --- edge cases ---
    def test_empty_string(self):
        result = normalize_vendor("")
        self.assertIsInstance(result, str)

    def test_whitespace_only(self):
        result = normalize_vendor("   ")
        self.assertIsInstance(result, str)


class TestParseAmount(unittest.TestCase):
    def test_plain_positive(self):
        amount, is_neg = parse_amount("47.99")
        self.assertAlmostEqual(amount, 47.99)
        self.assertFalse(is_neg)

    def test_negative_sign(self):
        amount, is_neg = parse_amount("-47.99")
        self.assertAlmostEqual(amount, 47.99)
        self.assertTrue(is_neg)

    def test_parentheses_negative(self):
        # Parentheses notation is standard accounting convention for negative amounts.
        # "(47.99)" means -47.99 — used by some banks in PDF/CSV exports.
        amount, is_neg = parse_amount("(47.99)")
        self.assertAlmostEqual(amount, 47.99)
        self.assertTrue(is_neg)

    def test_dollar_sign(self):
        amount, is_neg = parse_amount("$1,234.56")
        self.assertAlmostEqual(amount, 1234.56)
        self.assertFalse(is_neg)

    def test_comma_in_number(self):
        amount, is_neg = parse_amount("1,234.56")
        self.assertAlmostEqual(amount, 1234.56)
        self.assertFalse(is_neg)

    def test_negative_with_dollar(self):
        amount, is_neg = parse_amount("-$50.00")
        self.assertAlmostEqual(amount, 50.00)
        self.assertTrue(is_neg)

    def test_zero(self):
        amount, is_neg = parse_amount("0.00")
        self.assertAlmostEqual(amount, 0.0)
        self.assertFalse(is_neg)

    def test_invalid_returns_zero(self):
        amount, is_neg = parse_amount("N/A")
        self.assertAlmostEqual(amount, 0.0)
        self.assertFalse(is_neg)

    def test_whitespace_stripped(self):
        amount, is_neg = parse_amount("  25.00  ")
        self.assertAlmostEqual(amount, 25.00)

    def test_large_amount(self):
        amount, is_neg = parse_amount("$12,345.67")
        self.assertAlmostEqual(amount, 12345.67)


class TestParseDate(unittest.TestCase):
    def test_iso_format(self):
        self.assertEqual(parse_date("2025-03-15"), "2025-03-15")

    def test_slash_mdy_four_digit_year(self):
        self.assertEqual(parse_date("03/15/2025"), "2025-03-15")

    def test_slash_mdy_two_digit_year(self):
        self.assertEqual(parse_date("03/15/25"), "2025-03-15")

    def test_dash_mdy(self):
        self.assertEqual(parse_date("03-15-2025"), "2025-03-15")

    def test_empty_string(self):
        self.assertEqual(parse_date(""), "")

    def test_whitespace_only(self):
        self.assertEqual(parse_date("   "), "")

    def test_unknown_format_returns_raw(self):
        # If no format matches, the raw string is returned
        raw = "not-a-date"
        result = parse_date(raw)
        self.assertIsInstance(result, str)


class TestFindColumn(unittest.TestCase):
    def test_exact_match(self):
        headers = ["Date", "Description", "Amount"]
        self.assertEqual(find_column(headers, ["Date"]), "Date")

    def test_case_insensitive(self):
        headers = ["Transaction Date", "Description", "Amount"]
        self.assertEqual(find_column(headers, ["transaction date"]), "Transaction Date")

    def test_first_candidate_wins(self):
        headers = ["Posting Date", "Transaction Date", "Amount"]
        result = find_column(headers, ["Transaction Date", "Posting Date"])
        self.assertEqual(result, "Transaction Date")

    def test_fallback_to_second_candidate(self):
        headers = ["Posting Date", "Description", "Amount"]
        result = find_column(headers, ["Transaction Date", "Posting Date"])
        self.assertEqual(result, "Posting Date")

    def test_no_match_returns_none(self):
        headers = ["Date", "Description", "Amount"]
        self.assertIsNone(find_column(headers, ["Nonexistent Column"]))

    def test_empty_candidates_returns_none(self):
        headers = ["Date", "Description", "Amount"]
        self.assertIsNone(find_column(headers, []))

    def test_whitespace_in_header(self):
        headers = [" Amount ", "Date"]
        # Headers get .strip() applied in headers_lower; candidate must match stripped version
        self.assertEqual(find_column(headers, ["amount"]), " Amount ")


class TestParseCsvChase(unittest.TestCase):
    """Chase credit card: Type column drives debit/credit classification."""

    CHASE_CSV = (
        "Transaction Date,Post Date,Description,Category,Type,Amount\n"
        "03/15/2025,03/16/2025,OPENAI *API,Software,Sale,-49.00\n"
        "03/16/2025,03/17/2025,AMZN MKTP US*AB12CD,Shopping,Sale,-12.99\n"
        "03/17/2025,03/18/2025,REFUND FROM AMAZON,Shopping,Return,12.99\n"
        "03/18/2025,03/19/2025,GOOGLE *GSUITE_CO,Software,Sale,-18.00\n"
    )

    def setUp(self):
        self.path = _write_temp_csv(self.CHASE_CSV)

    def tearDown(self):
        os.unlink(self.path)

    def test_transaction_count(self):
        # "Return" credit row should be skipped
        txns = parse_csv(self.path, bank="chase")
        self.assertEqual(len(txns), 3)

    def test_vendor_normalized(self):
        txns = parse_csv(self.path, bank="chase")
        vendors = {t["vendor"] for t in txns}
        self.assertIn("OpenAI", vendors)
        self.assertIn("Amazon", vendors)
        self.assertIn("Google Workspace", vendors)

    def test_amount_positive_and_rounded(self):
        txns = parse_csv(self.path, bank="chase")
        amounts = {t["amount"] for t in txns}
        self.assertIn(49.0, amounts)
        self.assertIn(12.99, amounts)
        self.assertIn(18.0, amounts)

    def test_date_normalized(self):
        txns = parse_csv(self.path, bank="chase")
        dates = {t["transaction_date"] for t in txns}
        self.assertIn("2025-03-15", dates)

    def test_account_stamped(self):
        txns = parse_csv(self.path, bank="chase", account="Chase Sapphire")
        self.assertTrue(all(t["account"] == "Chase Sapphire" for t in txns))

    def test_source_field(self):
        txns = parse_csv(self.path, bank="chase")
        self.assertTrue(all(t["source"] == "Bank Import" for t in txns))

    def test_receipt_matched_false(self):
        txns = parse_csv(self.path, bank="chase")
        self.assertTrue(all(t["receipt_matched"] is False for t in txns))


class TestParseCsvChecking(unittest.TestCase):
    """Checking account sign convention: negative = debit, positive = deposit."""

    CHECKING_CSV = (
        "Date,Description,Amount\n"
        "03/01/2025,OPENAI SUBSCRIPTION,-49.00\n"
        "03/02/2025,PAYROLL DEPOSIT,2500.00\n"
        "03/03/2025,CANVA PRO,-16.00\n"
    )

    def setUp(self):
        self.path = _write_temp_csv(self.CHECKING_CSV)

    def tearDown(self):
        os.unlink(self.path)

    def test_deposits_skipped(self):
        # Positive amount in checking = credit/deposit → skip
        txns = parse_csv(self.path, bank="generic", account_type="checking")
        self.assertEqual(len(txns), 2)

    def test_debits_included(self):
        txns = parse_csv(self.path, bank="generic", account_type="checking")
        vendors = {t["vendor"] for t in txns}
        self.assertIn("OpenAI", vendors)
        self.assertIn("Canva", vendors)

    def test_amounts_positive(self):
        txns = parse_csv(self.path, bank="generic", account_type="checking")
        self.assertTrue(all(t["amount"] > 0 for t in txns))


class TestParseCsvCapitalOne(unittest.TestCase):
    """Capital One: separate Debit and Credit columns."""

    CAP_ONE_CSV = (
        "Transaction Date,Posted Date,Card No.,Description,Category,Debit,Credit\n"
        "2025-03-10,2025-03-11,1234,CANVA* SUBSCRIPTION,Software,16.00,\n"
        "2025-03-11,2025-03-12,1234,REFUND CANVA,Refund,,16.00\n"
        "2025-03-12,2025-03-13,1234,NOTION INC,Software,16.00,\n"
    )

    def setUp(self):
        self.path = _write_temp_csv(self.CAP_ONE_CSV)

    def tearDown(self):
        os.unlink(self.path)

    def test_credits_skipped(self):
        # Refund rows (credit column populated) → skip
        txns = parse_csv(self.path, bank="capital_one")
        self.assertEqual(len(txns), 2)

    def test_vendors(self):
        txns = parse_csv(self.path, bank="capital_one")
        vendors = {t["vendor"] for t in txns}
        self.assertIn("Canva", vendors)
        self.assertIn("Notion", vendors)


class TestParseCsvEdgeCases(unittest.TestCase):
    def test_skip_blank_rows(self):
        # Use checking account type: negative amounts = debits (expenses)
        csv_content = (
            "Date,Description,Amount\n"
            "03/01/2025,OpenAI,-49.00\n"
            ",,,\n"          # blank row — should be skipped
            "03/02/2025,Canva,-16.00\n"
        )
        path = _write_temp_csv(csv_content)
        try:
            txns = parse_csv(path, account_type="checking")
            self.assertEqual(len(txns), 2)
        finally:
            os.unlink(path)

    def test_skip_zero_amount(self):
        # Use checking account type: negative amounts = debits (expenses)
        csv_content = (
            "Date,Description,Amount\n"
            "03/01/2025,Pending Transaction,0.00\n"
            "03/02/2025,OpenAI,-49.00\n"
        )
        path = _write_temp_csv(csv_content)
        try:
            txns = parse_csv(path, account_type="checking")
            self.assertEqual(len(txns), 1)
            self.assertEqual(txns[0]["vendor"], "OpenAI")
        finally:
            os.unlink(path)

    def test_header_with_bom(self):
        # Some banks export CSVs with a UTF-8 BOM; utf-8-sig encoding handles it.
        # Negative amount + checking = debit (expense).
        csv_content = "\ufeffDate,Description,Amount\n03/01/2025,OpenAI,-49.00\n"
        path = _write_temp_csv(csv_content)
        try:
            txns = parse_csv(path, account_type="checking")
            self.assertEqual(len(txns), 1)
        finally:
            os.unlink(path)

    def test_bank_column_map_keys(self):
        # All expected bank names are present
        for bank in ["chase", "bofa", "wells_fargo", "amex", "capital_one", "generic"]:
            self.assertIn(bank, BANK_COLUMN_MAPS)

    def test_bank_column_map_required_fields(self):
        for bank, mapping in BANK_COLUMN_MAPS.items():
            self.assertIn("transaction_date", mapping, f"Missing transaction_date for {bank}")
            self.assertIn("vendor", mapping, f"Missing vendor for {bank}")
            self.assertIn("amount", mapping, f"Missing amount for {bank}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
