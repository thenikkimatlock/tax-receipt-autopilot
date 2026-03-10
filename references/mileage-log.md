<!-- Internal reference — Claude reads this file when Step 16 is triggered. No need to open or edit it. -->
# Mileage Log

Tax Receipt Autopilot tracks business mileage in `mileage.json`. The IRS requires a contemporaneous mileage log — vague estimates reconstructed at tax time are rejected on audit.

**Standard mileage rates by tax year:**
- **2025: 70 cents/mile** (IRS Revenue Procedure IR-2024-312)
- **2026: 72.5 cents/mile** (IRS announcement IR-2025-XXX, December 29, 2025 — up 2.5¢ from 2025)
- For future years: verify current rate at irs.gov/tax-professionals/standard-mileage-rates each January — it adjusts annually

**Rate to use:** always match the rate to `tax_year` from session state, not the current calendar year.

---

## When to Log a Trip

Log when the user mentions:
- "I drove to [place] for [reason]"
- "I went to a client meeting"
- "I drove to pick up supplies / go to the post office / meet a vendor"
- "I drove between two job sites / two offices"
- "I need to add a mileage entry"

Do NOT log:
- Commuting (home to regular workplace) — never deductible under any method
- Personal errands — not deductible even if business was also discussed during the drive
- Trips where the sole business use was thinking about work while driving

---

## mileage.json Schema

```json
[
  {
    "id": "mi_YYYYMMDD_NNN",
    "date": "YYYY-MM-DD",
    "start_location": "123 Home Office Rd, City, ST",
    "end_location": "456 Client Site Ave, City, ST",
    "miles": 12.4,
    "business_purpose": "Client meeting — quarterly review with Acme Corp",
    "vehicle": "2022 Honda CR-V",
    "round_trip": false,
    "rate_per_mile": 0.70,
    "deductible_amount": 8.68,
    "notes": ""
  }
]
```

**Field rules:**
- `id`: format `mi_YYYYMMDD_NNN` — date of trip + 3-digit counter starting at 001
- `miles`: one-way miles. If round_trip is true, Claude records one-way here and calculates total as `miles × 2` for reporting.
- `start_location` and `end_location`: street address or descriptive location (required by IRS — "home" and "office" alone are insufficient)
- `business_purpose`: specific and concrete. "Client meeting" is better than "business trip." "Quarterly review with Acme Corp" is better than "client meeting."
- `vehicle`: describe the vehicle. Only needed if user has multiple vehicles — helps separate logs for Section 179 / actual expense tracking.
- `round_trip`: set to `true` only if the user confirms the trip was driven in both directions on the same day for the same purpose. Total miles in the export = `miles × 2`.
- `rate_per_mile`: the IRS standard mileage rate for the tax year. Use the rate matching `tax_year` from session state: 0.70 for 2025, 0.725 for 2026. Must be stored as a number, not a string.
- `deductible_amount`: calculated as `miles × rate_per_mile` (or `miles × 2 × rate_per_mile` for round trips). This field is what `export_ledger.py` reads — if missing, the mileage deduction will show $0 in all exports. Always calculate and store this when writing the record.

---

## How to Log a Trip

1. Ask for any missing required fields: date, start, end, miles, purpose
2. If miles unknown, ask: "Do you know how far it was? If not, I can note the locations and you can check Google Maps."
3. If commute: "That sounds like a commute — home to your regular workplace isn't deductible. Is there a reason this would qualify as a separate business trip?"
4. Write to `mileage.json` (same safe-write pattern: read → append → write → verify)
5. Confirm: "Logged: [X] miles on [Date] — [purpose]. Running 2026 total: [N] miles = $[X] estimated deduction."

