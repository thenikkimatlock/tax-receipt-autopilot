<!-- Internal reference — Claude reads this file when Step 15 is triggered. No need to open or edit it. -->
# Income Tracking

Tax Receipt Autopilot tracks income separately from expenses in `income.json`. This enables accurate net profit estimates, self-employment tax estimates, and a complete picture for your accountant — not just one side of the ledger.

---

## When to Use This

Log income when the user mentions:
- "I got paid"
- "A client paid me"
- "I made a sale"
- "I received a commission"
- "PayPal / Stripe / Venmo payment came in"
- "I received a refund" (from a vendor — counts as reducing expenses, not income — see below)

---

## income.json Schema

```json
[
  {
    "id": "inc_YYYYMMDD_NNN",
    "source": "Client Name or Platform",
    "platform": "Stripe",
    "description": "Brief description of what this payment was for",
    "date": "YYYY-MM-DD",
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

**Field rules:**
- `id`: format `inc_YYYYMMDD_NNN` — today's date + 3-digit counter starting at 001
- `amount`: positive number, no currency symbol, no commas
- `platform`: the payment processor or marketplace that actually moved the money. Examples: `"Stripe"`, `"PayPal"`, `"Venmo"`, `"Square"`, `"Amazon"`, `"Etsy"`, `"ShareASale"`, `"ClickBank"`, `"Direct"`. Leave empty string `""` if paid by check, cash, or wire with no platform involved. This field drives 1099-K reconciliation — if you receive a 1099-K from a platform, you can match it against all records with that `platform` value.
- `category`: use one of the income categories below
- `1099_reported`: set to `true` if the payer issued a 1099-NEC or 1099-K for this amount
- `review_required`: set to `true` if anything is unclear or needs accountant attention

---

## Income Categories

| Category | Use For |
|---|---|
| `services` | Client payments for services rendered (consulting, design, writing, coaching, etc.) |
| `product_sales` | Digital or physical product sales |
| `affiliate_commissions` | Affiliate marketing commissions |
| `course_revenue` | Online course or training program sales |
| `ad_revenue` | YouTube AdSense, blog ads, platform monetization |
| `subscription_revenue` | Recurring membership or SaaS revenue |
| `refund_received` | Money received back from a vendor (reduces expenses — see note below) |
| `other_income` | Any income that doesn't fit a more specific category |

**Refund received note:** If a vendor refunds money you previously paid, it reduces your expenses — it is NOT new income. Log as `refund_received` and add a note indicating which expense it offsets. Your export will handle this correctly.

**Affiliate commissions note:** `affiliate_commissions` is Schedule C self-employment income. It is subject to SE tax (15.3% on net earnings up to the SS wage base) in addition to ordinary income tax — the same as any other self-employment income. There is no special rate or exemption. Always include affiliate income in SE tax estimates; never treat it as passive or capital income.

---

## How to Log Income

When user says they received a payment:

1. Ask (if not already clear): source/payer, amount, date, what it was for
2. Assign an income category
3. Ask: "Was this reported on a 1099?" — set `1099_reported` accordingly
4. Write to `income.json` (same safe-write pattern as ledger.json: read → append → write → verify)
5. Confirm: "Logged: $[X] from [Source] on [Date] as [category]."

**ID format:** `inc_YYYYMMDD_NNN` — use today's date. If multiple income records on the same date, increment NNN.

---

## Tax Implications

### Self-Employment Tax
All self-employment income is subject to SE tax (15.3% on net earnings up to the Social Security wage base, 2.9% above that). This is on top of income tax. Never omit this from estimates.

### 1099-NEC / 1099-K
- If a client pays you directly: threshold varies by tax year
  - 2025 payments: $600+ triggers a 1099-NEC
  - 2026 payments: $2,000+ triggers a 1099-NEC (raised by OBBBA, signed July 4, 2025)
- Stripe, PayPal, Venmo, Square, and other third-party payment platforms issue 1099-K when gross payments exceed the reporting threshold
  - 2025 and 2026 threshold: $20,000 AND more than 200 transactions (OBBBA permanently restored the original threshold retroactively — the planned $5,000 for 2025 and $600 for 2026 were never implemented)
  - Both conditions must be met — either one alone does NOT trigger 1099-K reporting
  - Payment card processors (credit/debit card transactions through banks): no minimum threshold — any amount may be reported
  - Some states have lower thresholds (e.g., Vermont, Massachusetts, Virginia, Maryland: $600) — verify your state
- Flag any income where `1099_reported` is `false` AND the payer likely should have issued one — note in `review_reason`
- You must report ALL income whether or not you receive a 1099 — reporting thresholds affect payer obligations, not your tax liability

### Gross Income vs. Taxable Income
- Gross income = sum of all income records
- Taxable income = gross income minus deductible business expenses (from ledger.json)
- Net profit estimate shown in monthly summary and tax export is: gross income - total deductible expenses
- Self-employment tax is calculated on 92.35% of net profit (the 7.65% reduction accounts for the deductible half of SE tax)

---

## Monthly Summary Integration

When running a monthly summary (`summary` subcommand with `--income`), Claude reports:
- Month income: total income received in the requested month
- YTD income: cumulative income through end of requested month
- Month expenses: total business expenses
- YTD deductible: cumulative deductible expenses
- Net profit estimate (YTD): YTD income minus YTD deductible expenses
- Estimated SE tax: net profit × 0.9235 × 0.153 (simple estimate — actual may differ)

---

## 1099-K Reconciliation

**Trigger:** User receives a 1099-K form from a payment platform (Stripe, PayPal, Venmo, Square, Amazon, etc.).

A 1099-K reports the gross payments a platform processed for you — it does NOT account for refunds, chargebacks, fees, or returns. The number on the form will typically be higher than your actual net income. You must still report the correct taxable income, not the 1099-K gross — but you need to be able to explain the difference if the IRS asks.

### Reconciliation procedure

1. **Identify the platform** — note which platform issued the 1099-K (e.g., "Stripe issued me a 1099-K for $8,400").

2. **Pull all income records for that platform** — filter income.json by `platform` field:
   - Read income.json → filter where `platform == "[Platform Name]"` AND `date.startswith("[TAX_YEAR]")`
   - Sum those records → this is your logged gross for that platform

3. **Compare totals:**
   - If logged gross ≈ 1099-K gross (within a few dollars) → set `1099_reported: true` on all matching records; done.
   - If 1099-K gross > logged gross → likely missing income records. Ask the user: "Your 1099-K from [Platform] shows $[X] but I only have $[Y] logged. Can you check your [Platform] payment history for any transactions we haven't recorded?"
   - If logged gross > 1099-K gross → normal. Platforms only report above-threshold amounts. No action needed — just confirm the 1099-K covers the expected period.

4. **Document the reconciliation** — add a note to affected records: `"1099-K reconciled: [Platform] form shows $[gross]. Difference explained by [refunds/fees/below-threshold payments]."` Set `review_required: true` on any record you cannot reconcile; set `review_reason` to the unexplained amount.

5. **Flag for accountant** — if the 1099-K amount and logged amount diverge by more than $100 and you cannot account for the difference, flag the entire platform's records for accountant review in the export.

### What to tell the user

When a user hands you a 1099-K:
> *"Got it — I'll reconcile your [Platform] 1099-K against what's in income.json. The 1099-K shows gross payments before refunds and fees, so the numbers won't match exactly and that's normal. I'll flag anything I can't account for."*

---

## Querying Income

- "How much did I make in February?" → filter income.json by `date.startswith("2026-02")`
- "What's my YTD gross?" → sum all income.json amounts year-to-date
- "Show me all my affiliate commissions" → filter by `category: "affiliate_commissions"`
- "What income hasn't been 1099'd?" → filter by `1099_reported: false`
- "I got a 1099-K from [Platform]" → run 1099-K reconciliation procedure above


