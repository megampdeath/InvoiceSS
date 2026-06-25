from fastapi import APIRouter

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/stripe-webhook")
def stripe_webhook_placeholder() -> dict[str, str]:
    return {"status": "not_configured", "message": "Stripe webhook wiring is intentionally deferred until keys are set."}
