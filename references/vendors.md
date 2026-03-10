<!-- Internal reference — Claude reads this file automatically. No need to open or edit it. -->
# Vendor Knowledge Base — Default Seeds

These 61 vendors are seeded automatically during first-time setup. Claude uses this list to auto-classify common business tools and personal defaults without asking the user each time.

Seed all vendors in the list below by writing the full array to vendors.json at setup.

---

## Batch 1 — Software & Subscriptions (Default Deductible: Yes)

| Vendor Name | Default Category | Notes |
|---|---|---|
| Canva | software_subscriptions | Design tool — 100% business use |
| Adobe Creative Cloud | software_subscriptions | Creative suite — 100% business use |
| Google Workspace | software_subscriptions | Business email + docs — 100% business use |
| OpenAI | software_subscriptions | ChatGPT / API — 100% business use |
| Anthropic | software_subscriptions | Claude API — 100% business use |
| Notion | software_subscriptions | Project management — confirm % business use |
| Slack | software_subscriptions | Team communication — 100% business use |
| Zoom | software_subscriptions | Video meetings — 100% business use |
| Dropbox | software_subscriptions | Cloud storage — confirm % business use |
| GitHub | software_subscriptions | Code hosting — 100% business use |

## Batch 2 — More Software + Marketing (Default Deductible: Yes)

| Vendor Name | Default Category | Notes |
|---|---|---|
| Microsoft 365 | software_subscriptions | Office suite — confirm % business use |
| QuickBooks | software_subscriptions | Accounting software — 100% business use |
| GoDaddy | software_subscriptions | Domain/hosting — 100% business use |
| Squarespace | software_subscriptions | Website builder — 100% business use |
| Cloudflare | software_subscriptions | CDN/DNS — 100% business use |
| Mailchimp | marketing_advertising | Email marketing — 100% business use |
| Kit (ConvertKit) | marketing_advertising | Email marketing — 100% business use |
| Meta Ads | marketing_advertising | Facebook/Instagram ads — 100% business use |
| Google Ads | marketing_advertising | Search/display ads — 100% business use |
| LinkedIn Ads | marketing_advertising | B2B ads — 100% business use |

## Batch 3 — Payment Processors + Office + Workspace (Default Deductible: Yes)

| Vendor Name | Default Category | Notes |
|---|---|---|
| Stripe | bank_fees | Payment processing fees — 100% business use |
| PayPal | bank_fees | Payment processing fees — 100% business use |
| Square | bank_fees | POS processing fees — 100% business use |
| Amazon | personal | No | Default: personal. Amazon is heavily mixed personal/business — only reclassify to the correct category if the user confirms a specific business purchase and what it was for. |
| Staples | office_supplies | Office supplies — 100% business use if business purchase |
| Office Depot | office_supplies | Office supplies — confirm business use |
| FedEx | other_business | Shipping — 100% business use if business shipment (Schedule C Line 27a) |
| UPS | other_business | Shipping — 100% business use if business shipment (Schedule C Line 27a) |
| USPS | other_business | Postage/shipping — 100% business use if business mail (Schedule C Line 27a) |
| WeWork | rent_lease | Coworking space — 100% business use |

## Batch 4 — Contractors + Telecom + Personal Defaults

| Vendor Name | Default Category | Default Deductible | W-9 On File | Notes |
|---|---|---|---|---|
| Regus | rent_lease | Yes | N/A | Coworking space — 100% business use |
| Fiverr | contractor_payments | Yes | false | Freelancer payments — collect W-9 if any payment |
| Upwork | contractor_payments | Yes | false | Freelancer payments — collect W-9 if any payment |
| Verizon | utilities | 50% | N/A | Phone/internet — deduct business-use % only. Confirm %. |
| AT&T | utilities | 50% | N/A | Phone/internet — deduct business-use % only. Confirm %. |
| Comcast | utilities | 50% | N/A | Internet — deduct business-use % only. Confirm %. |
| Starbucks | personal | No | Default: personal. Only reclassify if user confirms business meal with specific person + purpose. |
| McDonald's | personal | No | Default: personal. |
| Chipotle | personal | No | Default: personal. |
| Netflix | personal | No | Default: personal. Only business if used for professional content research — very rare. |
| Spotify | personal | No | Default: personal. |

## Batch 5 — Modern SaaS + Automation + Dev Tools (Default Deductible: Yes)

| Vendor Name | Default Category | Notes |
|---|---|---|
| Shopify | software_subscriptions | E-commerce platform — 100% business use |
| Klaviyo | marketing_advertising | Email/SMS marketing platform — 100% business use |
| ActiveCampaign | marketing_advertising | Email marketing automation — 100% business use |
| HubSpot | marketing_advertising | CRM/marketing platform — 100% business use |
| Zapier | software_subscriptions | Automation platform — 100% business use |
| Make.com | software_subscriptions | Automation platform (formerly Integromat) — 100% business use |
| Airtable | software_subscriptions | Database/project management — 100% business use |
| Figma | software_subscriptions | UI/UX design tool — 100% business use |
| DigitalOcean | software_subscriptions | Cloud hosting — 100% business use |
| Netlify | software_subscriptions | Web hosting/deployment — 100% business use |

