---
name: tax-receipt-autopilot
description: >
  Year-round automated expense tracking, receipt management, and tax preparation system.
  TRIGGER when user is actively doing bookkeeping work: submitting a receipt or bank statement,
  logging income or mileage, requesting an expense summary or dashboard, asking for a tax export
  or accountant files, running a ledger audit, asking if a specific purchase is deductible, or
  setting up expense tracking for the first time. Key trigger phrases: "I have a receipt to log",
  "here's my bank statement", "what am I missing receipts for?", "prepare my taxes",
  "is this deductible?", "show me my expenses", "roast my expenses", "tax panic mode",
  "deduction rescue", "show me my [X] problem".
  DO NOT trigger on casual mentions of tax, deductions, or business expenses in broader
  strategy or planning discussions.
---

# Tax Receipt Autopilot

Captures receipts and transactions from any source, classifies them using legitimate IRS categories, stores them in local JSON files, detects duplicates, tracks missing documentation, and produces accountant-ready exports — all year long.

---

## Document Map

| Who you are | Where to go |
|---|---|
| **New user** (no config file yet, or user says "set me up") | **Jump to Step 12 immediately.** Do not read the session checklist first. |
| **Returning user** (config exists) | Start at Session Start Checklist below |
| **Looking for a command?** | See the Task Router table |

---

## Skill Directory

The **skill directory** is the folder containing this SKILL.md file. Resolve it from the file path at session start — it is the base for all relative paths used in this skill.

Example: if SKILL.md is at `/Users/nikki/repos/tax-receipt-autopilot/SKILL.md`, the skill directory is `/Users/nikki/repos/tax-receipt-autopilot/`.

Config file location: `[SKILL_DIR]/config.json`
Default data location: `[SKILL_DIR]/data/tax-[YEAR]/`

---

## Session Start Checklist

At the beginning of EVERY session, before doing anything else:

1. **Load config** — Resolve the skill directory from the path to this SKILL.md file. Then try to Read `[SKILL_DIR]/config.json`:
   - If found → extract all session values, confirm in one line: *"Loaded: [business_name], [tax_year]. What do you need?"* → proceed
   - If found but local mode `ledger_path` file doesn't exist → warn: *"Your config is set up but I can't find [ledger_path]. Want to re-run setup?"*
   - **If not found → STOP. Do not proceed to steps 2 or 3. Jump directly to Step 12 (first-time setup).**
   - Also try `[SKILL_DIR]/config-[CURRENT_YEAR].json` and `[SKILL_DIR]/config-[PRIOR_YEAR].json` before giving up — if year-specific configs exist, list them: *"Found configs for: [years]. Which year do you want to work on?"*
   - If reading `ledger_path` fails with a JSON parse error at any point during the session → immediately surface recovery: *"Your ledger file may be corrupted. See the recovery steps in `references/local-file-mode.md` → 'Recovering a Corrupted Ledger'."*

2. **Check bank statement reminder** — Only run this check when the user's opening message is generic: a greeting, "what should I do?", "catch me up", "what's next?", or no specific task stated. **Skip this check entirely** if the user's message signals a specific task — any of the following:
   - Contains an attached file or bank statement
   - Submits a receipt or transaction to log
   - Asks about deductibility ("is X deductible?", "can I deduct X?")
   - Requests a dashboard or expense summary
   - Requests an audit or health check
   - Mentions switching years
   - Matches any entry in the Task Router table (Steps 2A–14)
   When the check does run: Read the ledger and find the most recent transaction where `source` is `"Bank Import"`:
   - Read `ledger_path` → filter in-memory for `source == "Bank Import"` → find max `transaction_date`
   - If no Bank Import transaction exists, or if the most recent one is more than 35 days old → trigger Step 10 (Monthly Reminder) before proceeding.

3. **Identify the task** — use the routing table below.

---

## Task Router

