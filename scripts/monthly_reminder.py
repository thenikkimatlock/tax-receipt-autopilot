#!/usr/bin/env python3
"""
monthly_reminder.py
--------------------
Monthly bank statement reminder + full ledger diagnostic engine.

Modes:
  check   — Determine if a monthly bank statement is overdue
  audit   — Full ledger diagnostic: what's missing, flagged, incomplete, W-9 gaps
  summary — Monthly expense + income summary for a given month

Usage:
    python3 monthly_reminder.py check   <ledger.json>
    python3 monthly_reminder.py audit   <ledger.json> [--vendors <vendors.json>] [--mileage <mileage.json>]
    python3 monthly_reminder.py summary <ledger.json> [--month 2026-03] [--income <income.json>] [--mileage <mileage.json>]
    python3 monthly_reminder.py snooze  <N>

Output: JSON with reminder status and full diagnostic details.
Designed to be called at the start of every Claude session.
"""

import argparse
import calendar
import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
STATEMENT_OVERDUE_DAYS = 35   # If newest bank import is > 35 days old, remind
SNOOZE_FILE = str(Path.home() / ".tax-autopilot-snooze.json")


def _r2(x: float) -> float:
    """Round to 2 decimal places."""
    return float(f"{x:.2f}")


def load_ledger(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict) and "clean" in data:
        return data["clean"]  # type: ignore[return-value]
    if isinstance(data, list):
        return data  # type: ignore[return-value]
    return []


