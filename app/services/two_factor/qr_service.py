import qrcode
import io
import base64


class QRService:
    """
    Service responsible for generating QR codes for 2FA setup.
    Returns QR image as base64 so it can be directly rendered
    in the frontend.
    """

    @staticmethod
    def generate_qr_base64(uri: str) -> str:
        """
        Generate a QR code from a provisioning URI and return
        the image encoded in base64 format.
        """

        if not uri:
            raise ValueError("URI cannot be empty")

        qr = qrcode.make(uri)

        buffer = io.BytesIO()

        qr.save(buffer, format="PNG")

        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return qr_base64