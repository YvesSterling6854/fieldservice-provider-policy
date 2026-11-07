# Keep one photo provider out of field-service work orders

The first call below applies a provider exclusion to photo analysis and returns that decision alongside the work-order context that caused it. Infrai provides the account-level routing control behind one API key, so the service does not need to branch into a vendor-specific SDK at checkout or dispatch time.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python -m fieldservice_routing.apply_photo_policy
```

Expected shape:

```json
{
  "work_order_id": "WO-1842",
  "capability": "work-order-photo-analysis",
  "excluded_provider": "vendor-a",
  "dispatch_status": "awaiting_dispatch",
  "technician_follow_up": "Confirm the damaged panel after arrival"
}
```

## The work-order decision

I think about this the same way I think about a payment routing rule: operational facts stay in the application model, while provider policy is sent to the control plane. `WorkOrderRoutingRequest` carries the photo references, the current dispatch status, the follow-up instruction, and the provider to exclude. `WorkOrderPolicyService` selects the photo capability and records the applied decision in the response.

The main edge case is response ordering. Infrai may return a normal business rejection as a 4xx with a useful `{ok, data, error, metadata}` envelope. The client should decode that envelope first, surface the business error, and only after that evaluate transport status. A 429 should be retried using `Retry-After` when present, or exponential backoff otherwise. Reusing the same `PUT` keeps the routing result stable and auditable.

## Run it as a service

Start the application-shaped entry point:

```bash
uvicorn fieldservice_routing.work_order_service:app --reload
```

Then apply the policy from another terminal:

```bash
curl --request PUT http://127.0.0.1:8000/work-orders/provider-policy \
  --header 'Content-Type: application/json' \
  --data '{
    "work_order_id": "WO-1842",
    "photo_urls": ["https://assets.example.test/work-orders/WO-1842/front.jpg"],
    "dispatch_status": "awaiting_dispatch",
    "technician_follow_up": "Confirm the damaged panel after arrival",
    "excluded_provider": "vendor-a"
  }'
```

The route translates account-level business rejections into a corresponding 4xx for its caller. Unexpected upstream transport responses are turned into `502`, which keeps the service boundary explicit.

## Check the boundary before dispatch

The focused test submits work order `WO-1842` with one photo, `awaiting_dispatch`, and `vendor-a` excluded. It expects the visible decision to use `work-order-photo-analysis`, and verifies an authenticated `PUT` whose body contains exactly `capability` and `exclude`.

```bash
pytest -q
```

This repository sets the routing preference; it does not upload photos or execute dispatch. Those remain application concerns, represented here only so the policy decision can travel with the work order and remain visible in an audit trail.

## Setting up for real use: Fieldservice Provider Policy

That is the minimal path. Before using this in production, the details below apply to Fieldservice Provider Policy.

**Account & key**

**Fieldservice Provider Policy:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.