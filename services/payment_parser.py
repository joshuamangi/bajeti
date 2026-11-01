"""Read M-Pesa SMS, bank SMS and payment emails (docs/design/payments.md).

The text is untrusted: it is only matched against fixed patterns, never evaluated, and capped
in length. Nothing here logs the message. A message that matches no type comes back as
kind "unknown" so it can still go to the inbox with its text kept.
"""
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

MAX_LENGTH = 2000

MONEY = r"(?:Ksh|KES|KShs?)\.?\s?([\d,]+(?:\.\d{1,2})?)"
PHONE = r"(?:\+?254|0)[17]\d{8}"

# Savings: money from a bank to M-Pesa and bank card purchases are withdrawals from a savings
# budget; a bank deposit adds to one. Only the last four digits of an account are kept.
BANK_RECEIVED = re.compile(r"\byou have received\s+" + MONEY + r"\s+from\s+((?:B2C\s+)?.*?\bbank\b.*?)"
                           r"(?:\s+on\s+\d{1,2}/|\.\s|\.$|$)", re.I | re.S)
CARD = re.compile(r"\btransaction of\s+" + MONEY + r"\s+was made on card ending(?: with)?\s+(\d{4})\s+at\s+(.+?)"
                  r"(?:\s+on\s+(\d{4}-\d{2}-\d{2})|\.\s|\.$|$)", re.I | re.S)
DEPOSIT = re.compile(MONEY + r"\s+was deposited to\s+(?:your\s+)?acc(?:ount)?\.?\s+ending(?: with)?\s+(\d{4})", re.I)

# Types that are not spending: money received from people, cash withdrawn at an agent (spent
# later), Fuliza notices (the "paid to" message for the same payment is the expense).
IGNORED = [
    ("received", re.compile(r"\byou have received\b", re.I),
     "This is money received, so it was not added."),
    ("withdraw", re.compile(r"\bwithdraw\b.{0,80}?\bfrom\b", re.I | re.S),
     "This is a cash withdrawal at an agent. Add what you spend the cash on instead."),
    ("fuliza", re.compile(r"\bFuliza M-?PESA amount is\b", re.I),
     "This is a Fuliza notice. The payment message for the same purchase is the one to add."),
]

KINDS = [
    ("airtime", re.compile(r"\bbought\b.{0,40}?\bof airtime\b", re.I | re.S)),
    ("paid", re.compile(r"\bpaid to\b", re.I)),
    ("sent", re.compile(r"\bsent to\b", re.I)),
    ("email", re.compile(r"\bpayment of\b.{0,60}?\bto\b", re.I | re.S)),
]

PAYEE = {
    "paid": re.compile(r"\bpaid to\s+(.+?)(?:\.?\s+on\s+\d{1,2}/|\.\s|\.$|\s+for account\b|$)", re.I | re.S),
    "sent": re.compile(r"\bsent to\s+(.+?)(?:\s+for account\b|\s+" + PHONE + r"\b|\.?\s+on\s+\d{1,2}/|\.\s|\.$|$)",
                       re.I | re.S),
    "email": re.compile(r"\bpayment of\b.{0,40}?\bto\s+(.+?)(?:\s+(?:was|has been|is)\b|\.\s|\.$|,|$)", re.I | re.S),
}

LEADING_REFERENCE = re.compile(r"^\s*([A-Z0-9]{8,12})\b")
LABELLED_REFERENCE = re.compile(
    r"\b(?:ref(?:erence)?|transaction(?:\s+id)?)\s*(?:no\.?|number)?\s*[:.#]?\s*([A-Z0-9]{6,14})\b", re.I)
FEE = re.compile(r"\bTransaction cost,?\s*" + MONEY, re.I)
BALANCE = re.compile(r"\b(?:New M-?PESA balance is|balance is)\s*" + MONEY + r"\.?", re.I)
DAY_LIMIT = re.compile(r"\bAmount you can transact within the day is\s*[\d,]+(?:\.\d{1,2})?\.?", re.I)
DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def _amount(text: str) -> Optional[Decimal]:
    try:
        value = Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None
    return value if value > 0 else None


def _date(text: str) -> Optional[date]:
    m = DATE.search(text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year = year + 2000 if year < 100 else year
    else:
        m = ISO_DATE.search(text)
        if not m:
            return None
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _clean_payee(text: str) -> Optional[str]:
    text = re.sub(PHONE, "", text)
    text = re.sub(r"[<>\"`]", "", text)          # no markup survives into the inbox
    text = re.sub(r"\s+", " ", text).strip(" .,-")
    return text[:80] or None


def _reference(text: str) -> Optional[str]:
    m = LEADING_REFERENCE.match(text)
    if m and re.search(r"\d", m.group(1)) and re.search(r"[A-Z]", m.group(1)):
        return m.group(1)
    m = LABELLED_REFERENCE.search(text)
    return m.group(1).upper() if m else None


def _savings(text: str) -> Optional[dict]:
    """A bank-to-M-Pesa transfer or card purchase (kinds "received", "card": a withdrawal) or a
    bank deposit (kind "deposit"). None for anything else."""
    m = BANK_RECEIVED.search(text)
    if m:
        payee = _clean_payee(re.sub(r"^B2C\s+", "", m.group(2), flags=re.I))
        return {"kind": "received", "amount": _amount(m.group(1)), "payee": payee, "account": None,
                "reference": _reference(text), "paid_on": _date(text)}
    m = CARD.search(text)
    if m:
        return {"kind": "card", "amount": _amount(m.group(1)), "payee": _clean_payee(m.group(3)),
                "account": f"Card ending {m.group(2)}", "reference": _reference(text),
                "paid_on": _date(m.group(4) or "")}
    m = DEPOSIT.search(text)
    if m:
        return {"kind": "deposit", "amount": _amount(m.group(1)), "payee": None,
                "account": f"Acc. ending {m.group(2)}", "reference": _reference(text), "paid_on": _date(text)}
    return None


def parse(raw: str) -> dict:
    """Return {"kind", "amount", "fee", "payee", "account", "reference", "paid_on"} for a spending
    or savings message, {"kind", "ignored": reason} for income, withdrawals and Fuliza, or kind
    "unknown"."""
    text = re.sub(r"\s+", " ", str(raw or "")).strip()[:MAX_LENGTH]
    savings = _savings(text)
    if savings:
        return {**savings, "fee": None}
    for kind, pattern, reason in IGNORED:
        if pattern.search(text):
            return {"kind": kind, "ignored": reason}

    reference = _reference(text)
    fee_match = FEE.search(text)
    fee = _amount(fee_match.group(1)) if fee_match else None
    # The amount is the first sum of money that is not the balance, the fee or the day limit.
    body = DAY_LIMIT.sub(" ", FEE.sub(" ", BALANCE.sub(" ", text)))
    amount_match = re.search(MONEY, body, re.I)
    amount = _amount(amount_match.group(1)) if amount_match else None

    kind = next((k for k, pattern in KINDS if pattern.search(text)), "unknown")
    payee = None
    if kind == "airtime":
        payee = "Airtime"
    elif kind in PAYEE:
        m = PAYEE[kind].search(text)
        payee = _clean_payee(m.group(1)) if m else None

    return {"kind": kind, "amount": amount, "fee": fee, "payee": payee, "account": None,
            "reference": reference, "paid_on": _date(text)}
