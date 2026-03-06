"""
Payments Router — Stripe Checkout Session + Webhook.

POST /api/payments/checkout   → Crea session de Stripe, devuelve URL
POST /api/payments/webhook    → Stripe llama esto cuando el pago se completa
"""

import secrets
import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from server.config import settings
from server import db as database

router = APIRouter(tags=["payments"])


class CheckoutRequest(BaseModel):
    email: EmailStr
    plan: str = "monthly"  # "monthly" | "yearly"


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(body: CheckoutRequest) -> CheckoutResponse:
    """
    La Landing llama esto al hacer click en "Go PRO".
    Devuelve la URL de Stripe Checkout para redirigir al usuario.
    """
    price_id = (
        settings.stripe_pro_yearly_price_id
        if body.plan == "yearly"
        else settings.stripe_pro_monthly_price_id
    )

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=body.email,
            success_url=settings.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.cancel_url,
            metadata={"plan": body.plan},
        )
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CheckoutResponse(
        checkout_url=session.url,
        session_id=session.id,
    )


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe llama este endpoint después de un pago exitoso.
    Acá generamos la license key y la guardamos.

    Para testear localmente:
      stripe listen --forward-to localhost:8000/api/payments/webhook
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await _handle_successful_payment(session)

    elif event["type"] == "customer.subscription.deleted":
        # Usuario canceló — desactivar licencia
        subscription = event["data"]["object"]
        _handle_cancellation(subscription)

    return {"status": "ok"}


async def _handle_successful_payment(session: dict):
    """Genera license key y la guarda al completarse el pago."""
    email = session.get("customer_email", "unknown@pisku.dev")
    plan = session.get("metadata", {}).get("plan", "monthly")
    session_id = session.get("id")

    # Generar key única: PISKU-PRO-XXXX-XXXX
    suffix = secrets.token_hex(4).upper()
    key = f"PISKU-PRO-{suffix[:4]}-{suffix[4:8]}"

    license_record = database.create_license(
        key=key,
        email=email,
        plan=plan,
        stripe_session_id=session_id,
    )

    # TODO: Enviar email con la key al usuario
    # En producción: integrar con Resend, SendGrid, etc.
    print(f"✅ License created: {key} → {email} ({plan})")

    return license_record


def _handle_cancellation(subscription: dict):
    """Desactiva la licencia si el usuario cancela la suscripción."""
    # Buscar por session_id en metadata o via customer
    # Por simplicidad, loggeamos — en producción vincular subscription_id
    customer_id = subscription.get("customer")
    print(f"⚠️  Subscription cancelled for customer: {customer_id}")
    # TODO: vincular customer_id con licencia para desactivar


@router.get("/success")
async def payment_success(session_id: str):
    """
    Devuelve la license key al usuario después del pago.
    La landing muestra esto en /success.html
    """
    license_record = database.get_by_stripe_session(session_id)
    if not license_record:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "license_key": license_record["key"],
        "email": license_record["email"],
        "expires_at": license_record["expires_at"],
        "plan": license_record["plan"],
    }