| User says / submits | Jump to |
|---|---|
| Receipt image / photo (single file) | Step 2A |
| "Process my receipts" / "process receipts folder" | Step 2C |
| "Pull receipts from Gmail" / "sync Gmail receipts" | Step 2D |
| Bank statement (CSV or PDF) | Step 3 |
| "What am I missing?" / "Audit me" / "What do I need to fix?" | Step 9 |
| "Show me [Month] expenses" / dashboard | Step 7 |
| "Prepare my tax export" / "send to accountant" | Step 8 |
| "Is [X] deductible?" | Step 4 + `references/irs-categories.md` |
| "That category is wrong" | Step 5 (vendor KB update) |
| "Roast my expenses" / "roast me" / "tear me apart" | Step 13A |
| "Show me my coffee problem" / "show me my [X] problem" | Step 13B |
| "Tax panic mode" / "emergency" / "my accountant needs this [soon]" | Step 13C |
| "How bad is it" | Step 13D |
| "Deduction rescue" / "find me more deductions" | Step 13E |
| "Help me estimate my Q[X] payment" / "how much do I owe" / "calculate my estimated taxes" | Step 11A |
| "Switch to [YEAR] taxes" / "open [YEAR] ledger" / "work on [YEAR]" | Step 14 |
| First time / setup / "set me up" / "I need to set this up" | Step 12 |
| "I got paid" / "log income" / "I received a payment" / "log a sale" | Step 15 |
| "I got a 1099-K" / "1099-K reconciliation" / "PayPal / Stripe sent me a 1099" | Step 15 → 1099-K reconciliation in `references/income-tracking.md` |
| "I drove to" / "log a trip" / "log mileage" / "I drove [X] miles" | Step 16 |

---

## Step 1 — Session State

### Loading from config file (primary method)

At session start, resolve the skill directory from the path to this SKILL.md file, then try to Read `[SKILL_DIR]/config.json`. This file is created automatically during Step 12 setup — users never need to create or edit it manually.

**Config file format:**
```json
{
  "ledger_path": "[SKILL_DIR]/data/tax-2026/ledger.json",
  "income_path": "[SKILL_DIR]/data/tax-2026/income.json",
  "mileage_path": "[SKILL_DIR]/data/tax-2026/mileage.json",
  "vendors_path": "[SKILL_DIR]/data/tax-2026/vendors.json",
  "business_name": "Acme Consulting LLC",
  "tax_year": "2026",
  "entity_type": "sole proprietor",
  "receipts_folder": "[SKILL_DIR]/data/tax-2026/receipts/",
  "gmail_label": ""
}
```

If the file exists → extract all values from it, including `income_path` and `mileage_path` for use in Steps 8, 9, 15, and 16. Confirm in one line and proceed:
> *"Loaded: Acme Consulting LLC, 2026. What do you need?"*

**Older configs** (installed before income/mileage support was added) may be missing `income_path` and `mileage_path`. If either is absent, derive the default: replace `ledger.json` in `ledger_path` with `income.json` / `mileage.json`. These are the paths setup always creates. Update the config with the derived values the next time you write it.

If local mode and `ledger_path` file does not exist → warn the user and offer to re-run setup (Step 12).

If config file not found → also check for year-specific configs before triggering setup:
- Try `[SKILL_DIR]/config-[CURRENT_YEAR].json` and `[SKILL_DIR]/config-[PRIOR_YEAR].json`
- If year-specific configs exist but no default → list them: *"Found configs for: [years]. Which year do you want to work on?"*
- If nothing found anywhere → trigger Step 12 (first-time setup).


If entity type is **S-corp or C-corp**, flag that Schedule C rules may not apply — recommend confirming with their accountant.

---

## Step 2 — Receipt Extraction (Image or Email)

**Read `references/ocr-tips.md` before extracting from any image.**

### 2A — Receipt Image

Extract in priority order:
1. Vendor name (largest text, top of receipt)
2. Grand total — always post-tip, post-tax
3. Date → convert to YYYY-MM-DD
4. Last 4 digits of card if visible (used for bank matching)

