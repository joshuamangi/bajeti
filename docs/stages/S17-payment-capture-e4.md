# S17: E4 Payment capture (#113)

**Prompt:** P11  |  **Mode:** design-gate  |  **Depends on:** S10  |  **Suggested branch:** `feature/issue-113-payment-capture`

## Goal

Capture M-Pesa and payment-email messages into an inbox and convert them to expenses, with a manual paste box first.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `models.py`, the expense service and schema
4. `docs/backlog.md` (iPhone ingestion options)
5. `core/security.py` (for the separate API token design)
6. app handlers and the dashboard template

### Outputs of earlier stages this stage relies on

- S10 cross-user test pattern

## Before you start

- Write anonymised sample messages with fake names and fake numbers. Never use real messages.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: design then build payment capture. Design first; wait for approval.

Spec: PendingPayment(raw_text, amount, merchant, reference, received_at, status). Parsers for M-Pesa SMS and payment emails, an authenticated POST /pending-payments, a "paste message" box, and an inbox where I pick a category and convert each item to an expense. Manual paste ships first; the iPhone transport is decided later.

Design must cover:
- M-Pesa message types: paid to, sent to, received, withdraw, airtime, fuliza (and fees/balance lines). For each type: expected fields, whether it is an expense, income or ignored, and how to treat the transaction fee.
- Parser design: a small library of regexes per type, a table-driven test file with many anonymised sample messages (use fake names and fake numbers; never real ones), safe failure (unparseable text stays in the inbox with raw_text intact).
- Dedupe by transaction code (unique per user), and what happens on re-paste.
- Privacy: raw messages are sensitive; do not log them; delete or redact raw_text after conversion (configurable).
- iPhone options with trade-offs in two lines each: Shortcuts automation on incoming message (may need a confirmation tap, may not fire reliably), share-sheet Shortcut that POSTs the text with a per-user API token, forwarding emails to a mailbox polled over IMAP, Gmail API with sender filter. Recommend one, including how a long-lived, revocable, scope-limited API token for the Shortcut would work (separate from the login JWT).

Then implement in PRs: model+migration, parser+tests, API, paste box + inbox UI.
```

## Watch out for

- Use fake sample messages only. Real messages contain names and phone numbers and the repo is public.
- Treat parsed text as untrusted input. Test hostile and malformed messages.
- Use a separate scoped API token for the phone, not the login token.

## Your part (Claude cannot or should not do these)

1. Choose the iPhone transport after reading the recommendation.
2. Approve the design.
3. Set up the Shortcut yourself later, using the scoped API token.

## Done when

- Design covers each message type, fee handling, parsers with table-driven tests, dedupe, privacy and the iPhone options.
- Implemented in PRs: model and migration, parser and tests, API, paste box and inbox.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- docs/design/payment-capture.md
- Parser library and tests
- Pending payments API and inbox UI

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: The chosen iPhone transport and token approach.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S18-code-workflow-e7.md`: E7 Code and workflow improvements (#116).
