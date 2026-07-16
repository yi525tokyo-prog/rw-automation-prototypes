"""
Inquiry Parser -- turns freeform property-inquiry text (email / web form) into
structured records ready for a CRM or Airtable base.

Design:
  - extract_with_llm(text): the production path. Builds a tightly-scoped prompt
    and sends it to an LLM, parses the JSON reply. Needs an API key.
  - extract_with_rules(text): a dependency-free fallback used whenever no key is
    configured, so this demo runs anywhere with zero setup and zero cost.

Run:
    python3 parser.py sample_inquiries.txt
"""

import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import Optional


LLM_SYSTEM_PROMPT = """You are a data-extraction engine for a real estate CRM.
Given a raw property inquiry (email or web form text), extract the fields below
and return ONLY a JSON object -- no prose, no markdown fences.

Fields:
  name: string or null
  phone: string or null (keep as written)
  email: string or null
  budget_min: integer NZD or null
  budget_max: integer NZD or null
  bedrooms: integer or null
  suburb_interest: string or null
  urgency: one of ["asap", "this_month", "browsing", null]
  notes: a one-sentence summary of anything else relevant

If a field isn't present in the text, use null. Do not guess.
"""

LLM_USER_PROMPT_TEMPLATE = """Inquiry:
---
{text}
---
Return the JSON object now."""


@dataclass
class Lead:
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    bedrooms: Optional[int] = None
    suburb_interest: Optional[str] = None
    urgency: Optional[str] = None
    notes: Optional[str] = None


def extract_with_llm(text: str, api_key: Optional[str] = None) -> Lead:
    """Production path. Shown here against a generic messages-style API.
    Falls back to the rule-based extractor if no key is configured, so the
    rest of the pipeline never breaks just because a secret isn't set.
    """
    api_key = api_key or os.environ.get("LLM_API_KEY")
    if not api_key:
        return extract_with_rules(text)

    import urllib.request

    payload = {
        "model": "claude-sonnet-5",
        "max_tokens": 400,
        "system": LLM_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": LLM_USER_PROMPT_TEMPLATE.format(text=text)}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())
    raw = body["content"][0]["text"]
    return Lead(**json.loads(raw))


# ---- fallback extractor: zero dependencies, zero API key, runs anywhere ----

PHONE_RE = re.compile(r"(?:\+?64|0)[\d\s\-]{7,12}\d")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
BUDGET_RE = re.compile(
    r"\$\s?(\d+(?:\.\d+)?)\s?([mMkK])(?:\s*(?:to|[-–])\s*\$?\s?(\d+(?:\.\d+)?)\s?([mMkK]))?"
)
BEDROOM_RE = re.compile(r"(\d)\s*[- ]?(?:bed|bedroom|br)\b", re.I)
NAME_RE = re.compile(r"(?:hi|hello|kia ora)?[,]?\s*(?:my name is|i'm|i am)\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)", re.I)

SUBURBS = ["remuera", "epsom", "parnell", "newmarket", "meadowbank", "st heliers", "mission bay"]
NEGATED_URGENCY = ["nothing urgent", "not urgent", "no rush", "no urgency"]
URGENCY_HINTS = {
    "asap": ["asap", "urgent", "this week", "immediately"],
    "this_month": ["this month", "next few weeks", "soon"],
    "browsing": ["just looking", "just started looking", "browsing", "exploring"],
}


def parse_amount(value: str, unit: str) -> int:
    multiplier = 1_000_000 if unit.lower() == "m" else 1_000
    return int(float(value) * multiplier)


def extract_with_rules(text: str) -> Lead:
    lead = Lead()

    phone = PHONE_RE.search(text)
    if phone:
        lead.phone = phone.group().strip()

    email = EMAIL_RE.search(text)
    if email:
        lead.email = email.group().rstrip(".")

    name = NAME_RE.search(text)
    if name:
        lead.name = name.group(1)

    budget = BUDGET_RE.search(text)
    if budget:
        v1, u1, v2, u2 = budget.groups()
        lo = parse_amount(v1, u1)
        hi = parse_amount(v2, u2) if v2 else lo
        lead.budget_min, lead.budget_max = min(lo, hi), max(lo, hi)

    bedrooms = BEDROOM_RE.search(text)
    if bedrooms:
        lead.bedrooms = int(bedrooms.group(1))

    lowered = text.lower()
    for suburb in SUBURBS:
        if suburb in lowered:
            lead.suburb_interest = suburb.title()
            break

    if any(neg in lowered for neg in NEGATED_URGENCY):
        lead.urgency = "browsing"
    else:
        for level, hints in URGENCY_HINTS.items():
            if any(h in lowered for h in hints):
                lead.urgency = level
                break

    lead.notes = (text.strip().split("\n")[0])[:140]
    return lead


def main():
    if len(sys.argv) < 2:
        print("usage: python3 parser.py <inquiries_file>")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        raw = f.read()

    inquiries = [block.strip() for block in raw.split("---") if block.strip()]
    results = [asdict(extract_with_llm(text)) for text in inquiries]

    print(json.dumps(results, indent=2))
    with open("parsed_leads.json", "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2)
    print(f"\n{len(results)} leads parsed -> parsed_leads.json", file=sys.stderr)


if __name__ == "__main__":
    main()
