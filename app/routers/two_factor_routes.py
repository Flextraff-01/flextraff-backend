from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client

from app.services.two_factor.totp_service import TOTPService
from app.services.two_factor.qr_service import QRService
from app.services.custom_auth_service import CustomAuthService
from app.config import settings

router = APIRouter(prefix="/auth/2fa", tags=["Two Factor"])

auth_service = CustomAuthService()

supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)


@router.post("/setup")
async def setup_two_factor(user_id: int):
    """
    Generate QR code for enabling 2FA
    """

    # Fetch user
    result = (
        supabase
        .table("users")
        .select("*")
        .eq("id", user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = result.data[0]

    if user["is_2fa_enabled"]:
        raise HTTPException(status_code=400, detail="2FA already enabled")

    # Generate secret
    secret = TOTPService.generate_secret()

    # Generate URI
    uri = TOTPService.generate_provisioning_uri(
        secret,
        user["username"]
    )

    # Generate QR
    qr_code = QRService.generate_qr_base64(uri)

    # Save secret temporarily
    supabase.table("users").update({
        "totp_secret": secret
    }).eq("id", user_id).execute()

    return {
        "qr_code": qr_code,
        "secret": secret
    }