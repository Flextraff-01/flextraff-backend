import qrcode
import io
import base64


class QRService:

    @staticmethod
    def generate_qr_base64(uri: str) -> str:
        """
        Generate QR code from URI and return base64 image
        """

        qr = qrcode.make(uri)

        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")

        return base64.b64encode(buffer.getvalue()).decode()