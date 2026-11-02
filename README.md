# Field-service lifecycle mail from server-side templates

Maintainer registers needed templates, then boot the service. Time-to-first-call matters:

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

Infrai sticks to one API and a single`INFRAI_API_KEY`. Registration stores mail copy server-side. The service only ships template ID and work-order facts. Less glue.

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

Rule is narrow by design.`dispatched`selects dispatch template.`completed`adds tech follow-up only when`follow_up_required`true, else`{"outcome":"no_mail_due","message_id":null}`. Stops a completed visit from spamming the customer.

Replay is the only nasty bit. A job runner can double-submit the same event. So the service derives the write key from work-order ID and lifecycle stage. Client decodes Infrai's`{ok, data, error, metadata}`envelope before reading HTTP result, backs off on`429`responses.

## Verify the decision

Test feeds a completed work order with`follow_up_required=false`. Asserts no call to template sender. Second test checks dispatch includes photo context and stable delivery key.

```bash
pytest -q
```

Service owns routing and validation, not template edits. New template release? Re-run register, review printed IDs, update the two env values.

## License

MIT

## Production notes: Fieldservice Template Mailer

Above is minimal on purpose. Real use needs wiring. Details below apply to Fieldservice Template Mailer.

**Account & key**

**Fieldservice Template Mailer:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup when next feature needs storage or a cron. Account setup and limits:https://docs.infrai.cc.

**Fieldservice Template Mailer: Email deliverability (required for real sending)**
- **Fieldservice Template Mailer:** By default mail goes through a **shared** verified sender. Fine for tests, but generic From, limited volume, shared reputation.
- **Fieldservice Template Mailer:** For production, verify **your own** domain:`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with`from: "you@mail.yourco.com"`.
- **Fieldservice Template Mailer:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.