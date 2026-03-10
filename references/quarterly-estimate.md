<!-- Internal reference — Claude reads this file when Step 11A is triggered. No need to open or edit it. -->
# Quarterly Tax Estimate — Calculation Procedure

Triggered by: "help me estimate my Q[X] payment", "how much do I owe", "calculate my estimated taxes", "what should I pay this quarter"

> These estimates use federal brackets and state top rates. They are working approximations — not substitutes for a CPA. Always end with both caution blocks from Step 5.

---

## Step 1 — Gather inputs

Pull the YTD deductible total from the ledger. Then ask:

> "To estimate your quarterly payment I need four things:
> (1) Your estimated gross business income for the year so far — total revenue before any deductions
> (2) Your filing status — single or married filing jointly?
> (3) What state do you live in?
> (4) Have you made any estimated tax payments this year? If yes, how much total?"

Also ask: "What was your total federal income tax on your prior year return (Form 1040, Line 24)? And was your prior year adjusted gross income over $150,000?"

**If filing status is Married Filing Jointly — ask one additional question:**
> "What is your spouse's estimated gross income for this year (W-2, salary, other employment income — not your business income)?"

This is required. Spouse income shifts your combined taxable income into higher brackets and can significantly increase the correct estimated payment. Do not skip it or assume $0 without asking.

Wait for all answers. Do not skip or guess.

---

## Step 2 — Determine tax year

Use `tax_year` from session state.

- **tax_year = 2025**: Use 2025 brackets and thresholds below. (Filing deadline: April 15, 2026)
- **tax_year = 2026**: Use 2026 brackets and thresholds below. (Quarterly payments due: Apr 15, Jun 15, Sep 15, 2026; Jan 15, 2027)
- If tax_year is not set, ask the user which year they are tracking.

---

## Step 3 — Federal Tax Calculation

### Part A — Self-Employment Tax

```
net_profit_est  = gross_income_ytd − ytd_deductible

se_base         = net_profit_est × 0.9235
se_tax          = se_base × 0.153          (15.3% = 12.4% SS + 2.9% Medicare)
se_deduction    = se_tax × 0.50            (50% of SE tax is deductible — Schedule 1, not Schedule C)
```

### Part B — QBID (Section 199A — Qualified Business Income Deduction)

The QBID is one of the most valuable deductions for sole proprietors. Calculate it before income tax.

**2025 thresholds (for tax year 2025):**
- Initial threshold: $197,300 (single) | $394,600 (MFJ)
- Upper phase-out: $247,300 (single) | $494,600 (MFJ)

**2026 thresholds (for tax year 2026):**
- Initial threshold: ~$203,000 (single) | ~$406,000 (MFJ)
- Upper phase-out: ~$272,300 (single) | ~$544,600 (MFJ)

**Classification rules:**

```
Compare net_profit_est to the initial threshold for the applicable year and filing status:

Case 1 — net_profit_est is BELOW the initial threshold:
  qbi_deduction = net_profit_est × 0.20
  (Simple 20% deduction — no further limitations apply)

Case 2 — net_profit_est is IN the phase-out range (between initial and upper threshold):
  Partial deduction applies. Compute using the actual linear phase-out formula:
    phase_out_width    = upper_threshold − initial_threshold
    position_in_range  = net_profit_est − initial_threshold
    phase_out_fraction = position_in_range / phase_out_width
    remaining_fraction = 1.0 − phase_out_fraction
    qbi_deduction      = net_profit_est × 0.20 × remaining_fraction

  Example (single filer, 2025, net_profit_est = $220,000):
    phase_out_width    = 247,300 − 197,300 = 50,000
    position_in_range  = 220,000 − 197,300 = 22,700
    phase_out_fraction = 22,700 / 50,000   = 0.454
    remaining_fraction = 1.0 − 0.454       = 0.546
    qbi_deduction      = 220,000 × 0.20 × 0.546 = $24,024

  Flag: "You are in the QBID phase-out range — deduction calculated using the actual
  linear interpolation formula. Your accountant should verify, as W-2 wage and qualified
  property tests may apply at higher income levels."

Case 3 — net_profit_est is ABOVE the upper phase-out:
  - If SSTB (Specified Service Trade or Business): qbi_deduction = $0
    SSTB includes: medicine, law, accounting, actuarial science, consulting,
    athletics, performing arts, financial services, brokerage, investing,
    trading in securities.
  - If NOT SSTB: deduction may still apply based on W-2 wages and qualified
    property. As a sole proprietor with no employees, this is typically $0
    (sole proprietors have no W-2 wages). Flag for accountant review.
    Use $0 as the conservative estimate.
  Flag: "You may be above the QBID income threshold. This estimate sets QBID
  to $0, which will overstate your tax if you qualify for a partial deduction.
  Confirm with your accountant."
```

Note: QBID was made permanent by the One Big Beautiful Bill Act (signed July 4, 2025). It no longer expires after 2025.

### Part C — Income Tax

**2025 Federal Brackets — Single:**
```
10%:  $0 – $11,925
12%:  $11,926 – $48,475
22%:  $48,476 – $103,350
24%:  $103,351 – $197,300
32%:  $197,301 – $250,525
35%:  $250,526 – $626,350
37%:  $626,351+
```

