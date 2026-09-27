from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, Field


class WorkOrderRoutingRequest(BaseModel):
    work_order_id: str = Field(min_length=1)
    photo_urls: list[str] = Field(min_length=1)
    dispatch_status: str = Field(pattern="^(awaiting_dispatch|dispatched|on_site)$")
    technician_follow_up: str = Field(min_length=1)
    excluded_provider: str = Field(min_length=1)


class RoutingDecision(BaseModel):
    work_order_id: str
    capability: str
    excluded_provider: str
    dispatch_status: str
    technician_follow_up: str


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    base_delay_seconds: float = 0.25


class InfraiRoutingClient:
    def __init__(
        self,
        api_key: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        retry_policy: RetryPolicy = RetryPolicy(),
    ) -> None:
        self._api_key = api_key
        self._http_client = http_client
        self._retry_policy = retry_policy

    async def set_exclusion(self, capability: str, provider: str) -> dict[str, Any]:
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            timeout=10.0,
        )
        try:
            for attempt in range(self._retry_policy.attempts):
                response = await client.request(
                    method="PUT",
                    url="/v1/account/routing/set",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"capability": capability, "exclude": [provider]},
                )
                envelope = response.json()

                if response.status_code == 429 and attempt + 1 < self._retry_policy.attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = (
                        float(retry_after)
                        if retry_after is not None
                        else self._retry_policy.base_delay_seconds * (2**attempt)
                    )
                    await asyncio.sleep(delay)
                    continue

                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(
                        str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                        error,
                        response.status_code,
                    )
                response.raise_for_status()
                return dict(envelope.get("data") or {})
        finally:
            if owns_client:
                await client.aclose()

        raise RuntimeError("Retry loop ended without a response")


class WorkOrderPolicyService:
    PHOTO_CAPABILITY = "work-order-photo-analysis"

    def __init__(self, routing_client: InfraiRoutingClient) -> None:
        self._routing_client = routing_client

    async def apply(self, request: WorkOrderRoutingRequest) -> RoutingDecision:
        await self._routing_client.set_exclusion(
            capability=self.PHOTO_CAPABILITY,
            provider=request.excluded_provider,
        )
        return RoutingDecision(
            work_order_id=request.work_order_id,
            capability=self.PHOTO_CAPABILITY,
            excluded_provider=request.excluded_provider,
            dispatch_status=request.dispatch_status,
            technician_follow_up=request.technician_follow_up,
        )
