<!-- Internal reference — Claude reads this file when Step 2C is triggered. No need to open or edit it. -->
# Batch Receipts Folder — Processing Procedure

Triggered by: "process my receipts", "process my receipts folder", "clear my receipt inbox"

This is the primary receipt workflow for Claude Code users. Instead of submitting one receipt at a time, the user drops all files into a single folder throughout the week/month, then processes everything in one command.

---

## Step 1 — Find the folder

Use `receipts_folder` from session state, or default to `[SKILL_DIR]/data/tax-[YEAR]/receipts/`. If neither exists, ask: *"Where do you want your receipts folder? Default: `[SKILL_DIR]/data/tax-[YEAR]/receipts/`"* then create it.

---

## Step 2 — List all files

Read the directory. Supported: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` (images), `.pdf` (PDF receipts/invoices), `.txt`, `.md`, `.eml` (pasted email content).

If no files: *"Your receipts folder is empty. Drop receipt images, PDFs, or saved email text files in `[path]` and run this again."*

---

## Step 3 — Process each file sequentially

For each file:
1. Read/view the file
2. Extract using Step 2A (images) or 2B (text/email files) from SKILL.md
3. Apply the receipt-to-ledger matching check from Step 2A: search for an existing bank import with vendor fuzzy ≥70%, amount ±$0.02, date ±5 days, and `receipt_matched: false`. If a match is found, update that transaction (`receipt_matched: true`, `receipt_path: [path]`) and skip to the next file — do not create a new record.
4. If no match found: classify via Step 4, run duplicate check (Step 6), then store as a new transaction with `receipt_matched: true` and `receipt_path: [relative or absolute path to this file]`

**`receipt_path` convention (local mode):** Use the absolute path if the file will stay in place, or the path after archiving if the user chooses to archive (e.g., `[SKILL_DIR]/data/tax-2026/receipts/processed/2026-03/receipt_starbucks_0312.jpg`). This links the transaction to the physical file for audit purposes.

Show a running count: `[3/12] Processing receipt_starbucks_0312.jpg...`

---

## Step 4 — Report

```
RECEIPTS PROCESSED — [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total files:     [N]
Logged:          [N]  (new transactions added)
Skipped:         [N]  (duplicates already in ledger)
Flagged:         [N]  (need review)
Unreadable:      [N]  (image quality too low)

Flagged for review:
  • [filename] — [reason]
  • [filename] — [reason]
```

After processing, ask: *"Archive processed files to `[receipts_folder]/processed/[YYYY-MM]/`, or leave them in place?"*

If archive:
1. Create the destination folder using Bash: `mkdir -p "[receipts_folder]/processed/[YYYY-MM]"` (Mac/Linux) or `mkdir "[receipts_folder]\processed\[YYYY-MM]"` (Windows)
2. Move each successfully processed file using Bash: `mv "[file]" "[receipts_folder]/processed/[YYYY-MM]/"` (Mac/Linux) or `move "[file]" "[receipts_folder]\processed\[YYYY-MM]\"` (Windows)
3. If Bash permission is denied: inform the user — *"Moving files requires shell access. You can manually drag the processed files to `[receipts_folder]/processed/[YYYY-MM]/` yourself, or I can leave them in place."*

Does NOT delete any files. Only moves to archive if user confirms and Bash permission is granted.
