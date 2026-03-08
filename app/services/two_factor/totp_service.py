import pyotp


class TOTPService:
    """
    Handles all TOTP operations
    """

    @staticmethod
    def generate_secret() -> str:
        """
        Generate new TOTP secret for a user
        """
        return pyotp.random_base32()

    @staticmethod
    def generate_provisioning_uri(secret: str, username: str) -> str:
        """
        Generate URI used to create QR code
        """
        totp = pyotp.TOTP(secret)

        return totp.provisioning_uri(
            name=username,
            issuer_name="FlexTraff"
        )

    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        """
        Verify TOTP code entered by user
        """
        totp = pyotp.TOTP(secret)

        return totp.verify(code, valid_window=1)