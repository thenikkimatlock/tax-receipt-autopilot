#!/usr/bin/env python3
"""
parse_bank_statement.py
-----------------------
Parses bank/credit card statements from CSV or PDF into a normalized
list of transaction dicts ready for the Tax Receipt Autopilot ledger.

Usage:
    python3 parse_bank_statement.py <file_path> [--output <out.json>] [--bank <bank_name>]

Outputs JSON array of transactions to stdout (or file if --output specified).
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    print(
        "WARNING: pdfplumber not installed — PDF parsing unavailable.\n"
        "         CSV parsing still works. Install for PDF support: pip install pdfplumber",
        file=sys.stderr,
    )

try:
    from dateutil import parser as dateparser
except ImportError:
    dateparser = None
    print(
        "WARNING: python-dateutil not installed — date parsing uses fallback patterns only.\n"
        "         Unusual date formats (e.g. 'Jan 15 2026') may not parse correctly.\n"
        "         Install for full date support: pip install python-dateutil",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Known bank CSV column mappings
# Format: bank_name -> {our_field: [possible column names in priority order]}
# ---------------------------------------------------------------------------
BANK_COLUMN_MAPS = {
    "chase": {
        "transaction_date": ["Transaction Date", "Posting Date"],
        "vendor":           ["Description"],
        "amount":           ["Amount"],
        "type":             ["Type"],
    },
    "bofa": {
        "transaction_date": ["Date"],
        "vendor":           ["Payee", "Description"],
        "amount":           ["Amount"],
        "type":             [],
    },
    "wells_fargo": {
        "transaction_date": ["Date"],
        "vendor":           ["Description"],
        "amount":           ["Amount"],
        "type":             [],
    },
    "amex": {
        "transaction_date": ["Date"],
        "vendor":           ["Description"],
        "amount":           ["Amount"],
        "type":             ["Type"],
    },
    "capital_one": {
        "transaction_date": ["Transaction Date", "Posted Date"],
        "vendor":           ["Description"],
        "amount":           ["Debit", "Credit"],
        "type":             [],
    },
    "generic": {
        "transaction_date": ["Date", "Transaction Date", "Trans Date", "Posting Date"],
        "vendor":           ["Description", "Payee", "Merchant", "Vendor", "Name"],
        "amount":           ["Amount", "Debit", "Transaction Amount"],
        "type":             ["Type", "Transaction Type"],
    },
}


# ---------------------------------------------------------------------------
# Vendor name normalizer
# ---------------------------------------------------------------------------
VENDOR_NORMALIZATIONS = [
    # --- E-commerce ---
    (r"AMZN\s?MKTP.*",              "Amazon"),
    (r"AMAZON\.COM.*",              "Amazon"),
    (r"AMAZON\s?WEB\s?SERVICES.*",  "Amazon Web Services"),
    (r"SHOPIFY\s?\*.*",             "Shopify"),
    (r"SHOPIFY.*",                  "Shopify"),
    (r"GUMROAD.*",                  "Gumroad"),

    # --- Payment processors / POS ---
    (r"PAYPAL\s?\*(.+)",            r"PayPal - \1"),
    (r"SQ\s?\*(.+)",                r"\1"),          # Square POS
    (r"TST\*\s?(.+)",               r"\1"),           # Toast POS

    # --- Social / Ad platforms ---
    (r"META\s?\*?ADS.*",            "Meta Ads"),
    (r"FACEBK\s?\*.*",              "Meta Ads"),
    (r"GOOGLE\s?\*?ADS.*",          "Google Ads"),
    (r"LINKEDIN\s?\*?ADS.*",        "LinkedIn Ads"),
    (r"TIKTOK\s?\*?ADS.*",          "TikTok Ads"),
    (r"PINTEREST\s?\*?ADS.*",       "Pinterest Ads"),
    (r"TWITTER\s?\*?ADS.*",         "X (Twitter) Ads"),
    (r"X\.COM\s?\*?ADS.*",          "X (Twitter) Ads"),

    # --- Google Workspace / cloud ---
    (r"GOOGLE\s?\*?GSUITE.*",       "Google Workspace"),
    (r"GOOGLE\s?\*?WORKSPACE.*",    "Google Workspace"),
    (r"GOOGLE\s?\*?STORAGE.*",      "Google Cloud"),
    (r"GOOGLE\s?\*?CLOUD.*",        "Google Cloud"),

    # --- Telecom ---
    (r"VZWRLSS.*",                  "Verizon Wireless"),
    (r"ATT\s?\*.*",                 "AT&T"),

    # --- Ride share / travel ---
    (r"UBER\s?\*?\s?TRIP.*",        "Uber"),
    (r"LYFT\s?\*.*",                "Lyft"),

    # --- Workspace ---
    (r"WEWORK.*",                   "WeWork"),

    # --- Streaming / personal ---
    (r"NETLFL?IX.*",                "Netflix"),
    (r"SPOTIFY.*",                  "Spotify"),
    (r"APPLE\.COM/BILL.*",          "Apple"),

    # --- Microsoft ---
    (r"MSFT\s?\*.*",                "Microsoft"),
    (r"MICROSOFT\s?\*.*",           "Microsoft 365"),

    # --- Adobe / Creative ---
    (r"ADOBE\s?\*.*",               "Adobe Creative Cloud"),
    (r"ADOBE\s?INC.*",              "Adobe Creative Cloud"),

    # --- Dev tools ---
    (r"GITHUB.*",                   "GitHub"),
    (r"DIGITALOCEAN.*",             "DigitalOcean"),
    (r"NETLIFY.*",                  "Netlify"),
    (r"VERCEL.*",                   "Vercel"),
    (r"CLOUDFLARE.*",               "Cloudflare"),
    (r"TWILIO.*",                   "Twilio"),
    (r"SENDGRID.*",                 "SendGrid"),
    (r"HEROKU.*",                   "Heroku"),

    # --- AI tools ---
    (r"OPENAI.*",                   "OpenAI"),
    (r"ANTHROPIC.*",                "Anthropic"),
    (r"MIDJOURNEY.*",               "Midjourney"),
    (r"ELEVENLABS.*",               "ElevenLabs"),

    # --- Productivity / project mgmt ---
    (r"NOTION.*",                   "Notion"),
    (r"SLACK.*",                    "Slack"),
    (r"ZOOM.*",                     "Zoom"),
    (r"DROPBOX.*",                  "Dropbox"),
    (r"AIRTABLE.*",                 "Airtable"),
    (r"CLICKUP.*",                  "ClickUp"),
    (r"ASANA.*",                    "Asana"),
    (r"TRELLO.*",                   "Trello"),
    (r"LINEAR\s?\*.*",              "Linear"),
    (r"LOOM\s?\*.*",                "Loom"),
    (r"LOOM\.COM.*",                "Loom"),
    (r"DESCRIPT.*",                 "Descript"),
    (r"RIVERSIDE.*",                "Riverside"),
    (r"CALENDLY.*",                 "Calendly"),
    (r"TYPEFORM.*",                 "Typeform"),

    # --- Email / marketing ---
    (r"MAILCHIMP.*",                "Mailchimp"),
    (r"CONVERTKIT.*",               "Kit (ConvertKit)"),
    (r"KIT\.COM.*",                 "Kit (ConvertKit)"),
    (r"KLAVIYO.*",                  "Klaviyo"),
    (r"ACTIVECAMPAIGN.*",           "ActiveCampaign"),
    (r"HUBSPOT.*",                  "HubSpot"),

    # --- Social media scheduling ---
    (r"BUFFER\s?\*.*",              "Buffer"),
    (r"BUFFER\.COM.*",              "Buffer"),
    (r"HOOTSUITE.*",                "Hootsuite"),
    (r"LATER\s?\*.*",               "Later"),
    (r"LATER\.COM.*",               "Later"),
    (r"TAILWIND\s?APP.*",           "Tailwind"),

    # --- Automation ---
    (r"ZAPIER.*",                   "Zapier"),
    (r"INTEGROMAT.*",               "Make.com"),
    (r"MAKE\.COM.*",                "Make.com"),

    # --- Website / CMS ---
    (r"SQUARESPACE.*",              "Squarespace"),
    (r"WORDPRESS.*",                "WordPress"),
    (r"WP\s?ENGINE.*",              "WP Engine"),
    (r"GODADDY.*",                  "GoDaddy"),
    (r"NAMECHEAP.*",                "Namecheap"),

    # --- Freelance platforms ---
    (r"FIVERR.*",                   "Fiverr"),
    (r"UPWORK.*",                   "Upwork"),

    # --- Business / SaaS ---
    (r"KAJABI.*",                   "Kajabi"),
    (r"CLICKFUNNELS.*",             "ClickFunnels"),
    (r"GOHIGHLEVEL.*",              "GoHighLevel"),
    (r"HIGHLEVEL.*",                "GoHighLevel"),
    (r"FIGMA.*",                    "Figma"),
    (r"CANVA\s?\*.*",               "Canva"),
    (r"CANVA.*",                    "Canva"),
    (r"EPIDEMIC\s?SOUND.*",         "Epidemic Sound"),
    (r"FAL\s?\*.*",                 "fal.ai"),
    (r"FAL\.AI.*",                  "fal.ai"),
]


def normalize_vendor(raw_name: str) -> str:
    """Apply normalization rules to a raw bank vendor string."""
    name = raw_name.strip().upper()
    for pattern, replacement in VENDOR_NORMALIZATIONS:
        match = re.match(pattern, name, re.IGNORECASE)
        if match:
            if r"\1" in replacement:
                # Reconstruct the full replacement string, preserving any prefix
                # e.g. "PAYPAL *STARBUCKS" → "PayPal - Starbucks" (not just "Starbucks")
                captured = match.group(1).strip().title()
                return replacement.replace(r"\1", captured)
            return replacement
    # Title-case the cleaned name as fallback
    cleaned = re.sub(r"[#\*].*$", "", raw_name).strip()
    return cleaned.title()


def parse_amount(raw: str) -> tuple[float, bool]:
    """
    Parse amount string. Returns (abs_amount, is_negative).
    Caller determines debit/credit based on account type and sign convention:
      - Credit card:  positive = expense (debit), negative = refund (credit)
      - Checking:     negative = expense (debit), positive = deposit (credit)
    """
    raw = raw.strip().replace(",", "").replace("$", "")
    is_negative = raw.startswith("-") or raw.startswith("(")
    raw = raw.strip("-()+")  # strip() removes both leading AND trailing parens/signs
    try:
        amount = float(raw)
    except ValueError:
        return 0.0, False
    return abs(amount), is_negative


def parse_date(raw: str) -> str:
    """Parse various date formats to YYYY-MM-DD."""
    if not raw or raw.strip() == "":
        return ""
    if dateparser:
        try:
            dt = dateparser.parse(raw.strip(), dayfirst=False)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    # Fallback manual patterns
    for fmt in ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw.strip()


def find_column(headers: list[str], candidates: list[str]) -> str | None:
    """Case-insensitive column finder."""
    headers_lower = [h.lower().strip() for h in headers]
    for candidate in candidates:
        if candidate.lower() in headers_lower:
            idx = headers_lower.index(candidate.lower())
            return headers[idx]
    return None


# ---------------------------------------------------------------------------
# CSV Parser
# ---------------------------------------------------------------------------
def parse_csv(file_path: str, bank: str = "generic", account_type: str = "credit", account: str = "") -> list[dict]:
    """
    account_type: 'credit' or 'checking'
      credit   — positive amounts are charges (expenses); negative are refunds.
                 Use for all credit cards (Amex, Chase Sapphire, etc.)
      checking — negative amounts are debits (expenses); positive are deposits.
                 Use for bank checking/debit accounts (Chase checking, BofA, etc.)
    """
    transactions = []
    bank_map = BANK_COLUMN_MAPS.get(bank.lower(), BANK_COLUMN_MAPS["generic"])

    with open(file_path, newline="", encoding="utf-8-sig") as f:
        # Skip non-CSV header lines (some banks add account info rows)
        lines = f.readlines()

    # Find the actual header row (first row with >= 3 commas)
    header_idx = 0
    for i, line in enumerate(lines):
        if line.count(",") >= 2:
            header_idx = i
            break

    csv_content = "".join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(csv_content))
    headers = reader.fieldnames or []

    # Map column names
    date_col   = find_column(headers, bank_map["transaction_date"])
    vendor_col = find_column(headers, bank_map["vendor"])
    amount_col = find_column(headers, bank_map["amount"])
    type_col   = find_column(headers, bank_map.get("type", []))

    # Capital One has separate Debit/Credit columns
    debit_col  = find_column(headers, ["Debit"])
    credit_col = find_column(headers, ["Credit"])

    for row in reader:
        if not any(row.values()):  # skip blank rows
            continue

        # Date
        raw_date = row.get(date_col, "").strip() if date_col else ""
        tx_date = parse_date(raw_date) if raw_date else ""

        # Vendor
        raw_vendor = row.get(vendor_col, "").strip() if vendor_col else "Unknown"
        vendor = normalize_vendor(raw_vendor)

        # Amount + type
        if debit_col and credit_col:
            # Banks with separate Debit/Credit columns (e.g. Capital One) — direction is unambiguous
            debit_val  = row.get(debit_col, "").strip()
            credit_val = row.get(credit_col, "").strip()
            if debit_val:
                amount, _ = parse_amount(debit_val)
                tx_type = "debit"
            elif credit_val:
                amount, _ = parse_amount(credit_val)
                tx_type = "credit"
            else:
                amount, tx_type = 0.0, "unknown"
        elif amount_col:
            raw_amount = row.get(amount_col, "0").strip()
            amount, is_negative = parse_amount(raw_amount)
            # Sign convention differs by account type:
            #   credit card  → positive = expense (debit), negative = refund (credit)
            #   checking     → negative = expense (debit), positive = deposit (credit)
            if account_type == "checking":
                tx_type = "debit" if is_negative else "credit"
            else:
                tx_type = "credit" if is_negative else "debit"
        else:
            amount, tx_type = 0.0, "unknown"

        # Override type from explicit bank type column if present (takes precedence over sign heuristic)
        # "sale" added here because Chase uses "Sale" for purchases, not "Debit" or "Purchase"
        if type_col and row.get(type_col):
            type_str = row[type_col].lower()
            if any(w in type_str for w in ["debit", "purchase", "charge", "payment", "sale"]):
                tx_type = "debit"
            elif any(w in type_str for w in ["credit", "refund", "return", "deposit"]):
                tx_type = "credit"

        # Skip credits/refunds by default
        if tx_type == "credit":
            continue

        if amount == 0.0 or not tx_date:
            continue

        transactions.append({
            "vendor":            vendor,
            "vendor_raw":        raw_vendor,
            "transaction_date":  tx_date,
            "amount":            round(amount, 2),
            "account":           account,
            "type":              tx_type,
            "source":            "Bank Import",
            "receipt_matched":   False,
            "review_required":   False,
            "category":          None,
            "notes":             "",
        })

    return transactions


# ---------------------------------------------------------------------------
# PDF Parser
# ---------------------------------------------------------------------------
def parse_pdf(file_path: str, account: str = "") -> list[dict]:
    if not pdfplumber:
        print("ERROR: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
        sys.exit(1)

    transactions = []
    # Date pattern: MM/DD/YYYY or MM/DD/YY
    date_pattern  = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")
    # Amount pattern: $1,234.56 or 1234.56 or (1234.56)
    amount_pattern = re.compile(r"\(?\$?([\d,]+\.\d{2})\)?")

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row:
                            continue
                        row_text = [str(cell).strip() if cell else "" for cell in row]
                        full_text = " ".join(row_text)

                        dates = date_pattern.findall(full_text)
                        amounts = amount_pattern.findall(full_text)

                        if not dates or not amounts:
                            continue

                        tx_date = parse_date(dates[0])
                        amount_str = amounts[-1].replace(",", "")
                        try:
                            amount = float(amount_str)
                        except ValueError:
                            continue

                        # Vendor: the cell that doesn't look like a date or amount.
                        # Use search() (not match()) so cells like "Balance: $47.99"
                        # are correctly excluded even if the amount isn't at the start.
                        vendor_raw = ""
                        for cell in row_text:
                            if (cell and
                                not date_pattern.search(cell) and
                                not amount_pattern.search(cell) and
                                len(cell) > 2):
                                vendor_raw = cell
                                break

                        if not vendor_raw or amount == 0:
                            continue

                        transactions.append({
                            "vendor":           normalize_vendor(vendor_raw),
                            "vendor_raw":       vendor_raw,
                            "transaction_date": tx_date,
                            "amount":           round(amount, 2),
                            "account":          account,
                            "type":             "debit",
                            "source":           "Bank Import",
                            "receipt_matched":  False,
                            "review_required":  amount > 5000,
                            "category":         None,
                            "notes":            "Parsed from PDF — verify accuracy",
                        })
            else:
                # Fallback: raw text extraction
                text = page.extract_text() or ""
                lines = text.split("\n")
                for line in lines:
                    dates   = date_pattern.findall(line)
                    amounts = amount_pattern.findall(line)
                    if dates and amounts:
                        tx_date    = parse_date(dates[0])
                        amount_str = amounts[-1].replace(",", "")
                        try:
                            amount = float(amount_str)
                        except ValueError:
                            continue
                        # Strip dates and amounts to get vendor
                        vendor_raw = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}", "", line)
                        vendor_raw = re.sub(r"\(?\$?[\d,]+\.\d{2}\)?", "", vendor_raw).strip()
                        vendor_raw = re.sub(r"\s+", " ", vendor_raw).strip()
                        if vendor_raw and amount > 0:
                            transactions.append({
                                "vendor":           normalize_vendor(vendor_raw),
                                "vendor_raw":       vendor_raw,
                                "transaction_date": tx_date,
                                "amount":           round(amount, 2),
                                "account":          account,
                                "type":             "debit",
                                "source":           "Bank Import",
                                "receipt_matched":  False,
                                "review_required":  True,
                                "category":         None,
                                "notes":            "PDF text extraction — verify accuracy",
                            })

    return transactions


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Parse bank statement CSV or PDF")
    ap.add_argument("file", help="Path to CSV or PDF bank statement")
    ap.add_argument("--output", help="Output JSON file path (default: stdout)")
    ap.add_argument("--bank",   default="generic",
                    help="Bank name for column mapping: chase, bofa, wells_fargo, amex, capital_one, generic")
    ap.add_argument("--account-type", dest="account_type", choices=["credit", "checking"], default="credit",
                    help=(
                        "Account type determines sign convention for the Amount column.\n"
                        "  credit   — positive = expense, negative = refund (Amex, Chase Sapphire, etc.)\n"
                        "  checking — negative = expense, positive = deposit (Chase checking, BofA checking, etc.)\n"
                        "Default: credit"
                    ))
    ap.add_argument("--account", default="",
                    help="Account name to stamp on every transaction (e.g. 'Amex Gold', 'Chase Checking'). "
                         "Required when importing multiple accounts — lets you filter by card later.")
    args = ap.parse_args()

    if not args.account:
        print(
            "WARNING: --account not specified. Strongly recommended when importing multiple "
            "accounts — stamps every transaction so you can filter by card/account later.\n"
            "  Example: --account \"Chase Checking\" or --account \"Amex Gold\"",
            file=sys.stderr,
        )

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    ext = path.suffix.lower()
    if ext == ".csv":
        transactions = parse_csv(str(path), bank=args.bank, account_type=args.account_type, account=args.account)
    elif ext == ".pdf":
        transactions = parse_pdf(str(path), account=args.account)
    else:
        print(f"ERROR: Unsupported file type: {ext}. Use .csv or .pdf", file=sys.stderr)
        sys.exit(1)

    result = json.dumps(transactions, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"✅ Parsed {len(transactions)} transactions → {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()