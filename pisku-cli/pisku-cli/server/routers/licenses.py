"""
Licenses Router — Endpoint que llama el CLI para validar keys PRO.

POST /api/licenses/validate
  Body: { "key": "PISKU-PRO-XXXX" }
  Response: { "valid": true, "expires_at": "2025-12-31T..." }
           | { "valid": false, "error": "..." }
"""

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from server import db as database

router = APIRouter(tags=["licenses"])


class ValidateRequest(BaseModel):
    key: str


class ValidateResponse(BaseModel):
    valid: bool
    expires_at: str | None = None
    plan: str | None = None
    error: str | None = None


@router.post("/validate", response_model=ValidateResponse)
async def validate_license(body: ValidateRequest) -> ValidateResponse:
    """
    El CLI llama este endpoint al hacer `pisku activate-pro <key>`.
    También puede llamarse en background para revalidar periodicamente.
    """
    key = body.key.strip().upper()

    license_record = database.get_license(key)

    if not license_record:
        return ValidateResponse(valid=False, error="License key not found")

    if not license_record.get("active"):
        return ValidateResponse(valid=False, error="License has been deactivated")

    # Chequear expiración
    expires_str = license_record.get("expires_at")
    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str)
            if datetime.now() > expires_dt:
                return ValidateResponse(valid=False, error="License has expired")
        except ValueError:
            return ValidateResponse(valid=False, error="Invalid license data")

    return ValidateResponse(
        valid=True,
        expires_at=license_record.get("expires_at"),
        plan=license_record.get("plan"),
    )