Build transaction dict per schema in `references/local-file-mode.md`. Source field: `Bank Import` | `Photo Upload` | `Email Receipt` | `Manual`

If ANY field is unreadable → set `"unreadable"`, set `review_required: true`.

**Before creating a new record — check for an existing bank import to link:**
1. Read the ledger at `ledger_path`
2. Search for a transaction where: vendor fuzzy-match ≥70%, amount within ±$0.02, date within ±5 days, and `receipt_matched` is `false`
3. If a match is found → show the user: *"This looks like it matches [Vendor] on [Date] for $[Amount] already in your ledger. Link the receipt to that transaction? (yes / no / create new)"*
   - **Yes** → update existing record: `receipt_matched: true`, `receipt_path: [path]`; do NOT create a new transaction; skip Step 6 (store) for this receipt
   - **No / create new** → proceed to Step 4 + Step 6 as a new transaction
4. If no match found → proceed to Step 4 (classify), Step 6 (store) as a new transaction

→ Then Step 4 (classify), Step 6 (store) — only if no existing match was confirmed.

### 2B — Email or Photo Receipt

**Email receipts:** Extract from subject, sender, or body:
- Vendor (sender domain or subject line)
- Date (email date or "order date" in body)
- Amount ("Total charged", "Order total", "Amount due")
- Confirmation/order number → put in notes
- Set `source: "Email Receipt"`

**Phone photo receipts:** User snapped a photo of a paper receipt on their phone and uploaded it directly to Claude.
- Treat same as Step 2A (image extraction)
- Set `source: "Photo Upload"`
- If image quality is low → extract what you can, flag `review_required: true`
- No scanner or app needed — this is the recommended method for paper receipts

**Before creating a new record — apply the same bank import matching check from Step 2A.** Email and photo receipts frequently correspond to a bank import that already exists. Link if a match is confirmed; create new only if no match found.

→ Then Step 4 (classify), Step 6 (store) — only if no existing match was confirmed.

### 2C — Batch Receipts Folder

Trigger: user says "process my receipts", "process my receipts folder", "clear my receipt inbox"

**Read `references/batch-receipts.md` and follow the procedure from Step 1.**

---

### 2D — Gmail MCP Receipt Sync

Trigger: "pull my receipts from Gmail", "sync Gmail receipts", "check my email for receipts", "scan my email for receipts"

> **Platform note:** Gmail sync works natively on claude.ai (browser). If the user is on Claude Code CLI, check whether a Gmail MCP connection is available before proceeding. If no Gmail MCP is connected, lead with the workaround: *"The fastest path: open the receipt email, copy the body, save it as a .txt file in your receipts folder, then say 'process my receipts' — Claude parses it exactly the same as a Gmail sync, and it's zero setup. If you want live Gmail sync instead, say 'walk me through connecting Gmail' and I'll guide you through it (Rube MCP is the easiest route; manual Google Cloud OAuth takes about 30 minutes)."* Do not push OAuth — only go there if the user explicitly asks.

**Read `references/gmail-sync.md` and follow the procedure from Step 1.**

---

## Step 3 — Bank Statement Import

### Option A: Parser Script (preferred for CSV)

> **Always request CSV.** Bank CSV exports are clean and reliable. PDF parsing flags every transaction for manual review — bank PDFs have unpredictable layouts, columns frequently misparse, and some miss transactions entirely. If the user submits a PDF, warn them before parsing: *"PDF parsing is best-effort only — every transaction will be flagged for manual review. If your bank offers CSV export, that will be much faster and more accurate."* Then proceed if they confirm.

**Before running, ask the user:**
- What bank? (`chase`, `bofa`, `wells_fargo`, `amex`, `capital_one`, `generic`)
- Checking or credit card account? This controls the amount sign convention.

