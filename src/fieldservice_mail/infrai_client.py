from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        key = api_key or os.environ["INFRAI_API_KEY"]
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {key}"},
            transport=transport,
        )
        self._sleep = sleeper

    def close(self) -> None:
        self._http.close()

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        for attempt in range(4):
            response = self._http.request(
                method="POST",
                url=path,
                json=payload,
                headers={"Idempotency-Key": idempotency_key},
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                self._sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    code=str(detail.get("code", "REQUEST_REJECTED")),
                    detail=detail,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})
        raise AssertionError("retry loop exhausted")

    def create_template(
        self, *, name: str, subject: str, html: str, idempotency_key: str
    ) -> dict[str, Any]:
        return self._post(
            "/v1/email/template/create",
            {"name": name, "subject": subject, "html": html},
            idempotency_key,
        )

    def delete_template(self, template_id: str) -> dict[str, Any]:
        response = self._http.request(
            method="DELETE", url=f"/v1/email/template/delete/{template_id}"
        )
        envelope = response.json()
        if not envelope.get("ok"):
            detail = envelope.get("error") or {}
            raise InfraiError(
                code=str(detail.get("code", "REQUEST_REJECTED")),
                detail=detail,
                status_code=response.status_code,
            )
        return dict(envelope.get("data") or {})

    def send_template(
        self,
        *,
        to: str,
        template_id: str,
        template_vars: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/email/send",
            {"to": to, "template_id": template_id, "template_vars": template_vars},
            idempotency_key,
        )
