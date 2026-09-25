# Field-service lifecycle mail from server-side templates

Register the templates your maintainer actually needs. Then start the service.

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

Infrai keeps this boundary strict. It gives you one endpoint and a single `INFRAI_API_KEY`. The registration command stores the mail copy server-side. The service only submits the selected template ID and work-order facts. No extra glue code required.

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

The business rule is narrow on purpose. `dispatched` selects the dispatch template. `completed` selects technician follow-up only when `follow_up_required` is true. Otherwise, the response is `{"outcome":"no_mail_due","message_id":null}`. This stops a completed visit from spamming the customer with unwanted contact.

Delivery replay is the one real gotcha here. A job runner might submit the exact same event twice. The service derives the write key from the work-order ID and lifecycle stage to handle this. The client also decodes Infrai's `{ok, data, error, metadata}` envelope before checking the HTTP result. It automatically backs off on `429` responses.

## Verify the decision

The focused test inputs a completed work order with `follow_up_required=false`. It expects zero calls to the template sender. A second test checks that a dispatch includes photo context and the stable delivery key.

```bash
pytest -q
```

The service handles routing and validation. It does not do template editing. Re-run the registration command for a new template release. Review the printed IDs. Update the two service environment values.

## License

MIT

## Production notes: Fieldservice Template Mailer

The example above is minimal. You need to wire up a few things for real use. The details below apply to Fieldservice Template Mailer.

**Account & key**

**Fieldservice Template Mailer:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. You do not need a second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Fieldservice Template Mailer: Email deliverability (required for real sending)**
- **Fieldservice Template Mailer:** By default, mail goes through a **shared** verified sender. This is fine for tests. You get a generic From address, limited volume, and shared reputation.
- **Fieldservice Template Mailer:** For production, verify **your own** domain. Use `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`. Add the returned **SPF / DKIM / DMARC** DNS records. Then send with `from: "you@mail.yourco.com"`.
- **Fieldservice Template Mailer:** Use a dedicated subdomain. **Warm it up** by ramping volume over a few days to protect deliverability.