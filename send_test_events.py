"""Fires sample events at the notifier to prove the scenario end-to-end.
Two valid leads (one HIGH priority, one LOW), and two deliberately broken
payloads to prove the error path doesn't just crash the workflow.
"""

import json
import urllib.request
import urllib.error

URL = "http://127.0.0.1:8787/webhook/new-lead"

EVENTS = [
    {"name": "Sarah Thompson", "email": "sarah.thompson@email.com",
     "source": "Open Home - Remuera", "urgency": "asap", "budget_max": 1400000},
    {"name": "Mike B", "phone": "021 555 0192", "source": "Newsletter",
     "urgency": "browsing"},
    {"name": "J. Chen", "source": "Facebook Ad"},          # missing contact -> rejected
    {"source": "Website form"},                             # missing name -> rejected
]

for event in EVENTS:
    req = urllib.request.Request(
        URL,
        data=json.dumps(event).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(resp.status, resp.read().decode())
    except urllib.error.HTTPError as e:
        print(e.code, e.read().decode())
