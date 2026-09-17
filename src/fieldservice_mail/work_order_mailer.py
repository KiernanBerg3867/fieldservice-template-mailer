from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class DispatchStatus(str, Enum):
    DISPATCHED = "dispatched"
    COMPLETED = "completed"


@dataclass(frozen=True)
class WorkOrderPhoto:
    photo_id: str
    photo_url: str
    caption: str


@dataclass(frozen=True)
class WorkOrderMail:
    work_order_id: str
    customer_email: str
    customer_name: str
    technician_name: str
    scheduled_window: str
    status: DispatchStatus
    photos: tuple[WorkOrderPhoto, ...] = ()
    follow_up_required: bool = False


class TemplateSender(Protocol):
    def send_template(
        self,
        *,
        to: str,
        template_id: str,
        template_vars: dict[str, object],
        idempotency_key: str,
    ) -> dict[str, object]:
        raise AssertionError("protocol method has no direct runtime call")


def send_lifecycle_mail(
    order: WorkOrderMail,
    template_ids: dict[str, str],
    sender: TemplateSender,
) -> str | None:
    if order.status is DispatchStatus.DISPATCHED:
        stage = "dispatch"
    elif order.status is DispatchStatus.COMPLETED and order.follow_up_required:
        stage = "follow_up"
    else:
        return None

    template_vars: dict[str, object] = {
        "customer_name": order.customer_name,
        "work_order_id": order.work_order_id,
        "technician_name": order.technician_name,
        "scheduled_window": order.scheduled_window,
        "photos": [
            {"photo_id": photo.photo_id, "photo_url": photo.photo_url, "caption": photo.caption}
            for photo in order.photos
        ],
    }
    result = sender.send_template(
        to=order.customer_email,
        template_id=template_ids[stage],
        template_vars=template_vars,
        idempotency_key=f"work-order:{order.work_order_id}:{stage}",
    )
    return str(result["message_id"])
