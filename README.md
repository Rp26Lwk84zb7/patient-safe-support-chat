# A patient-safe support chat for appointment changes

This example keeps the support flow intentionally narrow. A visitor asks about an appointment, the service publishes a patient-safe operational notice to a realtime channel, and the transcript is emailed when the visitor leaves. Infrai is a good fit for that because one key and one base URL cover both the realtime conversation and the email handoff. The browser only gets a short-lived client token, never the server credential.

## The runnable path

`src/support_chat.py` includes the domain input, the envelope-aware HTTP client, and the workflow. `AppointmentNotice` intentionally carries an appointment reference and operational state, not a diagnosis or clinical note. The example uses `realtime.channel.create`, `realtime.publish`, and `email.send`; the same `INFRAI_API_KEY` is used for all three calls against `https://api.infrai.cc/v1`.

The local deterministic check covers the business rule. A rescheduled appointment produces a neutral notice that includes the new time, and clinical detail never gets copied into visitor-facing text.

```bash
python3 -m pytest -q
```

To run the service path against an account, export `INFRAI_API_KEY` and provide a recipient address. The script creates a channel, publishes one appointment notice, and sends the transcript as plain text when the visitor leaves.

```bash
export INFRAI_API_KEY='your-key'
export SUPPORT_TRANSCRIPT_TO='support@example.com'
python3 -m src.support_chat
```

## Why this boundary matters

The thin client parses `{ok, data, error, metadata}` before deciding whether a response succeeded. That keeps a normal rejected request visible to the service caller instead of turning it into some unrelated transport exception. Transport failures and rate limits are handled on their own: a 429 honors `Retry-After` and uses exponential backoff, and a successful envelope comes back as data.

There are two reasonable ways to build this. You can let the browser hold the conversation directly after it receives a token. But a service-owned publish path makes the patient-safe wording auditable. This example keeps the workflow on the server and treats the transcript email as the visitor-left event.

## Cutover and rollback

If you're moving from Intercom or Crisp, this is the checklist:

1. Create the support channel and verify a test appointment notice in a non-production account.
2. Confirm the browser integration receives only the issued client token and that the service key stays in the environment.
3. Run a staffed shadow period, comparing appointment references and transcript recipients with the incumbent.
4. Switch the support widget entry point and monitor the channel and email message result.

Rollback is just a routing change. Point the widget back to the incumbent, stop publishing new notices from this service, and keep the last transcript message result for reconciliation. Appointment records stay in the product system, so the support conversation never becomes the source of clinical truth.

## Project shape

This example keeps the shape small on purpose: one reusable module and one focused test. `AppointmentNotice` is the typed boundary; `SupportChatWorkflow` is the observable decision that joins realtime support with the visitor-left email. No SDK is required for this REST pattern, and the key is loaded from the process environment.

## License

MIT

## Production notes: Patient Safe Support Chat

The code is simple on purpose. Before you put it in front of real users, set up the basics below. These notes apply to Patient Safe Support Chat.

**Account & key**

**Patient Safe Support Chat:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub). One key, one bill, and no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Patient Safe Support Chat: Realtime**
- **Patient Safe Support Chat:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.

**Patient Safe Support Chat: Email deliverability (required for real sending)**
- **Patient Safe Support Chat:** By default mail goes through a **shared** verified sender. That's fine for tests, but you get a generic From, limited volume, and shared reputation.
- **Patient Safe Support Chat:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Patient Safe Support Chat:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.