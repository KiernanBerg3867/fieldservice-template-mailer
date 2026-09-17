from __future__ import annotations

import uuid

from fieldservice_mail.infrai_client import InfraiClient

TEMPLATES = {
    "dispatch": {
        "subject": "Technician dispatched for work order {{work_order_id}}",
        "html": "<p>Hello {{customer_name}}, {{technician_name}} is scheduled for {{scheduled_window}}.</p>",
    },
    "follow_up": {
        "subject": "Follow-up for work order {{work_order_id}}",
        "html": "<p>Hello {{customer_name}}, your technician recorded the visit photos. Please reply if follow-up is needed.</p>",
    },
}


def main() -> None:
    release = uuid.uuid4().hex[:12]
    client = InfraiClient()
    created_ids: list[str] = []
    try:
        for stage, template in TEMPLATES.items():
            name = f"fieldservice-{stage}-{release}"
            result = client.create_template(
                name=name,
                subject=template["subject"],
                html=template["html"],
                idempotency_key=f"template:{name}",
            )
            template_id = str(result["template_id"])
            created_ids.append(template_id)
            print(f"{stage.upper()}_TEMPLATE_ID={template_id}")
    finally:
        for template_id in reversed(created_ids):
            client.delete_template(template_id)
        client.close()


if __name__ == "__main__":
    main()