```bash
# Parse — credit card (positive = expense, e.g. Amex, Chase Sapphire)
python3 scripts/parse_bank_statement.py <file> --bank <bank_name> --account-type credit --account "Amex Gold" --output transactions.json

# Parse — checking/debit account (negative = expense, e.g. Chase checking, BofA checking)
python3 scripts/parse_bank_statement.py <file> --bank <bank_name> --account-type checking --account "Chase Checking" --output transactions.json

# Deduplicate
python3 scripts/detect_duplicates.py transactions.json --output clean.json
```

> **`--account` is required when importing multiple accounts.** It stamps every transaction with a card/account name so you can filter by source later (e.g. "show me only Amex charges"). Use any label that's meaningful to you: `"Amex Gold"`, `"Chase Checking"`, `"PayPal Business"`, etc.

Supported bank names: `chase`, `bofa`, `wells_fargo`, `amex`, `capital_one`, `generic`

> **Windows users:** Use `python` instead of `python3` if `python3 --version` returns "not found". Run `python scripts/parse_bank_statement.py ...` from Command Prompt.

> If user doesn't know which to use: credit cards always use `--account-type credit`; bank checking/debit accounts use `--account-type checking`. When in doubt, ask.

Report stats to user: how many transactions parsed, how many duplicates removed.

### Option B: Claude parses manually

For each row in the statement extract: vendor, date, amount, type (debit/credit).
Skip credits/refunds and internal transfers unless user requests them.

### After parsing — classify all transactions

For each transaction:
1. Look up vendor in the vendor knowledge base first (see Step 5)
2. If found → apply stored defaults
3. If not → classify via Step 4, add to vendor KB

### Batch import

**Local mode:** Read ledger.json → append all new transactions → Write back. Run in-memory duplicate check first (same vendor + amount within $0.02 + date within 3 days).


Report to user:
```
✅ Imported [X] transactions from [Month] statement
   • [X] auto-classified from vendor knowledge base
   • [X] classified fresh (added to vendor KB)
   • [X] flagged for review
   • [X] duplicates detected and merged
   • [X] missing receipts
```

If flagged + missing receipts total is 3 or more, add one line after the report:
> *Psst — type "roast me" if you want the unfiltered take on these numbers.*