## Batch 6 — AI Tools + Content + Creator Platforms (Default Deductible: Yes)

| Vendor Name | Default Category | Notes |
|---|---|---|
| Midjourney | software_subscriptions | AI image generation — 100% business use |
| ElevenLabs | software_subscriptions | AI voice/audio — 100% business use |
| fal.ai | software_subscriptions | AI image/video generation — 100% business use |
| Vercel | software_subscriptions | Web hosting/deployment — 100% business use |
| Calendly | software_subscriptions | Scheduling software — 100% business use |
| Loom | software_subscriptions | Video messaging — 100% business use |
| Descript | software_subscriptions | Video/podcast editing — 100% business use |
| ClickUp | software_subscriptions | Project management — confirm % business use |
| Buffer | marketing_advertising | Social media scheduling — 100% business use |
| Epidemic Sound | software_subscriptions | Music licensing for content — 100% business use |

---

## JSON format (for local mode vendors.json seed)

```json
[
  {"vendor_name": "Canva", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Design tool — 100% business use"},
  {"vendor_name": "Adobe Creative Cloud", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Creative suite — 100% business use"},
  {"vendor_name": "Google Workspace", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Business email + docs — 100% business use"},
  {"vendor_name": "OpenAI", "default_category": "software_subscriptions", "default_deductible": true, "notes": "ChatGPT / API — 100% business use"},
  {"vendor_name": "Anthropic", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Claude API — 100% business use"},
  {"vendor_name": "Notion", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Project management — confirm % business use"},
  {"vendor_name": "Slack", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Team communication — 100% business use"},
  {"vendor_name": "Zoom", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Video meetings — 100% business use"},
  {"vendor_name": "Dropbox", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Cloud storage — confirm % business use"},
  {"vendor_name": "GitHub", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Code hosting — 100% business use"},
  {"vendor_name": "Microsoft 365", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Office suite — confirm % business use"},
  {"vendor_name": "QuickBooks", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Accounting software — 100% business use"},
  {"vendor_name": "GoDaddy", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Domain/hosting — 100% business use"},
  {"vendor_name": "Squarespace", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Website builder — 100% business use"},
  {"vendor_name": "Cloudflare", "default_category": "software_subscriptions", "default_deductible": true, "notes": "CDN/DNS — 100% business use"},
  {"vendor_name": "Mailchimp", "default_category": "marketing_advertising", "default_deductible": true, "notes": "Email marketing — 100% business use"},
  {"vendor_name": "Kit (ConvertKit)", "default_category": "marketing_advertising", "default_deductible": true, "notes": "Email marketing — 100% business use"},
  {"vendor_name": "Meta Ads", "default_category": "marketing_advertising", "default_deductible": true, "notes": "Facebook/Instagram ads — 100% business use"},
  {"vendor_name": "Google Ads", "default_category": "marketing_advertising", "default_deductible": true, "notes": "Search/display ads — 100% business use"},
  {"vendor_name": "LinkedIn Ads", "default_category": "marketing_advertising", "default_deductible": true, "notes": "B2B ads — 100% business use"},
  {"vendor_name": "Stripe", "default_category": "bank_fees", "default_deductible": true, "notes": "Payment processing fees — 100% business use"},
  {"vendor_name": "PayPal", "default_category": "bank_fees", "default_deductible": true, "notes": "Payment processing fees — 100% business use"},
  {"vendor_name": "Square", "default_category": "bank_fees", "default_deductible": true, "notes": "POS processing fees — 100% business use"},
  {"vendor_name": "Amazon", "default_category": "personal", "default_deductible": false, "notes": "Default: personal. Amazon is heavily mixed personal/business — only reclassify if user confirms a specific business purchase and what it was for."},
  {"vendor_name": "Staples", "default_category": "office_supplies", "default_deductible": true, "notes": "Office supplies — 100% business use if business purchase"},
  {"vendor_name": "Office Depot", "default_category": "office_supplies", "default_deductible": true, "notes": "Office supplies — confirm business use"},
  {"vendor_name": "FedEx", "default_category": "other_business", "default_deductible": true, "notes": "Shipping — 100% business use if business shipment (Schedule C Line 27a)"},
  {"vendor_name": "UPS", "default_category": "other_business", "default_deductible": true, "notes": "Shipping — 100% business use if business shipment (Schedule C Line 27a)"},
  {"vendor_name": "USPS", "default_category": "other_business", "default_deductible": true, "notes": "Postage/shipping — 100% business use if business mail (Schedule C Line 27a)"},
  {"vendor_name": "WeWork", "default_category": "rent_lease", "default_deductible": true, "notes": "Coworking space — 100% business use"},
  {"vendor_name": "Regus", "default_category": "rent_lease", "default_deductible": true, "notes": "Coworking space — 100% business use"},
  {"vendor_name": "Fiverr", "default_category": "contractor_payments", "default_deductible": true, "default_deductible_pct": 100, "w9_on_file": false, "notes": "Freelancer payments — collect W-9 if any payment"},
  {"vendor_name": "Upwork", "default_category": "contractor_payments", "default_deductible": true, "default_deductible_pct": 100, "w9_on_file": false, "notes": "Freelancer payments — collect W-9 if any payment"},
  {"vendor_name": "Verizon", "default_category": "utilities", "default_deductible": true, "default_deductible_pct": 50, "notes": "Phone/internet — 50% default. Ask user to confirm actual business-use %."},
  {"vendor_name": "AT&T", "default_category": "utilities", "default_deductible": true, "default_deductible_pct": 50, "notes": "Phone/internet — 50% default. Ask user to confirm actual business-use %."},
  {"vendor_name": "Comcast", "default_category": "utilities", "default_deductible": true, "default_deductible_pct": 50, "notes": "Internet — 50% default. Ask user to confirm actual business-use %."},
  {"vendor_name": "Starbucks", "default_category": "personal", "default_deductible": false, "notes": "Default: personal. Only reclassify if user confirms business meal with specific person + purpose."},
  {"vendor_name": "McDonald's", "default_category": "personal", "default_deductible": false, "notes": "Default: personal."},
  {"vendor_name": "Chipotle", "default_category": "personal", "default_deductible": false, "notes": "Default: personal."},
  {"vendor_name": "Netflix", "default_category": "personal", "default_deductible": false, "notes": "Default: personal. Only business if used for professional content research — very rare."},
  {"vendor_name": "Spotify", "default_category": "personal", "default_deductible": false, "notes": "Default: personal."},
  {"vendor_name": "Shopify", "default_category": "software_subscriptions", "default_deductible": true, "notes": "E-commerce platform — 100% business use"},
  {"vendor_name": "Klaviyo", "default_category": "marketing_advertising", "default_deductible": true, "notes": "Email/SMS marketing platform — 100% business use"},
  {"vendor_name": "ActiveCampaign", "default_category": "marketing_advertising", "default_deductible": true, "notes": "Email marketing automation — 100% business use"},
  {"vendor_name": "HubSpot", "default_category": "marketing_advertising", "default_deductible": true, "notes": "CRM/marketing platform — 100% business use"},
  {"vendor_name": "Zapier", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Automation platform — 100% business use"},
  {"vendor_name": "Make.com", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Automation platform (formerly Integromat) — 100% business use"},
  {"vendor_name": "Airtable", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Database/project management — 100% business use"},
  {"vendor_name": "Figma", "default_category": "software_subscriptions", "default_deductible": true, "notes": "UI/UX design tool — 100% business use"},
  {"vendor_name": "DigitalOcean", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Cloud hosting — 100% business use"},
  {"vendor_name": "Netlify", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Web hosting/deployment — 100% business use"},
  {"vendor_name": "Midjourney", "default_category": "software_subscriptions", "default_deductible": true, "notes": "AI image generation — 100% business use"},
  {"vendor_name": "ElevenLabs", "default_category": "software_subscriptions", "default_deductible": true, "notes": "AI voice/audio — 100% business use"},
  {"vendor_name": "fal.ai", "default_category": "software_subscriptions", "default_deductible": true, "notes": "AI image/video generation — 100% business use"},
  {"vendor_name": "Vercel", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Web hosting/deployment — 100% business use"},
  {"vendor_name": "Calendly", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Scheduling software — 100% business use"},
  {"vendor_name": "Loom", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Video messaging — 100% business use"},
  {"vendor_name": "Descript", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Video/podcast editing — 100% business use"},
  {"vendor_name": "ClickUp", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Project management — confirm % business use"},
  {"vendor_name": "Buffer", "default_category": "marketing_advertising", "default_deductible": true, "notes": "Social media scheduling — 100% business use"},
  {"vendor_name": "Epidemic Sound", "default_category": "software_subscriptions", "default_deductible": true, "notes": "Music licensing for content — 100% business use"}
]
```

---

## Adding vendors during operation

When Claude classifies a vendor that isn't in the knowledge base, it adds it automatically after confirming the category with the user. This list grows as you use the skill.

To add a vendor manually: "Add [Vendor] to my vendor list as [category]"
To correct a vendor: "Update [Vendor] — it should be [category]"
