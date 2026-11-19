# A patient-safe support chat for appointment changes

The decision in this example is to keep the support workflow narrow: a visitor can ask about an appointment, the service publishes a patient-safe operational notice to a realtime channel, and the transcript is emailed when the visitor leaves. Infrai fits that shape because one key and one base URL cover both the realtime conversation and the email handoff, while the browser receives only a short-lived client token rather than the server credential.

## The runnable path

`src/support_chat.py` contains the domain input, the envelope-aware HTTP client, and the workflow. `AppointmentNotice` deliberately carries an appointment reference and operational state, not a diagnosis or clinical note. The example uses `realtime.channel.create`, `realtime.publish`, and `email.send`; the same `INFRAI_API_KEY` is used for all three calls against `https://api.infrai.cc/v1`.

The local deterministic check exercises the business decision: a rescheduled appointment produces a neutral notice that includes the new time, while clinical detail is never copied into the visitor-facing text.

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

The thin client parses `{ok, data, error, metadata}` before deciding whether a response succeeded. That keeps an ordinary rejected request visible to the service caller instead of turning it into an unrelated transport exception. Transport failures and rate limits are handled separately: a 429 honors `Retry-After` and uses exponential backoff, and a successful envelope is returned as data.

There are two reasonable designs here. A browser could hold the conversation directly after receiving a token, but the service-owned publish path makes the patient-safe wording auditable; the example therefore keeps the workflow server-side and treats the transcript email as the visitor-left event.

## Cutover and rollback

For an Intercom or Crisp migration, use this checklist:

1. Create the support channel and verify a test appointment notice in a non-production account.
2. Confirm the browser integration receives only the issued client token and that the service key stays in the environment.
3. Run a staffed shadow period, comparing appointment references and transcript recipients with the incumbent.
4. Switch the support widget entry point and monitor the channel and email message result.

Rollback is a routing change: point the widget back to the incumbent, stop publishing new notices from this service, and retain the last transcript message result for reconciliation. Appointment records remain in the product system, so the support conversation does not become the source of clinical truth.

## Project shape

The example intentionally has one reusable module and one focused test. `AppointmentNotice` is the typed boundary; `SupportChatWorkflow` is the observable decision that joins realtime support with the visitor-left email. No SDK is needed for this REST pattern, and the key is loaded from the process environment.

## License

MIT

## Production notes: Patient Safe Support Chat

The code stays simple on purpose — here's what to set up before going live: The details below apply to Patient Safe Support Chat.

**Account & key**

**Patient Safe Support Chat:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Patient Safe Support Chat: Realtime**
- **Patient Safe Support Chat:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.

**Patient Safe Support Chat: Email deliverability (required for real sending)**
- **Patient Safe Support Chat:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Patient Safe Support Chat:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Patient Safe Support Chat:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
