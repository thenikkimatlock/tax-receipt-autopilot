<!-- Internal reference — Claude reads this file when Step 12 is triggered. No need to open or edit it. -->
# First-Time Setup Procedure

Triggered by: "set me up", "first time setup", "I need to set this up", or when Step 1 cannot establish a storage backend.

---

## Setup

> **Privacy note:** Your financial data lives in plain JSON files on your computer (`ledger.json`). This is readable by anyone with file-system access to that path. If you share your computer or have sensitive data, keep the tax folder somewhere only you can access. The data never leaves your machine unless you manually copy it.
>
> **To encrypt your tax folder** (optional but recommended if others have access to your machine):
> - **Windows**: Right-click the tax folder → Properties → Advanced → "Encrypt contents to secure data" (requires Windows Pro/Enterprise BitLocker). Or use **7-Zip**: right-click the folder → 7-Zip → Add to archive → set Encryption method to AES-256 and enter a strong password. Keep the unencrypted folder for daily use; archive+encrypt before sharing or storing off-device.
> - **Mac**: Open Disk Utility → File → New Image → Image from Folder → select your tax folder → set Encryption to AES-256 → save as a `.dmg`. Mount it to work with files; eject it when done.
> - **Cross-platform**: [VeraCrypt](https://veracrypt.fr) (free, open source) creates an encrypted container that works on Windows, Mac, and Linux. Create a container file, mount it as a virtual drive, store your tax folder inside it. Unmounting locks it automatically.

1. Ask: "Where do you want to store your tax files? Default: `[SKILL_DIR]/data/tax-[YEAR]/` (inside this repo, keeps everything together) — or tell me a different path. If you want access from multiple devices, you can point this to a Dropbox or Google Drive folder and the ledger will sync automatically (it's under 200KB all year)."
2. Ask (if not already known): business name, tax year, entity type.
3. Create data files and receipts folder:
   - Write `[path]/ledger.json` with content: `[]`
   - Write `[path]/income.json` with content: `[]`
   - Write `[path]/mileage.json` with content: `[]`
   - Write `[path]/vendors.json` with content: `[]`
   - Write `[path]/receipts/.gitkeep` with content: `` (empty file — this creates the receipts folder so it's ready immediately)
4. Seed vendors.json: read `references/vendors.md` → use the JSON block at the bottom of that file → write the complete array to vendors.json.
5. Write the config file to `[SKILL_DIR]/config.json`:
   ```json
   {
     "ledger_path": "[FULL_EXPANDED_PATH]/ledger.json",
     "income_path": "[FULL_EXPANDED_PATH]/income.json",
     "mileage_path": "[FULL_EXPANDED_PATH]/mileage.json",
     "vendors_path": "[FULL_EXPANDED_PATH]/vendors.json",
     "business_name": "[BUSINESS_NAME]",
     "tax_year": "[YEAR]",
     "entity_type": "[ENTITY_TYPE]",
     "receipts_folder": "[FULL_EXPANDED_PATH]/receipts/",
     "gmail_label": ""
   }
   ```
   Use the full absolute path (e.g. `C:/Users/Name/repos/tax-receipt-autopilot/data/tax-2026/ledger.json`) — not `~` shorthand, so the config is portable. `[SKILL_DIR]` is the directory containing SKILL.md.
6. Set session state from the config values.
7. **Multi-year check:** If `[SKILL_DIR]/config.json` already exists with a different `tax_year` → offer to save this new config as a year-specific file instead: `[SKILL_DIR]/config-[YEAR].json`. Say: *"You already have a config for [existing year]. I'll save this one as `config-[NEW_YEAR].json` inside the skill folder so both years stay accessible. Say 'switch to [YEAR] taxes' anytime to change years."* Save to the year-specific path.
8. Output the setup complete message (see Phase 2 below).

---

## Phase 2 — Setup Complete

```
TAX RECEIPT AUTOPILOT — Setup Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Here's what's live:
  ledger.json — created at [ledger_path]
  income.json — ready for client payments + affiliate commissions
  mileage.json — ready for business trips
  vendors.json — [N] vendors pre-classified
  receipts/ — folder ready at [receipts_folder]
  Config saved — [SKILL_DIR]/config.json
  No accounts required — your data stays on your computer

You're ready to go. Here's what to do next:

  1. Download last month's bank statement as CSV
  2. Come back and say: "Here's my [Month] statement" + attach it
  3. I'll handle everything — takes about 2 minutes

Your settings are saved. No need to paste anything at the start of
future sessions — I'll load your config automatically.
```
