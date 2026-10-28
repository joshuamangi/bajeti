"""Table-driven parser tests. Every message here is made up: fake names, fake numbers, fake codes."""
from datetime import date
from decimal import Decimal as D

import pytest

from services.payment_parser import MAX_LENGTH, parse

SPENDING = [
    # (message, kind, amount, fee, payee, reference, paid_on)
    ("QAB12CD3EF Confirmed. Ksh1,840.00 paid to Demo Supermarket. on 27/10/26 at 7:15 PM. New M-PESA balance is Ksh12,300.00. Transaction cost, Ksh0.00. Amount you can transact within the day is 498,160.00.",
     "paid", "1840.00", None, "Demo Supermarket", "QAB12CD3EF", date(2026, 10, 27)),
    ("QAB12CD3EG Confirmed. Ksh450.00 paid to Demo Grocer on 26/10/26 at 12:38 PM. New M-PESA balance is Ksh9,050.00. Transaction cost, Ksh0.00.",
     "paid", "450.00", None, "Demo Grocer", "QAB12CD3EG", date(2026, 10, 26)),
    ("QAB12CD3EH Confirmed. Ksh300.00 sent to DEMO PERSON 0700000000 on 27/10/26 at 9:02 AM. New M-PESA balance is Ksh8,743.00. Transaction cost, Ksh7.00.",
     "sent", "300.00", "7.00", "DEMO PERSON", "QAB12CD3EH", date(2026, 10, 27)),
    ("QAB12CD3EI Confirmed. Ksh2,000.00 sent to DEMO POWER PREPAID for account 12345678901 on 25/10/26 at 8:00 PM New M-PESA balance is Ksh6,700.00. Transaction cost, Ksh33.00.",
     "sent", "2000.00", "33.00", "DEMO POWER PREPAID", "QAB12CD3EI", date(2026, 10, 25)),
    ("QAB12CD3EJ Confirmed. Ksh 1,250.50 sent to Demo Water Vendor +254711111111 on 1/9/26 at 7:05 AM. Transaction cost, Ksh 13.00.",
     "sent", "1250.50", "13.00", "Demo Water Vendor", "QAB12CD3EJ", date(2026, 9, 1)),
    ("QAB12CD3EK confirmed.You bought Ksh100.00 of airtime on 27/10/26 at 8:00 AM.New M-PESA balance is Ksh4,900.00. Transaction cost, Ksh0.00.",
     "airtime", "100.00", None, "Airtime", "QAB12CD3EK", date(2026, 10, 27)),
    ("QAB12CD3EL Confirmed. You bought Ksh50.00 of airtime for 0722222222 on 2/10/26 at 6:00 PM. New M-PESA balance is Ksh950.00.",
     "airtime", "50.00", None, "Airtime", "QAB12CD3EL", date(2026, 10, 2)),
    ("Your payment of KES 3,500.00 to Demo Fibre Internet was successful. Reference: FBR20261027.",
     "email", "3500.00", None, "Demo Fibre Internet", "FBR20261027", None),
    ("Payment receipt: KES 1,250.00 paid to Demo Pharmacy. Reference: EML4471K2.",
     "paid", "1250.00", None, "Demo Pharmacy", "EML4471K2", None),
    ("Hello Amani, your payment of KES 899.00 to Demo Streaming has been received. Transaction ID: STR77AB12 on 03/10/2026.",
     "email", "899.00", None, "Demo Streaming", "STR77AB12", date(2026, 10, 3)),
    ("QAB12CD3EM Confirmed. Ksh25,000.00 paid to DEMO LANDLORD LTD. on 01/10/26 at 9:00 AM. New M-PESA balance is Ksh3,000.00. Transaction cost, Ksh0.00.",
     "paid", "25000.00", None, "DEMO LANDLORD LTD", "QAB12CD3EM", date(2026, 10, 1)),
    ("QAB12CD3EN Confirmed. Ksh60.00 paid to Demo Matatu Sacco. on 14/10/26 at 7:40 AM.",
     "paid", "60.00", None, "Demo Matatu Sacco", "QAB12CD3EN", date(2026, 10, 14)),
    ("QAB12CD3EO Confirmed. Kshs500.00 sent to DEMO SHOP 0733333333 on 5/10/26 at 5:00 PM.",
     "sent", "500.00", None, "DEMO SHOP", "QAB12CD3EO", date(2026, 10, 5)),
    ("QAB12CD3EP Confirmed. KES 2,600.00 paid to Demo Fuel Station on 20/10/26 at 6:03 PM. Transaction cost, KES 0.00.",
     "paid", "2600.00", None, "Demo Fuel Station", "QAB12CD3EP", date(2026, 10, 20)),
    ("Your payment of KES 12,000.00 to Demo School has been processed, ref no. SCH2026T3.",
     "email", "12000.00", None, "Demo School", "SCH2026T3", None),
]

