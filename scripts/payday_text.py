"""Payday text: on each biweekly payday, email a bill breakdown for the pay
period to phone(s) via carrier email-to-SMS gateways.

Runs from GitHub Actions (see .github/workflows/payday-text.yml).

Env:
  SMS_TO              comma-separated recipients, e.g. 5551234567@tmomail.net,...
  GMAIL_ADDRESS       account to send from
  GMAIL_APP_PASSWORD  Gmail app password (not the account password)
  LEDGER_TOKEN        optional: fine-grained PAT to read the private ledger repo
  LEDGER_REPO         optional: owner/name of the ledger data repo
  LEDGER_URL          site link appended to the text
  DRY_RUN             if set, print the message instead of sending
  FAKE_TODAY          if set (YYYY-MM-DD), pretend today is this date (testing)
"""
import json, os, smtplib, ssl, sys, urllib.request
from base64 import b64decode
from datetime import date, timedelta
from email.mime.text import MIMEText

# Snapshot of the app seed, used when LEDGER_TOKEN isn't configured.
DEFAULT = {
    "income": {"people": [{"amount": 1902.67}, {"amount": 2002.76}], "anchorPayday": "2026-08-14"},
    "bills": [
        {"name": "Mortgage (half)", "amount": 1084, "freq": "perpaycheck"},
        {"name": "Daycare", "amount": 379, "freq": "weekly", "weekday": 5},
        {"name": "Car/Life Ins", "amount": 325, "freq": "monthly", "dueDay": 20},
        {"name": "Phone", "amount": 169, "freq": "monthly", "dueDay": 21},
        {"name": "Water/Sewer", "amount": 110, "freq": "quarterly", "dueDay": 23, "anchorMonth": 8},
        {"name": "Electric", "amount": 597, "freq": "monthly", "dueDay": 24},
        {"name": "Internet", "amount": 105, "freq": "monthly", "dueDay": 25},
        {"name": "Trash", "amount": 30, "freq": "monthly", "dueDay": 15},
        {"name": "Gym", "amount": 70, "freq": "monthly", "dueDay": 1},
    ],
    "debts": [
        {"name": "Equity Loan", "min": 474, "dueDay": 1, "balance": 1},
        {"name": "Amazon Card", "min": 40, "dueDay": 3, "balance": 1},
        {"name": "Student Loans", "min": 575.83, "dueDay": 17, "balance": 1},
        {"name": "Medical Bills", "min": 80, "dueDay": 28, "balance": 1},
    ],
}


def load_ledger():
    token, repo = os.environ.get("LEDGER_TOKEN"), os.environ.get("LEDGER_REPO")
    if not (token and repo):
        return DEFAULT, "seed"
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/contents/ledger.json",
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        return json.loads(b64decode(data["content"])), "live"
    except Exception as e:
        print(f"ledger fetch failed ({e}); using seed snapshot", file=sys.stderr)
        return DEFAULT, "seed"


def parse_d(s):
    y, m, d = map(int, s.split("-"))
    return date(y, m, d)


def clamp(y, m, day):
    while m > 12: m -= 12; y += 1
    last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(day, last))


def paydays(anchor, start, end):
    d = anchor
    while d > start: d -= timedelta(days=14)
    while d < start: d += timedelta(days=14)
    out = []
    while d <= end: out.append(d); d += timedelta(days=14)
    return out


def occurrences(b, start, end, anchor):
    freq, out = b.get("freq"), []
    if freq == "perpaycheck":
        out = paydays(anchor, start, end)
    elif freq in ("weekly", "biweekly"):
        step = 7 if freq == "weekly" else 14
        wd = b.get("weekday", 5) % 7          # JS: 0=Sunday
        d = start + timedelta(days=(wd - (start.weekday() + 1) % 7) % 7)
        while d <= end: out.append(d); d += timedelta(days=step)
    elif freq == "monthly":
        y, m = start.year, start.month
        while date(y, m, 1) <= end:
            d = clamp(y, m, b.get("dueDay", 1))
            if start <= d <= end: out.append(d)
            m += 1
            if m > 12: m, y = 1, y + 1
    elif freq in ("quarterly", "annual"):
        step, am = (3, b.get("anchorMonth", 1)) if freq == "quarterly" else (12, b.get("anchorMonth", 1))
        for y in (start.year - 1, start.year, start.year + 1):
            for m in range(1, 13):
                if (m - am) % step == 0:
                    d = clamp(y, m, b.get("dueDay", 1))
                    if start <= d <= end: out.append(d)
    return out


def build_message(D, today):
    anchor = parse_d(D["income"]["anchorPayday"])
    pay = sum(float(p.get("amount") or 0) for p in D["income"]["people"])
    start, end = today, today + timedelta(days=13)
    items = []
    for b in D.get("bills", []):
        for d in occurrences(b, start, end, anchor):
            items.append((d, b["name"], float(b.get("amount") or 0)))
    for dt in D.get("debts", []):
        if float(dt.get("min") or 0) > 0 and float(dt.get("balance") or 0) > 0:
            for d in occurrences({"freq": "monthly", "dueDay": dt.get("dueDay", 1)}, start, end, anchor):
                items.append((d, dt["name"] + " min", float(dt["min"])))
    items.sort()
    total = sum(a for _, _, a in items)
    lines = [f"Payday! ${pay:,.0f} in. Bills thru {end.month}/{end.day}: ${total:,.0f}"]
    lines += [f"{d.month}/{d.day} {n[:18]} ${a:,.0f}" for d, n, a in items]
    left = pay - total
    lines.append(("Left: $" + f"{left:,.0f}") if left >= 0 else ("SHORT $" + f"{-left:,.0f}"))
    lines.append(os.environ.get("LEDGER_URL", "https://sharedsupport.github.io/WilliamsBudget/"))
    return "\n".join(lines)


def main():
    today = parse_d(os.environ["FAKE_TODAY"]) if os.environ.get("FAKE_TODAY") else date.today()
    D, source = load_ledger()
    anchor = parse_d(D["income"]["anchorPayday"])
    if (today - anchor).days % 14 != 0:
        print(f"{today} is not a payday (anchor {anchor}); nothing to send")
        return
    msg = build_message(D, today)
    print(f"[{source} data] message ({len(msg)} chars):\n{msg}")
    if os.environ.get("DRY_RUN"):
        return
    sender, pw = os.environ["GMAIL_ADDRESS"], os.environ["GMAIL_APP_PASSWORD"]
    recipients = [r.strip() for r in os.environ["SMS_TO"].split(",") if r.strip()]
    m = MIMEText(msg)
    m["From"], m["To"] = sender, ", ".join(recipients)
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(sender, pw)
        s.sendmail(sender, recipients, m.as_string())
    print(f"sent to {len(recipients)} recipient(s)")


if __name__ == "__main__":
    main()