**2025 Federal Brackets — Married Filing Jointly:**
```
10%:  $0 – $23,850
12%:  $23,851 – $96,950
22%:  $96,951 – $206,700
24%:  $206,701 – $394,600
32%:  $394,601 – $501,050
35%:  $501,051 – $751,600
37%:  $751,601+
```

**2026 Federal Brackets — Single:**
```
10%:  $0 – $12,400
12%:  $12,401 – $50,400
22%:  $50,401 – $105,700
24%:  $105,701 – $201,775
32%:  $201,776 – $256,225
35%:  $256,226 – $640,600
37%:  $640,601+
```

**2026 Federal Brackets — Married Filing Jointly:**
```
10%:  $0 – $24,800
12%:  $24,801 – $100,800
22%:  $100,801 – $211,400
24%:  $211,401 – $403,550
32%:  $403,551 – $512,450
35%:  $512,451 – $768,700
37%:  $768,701+
```

**Standard Deductions:**
- 2025: $15,750 (single) | $31,500 (MFJ)   ← raised by the One Big Beautiful Bill Act (signed July 4, 2025); original IRS inflation-adjusted amount was $15,000/$30,000
- 2026: $16,100 (single) | $32,200 (MFJ)

**Income tax calculation:**
```
# Single filers:
taxable_income  = net_profit_est − se_deduction − qbi_deduction − standard_deduction

# Married Filing Jointly — MUST include spouse income:
taxable_income  = (net_profit_est + spouse_gross_income) − se_deduction − qbi_deduction − standard_deduction

income_tax      = apply each bracket in layers to taxable_income (marginal calculation)
                  Do not apply the bracket rate to the full income — only to the income
                  within each bracket's range.

total_federal_tax = se_tax + income_tax
```

> **MFJ note:** If the user provided spouse income, always show it as a line item in the final estimate output so they can see how it affects the bracket. A spouse earning $60,000 W-2 can push self-employment income from the 12% into the 22% bracket — omitting this causes a materially wrong estimate.

---

## Step 4 — State Tax Calculation

Look up the user's state in the reference table at the bottom of this file.

```
For no-income-tax states (AK, FL, NV, NH, SD, TN, TX, WY):
  state_tax = $0

For flat-rate states:
  state_tax ≈ taxable_income × [flat rate]
  State taxable income ≈ federal taxable income for most sole proprietors.
  Some states use different standard deductions — this is an approximation.

For graduated/progressive states:
  Apply the top marginal rate as a ceiling estimate.
  state_tax ≈ taxable_income × [top rate]
  Note to user: "Actual state liability will be lower — this uses the top
  rate as a ceiling. Income in lower brackets is taxed at lower rates."

Special cases:
  Maryland: also add county/city tax of approximately 2.25%–3.2% depending on county.
  New York City residents: add NYC city income tax of up to 3.876%.
  Washington state: no income tax on self-employment income. If the user has
    capital gains over ~$270,000, Washington's 7%–9.9% capital gains tax may apply.
```

State tax is always an approximation in this tool. See Step 5 for required disclaimer.

---

## Step 5 — Calculate quarterly payment

```
total_annual_tax     = total_federal_tax + state_tax
prior_payments_made  = [amount user provided, or $0]
remaining_owed       = total_annual_tax − prior_payments_made
quarters_remaining   = 4 − quarters_already_past
suggested_payment    = remaining_owed ÷ quarters_remaining
```

---

## Step 6 — Present the estimate

```
QUARTERLY TAX ESTIMATE — Q[X] [YEAR]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gross income YTD:          $[X]
YTD deductions (ledger):  -$[X]
Estimated net profit:      $[X]
[MFJ only] Spouse income:  $[X]   (included in combined taxable income below)

FEDERAL
  Self-employment tax:      $[X]   (15.3% on 92.35% of net profit)
  SE tax deduction:        -$[X]   (50% of SE tax, reduces income tax)
  QBID (Sect. 199A):       -$[X]   (20% of net profit — below threshold)
  Standard deduction:      -$[X]   ($[15,750 or 16,100] single / $[31,500 or 32,200] MFJ)
  Income tax:               $[X]   ([bracket]% bracket on taxable income of $[X])
  Federal total:            $[X]

STATE ([State])
  Estimated state tax:      $[X]   ([rate]% — [flat rate / top marginal rate ceiling])

TOTAL ESTIMATED ANNUAL TAX:  $[X]
Prior payments made:         -$[X]
REMAINING THIS YEAR:          $[X]

Suggested Q[X] payment:      ~$[X]  (remaining ÷ [N] quarters left)
```

Always close with both blocks:

**Working estimate only.** Does not account for other income sources, itemized deductions, credits, the exact QBID phase-out calculation, or safe harbor rules. Verify with your accountant. Federal payments at irs.gov/payments → Direct Pay.

**State estimate.** Uses your state's flat rate or top marginal rate as an approximation. Actual state liability depends on your state's specific deductions, exemptions, and brackets — which differ from federal. Verify at your state's official tax agency website.

