from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

from .infrai_client import InfraiClient, InfraiError
from .work_order_mailer import (
    DispatchStatus,
    WorkOrderMail,
    WorkOrderPhoto,
    send_lifecycle_mail,
)


class PhotoRequest(BaseModel):
    photo_id: str = Field(min_length=1)
    photo_url: str = Field(min_length=1)
    caption: str = ""


class LifecycleMailRequest(BaseModel):
    work_order_id: str = Field(min_length=1)
    customer_email: EmailStr
    customer_name: str = Field(min_length=1)
    technician_name: str = Field(min_length=1)
    scheduled_window: str = Field(min_length=1)
    status: DispatchStatus
    photos: list[PhotoRequest] = Field(default_factory=list)
    follow_up_required: bool = False


class LifecycleMailResponse(BaseModel):
    outcome: str
    message_id: str | None = None


app = FastAPI(title="Field-service lifecycle mail")


@app.post("/work-orders/lifecycle-mail", response_model=LifecycleMailResponse)
def deliver_lifecycle_mail(request: LifecycleMailRequest) -> LifecycleMailResponse:
    template_ids = {
        "dispatch": os.environ["DISPATCH_TEMPLATE_ID"],
        "follow_up": os.environ["FOLLOW_UP_TEMPLATE_ID"],
    }
    order = WorkOrderMail(
        work_order_id=request.work_order_id,
        customer_email=str(request.customer_email),
        customer_name=request.customer_name,
        technician_name=request.technician_name,
        scheduled_window=request.scheduled_window,
        status=request.status,
        photos=tuple(WorkOrderPhoto(**photo.model_dump()) for photo in request.photos),
        follow_up_required=request.follow_up_required,
    )
    client = InfraiClient()
    try:
        message_id = send_lifecycle_mail(order, template_ids, client)
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": exc.detail.get("message", "request rejected")},
        ) from exc
    finally:
        client.close()
    if message_id is None:
        return LifecycleMailResponse(outcome="no_mail_due")
    return LifecycleMailResponse(outcome="sent", message_id=message_id)

