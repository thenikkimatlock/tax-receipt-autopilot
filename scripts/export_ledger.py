#!/usr/bin/env python3
"""
export_ledger.py
----------------
Generates accountant-ready exports from the Tax Receipt Autopilot ledger.

Produces:
  1. Full categorized CSV  (all business transactions)
  2. Summary CSV           (totals by category)
  3. Flagged items CSV     (review_required = True)
  4. Missing receipts CSV  (receipt_matched = False)
  5. Accountant cover note (text file)

Usage:
    python3 export_ledger.py <ledger.json> --year 2026 --name "Acme LLC" [--output-dir ./export]
    python3 export_ledger.py <ledger.json> --year 2026 --name "Acme LLC" --income <income.json> --mileage <mileage.json>

Input: JSON array of transaction dicts
Output: Directory of CSV files + cover note
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Category display names and schedule references
# ---------------------------------------------------------------------------
CATEGORY_META = {
    "software_subscriptions":  {"display": "Software & Subscriptions",       "schedule": "Sch C Line 18"},
    "marketing_advertising":   {"display": "Marketing & Advertising",        "schedule": "Sch C Line 8"},
    "office_supplies":         {"display": "Office Supplies",                "schedule": "Sch C Line 18"},
    "equipment":               {"display": "Equipment / Depreciation",       "schedule": "Sch C Line 13"},
    "travel":                  {"display": "Business Travel",                "schedule": "Sch C Line 24a"},
    "vehicle_mileage":         {"display": "Vehicle Mileage (Standard Rate)", "schedule": "Sch C Line 9"},
    "meals_entertainment":     {"display": "Meals (see deductible %)",       "schedule": "Sch C Line 24b"},
    "professional_services":   {"display": "Professional Services",          "schedule": "Sch C Line 17"},
    "utilities":               {"display": "Utilities",                      "schedule": "Sch C Line 25"},
    "rent_lease":              {"display": "Rent / Lease",                   "schedule": "Sch C Line 20b"},
    "education_training":      {"display": "Education & Training",           "schedule": "Sch C Line 27a"},
    "contractor_payments":     {"display": "Contract Labor",                 "schedule": "Sch C Line 11"},
    "insurance":               {"display": "Insurance",                      "schedule": "Sch C Line 15"},
    "bank_fees":               {"display": "Bank & Processing Fees",         "schedule": "Sch C Line 27a"},
    "home_office":             {"display": "Home Office",                    "schedule": "Form 8829"},
    "other_business":          {"display": "Other Business Expenses",        "schedule": "Sch C Line 27a"},
    "personal":                {"display": "Personal (Non-deductible)",      "schedule": "N/A"},
}

DEPRECIATION_FLAG = {"equipment"}  # May need Section 179 review


def load_transactions(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict) and "clean" in data:
        return data["clean"]  # Output from detect_duplicates.py
    if isinstance(data, list):
        return data
    raise ValueError("Unrecognized input format")


def load_json_file(path: str) -> list[dict]:
    """Load a JSON array file, returning [] if file doesn't exist or is empty."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        with open(p) as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"WARNING: {p.name} does not contain a JSON array — skipping. Check the file format.", file=sys.stderr)
            return []
        return data
    except json.JSONDecodeError as e:
        print(f"WARNING: {p.name} contains invalid JSON and could not be read ({e}). "
              f"This file will be treated as empty — income, mileage, or vendor totals "
              f"may show $0. Restore from backup or re-initialize the file.", file=sys.stderr)
        return []
    except OSError as e:
        print(f"WARNING: Could not open {p.name} ({e}). File will be treated as empty.", file=sys.stderr)
        return []


