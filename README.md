# Tax Receipt Autopilot

**Turn Claude Code into a year-round bookkeeper, no accountant, no app, no cloud account required.**

---

Tax Receipt Autopilot is a Claude Code skill that handles the entire expense tracking and tax prep workflow for freelancers, solo operators, and small business owners. Drop receipts into a folder and say "process my receipts," sync receipt emails directly from Gmail, or attach a bank statement CSV. Claude classifies everything against real IRS Schedule C categories, detects duplicates, tracks missing documentation, and builds an audit-ready ledger all year.

At tax time: one command generates accountant-ready files, full ledger, category summary, flagged items, missing receipts, and a cover note your CPA can actually use. No separate app. No subscription. No starting from scratch every April.


---

## What It Does

**Keeps taxes done before you know it.**
Every receipt, every monthly bank statement, every digital confirmation feeds the same running ledger all year. When April arrives, run one command and get 5 accountant-ready files: full ledger, category summary with Schedule C line references, flagged items, missing receipts list, and an accountant cover note. No scrambling. No data entry marathon.

**Actual IRS accuracy, not vibes.**
Categories map to real Schedule C lines. The 50% meals limitation is enforced: you cannot accidentally deduct a full business lunch. Equipment over $2,500 gets flagged for Section 179 review. Contractor payments are tracked against the 1099-NEC threshold (updated for OBBBA 2025: $600 for 2025 payments, $2,000 for 2026+). A vendor knowledge base auto-classifies 40+ common tools (Canva, OpenAI, Meta Ads, Stripe, etc.) from day one.

**Monthly routine is 2 minutes.**
Download your bank statement. Say "here's my March statement" and attach the CSV. Claude parses it, removes duplicates using fuzzy matching (catches "AMZN MKTP" = Amazon), classifies every line, and shows you what needs review.

---

## Installation

### Step 1: Get the skill

Copy this folder into your Claude Code skills directory:

```
.claude/skills/tax-receipt-autopilot/
```

> Claude Code automatically picks up any skill in `.claude/skills/`, no registration needed. Once this folder is in place, Claude reads `SKILL.md` and the skill is live in every session.

### Step 2: Install Python dependencies (for CSV/PDF bank statement parsing)

**Mac/Linux:**
```bash
bash .claude/skills/tax-receipt-autopilot/install.sh
```

**Windows:**
```bat
.claude\skills\tax-receipt-autopilot\install.bat
```

**Manual:**
```bash
pip install -r .claude/skills/tax-receipt-autopilot/scripts/requirements.txt
```

> Python is only needed for bank statement parsing. You can use the skill without it, just paste bank rows directly into Claude, or submit receipt photos one at a time.

### Step 3: Start tracking

Say to Claude:
```
Set up Tax Receipt Autopilot for me
```

Claude creates your ledger, seeds the vendor knowledge base, and saves your config automatically. Takes about 2 minutes. No need to paste anything at the start of future sessions, your settings are remembered.

> **Claude Code users:** During setup, Claude will ask for permission to write your ledger, vendor KB, and config file. Approve all three, these are the only files the skill writes to your system.

### Platform Notes

| Feature | claude.ai (browser) | Claude Code (CLI) |
|---|---|---|
| Receipt photos | Native, attach directly | Native, attach directly |
| Bank statement CSV | Native, attach directly | Native, attach directly |
| Gmail sync | Native, no setup | Workaround: copy email body to a .txt file → receipts folder → "process my receipts" (zero setup). Or: Rube MCP (easy) / manual OAuth (~30 min). |
| Python scripts | N/A | Full support |
| Dashboard HTML | N/A | Run `generate_dashboard.py` |

**Gmail on Claude Code CLI:** Gmail sync requires either the Rube MCP server (if configured) or a manual OAuth setup, see `references/gmail-sync.md` for both paths. If you'd rather skip it, use the receipts folder workaround: copy the email body to a `.txt` file, drop it in your receipts folder, say "process my receipts." Same result.

---

## What Local Mode Looks Like

No separate app, no spreadsheet to maintain. Claude is the interface.

- **Daily use**: Attach a receipt image or bank statement CSV and Claude processes it. Confirmation shows in the chat with vendor, amount, category, and receipt status.
- **Monthly check-in**: Say "Show me my March dashboard", Claude reads your ledger and returns a formatted expense breakdown with deductible totals, missing receipts, and top vendors.
- **Audit**: Say "What do I need to fix?", Claude scores your ledger health and lists every issue with a priority order.
- **Tax time**: Say "Generate my 2026 tax export", five CSV files land in a folder on your computer, ready to email to your accountant or open in Excel/Google Sheets yourself.

Your ledger is a JSON file on your computer. You never need to open it, Claude reads and writes it for you. If you want a persistent visual spreadsheet to browse outside of Claude at any time, open the CSV export in Excel, Numbers, or Google Sheets.

---

---

