# Local Files — No Accounts Required

Tax Receipt Autopilot runs entirely on local JSON files. No accounts, no MCP setup, no cloud services. Claude Code reads and writes the files directly. Your data stays on your machine.

---

## What It Looks Like

No separate app, no spreadsheet to maintain. Claude is the interface — your ledger is the data.

**Day-to-day usage:**
- Snap a photo of a paper receipt → attach it in Claude → Claude extracts, classifies, writes to ledger.json, and confirms in the chat
- Drop files in your receipts folder → say "process my receipts" → entire batch handled in one pass
- Attach a bank statement CSV → say "here's my [Month] statement" → Claude parses, deduplicates, classifies, and imports every transaction

**For visibility:**
- "Show me my March dashboard" → Claude reads ledger.json in-memory and returns a formatted expense summary
- "What do I need to fix?" → full audit with health score and prioritized issue list
- "Is [vendor] deductible?" → instant IRS category answer, no lookup required

**For your accountant or for visual browsing:**
- "Generate my 2026 tax export" → 5 CSV files written to a folder on your computer
- Open `[prefix]-full.csv` in Excel, Numbers, or Google Sheets for a visual grid of all transactions with categories and Schedule C references
- The `[prefix]-summary.csv` shows totals by category — this is what your accountant actually uses

The `ledger.json` file is a raw JSON array. You never need to open it directly.

---

## File Structure

Transactions live in JSON files in a folder on your computer:

```
[SKILL_DIR]/data/tax-2026/
  ledger.json     ← all your expense transactions
  income.json     ← all income/revenue records
  mileage.json    ← business mileage log
  vendors.json    ← your vendor knowledge base
  receipts/       ← receipt image files (named by transaction ID)
```

`[SKILL_DIR]` is the directory containing SKILL.md — wherever you cloned this repo.

Claude Code reads and writes these files natively. No MCP, no third-party auth, no accounts. The Python scripts (bank statement parser, dedup, export) work with these same files.

---

## File Formats

### ledger.json

A JSON array of transaction objects. Example:

```json
[
  {
    "id": "tx_20260115_001",
    "vendor": "Canva",
    "vendor_raw": "CANVA* 02301993",
    "transaction_date": "2026-01-15",
    "amount": 16.99,
    "account": "Amex Gold",
    "category": "software_subscriptions",
    "business_or_personal": "business",
    "deductible": true,
    "deductible_pct": 100,
    "receipt_matched": false,
    "receipt_path": "",
    "source": "Bank Import",
    "notes": "Monthly design subscription",
    "review_required": false,
    "review_reason": ""
  }
]
```

**Key fields:**
- `deductible` (bool): true if any portion of this expense is deductible
- `deductible_pct` (int 0-100): exact percentage that is deductible. 100 = fully deductible, 50 = meals/entertainment limitation, 0 = non-deductible. Never use a string like `"partial"` — store the actual number.
- `receipt_path` (str): relative or absolute path to the receipt file on disk (e.g., `receipts/canva-2026-01-15.jpg`). Empty string if no receipt file.

### income.json

A JSON array of income records (parallel to ledger.json but for money received). Example:

```json
[
  {
    "id": "inc_20260115_001",
    "source": "Stripe",
    "platform": "Stripe",
    "description": "Client payment — January retainer",
    "date": "2026-01-15",
    "amount": 500.00,
    "account": "Chase Business Checking",
    "category": "services",
    "1099_reported": false,
    "notes": "",
    "review_required": false,
    "review_reason": ""
  }
]
```

Income categories: `services`, `product_sales`, `affiliate_commissions`, `course_revenue`, `ad_revenue`, `subscription_revenue`, `refund_received`, `other_income`.

### mileage.json

A JSON array of mileage log entries. Example:

```json
[
  {
    "id": "mi_20260115_001",
    "date": "2026-01-15",
    "start_location": "Home office — 123 Main St",
    "end_location": "Client site — 456 Oak Ave",
    "miles": 12.4,
    "business_purpose": "Client meeting — quarterly review",
    "vehicle": "2022 Honda CR-V",
    "round_trip": false,
    "rate_per_mile": 0.725,
    "deductible_amount": 8.99,
    "notes": ""
  }
]
```

**IRS mileage log requirements:** date, start location, end location, business purpose, and miles are all required. Missing any field = record is incomplete and may be disallowed on audit.

