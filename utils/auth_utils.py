from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from django.conf import settings
import jwt
from datetime import datetime, timedelta
import base64


AES_SECRET_KEY = base64.b64decode(settings.AES_SECRET_KEY)

# Utility function to encrypt JWT
def encrypt_jwt(token: str) -> str:
    cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(token.encode('utf-8'), AES.block_size))
    iv = cipher.iv.hex()
    ct = ct_bytes.hex()
    return f"{iv}:{ct}"


# Utility function to decrypt JWT
def decrypt_jwt(encrypted_token: str) -> str:
    iv_hex, ct_hex = encrypted_token.split(":")
    iv = bytes.fromhex(iv_hex)
    ct = bytes.fromhex(ct_hex)
    cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt.decode('utf-8')

def generate_access_token(payload: dict) -> str:
    payload["type"] = "access"
    payload["exp"] = datetime.utcnow() + timedelta(minutes=15)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm="HS256"
    )


def generate_refresh_token(payload: dict) -> str:
    payload["type"] = "refresh"
    payload["exp"] = datetime.utcnow() + timedelta(days=7)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm="HS256"
    )

def generate_jwt(payload: dict) -> str:
    payload["exp"] = datetime.utcnow()
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def decode_jwt(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