def format_amount(amount) -> str:
    try:
        return f"${float(amount):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def get_deductible_pct(tx: dict) -> int:
    """
    Return the deductible percentage (0-100) for a transaction.

    Schema:
      deductible: true | false  — is this expense deductible at all?
      deductible_pct: int       — what percentage is deductible (0-100)?
                                  defaults to 100 when deductible=true.

    50% meals rule: meals_entertainment transactions should have deductible_pct=50
    stored on the record. No category-based magic here — the stored value is the truth.
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
        pct_int = int(pct)
        return max(0, min(100, pct_int))
    except (TypeError, ValueError):
        return 100


def write_csv(path: "str | Path", headers: list[str], rows: list[list]) -> int:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return len(rows)


def generate_cover_html(
    output_dir: Path,
    prefix: str,
    business_name: str,
    year: str,
    full_count: int,
    grand_total: float,
    grand_deductible: float,
    gross_income: float,
    net_profit_est: "float | None",
    total_miles: float,
    total_mileage_deduction: float,
    flagged_count: int,
    missing_count: int,
    income_records: list[dict],
    mileage_records: list[dict],
    meals_total: float,
    meals_deductible: float,
    equipment_total: float,
    contractor_total: float,
    cat_totals: "dict[str, dict]",
) -> Path:
    """Generate a print-ready HTML cover note. Open in any browser → Ctrl+P → Save as PDF."""
    today_str = datetime.now().strftime("%B %d, %Y")
    nec_threshold = "$600" if int(year) <= 2025 else "$2,000"

    # Summary rows
    summary_rows = [
        ("Total Business Transactions", str(full_count), False),
        ("Total Business Spending", format_amount(grand_total), False),
        ("Estimated Deductible Total", format_amount(grand_deductible), False),
        ("Transactions Missing Receipts", str(missing_count), missing_count > 0),
        ("Transactions Flagged for Review", str(flagged_count), flagged_count > 0),
    ]
    if gross_income > 0:
        summary_rows.append(("Gross Business Income", format_amount(gross_income), False))
        if net_profit_est is not None:
            summary_rows.append(("Est. Schedule C Net Profit", format_amount(net_profit_est), False))
    if total_miles > 0:
        summary_rows.append(("Total Business Miles", f"{total_miles:.1f} miles", False))
        summary_rows.append(("Mileage Deduction", format_amount(total_mileage_deduction), False))

    summary_html = "\n      ".join(
        f'<tr{"" if not warn else " class=\"warn-row\""}><td>{label}</td>'
        f'<td class="val">{value}</td></tr>'
        for label, value, warn in summary_rows
    )

    # Category breakdown rows
    cat_rows_html = ""
    for cat in sorted(cat_totals.keys()):
        meta = CATEGORY_META.get(cat, {"display": cat, "schedule": ""})
        data = cat_totals[cat]
        badge = ""
        if cat == "meals_entertainment":
            badge = ' <span class="badge">50% rule</span>'
        elif cat in DEPRECIATION_FLAG:
            badge = ' <span class="badge">Sec. 179 review</span>'
        cat_rows_html += (
            f"<tr><td>{meta['display']}{badge}</td>"
            f"<td>{meta['schedule']}</td>"
            f'<td class="num">{data["count"]}</td>'
            f'<td class="num">{format_amount(data["total"])}</td>'
            f'<td class="num">{format_amount(data["deductible_total"])}</td></tr>\n'
        )

    # Notes sections
    notes_parts = []
    if meals_total > 0:
        notes_parts.append(f"""
    <div class="note-block">
      <h3>Meals &amp; Entertainment &mdash; {format_amount(meals_total)} total</h3>
      <ul>
        <li>50% deductible limitation applies per TCJA 2018</li>
        <li>Deductible portion calculated as {format_amount(meals_deductible)}</li>
        <li>Verify business purpose documentation for each meal</li>
      </ul>
    </div>""")
    if equipment_total > 0:
        notes_parts.append(f"""
    <div class="note-block">
      <h3>Equipment &mdash; {format_amount(equipment_total)} total</h3>
      <ul>
        <li>Review for Section 179 expensing vs. MACRS depreciation</li>
        <li>Confirm business-use percentage for any mixed-use items</li>
        <li>Items over $2,500 may need to be capitalized</li>
      </ul>
    </div>""")
    if contractor_total > 0:
        notes_parts.append(f"""
    <div class="note-block">
      <h3>Contractor Payments &mdash; {format_amount(contractor_total)} total</h3>
      <ul>
        <li>For {year} payments: contractors paid {nec_threshold}+ require a 1099-NEC</li>
        <li>Confirm W-9 is on file for each contractor</li>
      </ul>
    </div>""")
    if missing_count > 0:
        notes_parts.append(f"""
    <div class="note-block warn-block">
      <h3>Missing Receipts &mdash; {missing_count} transactions</h3>
      <ul>
        <li>See <code>{prefix}-missing-receipts.csv</code> for full list</li>
        <li>IRS requires substantiation for all business deductions</li>
        <li>Client to provide receipts or written contemporaneous records</li>
      </ul>
    </div>""")
    if flagged_count > 0:
        notes_parts.append(f"""
    <div class="note-block warn-block">
      <h3>Flagged for Review &mdash; {flagged_count} transactions</h3>
      <ul>
        <li>See <code>{prefix}-flagged.csv</code> for full list</li>
        <li>Each item has a Review Reason column explaining the concern</li>
      </ul>
    </div>""")
    # 1099-K threshold HTML — same year logic as the text cover note above
    _html_year_int = int(year)
    if _html_year_int <= 2023:
        _k_html_li = (
            f"<li>For tax year {year}: threshold is $20,000 AND more than 200 transactions per platform "
            f"(pre-ARPA original threshold; IRS extended transition relief through {year}) &mdash; both conditions must be met</li>"
        )
    elif _html_year_int == 2024:
        _k_html_li = (
            f"<li>For tax year {year}: threshold is $5,000, no transaction minimum "
            f"(IRS Notice 2024-85 &mdash; enforced threshold for the 2024 filing season)</li>\n"
            f"        <li>Note: OBBBA (signed July 4, 2025) retroactively set the 2024 statutory threshold at "
            f"$20,000 AND 200 transactions, but TPSOs had already filed 2024 Forms 1099-K under the $5,000 rule "
            f"before OBBBA passed. No re-filing required &mdash; reconcile any 1099-K received against income records.</li>"
        )
    else:  # 2025+
        _k_html_li = (
            f"<li>For tax year {year}: threshold is $20,000 AND more than 200 transactions per platform "
            f"(One Big Beautiful Bill Act, signed July 4, 2025 &mdash; both conditions must be met)</li>"
        )
    notes_parts.append(f"""
    <div class="note-block">
      <h3>Form 1099-K &mdash; Payment Networks (PayPal, Stripe, Venmo, Square)</h3>
      <ul>
        {_k_html_li}
        <li>Threshold applies per platform, not combined across platforms</li>
        <li>Some states have lower thresholds &mdash; verify client&apos;s state of residence</li>
        <li>All income is taxable regardless of whether a 1099-K was issued</li>
      </ul>
    </div>""")
    notes_parts.append("""
    <div class="note-block">
      <h3>Home Office</h3>
      <ul>
        <li>If client claims home office deduction, Form 8829 is required</li>
        <li>Confirm exclusive and regular use, square footage calculation</li>
      </ul>
    </div>""")
    notes_parts.append("""
    <div class="note-block">
      <h3>Estimated Quarterly Taxes</h3>
      <ul>
        <li>Confirm quarterly estimated tax payments were made on time</li>
        <li>Q1: April&nbsp;15 &nbsp;&bull;&nbsp; Q2: June&nbsp;15 &nbsp;&bull;&nbsp; Q3: September&nbsp;15 &nbsp;&bull;&nbsp; Q4: January&nbsp;15</li>
      </ul>
    </div>""")
    notes_html = "".join(notes_parts)

    # Files list
    file_items = [
        f"<code>{prefix}-full.csv</code> &mdash; Complete ledger, all business transactions",
        f"<code>{prefix}-summary.csv</code> &mdash; Totals by IRS category with schedule references",
        f"<code>{prefix}-flagged.csv</code> &mdash; {flagged_count} transactions requiring review",
        f"<code>{prefix}-missing-receipts.csv</code> &mdash; {missing_count} transactions without receipts",
        f"<code>{prefix}-cover-note.txt</code> &mdash; Plain text version of this document",
        f"<code>{prefix}-cover-note.html</code> &mdash; This document (open in browser &rarr; Ctrl+P &rarr; Save as PDF)",
    ]
    if income_records:
        file_items.append(f"<code>{prefix}-income.csv</code> &mdash; Gross income log ({len(income_records)} entries)")
    if mileage_records:
        file_items.append(
            f"<code>{prefix}-mileage-log.csv</code> &mdash; Mileage log "
            f"({len(mileage_records)} trips, {total_miles:.1f} miles)"
        )
    files_html = "\n    ".join(f"<li>{item}</li>" for item in file_items)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Tax Export Cover Note &mdash; {business_name} {year}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: Georgia, "Times New Roman", serif;
      font-size: 11.5pt;
      line-height: 1.65;
      color: #1a1a1a;
      max-width: 760px;
      margin: 2cm auto;
      padding: 0 1cm;
    }}
    .doc-header {{
      border-bottom: 3px solid #1a1a1a;
      padding-bottom: 12px;
      margin-bottom: 22px;
    }}
    h1 {{ font-size: 17pt; letter-spacing: -0.3px; margin-bottom: 5px; }}
    .meta {{ font-size: 10pt; color: #555; }}
    .print-hint {{ font-size: 9pt; color: #888; margin-top: 4px; }}
    h2 {{
      font-size: 11pt;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      border-bottom: 1px solid #aaa;
      padding-bottom: 3px;
      margin: 1.5em 0 0.6em;
    }}
    h3 {{ font-size: 10.5pt; margin: 0 0 0.3em; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 10.5pt; margin: 0.4em 0; }}
    th {{
      text-align: left;
      border-bottom: 2px solid #333;
      padding: 4px 8px;
      font-size: 9pt;
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }}
    td {{ padding: 4px 8px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }}
    .summary-table td:first-child {{ color: #444; width: 62%; }}
    .summary-table td.val {{ font-weight: bold; }}
    .warn-row td {{ color: #b03a2e; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .badge {{
      display: inline-block;
      font-size: 8pt;
      font-family: Arial, sans-serif;
      background: #f0f0f0;
      border: 1px solid #ccc;
      border-radius: 3px;
      padding: 0 4px;
      margin-left: 5px;
      vertical-align: middle;
    }}
    .note-block {{ margin: 0.7em 0; padding: 0.5em 0.8em; border-left: 3px solid #ccc; }}
    .warn-block {{ border-left-color: #b03a2e; }}
    .warn-block h3 {{ color: #b03a2e; }}
    ul {{ padding-left: 1.3em; margin: 0.2em 0; }}
    li {{ margin: 0.1em 0; }}
    ol {{ padding-left: 1.3em; }}
    code {{
      font-family: "Courier New", monospace;
      font-size: 9.5pt;
      background: #f5f5f5;
      padding: 1px 4px;
      border-radius: 2px;
    }}
    .footer {{
      margin-top: 2.5em;
      padding-top: 10px;
      border-top: 1px solid #ccc;
      font-size: 9pt;
      color: #888;
      text-align: center;
    }}
    @media print {{
      body {{ margin: 0; padding: 0.5cm; max-width: 100%; font-size: 10.5pt; }}
      @page {{ margin: 1.8cm; size: letter; }}
      .print-hint {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="doc-header">
    <h1>Tax Export &mdash; Accountant Cover Note</h1>
    <div class="meta">
      <strong>{business_name}</strong> &nbsp;&bull;&nbsp; Tax Year {year}
      &nbsp;&bull;&nbsp; Prepared {today_str}
    </div>
    <div class="print-hint">To send as PDF: File &rarr; Print &rarr; Save as PDF (or Ctrl+P)</div>
  </div>

  <h2>Summary</h2>
  <table class="summary-table">
    <tbody>
      {summary_html}
    </tbody>
  </table>

  <h2>Expenses by Category</h2>
  <table>
    <thead>
      <tr>
        <th>Category</th>
        <th>IRS Schedule</th>
        <th class="num">Count</th>
        <th class="num">Total Spent</th>
        <th class="num">Est. Deductible</th>
      </tr>
    </thead>
    <tbody>
      {cat_rows_html}
    </tbody>
  </table>

  <h2>Notes for Review</h2>
  {notes_html}

  <h2>Files Included</h2>
  <ol>
    {files_html}
  </ol>

  <div class="footer">
    Generated by Tax Receipt Autopilot &nbsp;&bull;&nbsp;
    These are federal estimates. State tax treatment may differ. Verify with your accountant.
  </div>
</body>
</html>"""

    html_path = output_dir / f"{prefix}-cover-note.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path


