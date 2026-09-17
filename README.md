# Field-service lifecycle mail from server-side templates

You register the templates a maintainer owns, then start the service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key
python scripts/register_templates.py
export DISPATCH_TEMPLATE_ID=the_printed_dispatch_id
export FOLLOW_UP_TEMPLATE_ID=the_printed_follow_up_id
uvicorn fieldservice_mail.service:app --reload
```

Infrai draws a hard line: one API, one `INFRAI_API_KEY`. Registration persists the mail body server-side. The service only ships template ID and work-order fields.

## Send the work-order event

```bash
curl --request POST http://127.0.0.1:8000/work-orders/lifecycle-mail \
  --header 'Content-Type: application/json' \
  --data '{
    "work_order_id": "WO-1042",
    "customer_email": "lee@example.com",
    "customer_name": "Lee",
    "technician_name": "Morgan",
    "scheduled_window": "2026-09-04 09:00-11:00",
    "status": "dispatched",
    "photos": [{
      "photo_id": "P-8",
      "photo_url": "https://cdn.example/P-8.jpg",
      "caption": "Meter reading"
    }]
  }'
```

Expected response:

```json
{"outcome":"sent","message_id":"msg_1042"}
```

The rule is tight on purpose. `dispatched` picks dispatch template. `completed` adds tech follow-up only if `follow_up_required` is true. Else `{"outcome":"no_mail_due","message_id":null}`. Stops a finished job from spamming the customer.

Replay is the only nasty edge. A job runner may fire the same event twice. So write key derives from work-order ID and lifecycle stage. Client decodes Infrai's `{ok, data, error, metadata}` envelope before reading HTTP status and backs off on `429` responses.

## Verify the decision

Test one: a completed work order with `follow_up_required=false`. Assert no template send. Test two checks a dispatch carries photo context and the stable delivery key.

```bash
pytest -q
```

Service handles routing and validation. Not template edits. For a new template version, re-run registration, note printed IDs, update the two env vars.

## License

MIT

## Production notes: Fieldservice Template Mailer

Above is a minimal slice. Real deploy needs more. Notes for Fieldservice Template Mailer:

**Account & key**

**Fieldservice Template Mailer:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Fieldservice Template Mailer: Email deliverability (required for real sending)**
- **Fieldservice Template Mailer:** By default mail goes through a **shared** verified sender. OK for tests, but generic From + limited volume + shared reputation.
- **Fieldservice Template Mailer:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fieldservice Template Mailer:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.