**First bank import detection:** Before this import, check whether the ledger had zero Bank Import transactions. If it did (meaning this is the user's first statement), append this after the report (and after the roast hint if applicable):

```
Want to see this visually? Run this from your skill folder:

  python3 scripts/generate_dashboard.py

Then open dashboard.html in your browser — full breakdown by category,
spending heatmap, and quarterly tax estimate. Re-run it any time to refresh.
```

---

## Step 4 — IRS Expense Classification

**Read `references/irs-categories.md` for the full decision tree, all edge cases, and mandatory note requirements by category.**

For every transaction assign:

```json
{
  "business_or_personal": "business | personal | mixed | review_required",
  "deductible": true | false,
  "deductible_pct": 0-100,
  "category": "[irs-category-slug]",
  "review_required": false,
  "review_reason": ""
}
```

`deductible_pct` is always an integer 0–100. Never use a string like `"partial"`. The full decision tree and per-category note requirements are in `references/irs-categories.md` → "Classification Defaults".

---

## Step 5 — Vendor Knowledge Base

### Always look up before classifying

```
Read vendors_path → filter in-memory: vendor_name case-insensitive match
```

If found → apply `default_category`, `default_deductible`, and `default_deductible_pct` (if present in the KB entry). If `default_deductible_pct` is absent from the KB entry, default to 100 for fully deductible categories — but check Step 4 for categories that always require a specific %: `utilities` and `meals_entertainment` require the user to confirm the percentage before storing. Do NOT write 100 for these two categories if the KB entry has no explicit `default_deductible_pct`.
If not found → classify via Step 4, then add to KB.

### Add new vendor after classifying

Read vendors.json → append new vendor object → Write back.

### Update when user corrects a classification

Read vendors.json → find by vendor_name → update fields → Write back.

Confirm to user: *"Updated — [Vendor] will auto-classify as [Category] from now on."*

---

## Step 6 — Store Transaction

**Always run duplicate check before inserting.**

### Pre-write schema validation (run before every write)

Before appending any transaction to the ledger, validate the record. Do not write any record that fails validation — surface the problem instead.

**Required fields — reject if missing or null:**
- `vendor_name` — non-empty string
- `amount` — non-zero number
- `transaction_date` — ISO format YYYY-MM-DD
- `category` — must be a known IRS category slug (see `references/irs-categories.md`) or `"personal"`
- `deductible` — boolean `true` or `false`

**`deductible_pct` validation — this is the most common error:**
- Must be an **integer** in the range 0–100
- If it is a string (e.g. `"partial"`, `"50%"`, `"unknown"`): **reject** — do not write, do not silently convert. Set `deductible_pct: 0, review_required: true, review_reason: "Invalid deductible_pct — was a string. Confirm actual business-use %."` and alert the user: *"I caught an invalid deductible_pct before writing — it was '[value]' instead of a number. I've set it to 0% and flagged it for review. You can correct it now."*
- If it is `null` or missing: treat as `review_required: true` per Step 4 rules — ask for the %, do not guess
- If it is >100 or negative: reject with the same alert

**On validation failure:** Do not write the record. Surface the exact field and value that failed. Offer to fix it immediately before proceeding.

### Storing

See `references/local-file-mode.md` for file format and operation patterns.

1. Read ledger.json
2. Run pre-write schema validation (above) — stop and fix before proceeding if any check fails
3. Run in-memory duplicate check: same vendor (fuzzy), same amount (within $0.02), date within 3 days
4. If duplicate → show user both records, confirm before merging
5. Append transaction → Write ledger.json back using the **safe-write pattern** below
6. After writing, immediately Read the file back and confirm it parses as valid JSON — if it does not, alert the user immediately and do not proceed

Transaction ID format: `tx_YYYYMMDD_NNN` (e.g., `tx_20260315_001`). Increment NNN if multiple transactions on the same date.

**Safe-write pattern for ledger.json (local mode):**

Before any write that modifies the ledger (add, update, bulk import):
1. If the ledger has any existing transactions (1 or more), run `python3 scripts/backup_ledger.py [ledger_path]` first — this creates a timestamped backup in `backups/` before the write. Do not skip this for small ledgers — even a few months of records are worth protecting.
2. Write the updated array to `ledger_path`
3. Immediately Read `ledger_path` back — if it fails to parse or returns empty, surface this to the user: *"The ledger write may have failed or truncated. Your last backup is at `[ledger_path]/backups/ledger-backup-[timestamp].json`. Do not close this session — I can restore from backup if needed."*

### After storing

Confirm to user:
- Vendor, date, amount
- Category assigned
- Receipt matched status
- If flagged, why

---

## Step 7 — Monthly Dashboard

**HTML Dashboard (preferred):** When the user wants a visual browser-based dashboard, run:
```bash
python3 scripts/generate_dashboard.py
```
This reads ledger.json + income.json + mileage.json, generates `[tax_folder]/dashboard.html`, and tells the user to open it in their browser. The dashboard includes: expense breakdown by category, income section, mileage section, quarterly tax estimate, spending heatmap, and a paginated filterable transaction log. Re-run any time to refresh with current data.

**In-chat summary (fallback):** When the user wants a quick text summary, read ledger.json → filter in-memory: `transaction_date.startswith("YYYY-MM")`

Format output:
```
[Month Year] Expense Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Business Expenses:    $X,XXX.XX  ([X] transactions)
Est. Deductible:            $X,XXX.XX
Receipts Matched:           X of X
Missing Receipts:           X
Flagged for Review:         X

By Category:
  marketing_advertising     $XXX.XX  (X transactions)
  software_subscriptions    $XXX.XX  (X transactions)
  meals_entertainment       $XXX.XX  → 50% rule → deductible: $XXX.XX
  [etc.]

Top Vendors:
  1. [Vendor]  $XXX.XX
  2. [Vendor]  $XXX.XX

YTD Estimated Deductible:  $X,XXX.XX

Action Items:
  • [X] receipts still needed
  • [X] transactions to review
  [if Q est. tax due within 2 weeks]: Q[X] estimated tax due [DATE] — payment approaching
```

Always show meals as both gross and 50% net on separate lines.

If missing receipts + flagged total is 5 or more, add one line after the dashboard:
> *There are some commands that aren't in the menu — type "how bad is it" if you want the straight answer, no softening.*

---

## Step 8 — Tax Season Export

1. Get full ledger:
   - Use ledger.json at `ledger_path` directly.

2. Run export (include income and mileage if those files exist):
   ```bash
   python3 scripts/export_ledger.py ledger.json \
     --year [YEAR] --name "[Business Name]" --output-dir ./tax-export-[YEAR] \
     --income income.json \
     --mileage mileage.json \
     --html
   ```
   The `--html` flag generates a formatted HTML cover note alongside the text version. It requires no extra dependencies — open it in any browser and use File → Print → Save as PDF to get a clean, accountant-ready PDF.

3. Present all output files to user (up to 8 files):
   - `*-full.csv` — Complete categorized ledger with Deductible %, Deductible Amount, Receipt Path
   - `*-summary.csv` — Totals by category + IRS schedule references
   - `*-flagged.csv` — Items needing accountant attention
   - `*-missing-receipts.csv` — Undocumented transactions
   - `*-cover-note.txt` — Accountant briefing (plain text version)
   - `*-cover-note.html` — Print-ready accountant cover note (open in browser → Ctrl+P → Save as PDF)
   - `*-income.csv` — All income records (if `--income` provided)
   - `*-mileage.csv` — Full mileage log with totals (if `--mileage` provided)

Tell user: *"Send all files to your accountant. Open `*-cover-note.html` in your browser, print to PDF, and include that with the CSVs. Review the flagged file first — some items may just need a quick note from you."*

---

## Step 9 — Full Ledger Audit

When user asks "what do I need to fix?" or "audit me":

Get full ledger:
Use ledger.json at `ledger_path` directly.

Then run:

```bash
python3 scripts/monthly_reminder.py audit ledger.json \
  --vendors vendors.json \
  --mileage mileage.json
```

Pass `--vendors` and `--mileage` whenever those files exist — they enable W-9 coverage warnings and mileage log completeness checks in the audit output.

**Health score formula** (all percentages are relative to total transaction count; denominator floors at 10):
```
100 − (missing_receipts% × 40 + uncategorized% × 35 + flagged% × 15 + mixed_use% × 5 + contractor_warnings% × 5)
```
Missing receipts hurt the most (40 points). Uncategorized transactions second (35). Flagged items are fixable noise (15). Mixed-use and contractor warnings are minor (5 each). The denominator floors at 10 so a brand-new ledger with 3 transactions and 1 missing receipt scores ~96 (1/10) rather than 60 (1/3). A 500-transaction ledger with 25 missing receipts (5%) scores identically to a 50-transaction ledger with 5 missing receipts (5%).

Format results as:
```
LEDGER HEALTH AUDIT
━━━━━━━━━━━━━━━━━━━━
Health Score: [X]/100

ISSUES:
  [X] missing receipts
  [X] flagged for review
  [X] uncategorized
  [X] mixed-use needing business-% confirmed
  [X] equipment items for accountant review
  [X] contractors near 1099 threshold
  [X] meals missing business purpose notes

TOP 3 PRIORITIES:
1. [most impactful issue]
2. [second]
3. [third]

→ "Which would you like to tackle first?"
```

---

## Step 10 — Monthly Bank Statement Reminder

### When to trigger

- New session + new calendar month
- Last bank import > 35 days ago
- User asks "am I up to date?" or "what do I need to do?"

### Reminder format

```
MONTHLY REMINDER — [Last Month] Bank Statement

Your last import covered transactions through [date] ([X] days ago).

To catch up:
  1. Download [Last Month] statement from your bank as CSV
  2. Reply: "Here's my [Month] statement" + attach the file
  3. I'll handle the rest — usually takes 2 minutes

→ "Snooze [N] days" — if you need a few days
→ "Already done" — if you've already submitted it
```

### Snooze handling

```bash
python3 scripts/monthly_reminder.py snooze [N]
```

### Multiple accounts

Track each account separately using the `missing_by_account` key returned by `scripts/monthly_reminder.py check`. List all overdue accounts by name:
```
Statements needed for [Month]:
  • Chase checking  — missing
  • Amex card       — missing
  • PayPal business — imported
```
The `missing_by_account` dict is keyed by the `account` field on each Bank Import transaction. Accounts with no `account` field set appear under an empty string key — prompt the user to name their accounts during first-time setup.

---

## Step 11 — Quarterly Estimated Tax Reminders

Within 14 days of each due date, add to dashboard:

| Due Date | Covers |
|---|---|
| April 15 | Q1: Jan–Mar |
| June 15 | Q2: Apr–May only (not June) |
| September 15 | Q3: Jun–Aug |
| January 15 (next yr) | Q4: Sep–Dec |

> Note: Q2 covers only April and May — June income is reported in Q3 (due September 15). This is intentional per IRS Schedule. If users ask why June is missing from Q2, confirm: June belongs to the Q3 period.

```
Q[X] estimated tax due [DATE]
   YTD deductible: $X,XXX — this reduces your taxable income
   → Say "Help me estimate my Q[X] payment" to run through the numbers.
```

### Step 11A — Quarterly Tax Estimate (on request)

Trigger: "help me estimate my Q[X] payment", "how much do I owe", "calculate my estimated taxes", "what should I pay this quarter"

**Read `references/quarterly-estimate.md` and follow the calculation procedure.**

---

## Audit-Safety Guardrails

**Read `references/audit-guardrails.md` for the full rules table. Apply those rules every time a transaction is classified, reviewed, or stored.**

---

## Step 12 — First-Time Setup

> **NEW USER ENTRY POINT.** If you arrived here from the Document Map or from Step 1's "config not found" branch — this is exactly the right place.

Trigger when: user says "set me up", "first time setup", "I need to set this up", or when Step 1 cannot establish a storage backend.

**Read `references/setup-procedure.md` and follow it from the beginning.**

---

## Step 13 — Easter Eggs

**Read `references/response-modes.md` for full handling instructions.**

These commands are not listed in any documentation. Drop contextual hints at natural moments (hints already embedded in Steps 3 and 7). Never list all of them at once.

| Trigger | Step |
|---|---|
| "roast me" / "roast my expenses" / "tear me apart" / "be brutal" | 13A |
| "show me my [X] problem" / "how much am I spending on [X]" | 13B |
| "tax panic mode" / "emergency" / "accountant needs this [soon]" | 13C |
| "how bad is it" / "give it to me straight" / "what's the damage" | 13D |
| "deduction rescue" / "find me more deductions" / "am I missing anything" | 13E |

Silent easter eggs (fire automatically, no trigger needed) are also defined in `references/response-modes.md`.

---

## Step 14 — Multi-Year Support

**Trigger:** "switch to [YEAR] taxes", "work on [YEAR]", "open [YEAR] ledger", "I'm filing [YEAR]", "set up [YEAR]"

### Switching to an existing year

1. Try to Read `[SKILL_DIR]/config-[YEAR].json`
   - Found → load all session values from it, confirm: *"Switched to [YEAR]. [business_name]. What do you need?"*
   - Not found → go to "Setting up a new year" below

### Setting up a new year

If no config exists for the requested year:
> *"No [YEAR] ledger found. Want me to set one up? Takes about 60 seconds — I'll create a new ledger at `[SKILL_DIR]/data/tax-[YEAR]/` and save a separate config so both years stay accessible."*

If user confirms → run Step 12, but:
- Use `[SKILL_DIR]/data/tax-[YEAR]/` as the default path
- Write config to `[SKILL_DIR]/config-[YEAR].json` (year-specific, not the default path)
- Leave the existing default config untouched

### Config naming convention

| Scenario | Config file |
|---|---|
| Single year (default) | `[SKILL_DIR]/config.json` |
| Multi-year — year 1 | `[SKILL_DIR]/config-2025.json` |
| Multi-year — year 2 | `[SKILL_DIR]/config-2026.json` |

The default `[SKILL_DIR]/config.json` is always the fallback. Year-specific files take precedence when a year is explicitly requested.

### Scope note

This skill tracks both business expenses (ledger.json) and income (income.json) and mileage (mileage.json) — all separately, with clean audit trails. See Steps 15 and 16 for income and mileage logging.

---

## Step 15 — Income Logging

**Read `references/income-tracking.md` for full procedure, categories, and tax implications.**

Trigger: user says "I got paid", "log income", "I received a payment", "I made a sale", "I received a commission", or any similar phrase indicating money came in.

Quick procedure:
1. Ask for: source/payer, amount, date, what it was for (if not already clear)
2. Ask: "What platform or processor handled this payment?" (Stripe, PayPal, Venmo, Square, Amazon, ShareASale, ClickBank, Direct, etc.) — set `platform` field. Use `""` if paid by check, cash, or wire with no platform.
3. Assign income category from `references/income-tracking.md`
4. Ask: "Was this reported on a 1099?"
5. Write to `income.json` using the safe-write pattern (read → append → write → verify)
6. Confirm: *"Logged: $[X] from [Source] on [Date] as [category]. YTD gross income: $[sum]."*

**If user says "I got a 1099-K from [Platform]":** Read the 1099-K reconciliation procedure in `references/income-tracking.md` and follow it. Do not just log a single income record — the full reconciliation workflow applies.

Income ID format: `inc_YYYYMMDD_NNN` (use date of payment received).

---

## Step 16 — Mileage Log

**Read `references/mileage-log.md` for IRS requirements, qualifying trips, and commute rules.**

Trigger: user says "I drove to", "log a trip", "log mileage", "I drove [X] miles for business", or similar.

Quick procedure:
1. Ask for: date, start location (full address or clear description), end location, miles, business purpose (if not already clear)
2. If trip sounds like a commute (home → regular workplace), confirm before logging: "That sounds like a commute — commuting isn't deductible. Was there a separate business purpose?"
3. Ask: "Was this a round trip?"
4. Before writing: look up the IRS standard mileage rate for `tax_year` from session state:
   - `tax_year` = 2025 → `rate_per_mile` = 0.70
   - `tax_year` = 2026 → `rate_per_mile` = 0.725
   - Any other year → check `references/mileage-log.md` or irs.gov for the current rate
   Calculate: `deductible_amount = miles × rate_per_mile` (use `miles × 2 × rate_per_mile` if `round_trip: true`)
   Include both `rate_per_mile` and `deductible_amount` in the record — these are required by `export_ledger.py`; missing = $0 in all exports
5. Write to `mileage.json` using the safe-write pattern (read → append → write → verify)
6. Confirm: *"Logged: [X] miles on [Date] — [purpose]. Running [YEAR] total: [N] miles = $[sum of deductible_amount] estimated deduction at [rate × 100]¢/mile."*

Mileage ID format: `mi_YYYYMMDD_NNN` (use date of the actual trip).

**Rates:** 2025 = 70¢/mile | 2026 = 72.5¢/mile. Always match rate to `tax_year` from session state, not the current calendar date.