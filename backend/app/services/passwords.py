import bcrypt

from app.config import get_settings

_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    rounds = 4 if get_settings().app_env == "test" else 12
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_password_bytes(password), hashed.encode("utf-8"))
    except ValueError:
        return False


def _password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > _MAX_PASSWORD_BYTES:
        encoded = encoded[:_MAX_PASSWORD_BYTES]
    return encoded
