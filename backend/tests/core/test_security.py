from grid.core.security import generate_token, hash_password, hash_token, verify_password
from grid.db.models.cases import ROLE_RANK, CaseRole


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong password", hashed) is False


def test_password_hash_is_not_plaintext() -> None:
    assert hash_password("secret") != "secret"


def test_token_hash_is_deterministic_and_one_way() -> None:
    token = generate_token()
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token


def test_generate_token_is_unique() -> None:
    assert generate_token() != generate_token()


def test_role_rank_ordering() -> None:
    assert ROLE_RANK[CaseRole.VIEWER] < ROLE_RANK[CaseRole.EDITOR] < ROLE_RANK[CaseRole.OWNER]
