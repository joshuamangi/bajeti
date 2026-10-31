# Payment capture: design

Status: approved by the owner on 2026-10-29, as written.

Look and behaviour: Prototype A (`design/prototype-a/`, PORT-GUIDE §5.9). Manual paste ships first; the iPhone shortcut comes in a second step, after you try it.

## Decisions to approve

1. **What becomes an inbox item**, by M-Pesa message type:

| Type | Example (fake) | Fields | Treatment |
|---|---|---|---|
| Paid to (Buy Goods, Paybill) | `QAB12CD3EF Confirmed. Ksh1,840.00 paid to Demo Supermarket on 27/10/26 at 7:15 PM. New M-PESA balance is Ksh12,300.00. Transaction cost, Ksh0.00.` | reference, amount, payee, date, fee | expense, into the inbox |
| Sent to (to a person) | `QAB12CD3EG Confirmed. Ksh300.00 sent to DEMO PERSON 0700000000 on 27/10/26 at 9:02 AM. ... Transaction cost, Ksh7.00.` | same; the phone number is dropped | expense, into the inbox (dismiss it if it was not spending) |
| Airtime | `QAB12CD3EH Confirmed. You bought Ksh100.00 of airtime on 27/10/26 ...` | reference, amount, date | expense, payee "Airtime" |
| Received | `QAB12CD3EI Confirmed. You have received Ksh5,000.00 from DEMO PERSON ...` | | income: not added; the paste box says "This is money received, so it was not added" |
| Withdraw (agent) | `QAB12CD3EJ Confirmed. on 27/10/26 at 1:00 PM Withdraw Ksh2,000.00 from 123456 - Demo Agent ...` | | not added: cash is spent later; says so |
| Fuliza | `QAB12CD3EK Confirmed. Fuliza M-PESA amount is Ksh500.00 ...` | | not added: the "paid to" message for the same payment is the expense |
| Payment email | `Your payment of KES 3,500.00 to Demo Fibre Internet was successful. Reference: FBR20261027.` | amount, payee, reference | expense, into the inbox |

2. **Transaction fees count.** The fee is added to the amount, because that is the money that left the account. The card shows "Ksh300 + Ksh7 fee". You can change the amount before approving.
3. **Raw messages are deleted on approve or dismiss.** They are kept only while an item waits in the inbox, never logged, and hidden while amounts are hidden. A setting `KEEP_RAW_MESSAGES=false` controls this.
4. **Phone transport later: a share-sheet Shortcut with its own token** (details below), not an SMS automation. Built only after the paste flow has been used for a while.

## Data (one migration, reversible)

```
pending_payments
  id, user_id, source: paste | sms | email
  kind            paid | sent | airtime | email | unknown
  raw_text        nullable (cleared on approve or dismiss)
  amount, fee     Decimal, nullable when the text could not be read
  payee, reference, paid_on (date)
  status          pending | approved | dismissed
  expense_id      nullable
  received_at, created_at
  unique (user_id, reference)          dedupe

payee_rules                            "Remember Demo Grocer for next time"
  id, user_id, payee (normalised), category_id (FK categories, cascade)
  unique (user_id, payee)
```

## Parser

- A small table of regular expressions per message type in `services/payment_parser.py`. Amounts are read as Decimal. Text is untrusted, so the parser never evaluates it and caps its length at 2,000 characters.
- Test file: a table of at least 25 fake messages (fake names, fake numbers, references like `QAB12CD3EF`), with expected fields for each, plus hostile and malformed text: HTML, very long input, two amounts, missing reference, non-Latin text, numbers with spaces.
- **Safe failure:** text that matches no type still goes into the inbox as "Couldn't read this message", with the raw text kept, so you can type the amount or dismiss it.
- **Re-paste:** the same reference gives 409, and the paste box says "Already captured: QAB12CD3EF (approved 27 Oct)". Messages with no reference are not deduplicated.

## Category suggestion

1. A remembered payee rule, if its category is in the active budget.
2. Otherwise keywords from the prototype (grocer or supermarket → Groceries, pharm or clinic → Health, fuel or matatu → Transport, power, water or internet → Utilities, cinema or stream → Entertainment), matched by category name in the active budget.
3. Otherwise none: you pick a category.

## Endpoints (all scoped by user, each with a cross-user 404 test)

- `POST /api/payments/capture {raw}` parses and adds to the inbox (201), returns 409 for a duplicate, and 200 with a reason for income, withdrawals and Fuliza.
- `GET /api/payments?status=pending`
- `POST /api/payments/{id}/approve {category_id, amount?, remember}` creates the expense in the month of `paid_on`.
- `POST /api/payments/{id}/dismiss`, and `POST /api/payments/{id}/restore` for Undo (within 6 seconds, before the raw text is cleared).

## Screens

- **Home:** "3 payments waiting for a category" row, when there are any. The More tab count includes them.
- **More → Payments:** the paste box ("Read message"), a preview of what was read (amount, payee, reference), then the inbox cards. Each card has the source and time, amount, payee, reference and date, an "Original message" disclosure, a category select ("Category in Monthly", with a Suggested tag), "Remember Demo Grocer for next time", and Dismiss and Approve, both with Undo. Swiping left dismisses. The inbox lists every pending payment; only the category choices follow the active budget.

## Phone transport (step 2, after approval of this note)

- **Share-sheet Shortcut (recommended):** select the M-Pesa message, Share → "Send to Bajeti". It works every time you use it and needs no always-on automation.
- **SMS automation:** fully automatic, but iOS often asks for a confirmation tap and does not fire for every message.
- **Email forwarding to a mailbox polled over IMAP:** works for payment emails only, and adds a mailbox password on the Pi.
- **Gmail API:** precise filtering, but OAuth setup and a Google dependency, for emails only.

The Shortcut uses a **personal API token**, separate from the login:
- created on the Account page and shown once;
- stored only as a hash, named ("iPhone"), and revocable;
- scope `payments:capture`: it can only call `POST /api/payments/capture`;
- rate-limited, and listed with its last-used date.

## Phone capture: built (2026-10-31)

Step A (the share-sheet Shortcut) is built. Setup steps for the phone are in `docs/runbooks/iphone-shortcut.md`.

- **Phone tokens** (`api_tokens` table, `services/api_token_service.py`): `bjt_` followed by 32 random bytes. Only the SHA-256 hash and the first 8 characters (for display) are stored. Up to 5 per user. Revoking deletes the row.
- **Who can use them:** a token belongs to the user who created it on the Account page. Captures land in that user's inbox only. All inbox queries are scoped by `user_id`.
- **Capture only:** `POST /api/payments/capture` uses `core.security.get_capture_user`, which accepts the login token or a phone token. Every other endpoint uses `get_current_user`, where a phone token fails JWT decoding (401). Tokens are managed at `/api/tokens` with the login token only.
- **Limits** (`core/rate_limit.py`): 20 unknown tokens per address per 15 minutes; 60 captures per token per hour. Both return 429.
- **Reply:** every capture reply has a one-line `message` for the Shortcut to show (added, already captured, not spending). 409 replies keep `detail` as before.
- **Possible duplicate:** a message with **no reference** is flagged, not refused, when an earlier non-dismissed payment has the same amount, payee and date. Messages with a reference are deduplicated exactly (409), as before.
- **Install link:** `SHORTCUT_INSTALL_URL` (a GitHub Actions variable that the deploy writes into the Pi `.env`; never in the repo) adds an "Add the Shortcut" link on the Account page. The link does not carry the token: iCloud links are public. The Shortcut asks for the token when it is added.
