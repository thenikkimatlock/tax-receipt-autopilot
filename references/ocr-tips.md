<!-- Internal reference — Claude reads this file automatically. No need to open or edit it. -->
# OCR Tips for Receipt Extraction

## General Approach

When a receipt image is provided, extract text in this priority order:
1. Business/vendor name (usually largest text, top of receipt)
2. Total amount (look for "TOTAL", "AMOUNT DUE", "GRAND TOTAL", "BALANCE DUE")
3. Date (can appear at top or bottom — check both)
4. Payment method last 4 digits (helpful for bank matching)

---

## Common Receipt Formats

### Retail / Point of Sale
- Vendor name at very top (often uppercase)
- Date/time usually near top right
- Itemized list in middle
- Subtotal → Tax → **TOTAL** at bottom
- Card info + last 4 digits near bottom

### Email Receipts (HTML)
- Subject line often contains vendor name and amount
- Look for "Order Total", "Amount Charged", "You were charged"
- Date in email header or body
- Order confirmation number (useful for notes field)

### Invoice PDFs
- "Invoice" or "Bill" in header
- "Invoice Date" or "Bill Date"
- "Total Due", "Amount Due", "Balance Due"
- May have line items — capture the total, note line items in Notes field

### Bank Statement Rows
- Merchant name often truncated or coded (e.g., "AMZN MKTP US*A1B2C3")
- Date format varies by bank (MM/DD/YYYY most common)
- Amount column sign convention **depends on account type**:
  - Checking/debit accounts: negative = expense (debit), positive = deposit/income
  - Credit card statements: positive = charge (expense), negative = refund/credit
- Use `--account-type checking` or `--account-type credit` when running the parser script (see SKILL.md Step 3)

---

## Handling Difficult Receipts

### Low quality / blurry images
- Extract what is readable
- Set unreadable fields to `"unreadable"`
- Always flag `review_required: true`
- Note in review_reason: "Receipt image low quality — manual verification needed"

### Handwritten receipts
- Look for printed vendor name (letterhead or stamp)
- Date and total may be handwritten
- Extract best estimate and flag for review

### Foreign currency receipts
- Capture the amount in the original currency AND note the currency code
- If USD equivalent is visible, use that
- Otherwise: note "Foreign currency — USD conversion needed" in review_reason
- Flag for review

### Receipts with multiple payment methods (split payments)
- Capture the total transaction amount
- Note in Notes: "Split payment: $X cash + $Y card"

### Subscription receipts (recurring)
- These often look identical month to month
- Run duplicate check: same vendor + same amount within 25-35 days = likely recurring
- If duplicate detection triggers, confirm it's a new billing period before merging

### Restaurant receipts
- Look for two totals: pre-tip and post-tip
- Use the **post-tip total** (what was actually charged to the card)
- Note: "Includes tip" in Notes
- **Default classification: personal** — most restaurant charges are personal expenses
- Only classify as `meals_entertainment` if the user explicitly confirms it was a business meal (specific person, specific business purpose)
- Ask: "Was this a business meal or personal?" before storing if context is unclear
- If confirmed business meal: note "50% deductible. Business purpose: [user's answer]. Attendees: [user's answer]."

### Hotel folio receipts
- Hotel checkout folios often have multiple line items: room rate, taxes, resort fees, parking, room service, phone charges, minibar
- Capture the **total folio amount** as the transaction amount
- Note individual line items in the Notes field if they include non-deductible personal items (e.g., minibar, personal movies)
- Room rate + taxes = deductible business travel; personal charges are not
- If folio mixes business and personal charges, note both amounts and flag for review: "Hotel folio $XXX.XX — room rate $XXX.XX deductible, personal charges $XX.XX non-deductible"
- Business purpose note required: destination and purpose of trip

### Gas station receipts
- Capture the total fuel purchase amount
- Always flag with `review_required: true` — deductibility depends entirely on the vehicle expense method being used
- If using **standard mileage rate** (the common method for sole proprietors): gas is NOT separately deductible. The mileage deduction (miles × rate) already covers all vehicle operating costs including fuel. Do not add a separate deduction. Mark as non-deductible or personal.
- If using **actual expense method**: gas is deductible as a vehicle operating cost. Classify as `other_business` and note "Actual expense method — vehicle operating cost. Business-use % required." (Do NOT classify as `vehicle_mileage` — that category in this system represents the mileage-rate deduction, not individual vehicle expense line items.)
- Flag every gas purchase with review note: "Confirm vehicle expense method (standard mileage vs actual). If using standard mileage rate, this is not separately deductible."
- Ask the user: "Are you using the standard mileage rate or actual expenses for this vehicle?"

### Receipt vs. bank statement merchant name mismatch
- Common issue: receipt says "Starbucks" but bank statement says "SQ *STARBUCKS" — these are the same transaction
- Matching indicators: same amount, same date (within 1-2 days), consistent vendor name after normalization
- When matching a receipt to a bank import, update the bank record's `receipt_matched = true`
- Store the normalized name in the vendor KB so future auto-matching works
- If names are very different (e.g., parent company vs brand name), add a note in the Vendor KB: "Also appears as [bank name]"

---

## Vendor Name Normalization

When extracting vendor names, normalize for matching:

| Raw from receipt | Normalized |
|---|---|
| AMZN MKTP US*A1B2 | Amazon |
| SQ *COFFEE SHOP NAME | [Coffee Shop Name] |
| PAYPAL *VENDORNAME | [Vendor Name] |
| META*ADS | Meta Ads |
| GOOGLE*ADS | Google Ads |
| VZWRLSS*MYVZW | Verizon Wireless |
| TST* RESTAURANT NAME | [Restaurant Name] |
| UBER* TRIP | Uber |
| LYFT *RIDE | Lyft |

Store both the raw name (from bank) and the normalized name (for KB matching).

---

## Date Extraction Tips

Try these patterns in order:
1. Full date: `March 15, 2025` or `15 March 2025`
2. Numeric: `03/15/2025` or `03-15-25` or `2025-03-15`
3. Short: `3/15/25`
4. If only month/year visible: set day to `01` and flag for review

If no date found at all: use today's date as a fallback but flag `review_required: true` with reason "No date found on receipt."

---

## Amount Extraction Tips

- Always capture the **final total** (after tax, after tip)
- If you see multiple "total" figures, use the largest one (grand total)
- Strip currency symbols before storing (`$47.99` → `47.99`)
- Watch for comma-separated thousands (`$1,250.00` → `1250.00`)
- If amount is ambiguous, flag for review — never guess