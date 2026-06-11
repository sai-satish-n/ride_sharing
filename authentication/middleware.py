from utils.auth_utils import decode_jwt, decrypt_jwt
from django.contrib.auth.models import AnonymousUser
from authentication.models import User
from jwt import ExpiredSignatureError, InvalidTokenError


class EncryptedJWTMiddleware:
    """
    Decrypts AES-encrypted JWT and attaches decoded payload to request
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = AnonymousUser()
        request.jwt_payload = None

        access_token_enc = request.COOKIES.get("access_token")
        refresh_token_enc = request.COOKIES.get("refresh_token")

        if access_token_enc:
            user = self._authenticate_token(access_token_enc, expected_type="access")
            if user:
                request.user = user
                return self.get_response(request)

        if refresh_token_enc:
            user = self._authenticate_token(refresh_token_enc, expected_type="refresh")
            if user:
                request.user = user
                return self.get_response(request)

        return self.get_response(request)

    def _authenticate_token(self, encrypted_token, expected_type):
        try:
            decrypted_jwt = decrypt_jwt(encrypted_token)
            payload = decode_jwt(decrypted_jwt)

            # Validate token type
            if payload.get("type") != expected_type:
                return None

            user_id = payload.get("user_id")
            if not user_id:
                return None

            user = User.objects.get(user_id=user_id)
            return user

        except ExpiredSignatureError:
            return None
        except (InvalidTokenError, User.DoesNotExist, Exception):
            return None
