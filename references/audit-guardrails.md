<!-- Internal reference — Claude reads this file automatically. No need to open or edit it. -->
# Audit-Safety Guardrails

These rules are non-negotiable. Apply them every time a transaction is classified, reviewed, or stored. Never override them based on user convenience.

| Rule | Action |
|---|---|
| Uncertain category | `review_required: true` — never guess |
| Food/restaurant vendor | Default to `personal` — only reclassify to `meals_entertainment` if user explicitly confirms a business meal with a specific person and purpose |
| Meal classified as meals_entertainment | Always note 50% limitation + require business purpose and attendees before storing |
| Equipment >$2,500 | Flag for Section 179 / depreciation every time |
| Personal expense found | `personal`, `deductible: false` — no creative reclassification |
| Duplicate detected | Show user before merging — never silently merge |
| Receipt unreadable | Mark fields `"unreadable"`, flag for review |
| Mixed personal/business | Ask for business-use % — never assume 100% |
| S-corp / C-corp entity | Flag that Schedule C may not apply |
| Home office claimed | Require Form 8829 note — confirm exclusive and regular use |
| Cash transaction >$10k | Note "Form 8300 may be required" |
| Any deductible amount stated | Add: "These are federal deductions. State tax treatment may differ — verify with your accountant." |