---

## Step 7 — Safe Harbor

After presenting the estimate, always calculate and present the safe harbor:

```
SAFE HARBOR — avoid underpayment penalties
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
To avoid the underpayment penalty, pay the SMALLER of:

Option A (current year):  90% of estimated [YEAR] total tax
  = ~$[total_annual_tax × 0.90] total for the year
  = ~$[total_annual_tax × 0.90 ÷ 4] per quarter

Option B (prior year):   [100% or 110%] of your [PRIOR_YEAR] tax
  → Use 100% if your prior year AGI was $150,000 or under
  → Use 110% if your prior year AGI exceeded $150,000
  = $[prior_year_tax × multiplier] total for the year
  = $[prior_year_tax × multiplier ÷ 4] per quarter

Safe harbor met if total payments ≥ the smaller option above.
No penalty applies if total tax owed for the year is under $1,000.
```

If the user did not provide their prior year tax liability: "I need your total tax from your [PRIOR_YEAR] Form 1040, Line 24 to calculate your safe harbor. Check your prior return or ask your accountant. Without it, go with Option A: pay 90% of your estimated [YEAR] tax across four quarters."

---

## State Income Tax Reference (2025 rates — verify 2026 at state's official site)

> These rates are for the 2025 tax year. State rates change year to year. Always verify the current rate at your state's official tax authority website before making large payments or filing. The rates below are for estimation only.

### No State Income Tax

Business income tax: $0

Alaska, Florida, Nevada, New Hampshire, South Dakota, Tennessee, Texas, Wyoming

Washington state: No income tax on wages or self-employment income. Washington imposes capital gains tax of 7%–9.9% on taxable capital gains exceeding ~$270,000 (2025). For most sole proprietors without significant capital gains: $0.

---

### Flat-Rate States (2025)

Apply the rate to estimated state taxable income. State taxable income approximates federal taxable income for most sole proprietors, though state standard deductions differ.

| State | Rate | Notes |
|---|---|---|
| Arizona | 2.5% | Flat since 2023 |
| Colorado | 4.4% | |
| Georgia | 5.19% | 5.09% in 2026, dropping to 4.99% by 2027 |
| Idaho | 5.3% | |
| Illinois | 4.95% | |
| Indiana | 3.0% | 2.95% in 2026 |
| Iowa | 3.8% | |
| Kentucky | 4.0% | Drops to 3.5% in 2026 |
| Louisiana | 3.0% | |
| Massachusetts | 5.0% | Plus 4% surcharge on income over $1,000,000 |
| Michigan | 4.25% | |
| Mississippi | 4.4% | First $10,000 of income is exempt; 4.0% in 2026 |
| North Carolina | 4.25% | 3.99% in 2026 |
| Pennsylvania | 3.07% | |
| Utah | 4.5% | |

---

### Progressive/Graduated States (2025 top marginal rates)

For estimates, apply the top marginal rate as a ceiling. Actual liability is lower — income in lower brackets is taxed at lower rates. Provide the rate range to the user so they understand the spread.

| State | Rate Range | Notes |
|---|---|---|
| Alabama | 2%–5% | Top bracket starts at very low income (~$3,000 single); most income taxed at 5% |
| Arkansas | 2%–3.9% | |
| California | 1%–13.3% | 13.3% applies above $1M. ~9.3% effective rate near $100k. Highest in nation. |
| Connecticut | 3%–6.99% | |
| Delaware | 0%–6.6% | No sales tax offsets moderate income tax |
| District of Columbia | 4%–10.75% | |
| Hawaii | 1.4%–11% | Second-highest top rate in the nation |
| Kansas | 3.1%–5.7% | |
| Maine | 5.8%–7.15% | |
| Maryland | 2%–6.5% | Add county/city tax: typically 2.25%–3.2% depending on county |
| Minnesota | 5.35%–9.85% | |
| Missouri | 2%–4.7% | |
| Montana | 4.7%–5.9% | Top rate drops to 5.65% in 2026, 5.4% in 2027 |
| Nebraska | graduated to 5.2% | Drops to 4.55% in 2026 |
| New Jersey | graduated to 10.75% | |
| New Mexico | 1.5%–5.9% | |
| New York | 4%–10.9% | NYC residents add up to 3.876% city income tax |
| North Dakota | graduated to 2.5% | One of the lowest income tax states |
| Ohio | 2.75%–3.125% | 2025 top rate retroactively reduced to 3.125% by Ohio H.B. 96 (2025 budget); converting to flat 2.75% in 2026 |
| Oklahoma | 0.25%–4.75% | Converting to flat 4.5% in 2026 |
| Oregon | 4.75%–9.9% | No sales tax; high income tax |
| Rhode Island | 3.75%–5.99% | |
| South Carolina | graduated to 6% | |
| Vermont | 3.35%–8.75% | |
| Virginia | 2%–5.75% | Top bracket starts at $17,000; most income effectively taxed at ~5.75% |
| West Virginia | graduated to 4.82% | |
| Wisconsin | 3.5%–7.65% | |
