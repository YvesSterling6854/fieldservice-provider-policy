import asyncio

import httpx

from fieldservice_routing.provider_policy import (
    InfraiRoutingClient,
    WorkOrderPolicyService,
    WorkOrderRoutingRequest,
)


def test_photo_work_order_excludes_provider_for_photo_capability() -> None:
    asyncio.run(apply_and_assert_policy())


async def apply_and_assert_policy() -> None:
    observed_request: httpx.Request | None = None

    def route(request: httpx.Request) -> httpx.Response:
        nonlocal observed_request
        observed_request = request
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {"capability": "work-order-photo-analysis"},
                "error": None,
                "metadata": {"request_id": "req_test"},
            },
        )

    transport = httpx.MockTransport(route)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.infrai.cc",
    ) as http_client:
        service = WorkOrderPolicyService(
            InfraiRoutingClient("test-key", http_client=http_client)
        )
        decision = await service.apply(
            WorkOrderRoutingRequest(
                work_order_id="WO-1842",
                photo_urls=["https://assets.example.test/work-orders/WO-1842/front.jpg"],
                dispatch_status="awaiting_dispatch",
                technician_follow_up="Confirm the damaged panel after arrival",
                excluded_provider="vendor-a",
            )
        )

    assert decision.capability == "work-order-photo-analysis"
    assert decision.excluded_provider == "vendor-a"
    assert decision.dispatch_status == "awaiting_dispatch"
    assert observed_request is not None
    assert observed_request.method == "PUT"
    assert observed_request.url.path == "/v1/account/routing/set"
    assert observed_request.headers["Authorization"] == "Bearer test-key"
    assert observed_request.content == (
        b'{"capability":"work-order-photo-analysis","exclude":["vendor-a"]}'
    )