def generate_export(
    transactions: list[dict],
    year: str,
    business_name: str,
    output_dir: Path,
    income_records: list[dict] | None = None,
    mileage_records: list[dict] | None = None,
    html_cover: bool = False,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = business_name.replace(" ", "-").replace("/", "-")
    prefix = f"tax-export-{year}-{safe_name}"

    income_records = income_records or []
    mileage_records = mileage_records or []

    # -----------------------------------------------------------------------
    # Separate into buckets
    # -----------------------------------------------------------------------
    business_txns        = []
    flagged_txns         = []
    missing_receipt_txns = []

    for tx in transactions:
        biz = tx.get("business_or_personal", "review_required")
        if biz == "personal":
            continue
        if tx.get("review_required"):
            flagged_txns.append(tx)
        if not tx.get("receipt_matched"):
            missing_receipt_txns.append(tx)
        business_txns.append(tx)

    # -----------------------------------------------------------------------
    # 1. Full Categorized CSV
    # -----------------------------------------------------------------------
    full_headers = [
        "Date", "Vendor", "Amount", "Category", "Schedule Reference",
        "Business/Personal", "Deductible", "Deductible %", "Deductible Amount",
        "Receipt Matched", "Receipt Path", "Source", "Notes", "Review Required", "Review Reason",
    ]
    full_rows = []
    for tx in sorted(business_txns, key=lambda t: t.get("transaction_date", "")):
        cat  = tx.get("category", "")
        meta = CATEGORY_META.get(cat, {"display": cat, "schedule": ""})
        amt  = float(tx.get("amount", 0) or 0)
        pct  = get_deductible_pct(tx)
        ded_amt = amt * pct / 100

        full_rows.append([
            tx.get("transaction_date", ""),
            tx.get("vendor", ""),
            format_amount(amt),
            meta["display"],
            meta["schedule"],
            tx.get("business_or_personal", ""),
            "Yes" if pct > 0 else "No",
            f"{pct}%",
            format_amount(ded_amt),
            "Yes" if tx.get("receipt_matched") else "No",
            tx.get("receipt_path", "") or "",
            tx.get("source", ""),
            tx.get("notes", ""),
            "Yes" if tx.get("review_required") else "No",
            tx.get("review_reason", ""),
        ])
    full_count = write_csv(output_dir / f"{prefix}-full.csv", full_headers, full_rows)

    # -----------------------------------------------------------------------
    # 2. Summary by Category
    # -----------------------------------------------------------------------
    cat_totals: dict[str, dict] = defaultdict(
        lambda: {"total": 0.0, "count": 0, "deductible_total": 0.0}
    )

    for tx in business_txns:
        cat = tx.get("category", "other_business")
        amt = float(tx.get("amount", 0) or 0)
        pct = get_deductible_pct(tx)
        cat_totals[cat]["total"]           += amt
        cat_totals[cat]["count"]           += 1
        cat_totals[cat]["deductible_total"] += amt * pct / 100

    summary_headers = [
        "Category", "Schedule Reference", "Transaction Count",
        "Total Spent", "Est. Deductible Amount", "Notes",
    ]
    summary_rows = []
    grand_total      = 0.0
    grand_deductible = 0.0

    for cat in sorted(cat_totals.keys()):
        meta = CATEGORY_META.get(cat, {"display": cat, "schedule": ""})
        data = cat_totals[cat]
        notes = ""
        if cat == "meals_entertainment":
            notes = "50% deductible limitation applies (TCJA) — deductible_pct=50 stored per transaction"
        if cat in DEPRECIATION_FLAG:
            notes = "May qualify for Section 179 or MACRS depreciation — accountant review"
        summary_rows.append([
            meta["display"],
            meta["schedule"],
            data["count"],
            format_amount(data["total"]),
            format_amount(data["deductible_total"]),
            notes,
        ])
        grand_total      += data["total"]
        grand_deductible += data["deductible_total"]

    # Grand total row
    summary_rows.append(["", "", "", "", "", ""])
    summary_rows.append([
        "GRAND TOTAL", "", sum(d["count"] for d in cat_totals.values()),
        format_amount(grand_total), format_amount(grand_deductible), "",
    ])

    write_csv(output_dir / f"{prefix}-summary.csv", summary_headers, summary_rows)

    # -----------------------------------------------------------------------
    # 3. Flagged Transactions
    # -----------------------------------------------------------------------
    flag_headers = ["Date", "Vendor", "Amount", "Category", "Review Reason", "Notes"]
    flag_rows = [[
        tx.get("transaction_date", ""),
        tx.get("vendor", ""),
        format_amount(tx.get("amount", 0)),
        tx.get("category", ""),
        tx.get("review_reason", ""),
        tx.get("notes", ""),
    ] for tx in flagged_txns]
    write_csv(output_dir / f"{prefix}-flagged.csv", flag_headers, flag_rows)

    # -----------------------------------------------------------------------
    # 4. Missing Receipts
    # -----------------------------------------------------------------------
    missing_headers = ["Date", "Vendor", "Amount", "Category", "Source"]
    missing_rows = [[
        tx.get("transaction_date", ""),
        tx.get("vendor", ""),
        format_amount(tx.get("amount", 0)),
        tx.get("category", ""),
        tx.get("source", ""),
    ] for tx in missing_receipt_txns]
    write_csv(output_dir / f"{prefix}-missing-receipts.csv", missing_headers, missing_rows)

    # -----------------------------------------------------------------------
    # 5. Income Summary CSV (if income records provided)
    # -----------------------------------------------------------------------
    gross_income = 0.0
    if income_records:
        inc_headers = ["Date", "Source", "Payer", "Amount", "Form 1099?", "Notes"]
        inc_rows = []
        for rec in sorted(income_records, key=lambda r: r.get("date", "")):
            amt = float(rec.get("amount", 0) or 0)
            gross_income += amt
            inc_rows.append([
                rec.get("date", ""),
                rec.get("source", ""),
                rec.get("payer", ""),
                format_amount(amt),
                "Yes" if rec.get("1099_reported") else "No",
                rec.get("notes", ""),
            ])
        inc_rows.append(["", "", "TOTAL", format_amount(gross_income), "", ""])
        write_csv(output_dir / f"{prefix}-income.csv", inc_headers, inc_rows)

    # -----------------------------------------------------------------------
    # 6. Mileage Log CSV (if mileage records provided)
    # -----------------------------------------------------------------------
    total_miles        = 0.0
    total_mileage_deduction = 0.0
    if mileage_records:
        mil_headers = [
            "Date", "From", "To", "Business Purpose", "Miles",
            "Rate/Mile", "Deductible Amount", "Notes",
        ]
        mil_rows = []
        for rec in sorted(mileage_records, key=lambda r: r.get("date", "")):
            miles   = float(rec.get("miles", 0) or 0)
            ded_amt = float(rec.get("deductible_amount", 0) or 0)
            total_miles             += miles
            total_mileage_deduction += ded_amt
            mil_rows.append([
                rec.get("date", ""),
                rec.get("start_location", ""),
                rec.get("end_location", ""),
                rec.get("business_purpose", ""),
                f"{miles:.1f}",
                f"${rec.get('rate_per_mile', 0):.3f}",
                format_amount(ded_amt),
                rec.get("notes", ""),
            ])
        mil_rows.append(["", "", "", "TOTAL", f"{total_miles:.1f}", "", format_amount(total_mileage_deduction), ""])
        write_csv(output_dir / f"{prefix}-mileage-log.csv", mil_headers, mil_rows)

    # -----------------------------------------------------------------------
    # 7. Accountant Cover Note
    # -----------------------------------------------------------------------
    meals_total      = cat_totals.get("meals_entertainment", {}).get("total", 0.0)
    equipment_total  = cat_totals.get("equipment", {}).get("total", 0.0)
    contractor_total = cat_totals.get("contractor_payments", {}).get("total", 0.0)

    net_profit_est = gross_income - grand_deductible if gross_income > 0 else None

    cover = f"""
TAX EXPORT — ACCOUNTANT COVER NOTE
====================================
Business:     {business_name}
Tax Year:     {year}
Prepared:     {datetime.now().strftime("%B %d, %Y")} via Tax Receipt Autopilot
====================================

SUMMARY
-------
Total Business Transactions:    {full_count}
Total Business Spending:        {format_amount(grand_total)}
Estimated Deductible Total:     {format_amount(grand_deductible)}
Transactions Missing Receipts:  {len(missing_receipt_txns)}
Transactions Flagged for Review:{len(flagged_txns)}
"""

    if gross_income > 0:
        cover += f"""
INCOME (from income.json ledger)
---------------------------------
Gross Business Income YTD:      {format_amount(gross_income)}
Est. Schedule C Net Profit:     {format_amount(net_profit_est)}  (Schedule C Line 31 — gross income minus Schedule C deductions; before SE tax deduction, QBID, and standard deduction)
Note: Income source detail in {prefix}-income.csv
"""

    if total_miles > 0:
        cover += f"""
VEHICLE MILEAGE (from mileage.json log)
----------------------------------------
Total Business Miles:           {total_miles:.1f} miles
Mileage Deduction:              {format_amount(total_mileage_deduction)}
Mileage log detail in {prefix}-mileage-log.csv
Confirm: IRS requires date, start/end location, business purpose, and odometer for each trip.
"""

    cover += f"""
FILES INCLUDED
--------------
1. {prefix}-full.csv              — Complete ledger, all business transactions
2. {prefix}-summary.csv           — Totals by IRS category with schedule references
3. {prefix}-flagged.csv           — {len(flagged_txns)} transactions requiring your review
4. {prefix}-missing-receipts.csv  — {len(missing_receipt_txns)} transactions without receipts
5. {prefix}-cover-note.txt        — This document"""

    if income_records:
        cover += f"\n6. {prefix}-income.csv             — Gross income log ({len(income_records)} entries)"
    if mileage_records:
        cover += f"\n7. {prefix}-mileage-log.csv        — Mileage log ({len(mileage_records)} trips, {total_miles:.1f} miles)"

    cover += f"""

IMPORTANT NOTES FOR REVIEW
---------------------------
"""
    if meals_total > 0:
        meals_deductible = cat_totals.get("meals_entertainment", {}).get("deductible_total", 0.0)
        cover += f"""
MEALS & ENTERTAINMENT ({format_amount(meals_total)} total):
  - 50% deductible limitation applies per TCJA 2018
  - Deductible portion calculated as {format_amount(meals_deductible)} (stored deductible_pct=50 per transaction)
  - Please verify business purpose documentation for each meal
"""
    if equipment_total > 0:
        cover += f"""
EQUIPMENT ({format_amount(equipment_total)} total):
  - Review for Section 179 expensing vs. MACRS depreciation
  - Confirm business-use percentage for any mixed-use items
  - Items over $2,500 may need to be capitalized
"""
    if contractor_total > 0:
        nec_threshold = "$600" if int(year) <= 2025 else "$2,000"
        cover += f"""
CONTRACTOR PAYMENTS ({format_amount(contractor_total)} total):
  - For {year} payments: any contractor paid {nec_threshold}+ requires a 1099-NEC
  - Confirm W-9 is on file for each contractor
  - Review flagged file for contractors approaching the threshold
  - Contractors without W-9 on file are flagged in the vendor knowledge base
"""

    # 1099-K threshold varies by tax year:
    #   2021-2023: $20,000 AND 200+ transactions (IRS delayed ARPA's $600 reduction each year)
    #   2024:      $5,000, no transaction minimum (IRS Notice 2024-85)
    #   2025+:     $20,000 AND 200+ transactions (OBBBA, signed July 4, 2025, restored original)
    _year_int = int(year)
    if _year_int <= 2023:
        _k_threshold  = f"$20,000 AND more than 200 transactions per platform"
        _k_authority  = f"pre-ARPA original threshold; IRS extended transition relief through {year}"
        _k_conditions = "Both conditions must be met — either one alone does NOT trigger reporting"
        _k_extra      = ""
    elif _year_int == 2024:
        _k_threshold  = "$5,000, no transaction minimum"
        _k_authority  = "IRS Notice 2024-85 — enforced threshold for the 2024 filing season"
        _k_conditions = "No transaction minimum for 2024 — $5,000 gross is the sole condition"
        _k_extra      = (
            "  - Note: OBBBA (signed July 4, 2025) retroactively set the 2024 statutory threshold at\n"
            "    $20,000 AND 200 transactions, but TPSOs had already filed 2024 Forms 1099-K under\n"
            "    the $5,000 rule before OBBBA passed. No re-filing required.\n"
        )
    else:  # 2025+
        _k_threshold  = "$20,000 AND more than 200 transactions per platform"
        _k_authority  = "One Big Beautiful Bill Act, signed July 4, 2025"
        _k_conditions = "Both conditions must be met — either one alone does NOT trigger reporting"
        _k_extra      = ""

    cover += f"""
FORM 1099-K (Payment Networks — PayPal, Stripe, Venmo, Square, etc.):
  - For tax year {year}: threshold is {_k_threshold}
    ({_k_authority})
  - {_k_conditions}
  - Threshold applies per platform, not combined across platforms
{_k_extra}  - If client received any Form 1099-K, reconcile the reported amount against the ledger
  - All income is taxable regardless of whether a 1099-K was issued
  - Some states have lower thresholds (e.g., Vermont, Massachusetts, Virginia, Maryland: $600)
    — check client's state of residence
"""

    if len(missing_receipt_txns) > 0:
        cover += f"""
MISSING RECEIPTS ({len(missing_receipt_txns)} transactions):
  - See {prefix}-missing-receipts.csv for full list
  - These transactions lack supporting documentation
  - IRS requires substantiation for all business deductions
  - Client to provide receipts or written contemporaneous records
"""
    if len(flagged_txns) > 0:
        cover += f"""
FLAGGED FOR REVIEW ({len(flagged_txns)} transactions):
  - See {prefix}-flagged.csv for full list
  - Each has a Review Reason column explaining the concern
  - These may include: mixed-use items, unusual amounts, unclear business purpose
"""

    cover += f"""
HOME OFFICE:
  - If client claims home office deduction, Form 8829 required
  - Confirm exclusive and regular use, square footage calculation

ESTIMATED TAXES:
  - If client pays quarterly estimated taxes, confirm payments made
  - Q1: April 15 | Q2: June 15 | Q3: September 15 | Q4: January 15

====================================
Generated by Tax Receipt Autopilot
====================================
"""

    cover_path = output_dir / f"{prefix}-cover-note.txt"
    with open(cover_path, "w") as f:
        f.write(cover.strip())

    files_created = 5
    if income_records:
        files_created += 1
    if mileage_records:
        files_created += 1

    html_cover_path = None
    if html_cover:
        html_cover_path = generate_cover_html(
            output_dir=output_dir,
            prefix=prefix,
            business_name=business_name,
            year=year,
            full_count=full_count,
            grand_total=grand_total,
            grand_deductible=grand_deductible,
            gross_income=gross_income,
            net_profit_est=net_profit_est,
            total_miles=total_miles,
            total_mileage_deduction=total_mileage_deduction,
            flagged_count=len(flagged_txns),
            missing_count=len(missing_receipt_txns),
            income_records=income_records or [],
            mileage_records=mileage_records or [],
            meals_total=meals_total,
            meals_deductible=cat_totals.get("meals_entertainment", {}).get("deductible_total", 0.0),
            equipment_total=equipment_total,
            contractor_total=contractor_total,
            cat_totals=cat_totals,
        )
        files_created += 1

    return {
        "output_dir":          str(output_dir),
        "files_created":       files_created,
        "full_count":          full_count,
        "flagged_count":       len(flagged_txns),
        "missing_count":       len(missing_receipt_txns),
        "grand_total":         grand_total,
        "grand_deductible":    grand_deductible,
        "gross_income":        gross_income,
        "net_profit_est":      net_profit_est,
        "total_miles":         total_miles,
        "mileage_deduction":   total_mileage_deduction,
    }


def main():
    ap = argparse.ArgumentParser(description="Generate accountant-ready tax export")
    ap.add_argument("input",          help="Input JSON ledger file")
    ap.add_argument("--year",         default=str(datetime.now().year - 1),
                    help="Tax year (default: prior calendar year)")
    ap.add_argument("--name",         default="My Business", help="Business name")
    ap.add_argument("--output-dir",   default="./tax-export", help="Output directory")
    ap.add_argument("--income",       default="", help="Path to income.json (optional)")
    ap.add_argument("--mileage",      default="", help="Path to mileage.json (optional)")
    ap.add_argument("--html",         action="store_true",
                    help="Also generate a print-ready HTML cover note (open in browser → Ctrl+P → Save as PDF)")
    args = ap.parse_args()

    transactions  = load_transactions(args.input)
    income_recs   = load_json_file(args.income)  if args.income  else []
    mileage_recs  = load_json_file(args.mileage) if args.mileage else []

    result = generate_export(
        transactions,
        year=args.year,
        business_name=args.name,
        output_dir=Path(args.output_dir),
        income_records=income_recs,
        mileage_records=mileage_recs,
        html_cover=args.html,
    )

    print(f"\n✅ Tax export complete → {result['output_dir']}", file=sys.stderr)
    print(f"   Transactions:     {result['full_count']}", file=sys.stderr)
    print(f"   Total spending:   ${result['grand_total']:,.2f}", file=sys.stderr)
    print(f"   Est. deductible:  ${result['grand_deductible']:,.2f}", file=sys.stderr)
    gross_income_val: float = float(result["gross_income"] or 0)
    if gross_income_val > 0:
        print(f"   Gross income:     ${gross_income_val:,.2f}", file=sys.stderr)
        net = result["net_profit_est"]
        if net is not None and isinstance(net, (int, float)):
            print(f"   Est. net profit:  ${net:,.2f}", file=sys.stderr)
    if float(result["total_miles"] or 0.0) > 0:
        print(f"   Business miles:   {result['total_miles']:.1f} mi  (${result['mileage_deduction']:,.2f} deduction)", file=sys.stderr)
    print(f"   Flagged:          {result['flagged_count']}", file=sys.stderr)
    print(f"   Missing receipts: {result['missing_count']}", file=sys.stderr)


if __name__ == "__main__":
    main()
