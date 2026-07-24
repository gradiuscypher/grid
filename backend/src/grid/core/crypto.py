"""Credential vault primitives (ARCHITECTURE §6): named transform/LLM credentials
are Fernet-encrypted at rest under a single deployment key. No per-credential
scheme, no KMS integration yet — that's the documented later step, not MVP scope.
"""

import json

from cryptography.fernet import Fernet, InvalidToken

from grid.core.errors import ValidationError


def encrypt_credentials(credentials: dict[str, str], *, key: str) -> bytes:
    """Encrypts a name→value credential mapping into a single opaque blob."""
    fernet = Fernet(key.encode())
    return fernet.encrypt(json.dumps(credentials).encode())


def decrypt_credentials(blob: bytes, *, key: str) -> dict[str, str]:
    fernet = Fernet(key.encode())
    try:
        raw = fernet.decrypt(blob)
    except InvalidToken as exc:
        # Only reachable if the deployment key rotated without re-encrypting stored
        # creds — surfaced as a validation error rather than a 500 so it's obvious
        # at the API boundary what went wrong, without ever echoing the blob back.
        raise ValidationError("stored credentials could not be decrypted") from exc
    return json.loads(raw)
