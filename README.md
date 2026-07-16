# Automation & AI prototypes — for Ray White Remuera application

Three small, self-contained, actually-runnable prototypes mapped directly to
the job's "what you'll actually do" list. No paid API keys required — each
one runs with `python3` and the standard library only, so anyone can clone
and verify them in under a minute.

| # | Prototype | Maps to |
|---|---|---|
| 1 | `01_inquiry_parser/` | "Design AI-powered workflows using LLMs — document processing, data matching" |
| 2 | `02_lead_matcher/` | "Work with structured data across Airtable and SQL-based systems" |
| 3 | `03_webhook_notifier/` | "Build and maintain Make.com/Zapier scenarios... smart notifications" + "Troubleshoot and refine existing workflows" |

## 1. Inquiry Parser

Turns freeform property inquiries (email/web-form text) into structured
CRM-ready JSON — name, contact, budget, bedrooms, suburb, urgency.

Ships with a real LLM prompt (system + user message, strict JSON-only output
spec) for the production path, plus a dependency-free rule-based fallback so
the demo runs with zero setup and zero API cost.

```
cd 01_inquiry_parser
python3 parser.py sample_inquiries.txt
```

Sample output (one of four):
```json
{
  "name": "Sarah Thompson",
  "phone": "021 555 0192",
  "email": "sarah.thompson@email.com",
  "budget_min": 1200000,
  "budget_max": 1400000,
  "bedrooms": 3,
  "suburb_interest": "Remuera",
  "urgency": "this_month"
}
```

## 2. Lead Matcher

Reconciles new marketing signups (open homes, newsletter, Facebook ads)
against existing CRM contacts using real SQL (SQLite, in-memory) — matches
on normalized email, then phone, then name, so the office doesn't create
duplicate records or miss a returning enquirer.

```
cd 02_lead_matcher
python3 matcher.py
```

Output:
```
Already in CRM (2) -- link to existing record, don't duplicate:
  Sarah Thompson     (via Open Home - Remuera ) -> CRM #1 Sarah Thompson  [matched on email]
  Grace  Liu         (via Open Home - Epsom   ) -> CRM #2 Grace Liu  [matched on email]

New leads (2) -- create CRM record:
  Mike B             mike.b@mailbox.co.nz      (no phone)      via Newsletter
  J. Chen            jchen@email.com           022 111 2233    via Facebook Ad
```

## 3. Webhook Notifier

A minimal webhook receiver standing in for a Make.com/Zapier scenario:
trigger (new lead POSTed) → validate → priority-score → notify. Swapping
`send_notification()` for a real Slack/Teams incoming webhook is a one-line
change — the trigger/validate/transform/route shape stays identical.

Malformed events are rejected with a structured reason and logged instead of
crashing the workflow — this is the "troubleshoot and refine, implement
durable fixes" part of the brief in practice.

```
cd 03_webhook_notifier
python3 notifier.py &
python3 send_test_events.py
```

Output:
```
200 {"status": "notified"}
200 {"status": "notified"}
422 {"error": ["no contact method: need email or phone"]}
422 {"error": ["missing required field: name", "no contact method: need email or phone"]}
```
`notifications.log` shows the two valid leads, correctly priority-scored
(HIGH for the urgent $1.4M enquiry, LOW for the casual browser). `errors.log`
shows the two rejected payloads with the exact reason each failed validation.

---

All three were built and run-verified for this application — happy to walk
through any of them, or build against a real Make.com/Airtable/CRM sandbox
if that's more useful to see.
