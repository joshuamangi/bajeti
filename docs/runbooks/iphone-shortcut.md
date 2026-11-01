# iPhone Shortcut: "Send to Bajeti"

Sends an M-Pesa or bank SMS to the Payments inbox from the share sheet. Bank transfers to M-Pesa, card purchases and deposits arrive as savings items. You approve it in Bajeti as usual. Design: `docs/design/payments.md` ("Phone capture").

`<BAJETI_URL>` below is the public address of your Bajeti, for example `https://<your-domain>`. Never put the real address or a token in this repository.

## 1. Create a phone token

1. In Bajeti, open More → Account → Phone capture.
2. Name the phone, then tap **Create token**.
3. Tap **Copy**. The token starts with `bjt_` and is shown only once. If you lose it, revoke it and create a new one.

The token can only add messages to your own inbox. It cannot read your budgets or payments, approve anything, or log in.

## 2. Build the Shortcut (once, by the owner)

In the Shortcuts app, tap **+** and name it **Send to Bajeti**.

1. Open the Shortcut's details (ⓘ) and turn on **Show in Share Sheet**. Set the accepted input to **Text** only.
2. Add a **Text** action and paste your token into it. Make sure there is **no empty line or space after the token**: a line break ends up in the header and the request is rejected before it reaches Bajeti. Optionally add **Set Variable** `Token` to `Text` below it.
3. Add **Get Contents of URL**:
   - URL: `<BAJETI_URL>/api/payments/capture`
   - Method: **POST**
   - Headers: `Authorization` = `Bearer ` followed by the `Token` variable (one space after Bearer, and **no space after `Authorization`** in the name field)
   - Request Body: **JSON**, with fields `raw` (Text) = **Shortcut Input** and `source` (Text) = `sms`
4. Add **Get Dictionary Value**: get the value for `message` in **Contents of URL**.
5. Add **If** Dictionary Value **has any value**: **Show Notification** with the Dictionary Value.
   **Otherwise**: **Get Dictionary Value** for `detail` in Contents of URL, then **Show Notification** with it. This covers an invalid token (401) or too many sends (429).

The same Shortcut works for bank SMS: share the bank's message the same way. If you add a Message automation, add one trigger per sender (M-Pesa and your bank) that runs this Shortcut.

Try it: in Messages, press and hold an M-Pesa message → **Share** (or select the text → Share) → **Send to Bajeti**. You should see "Added … Approve it in Bajeti." Send the same message again: you should see "Already captured: …".

## 3. Share it for other household members (optional)

1. **Duplicate** the Shortcut and clear the token from the copy's Text action, so the copy holds no token.
2. In the copy's details, add an **Import Question** for that Text action: "Paste your Bajeti phone token".
3. Share the copy → **Copy iCloud Link**.
4. In GitHub → Settings → Secrets and variables → Actions → **Variables**, add `SHORTCUT_INSTALL_URL` = the iCloud link. The next deploy writes it into the Pi `.env` (the deploy rewrites `.env` every time, so do not edit it on the Pi). The Account page then shows **Add the Shortcut**.

Each person then creates their own token, taps **Add the Shortcut**, and pastes their token when asked. Their messages go to their own inbox only.

## If it does not work

| You see | Cause | Fix |
|---|---|---|
| "This phone token is not valid…" | Token revoked, mistyped, or missing `Bearer ` | Create a new token and paste it again |
| "Too many attempts…" | Rate limit (60 sends per hour, or repeated bad tokens) | Wait and try again |
| "couldn't convert from Text to Dictionary" | The reply was not JSON. The server refused the request as malformed (server log: "Invalid HTTP request received"). Usually a space after `Authorization` in the header name, or a line break after the token | Make the header name exactly `Authorization` (no trailing space) and delete any empty line after the token |
| Nothing, or a web page | Cloudflare challenged the request (bot protection) | Check the Cloudflare security events for `/api/payments/capture`; allow that path for the Shortcut |

## Revoke a phone

Account → Phone capture → **Revoke**. That phone can no longer send messages.
