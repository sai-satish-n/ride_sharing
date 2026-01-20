from django.http import JsonResponse
from authentication.utils import decode_jwt, decrypt_jwt


class EncryptedJWTMiddleware:
    """
    Decrypts AES-encrypted JWT and attaches decoded payload to request
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth = request.headers.get("Authorization")

        if auth:
            try:
                # Remove Bearer if present
                if auth.startswith("Bearer "):
                    auth = auth.replace("Bearer ", "")

                decrypted_jwt = decrypt_jwt(auth)
                payload = decode_jwt(decrypted_jwt)

                # Attach to request
                request.jwt_payload = payload

            except Exception:
                return JsonResponse(
                    {"error": "Invalid or expired token"},
                    status=401
                )

        return self.get_response(request)
