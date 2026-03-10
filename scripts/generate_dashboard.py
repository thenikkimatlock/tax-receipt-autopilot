#!/usr/bin/env python3
"""
generate_dashboard.py
---------------------
Reads your Tax Receipt Autopilot JSON files and generates a standalone
dashboard.html in your tax folder. Open it in any browser — no server needed.

Usage:
    python3 generate_dashboard.py
    python3 generate_dashboard.py --config ../config-2025.json
    python3 generate_dashboard.py --output ~/Desktop/tax-dashboard.html

Template
--------
The HTML/CSS/JS template lives in a separate file:
    scripts/templates/dashboard.html

Substitution points in the template (replaced at render time):
    {{TAX_YEAR}}    — replaced with the tax year string (e.g. "2026")
    {{GENERATED}}   — replaced with the human-readable generation timestamp
    %%DATA_JSON%%   — replaced with the full JSON data blob (window.DATA)

To edit the dashboard appearance: open templates/dashboard.html directly in
any editor with HTML/CSS/JS syntax highlighting. The Python data-preparation
logic (compute_data) is independent of the template and fully unit-tested.

If you add a new data field, update compute_data() to include it in the
returned dict, then reference it as DATA.your_field in the JS template.
A missed reference produces a blank chart rather than a crash — test by
running the script against a real or sample ledger and opening the output.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ── IRS MILEAGE RATES ────────────────────────────────────────────────────────
MILEAGE_RATES = {2025: 0.70, 2026: 0.725}

# ── FEDERAL INCOME TAX BRACKETS (single filer) ───────────────────────────────
# Source: IRS Rev. Proc. 2024-61 (2025), OBBBA 2025 adjustments (2026)
# Each tuple: (upper_bound_of_bracket, marginal_rate)
FEDERAL_BRACKETS: dict[int, list] = {
    2025: [
        (11_925,       0.10),
        (48_475,       0.12),
        (103_350,      0.22),
        (197_300,      0.24),
        (250_525,      0.32),
        (626_350,      0.35),
        (float("inf"), 0.37),
    ],
    2026: [
        (12_400,       0.10),
        (50_400,       0.12),
        (105_700,      0.22),
        (201_775,      0.24),
        (256_225,      0.32),
        (640_600,      0.35),
        (float("inf"), 0.37),
    ],
}

# Standard deduction (single filer): 2025 = $15,750 | 2026 = $16,100 (OBBBA)
STANDARD_DEDUCTIONS: dict[int, float] = {2025: 15_750.0, 2026: 16_100.0}


def _calc_income_tax(taxable_income: float, brackets: list) -> float:
    """Apply marginal federal income tax brackets to the given taxable income."""
    tax = 0.0
    prev = 0.0
    for upper, rate in brackets:
        if taxable_income <= prev:
            break
        income_in_band = min(taxable_income, upper) - prev
        tax += income_in_band * rate
        prev = upper
    return max(0.0, tax)

# ── LABELS ───────────────────────────────────────────────────────────────────
CATEGORY_LABELS = {
    "software_subscriptions": "Software & Subscriptions",
    "marketing_advertising":  "Marketing & Advertising",
    "office_supplies":        "Office Supplies",
    "equipment":              "Equipment",
    "travel":                 "Travel",
    "vehicle_mileage":        "Vehicle / Mileage",
    "meals_entertainment":    "Meals & Entertainment",
    "professional_services":  "Professional Services",
    "utilities":              "Utilities",
    "rent_lease":             "Rent & Lease",
    "education_training":     "Education & Training",
    "contractor_payments":    "Contractor Payments",
    "insurance":              "Insurance",
    "bank_fees":              "Bank Fees",
    "home_office":            "Home Office",
    "other_business":         "Other Business",
    "personal":               "Personal (Non-Deductible)",
}
INCOME_LABELS = {
    "services":              "Services / Consulting",
    "product_sales":         "Product Sales",
    "affiliate_commissions": "Affiliate Commissions",
    "course_revenue":        "Course Revenue",
    "ad_revenue":            "Ad Revenue",
    "subscription_revenue":  "Subscription Revenue",
    "refund_received":       "Refunds Received",
    "other_income":          "Other Income",
}


# ── DATA LOADING ─────────────────────────────────────────────────────────────

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        print(f"ERROR: Config not found at {config_path}", file=sys.stderr)
        print("Run the Tax Receipt Autopilot setup first.", file=sys.stderr)
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def load_json(path_str: str) -> list:
    p = Path(path_str).expanduser().resolve()
    if not p.exists():
        return []
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def receipt_status(tx: dict) -> str:
    if tx.get("receipt_matched"):
        return "matched"
    if tx.get("review_required"):
        return "review"
    return "missing"


# ── DATA COMPUTATION ─────────────────────────────────────────────────────────

def compute_data(config: dict, ledger: list, income: list, mileage: list) -> dict:
    tax_year = str(config.get("tax_year", datetime.now().year))
    try:
        mileage_rate = MILEAGE_RATES.get(int(tax_year), 0.70)
    except (ValueError, TypeError):
        mileage_rate = 0.70

    # ── LEDGER ───────────────────────────────────────────────────────────────
    transactions = []
    by_month_exp = defaultdict(lambda: {"expenses": 0.0, "deductible": 0.0, "count": 0})
    by_category  = defaultdict(lambda: {"total": 0.0, "deductible": 0.0, "count": 0})
    by_day       = defaultdict(float)

    total_expenses   = 0.0
    total_deductible = 0.0
    missing_receipts = 0
    review_count     = 0

    for tx in ledger:
        amt     = float(tx.get("amount") or 0)
        is_ded  = bool(tx.get("deductible"))
        ded_pct = int(tx.get("deductible_pct", 100) if is_ded else 0)
        ded_amt = round(amt * ded_pct / 100, 2)

        raw_date = tx.get("transaction_date") or tx.get("date") or ""
        try:
            d = datetime.strptime(raw_date[:10], "%Y-%m-%d")
            month_key = d.strftime("%Y-%m")
            day_key   = raw_date[:10]
        except (ValueError, TypeError):
            month_key = ""
            day_key   = ""

        cat    = tx.get("category") or "other_business"
        status = receipt_status(tx)

        if status == "missing":
            missing_receipts += 1
        if tx.get("review_required"):
            review_count += 1

        total_expenses   += amt
        total_deductible += ded_amt

        if month_key:
            by_month_exp[month_key]["expenses"]   += amt
            by_month_exp[month_key]["deductible"] += ded_amt
            by_month_exp[month_key]["count"]      += 1
        if day_key:
            by_day[day_key] += amt

        by_category[cat]["total"]      += amt
        by_category[cat]["deductible"] += ded_amt
        by_category[cat]["count"]      += 1

        transactions.append({
            "id":               tx.get("id") or "",
            "date":             day_key,
            "vendor":           tx.get("vendor") or "",
            "category":         cat,
            "category_label":   CATEGORY_LABELS.get(cat, cat),
            "amount":           round(amt, 2),
            "deductible":       is_ded,
            "deductible_pct":   ded_pct,
            "deductible_amount": ded_amt,
            "receipt_status":   status,
            "notes":            tx.get("notes") or "",
            "review_required":  bool(tx.get("review_required")),
        })

    transactions.sort(key=lambda t: t["date"], reverse=True)

    # ── INCOME ───────────────────────────────────────────────────────────────
    income_records = []
    income_by_cat  = defaultdict(lambda: {"total": 0.0, "count": 0})
    by_month_inc   = defaultdict(float)
    total_income   = 0.0

    for rec in income:
        amt      = float(rec.get("amount") or 0)
        raw_date = rec.get("date") or ""
        try:
            d = datetime.strptime(raw_date[:10], "%Y-%m-%d")
            month_key = d.strftime("%Y-%m")
            day_key   = raw_date[:10]
        except (ValueError, TypeError):
            month_key = ""
            day_key   = ""

        cat = rec.get("category") or "other_income"
        total_income += amt
        income_by_cat[cat]["total"] += amt
        income_by_cat[cat]["count"] += 1
        if month_key:
            by_month_inc[month_key] += amt

        income_records.append({
            "id":           rec.get("id") or "",
            "date":         day_key,
            "source":       rec.get("source") or "",
            "description":  rec.get("description") or "",
            "category":     cat,
            "category_label": INCOME_LABELS.get(cat, cat),
            "amount":       round(amt, 2),
            "reported_1099": bool(rec.get("1099_reported")),
            "review_required": bool(rec.get("review_required")),
        })

    income_records.sort(key=lambda r: r["date"], reverse=True)

    # ── MILEAGE ──────────────────────────────────────────────────────────────
    mileage_records = []
    total_miles = 0.0
    total_mileage_ded = 0.0

    for mi in mileage:
        raw_miles = float(mi.get("miles") or 0)
        is_rt     = bool(mi.get("round_trip"))
        rate      = float(mi.get("rate_per_mile") or mileage_rate)
        ded       = float(mi.get("deductible_amount") or 0)
        actual_miles = raw_miles * (2 if is_rt else 1)
        if ded == 0 and actual_miles > 0:
            ded = round(actual_miles * rate, 2)

        total_miles      += actual_miles
        total_mileage_ded += ded

        raw_date = mi.get("date") or ""
        mileage_records.append({
            "id":       mi.get("id") or "",
            "date":     raw_date[:10] if raw_date else "",
            "start":    mi.get("start_location") or "",
            "end":      mi.get("end_location") or "",
            "purpose":  mi.get("business_purpose") or "",
            "miles":    round(actual_miles, 1),
            "round_trip": is_rt,
            "deductible_amount": round(ded, 2),
        })

    mileage_records.sort(key=lambda r: r["date"], reverse=True)

    # ── QUARTERLY ESTIMATE ───────────────────────────────────────────────────
    net_profit = total_income - total_deductible - total_mileage_ded

    try:
        year_int = int(tax_year)
    except (ValueError, TypeError):
        year_int = 2025

    brackets     = FEDERAL_BRACKETS.get(year_int, FEDERAL_BRACKETS[2025])
    std_deduction = STANDARD_DEDUCTIONS.get(year_int, 15_750.0)

    # SE tax: net profit × 92.35% × 15.3%
    se_tax_est = max(0.0, round(net_profit * 0.9235 * 0.153, 2))
    # Deductions that reduce taxable income for federal income tax
    se_deduction  = round(se_tax_est * 0.50, 2)                          # IRS §164(f)
    qbid          = round(max(0.0, net_profit) * 0.20, 2) if net_profit > 0 else 0.0  # §199A
    taxable_income = max(0.0, net_profit - se_deduction - qbid - std_deduction)
    fed_income_est = max(0.0, round(_calc_income_tax(taxable_income, brackets), 2))
    total_tax_est  = round(se_tax_est + fed_income_est, 2)

    # ── ALERTS ───────────────────────────────────────────────────────────────
    alerts = []
    if missing_receipts > 0:
        alerts.append({"type": "warning", "msg": f"{missing_receipts} transaction{'s' if missing_receipts != 1 else ''} missing receipt documentation."})
    if review_count > 0:
        alerts.append({"type": "warning", "msg": f"{review_count} transaction{'s' if review_count != 1 else ''} flagged for accountant review."})
    if total_income == 0 and len(ledger) > 0:
        alerts.append({"type": "info", "msg": "No income recorded yet. Add income entries to see net profit and tax estimates."})
    if net_profit < 0 and total_income > 0:
        alerts.append({"type": "info", "msg": f"Net loss of ${abs(net_profit):,.2f} YTD. Deductions exceed income — verify classification with accountant."})
    if total_mileage_ded > 0:
        alerts.append({"type": "info", "msg": f"Mileage: {total_miles:.1f} miles = ${total_mileage_ded:,.2f} deduction (@ ${mileage_rate}/mi). Report on Schedule C, Line 9."})
    if net_profit > 0:
        alerts.append({"type": "info", "msg": f"Tax estimate uses single filer {tax_year} federal brackets, after SE deduction, QBID (20%), and standard deduction. Does not include state taxes, credits, or other income. Married filing jointly? Your combined income may push you into higher brackets — say 'help me estimate my Q[X] payment' for an accurate MFJ calculation."})
        alerts.append({"type": "info", "msg": "This dashboard estimate is a working approximation. For a precise quarterly payment amount, say 'help me estimate my Q[X] payment' — that flow asks for filing status, spouse income, state, and prior payments."})

    # ── MONTHS ───────────────────────────────────────────────────────────────
    all_months = sorted(set(list(by_month_exp.keys()) + list(by_month_inc.keys())))

    return {
        "meta": {
            "business_name": config.get("business_name") or "My Business",
            "tax_year":      tax_year,
            "entity_type":   config.get("entity_type") or "",
            "generated":     datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            "ledger_path":   config.get("ledger_path") or "",
            "mileage_rate":  mileage_rate,
        },
        "summary": {
            "total_expenses":    round(total_expenses, 2),
            "deductible_total":  round(total_deductible, 2),
            "income_total":      round(total_income, 2),
            "mileage_miles":     round(total_miles, 1),
            "mileage_deduction": round(total_mileage_ded, 2),
            "net_profit":        round(net_profit, 2),
            "se_tax_est":        se_tax_est,
            "fed_income_est":    fed_income_est,
            "total_tax_est":     total_tax_est,
            "missing_receipts":  missing_receipts,
            "review_required":   review_count,
            "tx_count":          len(transactions),
            "income_count":      len(income_records),
            "mileage_count":     len(mileage_records),
        },
        "by_month": {
            k: {
                "expenses":   round(by_month_exp[k]["expenses"], 2),
                "deductible": round(by_month_exp[k]["deductible"], 2),
                "income":     round(by_month_inc.get(k, 0.0), 2),
                "count":      by_month_exp[k]["count"],
            }
            for k in all_months
        },
        "by_category": {
            k: {
                "label":     CATEGORY_LABELS.get(k, k),
                "total":     round(v["total"], 2),
                "deductible": round(v["deductible"], 2),
                "count":     v["count"],
            }
            for k, v in sorted(by_category.items(), key=lambda x: -x[1]["total"])
        },
        "income_by_category": {
            k: {
                "label": INCOME_LABELS.get(k, k),
                "total": round(v["total"], 2),
                "count": v["count"],
            }
            for k, v in sorted(income_by_cat.items(), key=lambda x: -x[1]["total"])
        },
        "transactions":    transactions,
        "income_records":  income_records,
        "mileage_records": mileage_records,
        "heatmap":         {k: round(v, 2) for k, v in by_day.items()},
        "alerts":          alerts,
        "all_months":      all_months,
    }


# ── HTML TEMPLATE ─────────────────────────────────────────────────────────────

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "dashboard.html"


# ── HTML GENERATION ───────────────────────────────────────────────────────────

def render_html(data: dict) -> str:
    if not _TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Dashboard template not found: {_TEMPLATE_PATH}\n"
            "Ensure the tax-receipt-autopilot skill folder is intact with "
            "scripts/templates/dashboard.html present."
        )
    data_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    html = _TEMPLATE_PATH.read_text(encoding="utf-8")
    html = html.replace('{{TAX_YEAR}}', data['meta']['tax_year'])
    html = html.replace('{{GENERATED}}', data['meta']['generated'])
    html = html.replace('%%DATA_JSON%%', data_json)
    return html


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='Generate Tax Receipt Autopilot dashboard')
    ap.add_argument('--config', default='', help='Path to config file (default: <skill_dir>/config.json)')
    ap.add_argument('--output', default='', help='Output HTML path (default: <tax_folder>/dashboard.html)')
    args = ap.parse_args()

    # Default: config.json lives in the skill root (parent of scripts/)
    skill_dir = Path(__file__).resolve().parent.parent
    config_path = Path(args.config).expanduser() if args.config else skill_dir / 'config.json'
    config = load_config(config_path)

    ledger  = load_json(config.get('ledger_path', ''))
    income  = load_json(config.get('income_path', ''))
    mileage = load_json(config.get('mileage_path', ''))

    print(f'Loaded: {len(ledger)} expenses, {len(income)} income records, {len(mileage)} mileage trips')

    data = compute_data(config, ledger, income, mileage)
    html = render_html(data)

    if args.output:
        out_path = Path(args.output).expanduser().resolve()
    else:
        ledger_path = Path(config.get('ledger_path', '')).expanduser()
        out_path = ledger_path.parent / 'dashboard.html'

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    s = data['summary']
    print(f'\nDashboard generated: {out_path}')
    print('─' * 50)
    print(f'  Expenses:    ${s["total_expenses"]:>10,.2f}  ({s["tx_count"]} transactions)')
    print(f'  Deductible:  ${s["deductible_total"]:>10,.2f}')
    print(f'  Income:      ${s["income_total"]:>10,.2f}  ({s["income_count"]} records)')
    print(f'  Mileage:     ${s["mileage_deduction"]:>10,.2f}  ({s["mileage_miles"]:.1f} miles)')
    print(f'  Net profit:  ${s["net_profit"]:>10,.2f}')
    print(f'  Est. tax:    ${s["total_tax_est"]:>10,.2f}')
    if s['missing_receipts']:
        print(f'  Missing receipts: {s["missing_receipts"]}')
    if s['review_required']:
        print(f'  Needs review:     {s["review_required"]}')
    print()
    print('Open in browser to view dashboard.')


if __name__ == '__main__':
    main()
