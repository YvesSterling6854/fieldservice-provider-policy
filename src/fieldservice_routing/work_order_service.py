import os

from fastapi import FastAPI, HTTPException

from .provider_policy import (
    InfraiError,
    InfraiRoutingClient,
    RoutingDecision,
    WorkOrderPolicyService,
    WorkOrderRoutingRequest,
)

app = FastAPI(title="Work-order provider policy")


def build_policy_service() -> WorkOrderPolicyService:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set INFRAI_API_KEY before starting the service")
    return WorkOrderPolicyService(InfraiRoutingClient(api_key))


@app.put("/work-orders/provider-policy", response_model=RoutingDecision)
async def set_work_order_provider_policy(
    request: WorkOrderRoutingRequest,
) -> RoutingDecision:
    try:
        return await build_policy_service().apply(request)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

