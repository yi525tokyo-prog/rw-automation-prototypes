"""
Lead Matcher -- reconciles new marketing signups against existing CRM contacts
so the office doesn't create duplicate records or miss a returning enquirer.

Real SQL (SQLite, Python stdlib only) doing the join -- the same logic you'd
otherwise hand-wire in Make/Zapier with a lookup + filter + router module.

Run:
    python3 matcher.py
"""

import csv
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"[^\d]", "", phone or "")
    return digits[-9:]  # last 9 digits -- drops +64 / 0 trunk-prefix noise


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    crm = load_csv(HERE / "crm_contacts.csv")
    signups = load_csv(HERE / "marketing_signups.csv")

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE crm (
            id INTEGER, name TEXT, email TEXT, phone TEXT,
            norm_email TEXT, norm_phone TEXT, norm_name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE signups (
            name TEXT, email TEXT, phone TEXT, source TEXT,
            norm_email TEXT, norm_phone TEXT, norm_name TEXT
        )
    """)

    cur.executemany(
        "INSERT INTO crm VALUES (?,?,?,?,?,?,?)",
        [
            (r["id"], r["name"], r["email"], r["phone"],
             normalize_email(r["email"]), normalize_phone(r["phone"]), normalize_name(r["name"]))
            for r in crm
        ],
    )
    cur.executemany(
        "INSERT INTO signups VALUES (?,?,?,?,?,?,?)",
        [
            (r["name"], r["email"], r["phone"], r["source"],
             normalize_email(r["email"]), normalize_phone(r["phone"]), normalize_name(r["name"]))
            for r in signups
        ],
    )
    conn.commit()

    matched = cur.execute("""
        SELECT s.name, s.source, c.id AS crm_id, c.name AS crm_name,
               CASE
                 WHEN s.norm_email = c.norm_email AND s.norm_email != '' THEN 'email'
                 WHEN s.norm_phone = c.norm_phone AND s.norm_phone != '' THEN 'phone'
                 ELSE 'name'
               END AS matched_on
        FROM signups s
        JOIN crm c
          ON (s.norm_email = c.norm_email AND s.norm_email != '')
          OR (s.norm_phone = c.norm_phone AND s.norm_phone != '')
          OR (s.norm_name = c.norm_name)
    """).fetchall()

    matched_names = {row[0] for row in matched}

    all_signups = cur.execute("SELECT name, email, phone, source FROM signups").fetchall()
    new_leads = [r for r in all_signups if r[0] not in matched_names]

    print(f"{'='*64}\nAlready in CRM ({len(matched)}) -- link to existing record, don't duplicate:\n{'='*64}")
    for name, source, crm_id, crm_name, matched_on in matched:
        print(f"  {name:18s} (via {source:20s}) -> CRM #{crm_id} {crm_name}  [matched on {matched_on}]")

    print(f"\n{'='*64}\nNew leads ({len(new_leads)}) -- create CRM record:\n{'='*64}")
    for name, email, phone, source in new_leads:
        print(f"  {name:18s} {email or '(no email)':25s} {phone or '(no phone)':15s} via {source}")

    conn.close()


if __name__ == "__main__":
    main()
