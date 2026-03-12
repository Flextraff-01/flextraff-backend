from fastapi import APIRouter, Depends, HTTPException

from app.services.two_factor.totp_service import TOTPService
from app.services.two_factor.qr_service import QRService
from app.services.custom_auth_service import CustomAuthService
from app.dependencies.auth_dependency import get_current_user


router = APIRouter(prefix="/auth/2fa", tags=["Two Factor"])

auth_service = CustomAuthService()


# =========================================================
# SETUP 2FA
# =========================================================

@router.post("/setup")
async def setup_two_factor(current_user=Depends(get_current_user)):
    """
    Generate QR code for enabling 2FA
    """

    user_id = current_user["id"]

    if current_user.get("is_2fa_enabled"):
        raise HTTPException(
            status_code=400,
            detail="2FA already enabled"
        )

    # Generate secret
    secret = TOTPService.generate_secret()

    # Generate URI
    uri = TOTPService.generate_provisioning_uri(
        secret,
        current_user["username"]
    )

    # Generate QR code
    qr_code = QRService.generate_qr_base64(uri)

    # Save temporary secret
    auth_service.supabase.table("users").update({
        "totp_secret_temp": secret
    }).eq("id", user_id).execute()

    return {
        "message": "Scan this QR code using Google Authenticator",
        "qr_code": f"data:image/png;base64,{qr_code}",
        "secret": secret
    }


# =========================================================
# VERIFY 2FA SETUP
# =========================================================

@router.post("/verify")
async def verify_two_factor(
    code: str,
    current_user=Depends(get_current_user)
):
    """
    Verify OTP and enable 2FA
    """

    user_id = current_user["id"]

    temp_secret = current_user.get("totp_secret_temp")

    if not temp_secret:
        raise HTTPException(
            status_code=400,
            detail="2FA setup not initiated"
        )

    if not TOTPService.verify_code(temp_secret, code):
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )

    # Enable 2FA
    auth_service.supabase.table("users").update({
        "totp_secret": temp_secret,
        "totp_secret_temp": None,
        "is_2fa_enabled": True
    }).eq("id", user_id).execute()

    return {
        "message": "Two-factor authentication enabled successfully"
    }


# =========================================================
# LOGIN WITH OTP
# =========================================================

@router.post("/login")
async def login_with_2fa(username: str, code: str):
    """
    Complete login using OTP
    """

    result = (
        auth_service.supabase
        .table("users")
        .select("*")
        .eq("username", username)
        .eq("is_active", True)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    user = result.data[0]

    if not user.get("is_2fa_enabled"):
        raise HTTPException(
            status_code=400,
            detail="2FA not enabled for this user"
        )

    secret = user.get("totp_secret")

    if not secret:
        raise HTTPException(
            status_code=400,
            detail="2FA secret missing"
        )

    if not TOTPService.verify_code(secret, code):
        raise HTTPException(
            status_code=401,
            detail="Invalid OTP"
        )

    # Create session
    session = await auth_service.create_session(user)

    return session


# =========================================================
# DISABLE 2FA
# =========================================================

@router.post("/disable")
async def disable_two_factor(
    code: str,
    current_user=Depends(get_current_user)
):
    """
    Disable 2FA
    """

    user_id = current_user["id"]

    secret = current_user.get("totp_secret")

    if not secret:
        raise HTTPException(
            status_code=400,
            detail="2FA not enabled"
        )

    if not TOTPService.verify_code(secret, code):
        raise HTTPException(
            status_code=401,
            detail="Invalid OTP"
        )

    auth_service.supabase.table("users").update({
        "totp_secret": None,
        "totp_secret_temp": None,
        "is_2fa_enabled": False
    }).eq("id", user_id).execute()

    return {
        "message": "Two-factor authentication disabled"
    }