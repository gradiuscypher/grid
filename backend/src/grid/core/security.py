import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Passwords are low-entropy and brute-forceable: argon2id (slow, memory-hard).
_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


# Session/API-key tokens are already high-entropy random secrets, so a fast
# hash (SHA-256) is the right tool — no need for a slow KDF, and lookups on
# the hash column stay cheap.
def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