**ID format:** `mi_YYYYMMDD_NNN` — use the date of the actual trip (not today's date if logging retroactively). If multiple trips same day, increment NNN.

---

## IRS Documentation Requirements

The IRS requires ALL of the following for a valid mileage log (Rev. Proc. 2019-46):

| Required Element | Field in mileage.json |
|---|---|
| Date of travel | `date` |
| Starting location | `start_location` |
| Ending location | `end_location` |
| Business purpose | `business_purpose` |
| Miles driven | `miles` |

Business percentage (miles / total annual miles) is reported on Schedule C Part IV and requires total annual miles, business miles, and commuting miles for the year.

---

## Annual Vehicle Information (Schedule C Part IV)

Schedule C Part IV asks for vehicle-level information once per year, not per trip. The per-trip mileage log satisfies the contemporaneous record requirement — but Part IV also requires:

| Part IV Question | What to Collect |
|---|---|
| Date vehicle was placed in service | Year the vehicle was first used for business |
| Total miles driven during the year | Business miles + commuting miles + personal miles |
| Business miles | Sum of all logged business trips |
| Commuting miles | Miles from home to primary workplace (never deductible) |
| Personal miles | Total minus business minus commuting |
| Odometer reading at start of year (January 1) | Annual snapshot — strengthens the record |
| Odometer reading at end of year (December 31) | Annual snapshot — confirms total miles driven |
| Was vehicle available for personal use? | Almost always "Yes" for personal vehicles used for business |
| Do you have another vehicle for personal use? | If the user has a second vehicle |
| Evidence to support mileage claim? | Answer is the mileage log itself |

**Prompt the user at year-end** (or when exporting for tax prep) to provide:
1. Total odometer miles driven in the year (all purposes combined)
2. How many of those were commuting
3. How many were personal (non-commuting, non-business)

Then calculate: personal = total - business - commuting.

If the user tracks a single vehicle and only logs business trips, remind them: "For Schedule C Part IV, I also need your total annual odometer miles and commuting miles. Do you have a ballpark for how much you drove this year for personal use?"

Note: Annual odometer readings (Jan 1 and Dec 31) are not required by the IRS, but they strengthen the mileage record during an audit by providing an independent verification of total miles driven. Recommend recording them.

---

## What Qualifies as Deductible Business Mileage

| Deductible | Not Deductible |
|---|---|
| Driving to a client meeting | Commuting to regular workplace |
| Driving between two business locations | Driving home from work |
| Driving to pick up business supplies | Personal errands |
| Driving to a business conference | Driving to a place incidentally related to work |
| Driving to a coworking space (not regular workplace) | Driving to your regular coworking space (commuting) |
| Driving to a bank for business transactions | Mixed personal/business errands |
| Driving to a networking event | Any trip where business wasn't the primary purpose |

**Commuting is never deductible** — even if you take calls during the drive, answer emails at red lights, or have a client in the same direction as your commute. The IRS is explicit on this.

---

## Standard Mileage Rate vs. Actual Expenses

The user must choose ONE method per vehicle. They cannot switch between methods for the same vehicle once they've started (with one exception: if they used actual expenses in a prior year, they can never switch to standard mileage for that vehicle).

| Method | What's Deductible | When to Use |
|---|---|---|
| **Standard mileage rate** | Miles × rate (70¢/mi for 2025, 72.5¢/mi for 2026) | Simpler; good for most sole proprietors |
| **Actual expense method** | Gas + insurance + repairs + depreciation × business-use % | Better if vehicle is expensive, high maintenance, or mostly business use |

**Gas purchases:** If using the standard mileage rate, gas is NOT separately deductible. The rate already covers fuel, oil, tires, insurance, and depreciation. Do not log gas as a separate deduction — flag any gas receipts with this note.

If the user hasn't decided: recommend standard mileage rate (simpler, lower audit risk for most small businesses). Flag the choice for accountant confirmation.

---

## Mileage Log Completeness Check

The `monthly_reminder.py audit` command checks for incomplete entries (any of: start_location, end_location, business_purpose, or miles missing or empty). Flag all incomplete entries — incomplete records are unsubstantiated and can be disallowed entirely on audit.

When flagging: "Trip on [date] is missing [field]. The IRS requires all fields — an incomplete log entry may be disallowed on audit."

---

## Running Totals

When a user asks for mileage totals:
- Total business miles: sum all `miles` values (multiply by 2 for round_trip entries)
- Estimated deduction: sum `deductible_amount` from all records (already calculated at logging time). If any records are missing `deductible_amount`, recalculate as `miles × rate_per_mile` (or `miles × 2 × rate_per_mile` for round trips).
- Rate by tax year: 2025 = 70¢/mile, 2026 = 72.5¢/mile
- Monthly breakdown: filter by `date.startswith("YYYY-MM")`

---

## Export

The `export_ledger.py --mileage` flag generates a mileage CSV with:
- All trip details (date, start, end, purpose, miles, vehicle)
- A running total row at the bottom: total business miles + total estimated deduction
- Cover note includes: total miles for the year, estimated deduction at standard mileage rate

This CSV can be given directly to an accountant for Schedule C Part IV.