## Quick Commands

| Say this | What happens |
|---|---|
| `Set up Tax Receipt Autopilot for me` | First-time setup wizard |
| `Here's my March bank statement` + attach CSV | Parses, deduplicates, classifies, imports |
| `Process my receipts` | Batch-processes all files in your receipts folder |
| `Pull my receipts from Gmail` | Gmail sync, works natively on claude.ai. Claude Code CLI: requires Rube MCP or manual OAuth setup (~30 min). No Gmail? Use the receipts folder: copy email body to a .txt file, drop in your receipts folder, say "process my receipts." Same result. |
| `Here's a receipt` + file path or pasted text | Single receipt, extracts, classifies, stores |
| `Show me my March dashboard` | Monthly summary with deductible totals |
| `What do I need to fix?` | Full audit with health score |
| `Generate my 2025 tax export` | 5 accountant-ready files |
| `Is [vendor] deductible?` | IRS category lookup |

---

## Monthly Import Cadence

**Bank statements do not import themselves.** This is a manual step, and it's the most important recurring action in the system. The skill tracks the date of your last import and will remind you when you're overdue, but you still have to initiate it.

**The routine (takes 2 minutes):**
1. Log into each bank/card account you use for business
2. Download last month's statement as CSV (not PDF, every bank has CSV export; look for "Download," "Export," or "Statements" in your account history)
3. Tell Claude: "Here's my [Month] statement" + attach the file
4. Claude parses, deduplicates, classifies, imports, done

**How often:** Once a month, first week of the following month. If you let it slip two or three months, catching up is still possible but takes longer, you'll have more transactions to review and more potential duplicates to sort through.

**Multiple accounts:** If you use multiple cards or accounts for business, import each one separately. Claude tracks which accounts have been imported and will flag which ones are overdue.

**What happens if you skip:** The skill still works for receipt logging and deductibility questions, but your monthly dashboard and YTD deductible totals will be incomplete. The quarterly tax estimate will also be based on partial data. For the system to work at its best, bank statement imports should be current.

---

## What's in the Box

```
tax-receipt-autopilot/
├── SKILL.md                      # Core skill, Claude's operating instructions
├── README.md                     # This file
├── install.sh                    # Mac/Linux: installs Python deps in one command
├── install.bat                   # Windows: installs Python deps in one command
├── references/
│   ├── setup-procedure.md        # Step-by-step setup procedure (internal, Claude reads this)
│   ├── irs-categories.md         # All 16 Schedule C categories with edge cases
│   ├── ocr-tips.md               # Receipt image extraction guide
│   ├── batch-receipts.md         # Folder-based batch receipt processing workflow
│   ├── gmail-sync.md             # Gmail MCP receipt sync procedure
│   ├── vendors.md                # 61 pre-classified vendors (auto-seeded at setup)
│   ├── local-file-mode.md        # Local JSON file format and operation patterns
│   ├── income-tracking.md        # income.json schema and 8 income categories
│   ├── mileage-log.md            # IRS mileage logging requirements and rates
│   ├── quarterly-estimate.md     # Federal/state tax calculation with safe harbor rules
│   ├── response-modes.md         # Easter egg command formats (roast, panic, deduction rescue)
│   └── example-ledger.json       # Example transaction record structure
└── scripts/
    ├── requirements.txt           # Python dependencies
    ├── generate_dashboard.py      # Generates standalone dashboard.html in tax folder (open in browser)
    ├── parse_bank_statement.py    # CSV/PDF bank statement parser (Chase, BofA, Amex, etc.)
    ├── detect_duplicates.py       # Fuzzy duplicate detection and merge
    ├── export_ledger.py           # Generates 5–8 accountant-ready files (ledger, summary, flagged, missing receipts, cover note + optional income, mileage, HTML)
    ├── monthly_reminder.py        # Health score, audit, monthly summary (3 modes: check/audit/summary)
    └── backup_ledger.py           # Timestamped ledger backup to backups/ subfolder
```

---

## Hidden Modes

Not everything is in the quick commands table. Use the skill and pay attention.

---

## Who It's For

- Freelancers and consultants who hate bookkeeping but hate surprises at tax time more
- Solo operators running on Claude Code who want their financial records in the same place as everything else
- Anyone who has ever paid a CPA to organize receipts that should have been organized in January

---

## What the Tax Export Looks Like

Running `Generate my 2026 tax export` produces 5 files in a folder on your computer. Here's what your accountant actually receives.

**`*-summary.csv`**, the one your CPA opens first:

```
Category,Schedule Reference,Transaction Count,Total Spent,Est. Deductible Amount,Notes
Software & Subscriptions,Sch C Line 18,24,$847.76,$847.76,
Marketing & Advertising,Sch C Line 8,8,$2340.00,$2340.00,
Meals (50% deductible),Sch C Line 24b,6,$284.50,$142.25,50% deductible limitation applies (TCJA)
Equipment / Depreciation,Sch C Line 13,1,$1899.99,$1899.99,May qualify for Section 179 or MACRS depreciation
Contract Labor,Sch C Line 11,3,$4500.00,$4500.00,
,,,,
GRAND TOTAL,,42,$9872.25,$9729.25,
```