**`rate_per_mile` and `deductible_amount` rules:**
- `rate_per_mile`: use the IRS standard mileage rate for the tax year. 2025 = 0.70, 2026 = 0.725. Store as a number.
- `deductible_amount`: `miles × rate_per_mile` (or `miles × 2 × rate_per_mile` for round trips). This is what `export_ledger.py` reads for the mileage deduction total — if this field is 0 or missing, the export will show $0 for mileage deductions. Always calculate and store it when writing the record.

### vendors.json

A JSON array of vendor knowledge base entries. Example:

```json
[
  {
    "vendor_name": "Canva",
    "default_category": "software_subscriptions",
    "default_deductible": true,
    "default_deductible_pct": 100,
    "notes": "Design tool — 100% business use"
  },
  {
    "vendor_name": "Verizon",
    "default_category": "utilities",
    "default_deductible": true,
    "default_deductible_pct": 50,
    "notes": "Phone/internet — 50% default. Confirm actual business-use %."
  },
  {
    "vendor_name": "Fiverr",
    "default_category": "contractor_payments",
    "default_deductible": true,
    "default_deductible_pct": 100,
    "w9_on_file": false,
    "notes": "Freelancer payments — collect W-9 if any payment"
  }
]
```

`w9_on_file` field is only used on `contractor_payments` vendors. Once a W-9 is received, update to `true`.

---

## How Claude Operates on Local Files

### Read the ledger
```
Read tool: [SKILL_DIR]/data/tax-2026/ledger.json
```

### Add a transaction (safe-write pattern)
1. If the ledger has any existing transactions (1 or more), back it up first: `python3 scripts/backup_ledger.py [ledger_path]`. Do not skip this for small ledgers — even a few months of records are worth protecting.
2. Read ledger.json
3. Append new transaction object to the array
4. Write the updated array back to ledger.json
5. Immediately Read the file back — confirm it parses as valid JSON
6. If it fails or returns empty: alert the user immediately. The backup in `[ledger_dir]/backups/` is the recovery path.

Transaction ID format: `tx_YYYYMMDD_NNN` — use today's date + a 3-digit counter starting at 001. If the ledger already has transactions on today's date, increment NNN.

### Update a transaction
1. Read ledger.json
2. Find by `id` field
3. Update the relevant fields
4. Write back

### Query by month
1. Read ledger.json
2. Filter in-memory: `transaction_date.startswith("YYYY-MM")`

### Duplicate check
1. Read ledger.json
2. Filter: same vendor (fuzzy), same amount (within $0.02), date within 3 days
3. If match found — show user before inserting

### Read/add/update vendors
Same pattern with vendors.json — read, modify, write back.

---

## Creating Your Local Files

When setting up for the first time, create these files:

```json
[]
```

That's it. An empty JSON array for each. Claude will build them up as transactions are added.

Suggest this folder structure to the user:
```
[SKILL_DIR]/data/tax-2026/       ← default, inside the repo where everything stays together
```

Or wherever they want it — a custom path, Dropbox folder, etc. always works.

---

## Running Python Scripts Against Local Files

All scripts work the same — they operate on the same JSON format:

```bash
# Parse a bank statement CSV → transactions.json
python3 scripts/parse_bank_statement.py statement.csv --bank chase --account-type credit --output transactions.json

# Dedup the parsed transactions
python3 scripts/detect_duplicates.py transactions.json --output clean.json

# Audit the ledger (with vendors and mileage for full W-9 + mileage completeness check)
python3 scripts/monthly_reminder.py audit data/tax-2026/ledger.json \
  --vendors data/tax-2026/vendors.json \
  --mileage data/tax-2026/mileage.json

# Monthly summary with income and mileage
python3 scripts/monthly_reminder.py summary data/tax-2026/ledger.json --month 2026-02 \
  --income data/tax-2026/income.json \
  --mileage data/tax-2026/mileage.json

# Export for accountant (includes income and mileage CSVs)
python3 scripts/export_ledger.py data/tax-2026/ledger.json --year 2026 --name "My Business" \
  --output-dir ./tax-export-2026 \
  --income data/tax-2026/income.json \
  --mileage data/tax-2026/mileage.json
```

---

## Multi-Account Tracking in Local Mode

When importing from multiple accounts, always set the `account` field on each transaction so you can filter later:

