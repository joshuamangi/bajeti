# Backlog

Ideas that are not scheduled yet. Move an item into `docs/roadmap.md` and open an issue when it is picked up.

## Payment ingestion on iPhone (M-Pesa SMS and payment emails)

Open question: how do the raw messages get from the phone to Bajeti?

Options to evaluate:

- iOS Shortcuts automation on incoming message. Needs testing for reliability, because SMS automations on iOS often ask for a confirmation tap and may not fire for every message.
- Share sheet Shortcut: select the M-Pesa message, share to a Shortcut that POSTs it to `/api/pending-payments`.
- Forward payment emails to a dedicated mailbox that the Pi polls over IMAP.
- Gmail API with a filter on payment senders.
- Manual paste box in the app (the first thing to ship, works with any option above).

Decision needed after trying the share sheet Shortcut for a week.

## Other ideas

- Loading spinners (from `docs/TODO.md`)
- Consistent button and input sizes, for example Quick Expense (from `docs/TODO.md`)

## Missed-backup alerts (from S02, not urgent)

Today a missed night is silent. Both Pis already support it; it only needs two free dead-man's-switch checks (for example on healthchecks.io):

- Check 1: period 1 day, grace 3 hours. Put its URL in `BACKUP_PING_URL` in `~/.config/bajeti/backup.env` on the app Pi. `backup.sh` pings on success and at `/fail` on failure.
- Check 2: period 1 day, grace 3 hours. Put its URL in `PULL_PING_URL` in `~/.config/bajeti/pull.env` on the backup Pi. Pinged only after a fully verified pull.

The URLs are secrets: keep them only in those two files and the password manager, never in the repo. The Mac already warns by notification when its newest copy is over 7 days old.
