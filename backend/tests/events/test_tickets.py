import uuid

import pytest

from grid.events import tickets


def test_issued_ticket_redeems_to_the_issuing_user() -> None:
    user_id = uuid.uuid4()
    ticket = tickets.issue_ticket(user_id)
    assert tickets.redeem_ticket(ticket) == user_id


def test_ticket_is_single_use() -> None:
    ticket = tickets.issue_ticket(uuid.uuid4())
    assert tickets.redeem_ticket(ticket) is not None
    assert tickets.redeem_ticket(ticket) is None


def test_unknown_ticket_rejected() -> None:
    assert tickets.redeem_ticket("not-a-real-ticket") is None


def test_expired_ticket_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4()
    ticket = tickets.issue_ticket(user_id)
    monkeypatch.setattr(tickets.time, "monotonic", lambda: float("inf"))
    assert tickets.redeem_ticket(ticket) is None
