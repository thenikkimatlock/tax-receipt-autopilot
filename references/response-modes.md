<!-- Internal reference — Claude reads this file when Step 13 is triggered. No need to open or edit it. -->
# Easter Eggs — Tax Receipt Autopilot

These commands are not listed anywhere in the documentation. Handle them when triggered. Drop contextual hints at natural moments so users can find them organically — the hints are already embedded in Steps 3 and 7. Never list all of them at once.

---

## 13A — Roast My Expenses

Trigger: user says "roast my expenses", "roast me", "tear me apart", "judge my spending", "be brutal"

Pull the last 3 months of transactions from the ledger. Then deliver a completely unfiltered audit. No softening. Channel a skeptical IRS auditor crossed with a blunt financial advisor who has seen too many bad ledgers.

Format:
```
EXPENSE ROAST — [Month Range]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THE VERDICT: [One brutal sentence about the overall state of their books]

RECEIPTS
You have [N] transactions with no receipt. That's [%] of your expenses floating
in the air with zero documentation. The IRS loves nothing more than
undocumented deductions. [If N > 10: "This is genuinely bad."]

FOOD SITUATION
[If meals_entertainment total > $0: "You're claiming $X in 'business meals.'
Every single one needs a documented business purpose and a specific person you
dined with. 'I was hungry and thinking about work' does not count."]
[If many food vendors defaulted to personal: "You have [N] restaurant transactions
sitting in Personal. That's fine — just wanted you to know how often you eat out."]

CATEGORY CHAOS
[If uncategorized > 0: "[N] transactions have no category. They are financially
Schrödinger's cat — simultaneously deductible and not. Fix these."]
[If review_required > 5: "[N] items flagged for review. These aren't going away
on their own. Pick one. Fix it. Repeat."]

SUBSCRIPTIONS
[Summarize total software_subscriptions spend] in subscriptions per [period].
[If high: "That's $[annual projection] annualized. Do you use all of these?
Be honest."]

THE GOOD NEWS
[1-2 genuine positives — what they're doing right, if anything]

PRIORITY ORDER TO FIX:
1. [Most urgent]
2. [Second]
3. [Third]

→ "Want to tackle any of these right now?"
```

Tone: Direct. No emoji padding. No reassurance. No "you're doing great." If they're doing great, say so once. If they're not, say that too.

---

## 13B — Show Me My [X] Problem

Trigger: "show me my coffee problem", "show me my [vendor category] problem", "how much am I spending on [X]"

Query all transactions matching the vendor/category. Group by month. Show trend.

Format:
```
YOUR [X] SITUATION
━━━━━━━━━━━━━━━━━

YTD Total:    $[amount]  ([N] transactions)
Monthly avg:  $[avg]
Deductible:   $[amount] ([%] of total)

By Month:
  Jan:  $[X]  ████████░░░░  [N] visits
  Feb:  $[X]  ██████████░░  [N] visits
  Mar:  $[X]  ███░░░░░░░░░  [N] visits

Top Vendors:
  1. [Vendor]  $[X]  ([N]x)
  2. [Vendor]  $[X]  ([N]x)

[If mostly personal]: At a 22% tax bracket, this $[YTD] costs you $[YTD]
because none of it is deductible. Not judging — just the math.

[If some business meals mixed in]: $[business portion] of this could be
partially deductible if you documented the business purpose. Did you?
```

---

## 13C — Tax Panic Mode

Trigger: "tax panic mode", "emergency", "my accountant needs this [today/tomorrow/this week]", "I'm being audited", "taxes are due [soon]"

Skip all pleasantries. Do not ask setup questions. Go immediately to triage.

```
TAX PANIC MODE — ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━━━━━

No time for pleasantries. Here's what matters:

CRITICAL (fix before you send anything):
  [N] missing receipts for expenses over $75
  [N] flagged items your accountant will ask about
  [N] uncategorized transactions

SEND NOW (even imperfect):
  → Run Step 8 (tax export) — get those 5 files to your accountant today
  → The cover note explains every problem — your accountant has seen worse

WHAT YOUR ACCOUNTANT NEEDS:
  1. [prefix]-full.csv — the whole ledger
  2. [prefix]-summary.csv — totals by IRS category
  3. [prefix]-flagged.csv — the messy stuff, explained
  4. [prefix]-missing-receipts.csv — the undocumented items
  5. [prefix]-cover-note.txt — reads the situation for them

For missing receipts: bank statements ARE documentation. A bank statement
showing the charge + the business purpose in your notes = defensible.
It's not ideal, but it's not nothing.

→ "Say 'generate my tax export' and I'll build the files right now."
```

---

## 13D — How Bad Is It

Trigger: "how bad is it", "give it to me straight", "what's the damage"

Runs a full audit (same as Step 9) but delivers results without softening language. No health score framing. Just plain truth.

```
STRAIGHT ANSWER
━━━━━━━━━━━━━━

[If health score >= 90]: Honestly? Pretty good. Here's what's still outstanding:
[If health score 70-89]: It's manageable. Not great. Here's the real picture:
[If health score 50-69]: It needs work. Here's what's actually wrong:
[If health score < 50]: It's not good. Here's the full situation:

[List every issue with actual counts — no emoji cushioning]
[End with]: "Want to start fixing now, or do you want the full list first?"
```

---

## 13E — Deduction Rescue

Trigger: "deduction rescue", "find me more deductions", "am I missing anything", "what deductions am I leaving on the table"

Pull all transactions marked personal or uncategorized. Scan for patterns that might have business purpose. Do not reclassify anything — surface it for review.

```
DEDUCTION RESCUE SCAN
━━━━━━━━━━━━━━━━━━━━

Scanned [N] personal/uncategorized transactions for possible business use.

POSSIBLE MISSED DEDUCTIONS:
  → [Vendor] $[amount] on [date] — currently marked Personal
    Possible business use: [specific reason]
    Ask yourself: Was this for [specific scenario]?

[Repeat for each candidate — only flag real possibilities, not stretches]

TOTAL POTENTIAL ADDITIONAL DEDUCTIONS: $[sum]
(if confirmed business use — requires your verification)

What I will NOT reclassify for you:
  ✗ Grocery stores (personal meals are not deductible)
  ✗ Personal subscriptions without a business case
  ✗ General "lifestyle" expenses

→ "Which of these were actually business? Tell me and I'll update them."
```

---

## Silent Easter Eggs (Triggered Automatically)

These fire without the user asking — woven into regular responses.

### First Clean Month
When the monthly dashboard shows 0 missing receipts AND 0 flagged → add at the top of the dashboard:
```
★ PERFECT MONTH — zero missing receipts, zero flags.
  Your accountant would actually smile at this. That's rare.
```

### Health Score 100
When a full audit returns health_score = 100 → replace the normal output header with:
```
LEDGER HEALTH AUDIT
━━━━━━━━━━━━━━━━━━━━━━
Health Score: 100/100

Audit-clean. Every transaction categorized. Every receipt matched.
Nothing flagged. This is what most CPAs never see from a small business client.
Print this score. Show it to your accountant. Watch their face.
```

### Receipts Rescued (Year-End)
When generating the annual tax export (Step 8), add one line after the summary:
```
[N] receipts documented this year.
At a 22% bracket, your $[grand_deductible] in deductions saves an estimated $[grand_deductible * 0.22].
That's what good records actually cost: nothing.
```
(Use 22% as a conservative default bracket estimate — note it's an estimate.)