IGNORED = [
    ("QAB12CD3EQ Confirmed.You have received Ksh5,000.00 from DEMO PERSON 0744444444 on 27/10/26 at 1:00 PM New M-PESA balance is Ksh10,000.00.", "received"),
    ("QAB12CD3ER Confirmed.on 27/10/26 at 1:00 PM Withdraw Ksh2,000.00 from 123456 - Demo Agent Shop New M-PESA balance is Ksh8,000.00. Transaction cost, Ksh29.00.", "withdraw"),
    ("QAB12CD3ES Confirmed. Fuliza M-PESA amount is Ksh 500.00. Access Fee charged Ksh 5.00. Total Fuliza M-PESA outstanding amount is Ksh505.00 due on 26/11/26.", "fuliza"),
    ("You have received KES 1,000.00 from Demo Employer. Reference: SAL202610.", "received"),
]


@pytest.mark.parametrize("message,kind,amount,fee,payee,reference,paid_on", SPENDING)
def test_spending_messages(message, kind, amount, fee, payee, reference, paid_on):
    got = parse(message)
    assert got["kind"] == kind
    assert got["amount"] == D(amount)
    assert got["fee"] == (D(fee) if fee else None)
    assert got["payee"] == payee
    assert got["reference"] == reference
    assert got["paid_on"] == paid_on


@pytest.mark.parametrize("message,kind", IGNORED)
def test_income_withdrawals_and_fuliza_are_ignored(message, kind):
    got = parse(message)
    assert got["kind"] == kind and got["ignored"]


@pytest.mark.parametrize("message", [
    "",
    "hello there",
    "Meeting at 10 tomorrow, bring Ksh",
    "<script>alert(1)</script> paid to <b>Demo</b>",
    "QAB12CD3EF Confirmed. paid to Demo Shop on 27/10/26.",           # no amount
    "Ksh-50.00 paid to Demo",                                         # negative
    "Ksh0.00 paid to Demo Shop",                                      # zero
    "Malipo ya Ksh 200.00 yamefanikiwa kwa Duka la Demo",             # not a known format
    "Ksh 1,0,0,0.00 paid to Demo",                                    # mangled number
    "QAB12CD3EF Confirmed. Ksh100.00 paid to Demo on 31/02/26 at 1PM.",  # impossible date
])
def test_malformed_and_hostile_text_never_raises(message):
    got = parse(message)
    assert got["kind"] in ("paid", "sent", "email", "airtime", "unknown")
    assert got.get("amount") is None or got["amount"] > 0
    assert "<" not in (got.get("payee") or "") and ">" not in (got.get("payee") or "")


def test_impossible_date_is_dropped_not_guessed():
    assert parse("QAB12CD3EF Confirmed. Ksh100.00 paid to Demo on 31/02/26 at 1PM.")["paid_on"] is None


def test_unknown_text_keeps_kind_unknown():
    assert parse("Malipo ya Ksh 200.00 yamefanikiwa kwa Duka la Demo")["kind"] == "unknown"


def test_very_long_text_is_cut_and_still_reads():
    message = "QAB12CD3EF Confirmed. Ksh100.00 paid to Demo Shop on 27/10/26. " + "x" * (MAX_LENGTH * 5)
    got = parse(message)
    assert got["amount"] == D("100.00") and got["payee"] == "Demo Shop"


def test_balance_and_day_limit_are_not_taken_as_the_amount():
    got = parse("QAB12CD3EF Confirmed. New M-PESA balance is Ksh9,999.00. Ksh75.00 paid to Demo Kiosk on 2/10/26.")
    assert got["amount"] == D("75.00")
