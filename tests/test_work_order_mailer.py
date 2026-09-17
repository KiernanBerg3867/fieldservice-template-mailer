from fieldservice_mail.work_order_mailer import (
    DispatchStatus,
    WorkOrderMail,
    WorkOrderPhoto,
    send_lifecycle_mail,
)


class RecordingSender:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def send_template(self, **request: object) -> dict[str, object]:
        self.calls.append(request)
        return {"message_id": "msg_123"}


def make_order(**changes: object) -> WorkOrderMail:
    values: dict[str, object] = {
        "work_order_id": "WO-1042",
        "customer_email": "lee@example.com",
        "customer_name": "Lee",
        "technician_name": "Morgan",
        "scheduled_window": "2026-09-04 09:00-11:00",
        "status": DispatchStatus.DISPATCHED,
        "photos": (WorkOrderPhoto("P-8", "https://cdn.example/P-8.jpg", "Meter reading"),),
    }
    values.update(changes)
    return WorkOrderMail(**values)  # type: ignore[arg-type]


def test_dispatch_sends_photo_context_with_stable_delivery_key() -> None:
    sender = RecordingSender()
    message_id = send_lifecycle_mail(
        make_order(), {"dispatch": "tpl_dispatch", "follow_up": "tpl_follow"}, sender
    )

    assert message_id == "msg_123"
    assert sender.calls == [
        {
            "to": "lee@example.com",
            "template_id": "tpl_dispatch",
            "template_vars": {
                "customer_name": "Lee",
                "work_order_id": "WO-1042",
                "technician_name": "Morgan",
                "scheduled_window": "2026-09-04 09:00-11:00",
                "photos": [
                    {
                        "photo_id": "P-8",
                        "photo_url": "https://cdn.example/P-8.jpg",
                        "caption": "Meter reading",
                    }
                ],
            },
            "idempotency_key": "work-order:WO-1042:dispatch",
        }
    ]


def test_completed_order_without_follow_up_sends_nothing() -> None:
    sender = RecordingSender()
    message_id = send_lifecycle_mail(
        make_order(status=DispatchStatus.COMPLETED, follow_up_required=False),
        {"dispatch": "tpl_dispatch", "follow_up": "tpl_follow"},
        sender,
    )

    assert message_id is None
    assert sender.calls == []

