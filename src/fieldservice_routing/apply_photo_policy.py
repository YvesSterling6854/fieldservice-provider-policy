import asyncio
import json
import os

from .provider_policy import (
    InfraiRoutingClient,
    WorkOrderPolicyService,
    WorkOrderRoutingRequest,
)


async def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("Set INFRAI_API_KEY before running this command")

    request = WorkOrderRoutingRequest(
        work_order_id="WO-1842",
        photo_urls=["https://assets.example.test/work-orders/WO-1842/front.jpg"],
        dispatch_status="awaiting_dispatch",
        technician_follow_up="Confirm the damaged panel after arrival",
        excluded_provider="vendor-a",
    )
    decision = await WorkOrderPolicyService(InfraiRoutingClient(api_key)).apply(request)
    print(json.dumps(decision.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())

