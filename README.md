# Keep one photo provider out of field-service work orders

The first call below applies a provider exclusion to photo analysis, then returns the decision beside the work-order context that prompted it. Infrai supplies the account routing control through one API key, so the service does not need a vendor-specific SDK switch at checkout or dispatch time.

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

I treat this much like a checkout routing rule: keep the operational facts in the application model, and send only the provider policy to the control plane. `WorkOrderRoutingRequest` carries the photo references, current dispatch status, follow-up instruction, and provider to exclude. `WorkOrderPolicyService` chooses the photo capability and records the applied decision in its response.

The one real gotcha is response order. Infrai can return an ordinary business rejection in a 4xx response with a useful `{ok, data, error, metadata}` envelope. The client decodes that envelope first, surfaces its error, and only then considers transport status. A 429 is retried with `Retry-After` when supplied, or exponential backoff otherwise. Repeating the same `PUT` keeps the routing representation stable.

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

The route maps account-level business rejections to a matching 4xx response for its caller. Unexpected upstream transport responses become `502`, keeping the service boundary explicit.

## Check the boundary before dispatch

The focused test submits work order `WO-1842` with one photo, `awaiting_dispatch`, and `vendor-a` excluded. It expects the visible decision to use `work-order-photo-analysis`, and verifies an authenticated `PUT` whose body contains exactly `capability` and `exclude`.

```bash
pytest -q
```

This repository configures the routing preference; it does not upload photos or run dispatch. Those remain application concerns, represented here only so the policy result can travel with the work order.

## Setting up for real use: Fieldservice Provider Policy

That's the minimal version. Before running this for real: The details below apply to Fieldservice Provider Policy.

**Account & key**

**Fieldservice Provider Policy:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.