```json
{ "account": "Chase Checking", ... }
{ "account": "Amex Gold", ... }
{ "account": "PayPal Business", ... }
```

To see just one account: Read ledger.json → filter by `account` field.

---

## Backing Up Your Data

Remind users to back up their tax folder periodically. Simple options:
- Copy the folder to Google Drive or Dropbox manually
- Or just email themselves ledger.json once a month

The files are small — a full year of transactions is typically 50–200 KB.

---

## Recovering a Corrupted Ledger

If `ledger.json` becomes unreadable (empty file, truncated JSON, or a parse error after a crash), here's how to recover.

**Step 1 — Diagnose**
Ask Claude: "Can you read my ledger file?" Claude will attempt to read `ledger_path` and report what it finds.

Common causes:
- File is empty or contains just `[` with no closing bracket (partial write interrupted mid-operation)
- File contains `null` or malformed JSON

**Step 2 — Check your backup first**
If you have a recent backup (Google Drive, Dropbox, email copy): restore it. This is the fastest path.

**Step 3 — Recover from a partial write**
If the file has content but isn't valid JSON:
1. Ask Claude to read the file and show the raw contents
2. If it starts with `[` and cuts off mid-record, it truncated during a write
3. Tell Claude: "Try to recover valid transactions from this file"
4. Claude extracts all complete transaction objects and rebuilds a valid array

**Step 4 — Start fresh if unrecoverable**
If there is no backup and the file cannot be repaired:
1. Tell Claude: "Re-initialize my ledger file"
2. Claude writes an empty `[]` to `ledger_path`
3. Re-import your bank statements — they contain every transaction
4. Manually re-enter any receipts that aren't on bank statements

**Prevention:** On the 1st of each month, copy `ledger.json` to Google Drive or email it to yourself. A full year of transactions is under 200 KB and takes 30 seconds to back up.

---

---

## Privacy and Security

Your ledger and vendor files are plain JSON — readable by any application or user with file-system access to that path.

**Risks to be aware of:**
- Other users on a shared machine can read your financial data
- Backup tools (Time Machine, Dropbox sync) may upload unencrypted copies to cloud storage
- Any app with access to your home directory (~) has access to the ledger

**Mitigations:**
- Keep the tax folder outside shared directories (not Desktop, not a shared Dropbox folder)
- For sensitive data, store in an encrypted disk image (macOS Disk Utility → encrypted sparse image) or BitLocker-protected drive (Windows)
- The entire year's ledger is under 200KB — fits in any password-protected zip file for backups

---

---

## Managing Multiple Tax Years

Each tax year gets its own ledger and config. You can switch between years at any time with no data loss.

### Folder structure

```
[SKILL_DIR]/data/tax-2025/
  ledger.json      ← 2025 transactions
  vendors.json     ← vendor KB (can be shared or separate)
  receipts/

[SKILL_DIR]/data/tax-2026/
  ledger.json      ← 2026 transactions
  vendors.json
  receipts/
```

`[SKILL_DIR]` is the directory containing SKILL.md — wherever you cloned the repo.

### Config files

| Scenario | Config path |
|---|---|
| Single year (default) | `[SKILL_DIR]/config.json` |
| Second year added | `[SKILL_DIR]/config-2025.json` |
| Third year | `[SKILL_DIR]/config-2026.json` |

When you have multiple years, Claude saves each year's config to a year-specific file and picks up the right one when you say "switch to [YEAR] taxes."

### Setting up a new year

Tell Claude: *"Set up my 2025 ledger"* or *"Switch to 2025 taxes"* — Claude creates `[SKILL_DIR]/data/tax-2025/`, initializes the files, and saves `[SKILL_DIR]/config-2025.json`. Your current year's config is untouched.

### Switching years mid-session

Tell Claude: *"Switch to 2025 taxes"* — Claude loads `[SKILL_DIR]/config-2025.json` and all subsequent operations run against the 2025 ledger until you switch back.

### Sharing the vendor KB across years

If you want both years to use the same vendor knowledge base (so you don't re-classify the same vendors twice), point both configs to the same `vendors_path`. Your classifications carry forward automatically.

```json
// In [SKILL_DIR]/config-2025.json AND [SKILL_DIR]/config-2026.json:
{
  "vendors_path": "/absolute/path/to/shared/vendors.json"
}
```