**`*-cover-note.txt`**, explains every issue to your accountant so you don't have to:

```
TAX EXPORT — ACCOUNTANT COVER NOTE
====================================
Business:     My Business LLC
Tax Year:     2026
====================================

SUMMARY
-------
Total Business Transactions:   42
Total Business Spending:       $9,872.25
Estimated Deductible Total:    $9,729.25
Transactions Missing Receipts: 3
Transactions Flagged for Review: 2

MEALS & ENTERTAINMENT ($284.50 total):
  - 50% deductible limitation applies per TCJA 2018
  - Deductible portion already calculated as $142.25
  - Please verify business purpose documentation for each meal

MISSING RECEIPTS (3 transactions):
  - See *-missing-receipts.csv for full list
  - IRS requires substantiation for all business deductions
```

The other three files: `*-full.csv` (every transaction with categories), `*-flagged.csv` (items needing accountant review), `*-missing-receipts.csv` (undocumented transactions).

---

## Supported Banks (CSV Parsing)

Chase, Bank of America, Wells Fargo, American Express, Capital One, and any bank with a generic CSV export.

**Always download CSV, every bank has it.** Log into your bank portal, go to account history, and look for "Download," "Export," or "Statements." Select CSV or Excel (Excel exports as CSV). It takes 30 seconds and produces clean, reliable data.

PDF is a last resort, not an option. The PDF parser flags every transaction for manual review because bank PDFs have unpredictable layouts, columns misparse, running totals get picked up as transactions, and some PDFs miss line items entirely. If you submit a PDF, treat the output as a rough draft that needs verification row by row. If your bank only offers PDF exports, call them and ask for CSV, all major banks support it.

---

## Local Mode: Privacy Note

In local mode, your ledger is a plain JSON file on your computer. It's not encrypted. Anyone with access to that path can read it, including other users on a shared machine and any application with file-system access.

**Basic precautions:**
- Store the tax folder in a location only your user account can access (not Desktop, not a shared folder)
- Never commit the tax folder to a git repository

**Cross-device access (optional):** Storing the tax folder inside your personal Dropbox or Google Drive folder is a simple way to access your ledger from multiple computers. The folder stays under 200KB all year, so sync is near-instant. Use a private folder, not a shared or team drive, and make sure you trust the cloud provider with financial data before enabling this. Alternatively, keep the folder local and run the tax export when you need to move data.

**If you want encryption (recommended for shared machines):**

- **Windows**: Enable BitLocker on the drive, or use 7-Zip, right-click the tax folder → 7-Zip → Add to archive → set a password and select AES-256 encryption. The resulting `.7z` file is strongly encrypted; delete the unencrypted folder afterward.
- **Mac**: Open Disk Utility → File → New Image → Image from Folder → select the tax folder → set encryption to AES-256 → save as a `.dmg`. Mount it when working, eject when done.
- **Cross-platform (free)**: VeraCrypt creates an encrypted container that works on Windows, Mac, and Linux. Store the container anywhere, including cloud storage, and it stays encrypted until you mount it with your password.

A full year of data is under 200KB, so any of these options adds negligible overhead.

---

## IRS Compliance Notes

- Categories map to Schedule C (Form 1040), sole proprietors and single-member LLCs
- S-corps and C-corps: the skill flags that Schedule C rules may not apply and recommends accountant review
- All deductible amounts are federal estimates, state treatment may differ
- **Income and mileage tracking are included.** In addition to expenses, the skill tracks business income (Step 15, `income.json`) and vehicle mileage (Step 16, `mileage.json`) in separate ledger files. Both feed into the tax export: the income file produces a gross income total and net profit estimate; the mileage file produces a deductible mileage amount at the IRS standard rate. Say "I got paid" to log income, or "I drove to [location]" to log a trip.
- **Quarterly estimated tax estimates:** When a quarterly payment deadline is approaching, say "Help me estimate my Q[X] payment." Claude will use your YTD deductible total from the ledger plus your estimated gross income (you provide this when asked) to walk through the SE tax and income tax calculation. This is an estimate to help you ballpark, your accountant confirms the final number.
- **Multiple tax years:** Each year gets its own ledger and config. Say "switch to 2025 taxes" or "set up my 2025 ledger" to work on a prior year. See `references/local-file-mode.md` for managing multiple years.
- This is organizational tooling, not tax advice. Use it with a real accountant.

---

## Credits

Built by Nikki Matlock.
Skill type: Productivity / Finance / Tax Prep
Trigger phrases: "receipts", "expense tracking", "tax deductions", "bank statement", "is this deductible"
