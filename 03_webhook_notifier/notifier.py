"""
Lead Notifier -- a minimal webhook receiver that plays the same role a
Make.com / Zapier scenario would: trigger (new lead submitted) -> validate
-> transform/enrich -> route to a notification channel.

Swap send_notification() for a real Slack/Teams incoming-webhook POST (one
line) to go from demo to production. Everything else -- validation, priority
scoring, error logging -- stays the same.

Run:
    python3 notifier.py &          # starts the receiver on :8787
    python3 send_test_events.py    # fires sample events at it
"""

import json
import http.server
import socketserver
from datetime import datetime, timezone

PORT = 8787
LOG_FILE = "notifications.log"
ERROR_FILE = "errors.log"

REQUIRED_FIELDS = ["name", "source"]
CONTACT_FIELDS = ["email", "phone"]


def validate(payload: dict) -> list:
    problems = []
    for field in REQUIRED_FIELDS:
        if not payload.get(field):
            problems.append(f"missing required field: {field}")
    if not any(payload.get(f) for f in CONTACT_FIELDS):
        problems.append("no contact method: need email or phone")
    return problems


def priority(payload: dict) -> str:
    urgency = (payload.get("urgency") or "").lower()
    budget_max = payload.get("budget_max") or 0
    if urgency == "asap" or budget_max >= 1_500_000:
        return "HIGH"
    if urgency == "this_month":
        return "MEDIUM"
    return "LOW"


def send_notification(payload: dict):
    """Stand-in for a Slack/Teams webhook POST -- same shape, different transport."""
    line = (
        f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] "
        f"({priority(payload)}) New lead via {payload.get('source')}: "
        f"{payload.get('name')} -- {payload.get('email') or payload.get('phone')}"
    )
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def log_error(payload: dict, problems: list):
    entry = {
        "payload": payload,
        "problems": problems,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with open(ERROR_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[REJECTED] {problems}: {payload}")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook/new-lead":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "invalid JSON"}')
            return

        problems = validate(payload)
        if problems:
            log_error(payload, problems)
            self.send_response(422)
            self.end_headers()
            self.wfile.write(json.dumps({"error": problems}).encode())
            return

        send_notification(payload)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "notified"}')

    def log_message(self, format, *args):
        pass  # quiet -- we do our own logging above


if __name__ == "__main__":
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"listening on :{PORT} ... (Ctrl+C to stop)")
        httpd.serve_forever()
