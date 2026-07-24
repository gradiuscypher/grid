import pytest
from cryptography.fernet import Fernet

from grid.core.crypto import decrypt_credentials, encrypt_credentials
from grid.core.errors import ValidationError

_KEY = Fernet.generate_key().decode()


def test_credentials_roundtrip() -> None:
    creds = {"api_key": "s3cr3t", "api_secret": "also-secret"}
    blob = encrypt_credentials(creds, key=_KEY)
    assert decrypt_credentials(blob, key=_KEY) == creds


def test_blob_does_not_contain_plaintext() -> None:
    blob = encrypt_credentials({"api_key": "s3cr3t-value"}, key=_KEY)
    assert b"s3cr3t-value" not in blob


def test_wrong_key_fails_closed() -> None:
    blob = encrypt_credentials({"api_key": "s3cr3t"}, key=_KEY)
    other_key = Fernet.generate_key().decode()
    with pytest.raises(ValidationError):
        decrypt_credentials(blob, key=other_key)
