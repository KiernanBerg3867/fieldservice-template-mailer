import httpx

from fieldservice_mail.infrai_client import InfraiClient


def test_rate_limit_honors_retry_after_then_returns_message_id() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"ok": False, "data": None, "error": {"code": "RATE_LIMITED"}, "metadata": {}},
            )
        return httpx.Response(
            200,
            json={"ok": True, "data": {"message_id": "msg_9"}, "error": None, "metadata": {}},
        )

    client = InfraiClient(api_key="test-key", transport=httpx.MockTransport(handler), sleeper=lambda _: None)
    try:
        result = client.send_template(
            to="lee@example.com",
            template_id="tpl_dispatch",
            template_vars={"work_order_id": "WO-9"},
            idempotency_key="work-order:WO-9:dispatch",
        )
    finally:
        client.close()

    assert attempts == 2
    assert result["message_id"] == "msg_9"

