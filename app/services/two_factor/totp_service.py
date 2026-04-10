import pyotp
from typing import Optional


class TOTPService:
    """
    Service responsible for all TOTP (Time-based One-Time Password) operations.
    Used for enabling and verifying Two-Factor Authentication (2FA).
    """

    @staticmethod
    def generate_secret() -> str:
        """
        Generate a new base32 secret for a user.
        This secret will be stored in the database.
        """
        return pyotp.random_base32()

    @staticmethod
    def generate_provisioning_uri(secret: str, username: str) -> str:
        """
        Generate the provisioning URI used by authenticator apps
        to create a new 2FA entry.

        Example:
        otpauth://totp/FlexTraff:user@email.com?secret=XXXX&issuer=FlexTraff
        """

        if not secret:
            raise ValueError("Secret cannot be empty")

        totp = pyotp.TOTP(secret)

        return totp.provisioning_uri(
            name=username,
            issuer_name="FlexTraff"
        )

    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        """
        Verify a TOTP code provided by the user.

        valid_window=1 allows slight time drift (~30 seconds)
        between server and authenticator device.
        """

        if not secret or not code:
            return False

        try:
            totp = pyotp.TOTP(secret)

            return totp.verify(code, valid_window=1)

        except Exception:
            return False