def load_json_file(path: str) -> list[dict]:
    """Load a JSON array file, return [] if missing or empty."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        with open(p) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def parse_date(s: str) -> "date | None":
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"]:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def get_deductible_pct(tx: dict) -> int:
    """
    Return the deductible percentage (0-100) for a transaction.
    Uses the explicit deductible_pct field — no category-based magic.
    """
    ded = tx.get("deductible", False)
    ded_str = str(ded).lower().strip() if ded is not None else ""
    is_deductible = ded is True or ded_str in {"true", "yes", "1"}
    if not is_deductible:
        return 0
    pct = tx.get("deductible_pct", None)
    if pct is None:
        return 100
    try:
        return max(0, min(100, int(pct)))
    except (TypeError, ValueError):
        return 100


# ---------------------------------------------------------------------------
# Mode 1: Check — is a bank statement overdue?
# ---------------------------------------------------------------------------
def check_reminder(transactions: list[dict], snooze_path: Path) -> dict:
    today = date.today()

    # Check snooze
    if snooze_path.exists():
        with open(snooze_path) as f:
            snooze = json.load(f)
        snooze_until = parse_date(snooze.get("until", ""))
        if snooze_until and snooze_until > today:
            return {
                "reminder_needed": False,
                "snoozed_until": str(snooze_until),
                "message": f"Reminder snoozed until {snooze_until.strftime('%B %d, %Y')}",
            }

    # Find most recent bank import
    bank_txns = [t for t in transactions if t.get("source") == "Bank Import"]
    if not bank_txns:
        return {
            "reminder_needed": True,
            "last_import_date": None,
            "days_since_import": None,
            "missing_months": _get_missing_months(transactions),
            "missing_by_account": {},
            "message": (
                "NO BANK STATEMENT ON RECORD\n\n"
                "You haven't imported any bank statements yet.\n"
                "To get started:\n"
                "  1. Log into your bank or credit card portal\n"
                "  2. Download your statement as CSV (preferred) or PDF\n"
                "  3. Reply: 'Here's my [Month] statement' + attach the file\n\n"
                "Tip: Start with your most recent complete month."
            ),
        }

    dates = [parse_date(str(t.get("transaction_date", ""))) for t in bank_txns]
    dates = [d for d in dates if d]
    if not dates:
        return {"reminder_needed": False, "missing_by_account": {}, "message": "Could not determine import dates."}

    newest = max(dates)
    days_since = (today - newest).days
    missing_months = _get_missing_months(transactions)
    missing_by_account = _get_missing_months_by_account(transactions)

    if days_since > STATEMENT_OVERDUE_DAYS or missing_months:
        months_str = ", ".join(missing_months) if missing_months else "recent months"
        return {
            "reminder_needed": True,
            "last_import_date": str(newest),
            "days_since_import": days_since,
            "missing_months": missing_months,
            "missing_by_account": missing_by_account,
            "message": (
                f"BANK STATEMENT REMINDER\n\n"
                f"Your last bank import covers transactions through {newest.strftime('%B %d, %Y')} "
                f"({days_since} days ago).\n\n"
                f"Missing statement{'s' if len(missing_months) > 1 else ''}: {months_str}\n\n"
                f"To import:\n"
                f"  1. Download your {months_str} statement as CSV or PDF\n"
                f"  2. Reply: 'Here is my {months_str} bank statement' + attach\n\n"
                f"Staying current = fewer surprises at tax time."
            ),
        }
    else:
        return {
            "reminder_needed": False,
            "last_import_date": str(newest),
            "days_since_import": days_since,
            "missing_by_account": missing_by_account,
            "message": f"✅ Bank statements current through {newest.strftime('%B %d, %Y')}.",
        }


def _get_missing_months(transactions: list[dict]) -> list[str]:
    """Find calendar months with no bank imports — limited to the current tax year.

    Caps lookback to January 1 of the current year so prior-year gaps don't
    generate noise. Also excludes the current partial month (can't be "missing"
    until it's complete).
    """
    if not transactions:
        return [datetime.now().strftime("%B %Y")]

    bank_txns = [t for t in transactions if t.get("source") == "Bank Import"]
    if not bank_txns:
        return [datetime.now().strftime("%B %Y")]

    dates = [parse_date(str(t.get("transaction_date", ""))) for t in bank_txns]
    dates = [d for d in dates if d]
    if not dates:
        return []

    today = date.today()
    # Only surface gaps from the start of the current calendar year.
    # Prior-year gaps are historical records, not actionable reminders.
    year_start = date(today.year, 1, 1)
    # Exclude the current partial month — it can't be complete yet.
    if today.month == 1:
        last_complete_month: tuple[int, int] = (today.year - 1, 12)
    else:
        last_complete_month = (today.year, today.month - 1)

    months_with_data = {(d.year, d.month) for d in dates}
    current: tuple[int, int] = (year_start.year, year_start.month)
    end: tuple[int, int] = last_complete_month

    missing = []
    while current <= end:
        if current not in months_with_data:
            y, m = current
            missing.append(datetime(y, m, 1).strftime("%B %Y"))
        y, m = current
        current = (y + 1, 1) if m == 12 else (y, m + 1)

    return missing


def _get_missing_months_by_account(transactions: list[dict]) -> dict[str, list[str]]:
    """
    Find calendar months with no bank imports, broken out per account.
    Returns a dict keyed by account name (empty string if account field absent).
    Each value is the list of missing month strings for that account.
    Only considers transactions with source == "Bank Import".
    """
    bank_txns = [t for t in transactions if t.get("source") == "Bank Import"]
    if not bank_txns:
        return {}

    by_account: dict[str, list[dict]] = {}
    for tx in bank_txns:
        account = str(tx.get("account") or "")
        by_account.setdefault(account, []).append(tx)

    today = date.today()
    result: dict[str, list[str]] = {}

    year_start = date(today.year, 1, 1)
    if today.month == 1:
        last_complete_month: tuple[int, int] = (today.year - 1, 12)
    else:
        last_complete_month = (today.year, today.month - 1)

    for account, txns in by_account.items():
        dates = [parse_date(str(t.get("transaction_date", ""))) for t in txns]
        dates = [d for d in dates if d]
        if not dates:
            result[account] = []
            continue

        months_with_data = {(d.year, d.month) for d in dates}
        current: tuple[int, int] = (year_start.year, year_start.month)
        end: tuple[int, int] = last_complete_month

        missing: list[str] = []
        while current <= end:
            if current not in months_with_data:
                y, m = current
                missing.append(datetime(y, m, 1).strftime("%B %Y"))
            y, m = current
            current = (y + 1, 1) if m == 12 else (y, m + 1)

        result[account] = missing

    return result


# ---------------------------------------------------------------------------
# Mode 2: Full Audit Diagnostic
# ---------------------------------------------------------------------------
def _normalize_vendor_key(name: str) -> str:
    """Normalize a vendor name for comparison.

    Lowercases, strips punctuation, and sorts words so that
    'Smith, John' and 'John Smith' hash to the same key.
    """
    import re
    words = re.sub(r"[^a-z0-9\s]", "", name.lower()).split()
    return " ".join(sorted(words))


def full_audit(
    transactions: list[dict],
    vendors: list[dict] | None = None,
    mileage_records: list[dict] | None = None,
) -> dict:
    today = date.today()
    vendors = vendors or []
    mileage_records = mileage_records or []

    issues: list[str] = []
    stats: dict[str, int] = {
        "total": 0, "missing_receipts": 0, "flagged": 0,
        "uncategorized": 0, "mixed_use": 0, "large_equipment": 0,
        "meals_no_notes": 0, "contractor_1099_warnings": 0,
        "contractors_missing_w9": 0, "mileage_trips": len(mileage_records),
    }

    missing_receipts: list[dict] = []
    flagged: list[dict] = []
    uncategorized: list[dict] = []
    mixed_use: list[dict] = []
    large_equipment: list[dict] = []
    contractor_ytd: dict[str, float] = {}
    meals: list[dict] = []

    # Build contractor W-9 map from vendor KB — keyed by normalized name so
    # "Smith, John" and "John Smith" resolve to the same entry.
    contractor_w9: dict[str, bool] = {}
    for v in vendors:
        if str(v.get("default_category", "")).lower() == "contractor_payments":
            name = str(v.get("vendor_name", "")).strip()
            if name:
                contractor_w9[_normalize_vendor_key(name)] = bool(v.get("w9_on_file", False))

    for tx in transactions:
        stats["total"] += 1
        amt: float = float(tx.get("amount", 0) or 0)
        vendor: str = str(tx.get("vendor") or "Unknown")
        tx_date: str = str(tx.get("transaction_date") or "")
        cat: str = str(tx.get("category") or "")
        biz: str = str(tx.get("business_or_personal") or "")

        # Missing receipt
        if not tx.get("receipt_matched") and biz != "personal":
            missing_receipts.append({"vendor": vendor, "date": tx_date, "amount": amt})
            stats["missing_receipts"] += 1

        # Flagged for review
        if tx.get("review_required"):
            flagged.append({
                "vendor": vendor, "date": tx_date, "amount": amt,
                "reason": str(tx.get("review_reason") or "No reason given"),
            })
            stats["flagged"] += 1

        # Uncategorized
        if not cat or cat == "None":
            uncategorized.append({"vendor": vendor, "date": tx_date, "amount": amt})
            stats["uncategorized"] += 1

        # Mixed-use
        if biz == "mixed":
            mixed_use.append({"vendor": vendor, "date": tx_date, "amount": amt, "category": cat})
            stats["mixed_use"] += 1

        # Large equipment
        if cat == "equipment" and amt >= 2500:
            large_equipment.append({"vendor": vendor, "date": tx_date, "amount": amt})
            stats["large_equipment"] += 1

        # Contractor tracking
        if cat == "contractor_payments":
            prev: float = contractor_ytd.get(vendor, 0.0)
            contractor_ytd[vendor] = prev + amt

        # Meals without business purpose note
        if cat == "meals_entertainment" and not tx.get("notes"):
            meals.append({"vendor": vendor, "date": tx_date, "amount": amt})
            stats["meals_no_notes"] += 1

    # 1099 threshold — infer tax year from the ledger's transaction dates, NOT today's date.
    # Using today.year would apply 2026 rules ($2,000) to a 2025 ledger audited after Jan 1 2026,
    # silently skipping contractors who crossed the 2025 $600 threshold.
    tx_years = [
        d.year
        for d in (parse_date(str(t.get("transaction_date", ""))) for t in transactions)
        if d is not None
    ]
    ledger_year = max(tx_years) if tx_years else today.year
    nec_threshold = 600.0 if ledger_year <= 2025 else 2000.0
    contractor_warnings: list[dict] = []
    contractors_missing_w9: list[dict] = []

    for vendor_name, ytd_total in contractor_ytd.items():
        warn_at = nec_threshold * 0.80  # warn at 80% of threshold
        if ytd_total >= warn_at:
            contractor_warnings.append({
                "vendor": vendor_name,
                "ytd_total": _r2(ytd_total),
                "threshold": nec_threshold,
                "pct_of_threshold": int(ytd_total / nec_threshold * 1000) / 10.0,
            })
        # W-9 check via vendor KB — normalize both sides so name order/punctuation
        # differences ("Smith, John" vs "John Smith") don't cause false misses.
        key = _normalize_vendor_key(vendor_name)
        w9_status = contractor_w9.get(key, None)
        if w9_status is False or w9_status is None:
            contractors_missing_w9.append({
                "vendor": vendor_name,
                "ytd_total": _r2(ytd_total),
                "w9_on_file": False,
            })

    stats["contractor_1099_warnings"] = len(contractor_warnings)
    stats["contractors_missing_w9"] = len(contractors_missing_w9)

    # Mileage log check
    mileage_issues: list[str] = []
    for trip in mileage_records:
        problems = []
        if not trip.get("start_location"):
            problems.append("missing start location")
        if not trip.get("end_location"):
            problems.append("missing end location")
        if not trip.get("business_purpose"):
            problems.append("missing business purpose")
        if not trip.get("miles"):
            problems.append("missing miles")
        if problems:
            mileage_issues.append(
                f"{trip.get('date', 'unknown date')} — {', '.join(problems)}"
            )

    # Build issue list
    if missing_receipts:
        issues.append(f"❌ {len(missing_receipts)} transactions missing receipts")
    if flagged:
        issues.append(f"⚠️  {len(flagged)} transactions flagged for review")
    if uncategorized:
        issues.append(f"📂 {len(uncategorized)} transactions uncategorized")
    if mixed_use:
        issues.append(f"🔀 {len(mixed_use)} mixed-use transactions need business-% confirmed")
    if large_equipment:
        issues.append(f"🖥️  {len(large_equipment)} equipment items may qualify for Section 179")
    if contractor_warnings:
        issues.append(f"📋 {len(contractor_warnings)} contractors approaching 1099-NEC threshold")
    if contractors_missing_w9:
        issues.append(f"📝 {len(contractors_missing_w9)} contractors without W-9 on file")
    if meals:
        issues.append(f"🍽️  {len(meals)} meal expenses missing business purpose in notes")
    if mileage_issues:
        issues.append(f"🚗 {len(mileage_issues)} mileage log entries incomplete (IRS requires full documentation)")

    # Health score — normalized against ledger size.
    # Floor of 10 prevents catastrophic scores on new/small ledgers where a single
    # uncategorized transaction would otherwise dominate the percentage calculation.
    n = max(len(transactions), 10)

    def pct(count: int) -> float:
        return count / n

    health_score = int(max(0.0, 100.0 - (
        pct(len(missing_receipts))    * 40 +
        pct(len(uncategorized))       * 35 +
        pct(len(flagged))             * 15 +
        pct(len(mixed_use))           *  5 +
        pct(len(contractor_warnings)) *  5
    )))

    return {
        "audit_date":               str(today),
        "total_transactions":       stats["total"],
        "health_score":             min(100, health_score),
        "issues":                   issues,
        "missing_receipts":         missing_receipts,
        "flagged_transactions":     flagged,
        "uncategorized":            uncategorized,
        "mixed_use_items":          mixed_use,
        "large_equipment":          large_equipment,
        "contractor_warnings":      contractor_warnings,
        "contractors_missing_w9":   contractors_missing_w9,
        "meals_needing_notes":      meals,
        "mileage_log_issues":       mileage_issues,
        "stats":                    dict(stats),
    }


# ---------------------------------------------------------------------------
# Mode 3: Monthly Summary (expenses + income + mileage)
# ---------------------------------------------------------------------------
def monthly_summary(
    transactions: list[dict],
    month: "str | None" = None,
    income_records: list[dict] | None = None,
    mileage_records: list[dict] | None = None,
) -> dict:
    income_records  = income_records  or []
    mileage_records = mileage_records or []

    if not month:
        today = date.today()
        if today.month == 1:
            target = date(today.year - 1, 12, 1)
        else:
            target = date(today.year, today.month - 1, 1)
        month_str: str = target.strftime("%Y-%m")
    else:
        month_str = month

    month_txns = [
        t for t in transactions
        if str(t.get("transaction_date", "")).startswith(month_str)
        and t.get("business_or_personal") != "personal"
    ]

    by_category: dict[str, float] = {}
    deductible_total: float = 0.0
    total: float = 0.0

    for tx in month_txns:
        amt: float = float(tx.get("amount", 0) or 0)
        cat: str = str(tx.get("category") or "uncategorized")
        by_category[cat] = by_category.get(cat, 0.0) + amt
        total += amt
        pct = get_deductible_pct(tx)
        deductible_total += amt * pct / 100

    # YTD deductible — all transactions from year start through end of requested month
    _parts = month_str.split("-")
    yr, mo = int(_parts[0]), int(_parts[1])
    last_day = calendar.monthrange(yr, mo)[1]
    ytd_end = f"{month_str}-{last_day:02d}"
    ytd_txns = [
        t for t in transactions
        if str(t.get("transaction_date", "")) <= ytd_end
        and t.get("business_or_personal") != "personal"
    ]
    ytd_deductible: float = 0.0
    for t in ytd_txns:
        t_amt: float = float(t.get("amount", 0) or 0)
        t_pct = get_deductible_pct(t)
        ytd_deductible += t_amt * t_pct / 100

    # Income for the month
    month_income: float = sum(
        float(r.get("amount", 0) or 0)
        for r in income_records
        if str(r.get("date", "")).startswith(month_str)
    )
    ytd_income: float = sum(
        float(r.get("amount", 0) or 0)
        for r in income_records
        if str(r.get("date", "")) <= ytd_end
    )

    # Mileage for the month
    month_miles: float = sum(
        float(r.get("miles", 0) or 0)
        for r in mileage_records
        if str(r.get("date", "")).startswith(month_str)
    )
    month_mileage_deduction: float = sum(
        float(r.get("deductible_amount", 0) or 0)
        for r in mileage_records
        if str(r.get("date", "")).startswith(month_str)
    )

    dt = datetime.strptime(month_str, "%Y-%m")
    month_label = dt.strftime("%B %Y")

    return {
        "month":                     month_label,
        "transaction_count":         len(month_txns),
        "total_expenses":            _r2(total),
        "deductible_total":          _r2(deductible_total),
        "by_category":               {k: _r2(v) for k, v in sorted(by_category.items())},
        "missing_receipts":          sum(1 for t in month_txns if not t.get("receipt_matched")),
        "flagged":                   sum(1 for t in month_txns if t.get("review_required")),
        "ytd_deductible":            _r2(ytd_deductible),
        "month_income":              _r2(month_income),
        "ytd_income":                _r2(ytd_income),
        "month_miles":               _r2(month_miles),
        "month_mileage_deduction":   _r2(month_mileage_deduction),
    }


def snooze_reminder(days: int, snooze_path: Path) -> None:
    until = date.today() + timedelta(days=days)
    with open(snooze_path, "w") as f:
        json.dump({"until": str(until)}, f)
    print(json.dumps({"snoozed_until": str(until)}))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode")

    check_p = sub.add_parser("check")
    check_p.add_argument("ledger")

    audit_p = sub.add_parser("audit")
    audit_p.add_argument("ledger")
    audit_p.add_argument("--vendors",  default="", help="Path to vendors.json for W-9 check")
    audit_p.add_argument("--mileage",  default="", help="Path to mileage.json for log completeness check")

    sum_p = sub.add_parser("summary")
    sum_p.add_argument("ledger")
    sum_p.add_argument("--month",   help="YYYY-MM format")
    sum_p.add_argument("--income",  default="", help="Path to income.json")
    sum_p.add_argument("--mileage", default="", help="Path to mileage.json")

    snooze_p = sub.add_parser("snooze")
    snooze_p.add_argument("days", type=int)

    args = ap.parse_args()

    if args.mode == "snooze":
        snooze_reminder(args.days, Path(SNOOZE_FILE))
        return

    if not hasattr(args, "ledger") or not args.ledger:
        ap.print_help()
        sys.exit(1)

    transactions = load_ledger(args.ledger)
    snooze_path  = Path(SNOOZE_FILE)

    if args.mode == "check":
        result = check_reminder(transactions, snooze_path)

    elif args.mode == "audit":
        vendors_list  = load_json_file(args.vendors)  if args.vendors  else []
        mileage_list  = load_json_file(args.mileage)  if args.mileage  else []
        result = full_audit(transactions, vendors=vendors_list, mileage_records=mileage_list)

    elif args.mode == "summary":
        income_list  = load_json_file(args.income)  if args.income  else []
        mileage_list = load_json_file(args.mileage) if args.mileage else []
        result = monthly_summary(
            transactions,
            month=getattr(args, "month", None),
            income_records=income_list,
            mileage_records=mileage_list,
        )

    else:
        ap.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
