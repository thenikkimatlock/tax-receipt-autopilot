<!-- Internal reference — Claude reads this file when Step 2D is triggered. No need to open or edit it. -->
# Gmail MCP Receipt Sync — Procedure

Triggered by: "pull my receipts from Gmail", "sync Gmail receipts", "check my email for receipts", "scan my email for receipts"

---

## Step 1 — Check Gmail access

Test Gmail MCP access (try a simple list call). Check Rube MCP as a fallback if the user has it connected.

- **Gmail is connected** → proceed to Step 2 below.
- **Gmail is NOT connected** → tell the user:
  > "Gmail isn't connected to Claude Code CLI. The fastest path is the receipts folder — it's what most Claude Code users do and it's zero setup: open any email receipt, copy the body, save it as a .txt file in your receipts folder, then say 'process my receipts'. Claude parses it exactly the same as a Gmail sync.
  >
  > If you specifically want live Gmail sync, say 'walk me through connecting Gmail' and I'll guide you step by step. Takes about 5 minutes with Rube, or 30-60 minutes via manual Google Cloud OAuth."
  > Then stop. Do not attempt Gmail operations.

---

## Step 2 — Search for receipt emails

If `gmail_label` is set in session state → search that label.
Otherwise, search with these combined criteria:
```
subject:(receipt OR order confirmation OR invoice OR "your order" OR "payment confirmation" OR "you've been charged")
-category:promotions
newer_than:35d
```

Also search by common receipt senders:
- `from:(receipts@amazon.com OR no-reply@stripe.com OR service@paypal.com OR noreply@shopify.com OR donotreply@apple.com)`

---

## Step 3 — Process each email

For each result:
1. Read email subject, sender, date, body
2. Extract: vendor (from sender domain), date (email date), amount (search for "$", "Total", "Amount charged", "Order total")
3. Set `source: "Email Receipt"`
4. Classify via Step 4
5. Duplicate check → skip if already in ledger (same vendor + amount + date within 3 days)
6. Store new transactions

---

## Step 4 — Report

```
GMAIL RECEIPT SYNC
━━━━━━━━━━━━━━━━━━
Emails scanned:  [N]
New receipts:    [N]  (added to ledger)
Duplicates:      [N]  (already logged)
Couldn't parse:  [N]  (flagged for manual review)
```

---

## Gmail label (optional but speeds up future syncs)

Create a Gmail filter: `subject:(receipt OR invoice OR order confirmation) → Apply label: receipts`
Then say "Update my gmail_label to receipts" — Claude updates your config and future syncs only scan that label.

---

## Connecting Gmail (if user asks)

Walk them through it conversationally, one step at a time. The path depends on how they access Claude:

- **claude.ai browser/desktop app**: Settings → Integrations → Google → Connect → authorize → done. Test with "List my Gmail labels."
- **Claude Code CLI with Rube**: Rube handles the OAuth flow automatically. Say "Do I have Rube connected?" to check. If not, ask if they want to set up Rube — it handles the Google auth for them with no manual Google Cloud setup required.
- **Claude Code CLI without Rube**: Recommend the receipts folder method instead — copy email body to a .txt file, drop it in the receipts folder, say "process my receipts". Same result, zero setup. Only pursue the manual Google Cloud OAuth path (30-60 min) if the user explicitly asks for it and understands the effort involved.
