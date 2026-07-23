"""Short-lived, single-use WS auth tickets (ARCHITECTURE §5 doesn't cover WS auth
specifically; decided with gradius that browsers can't attach the CSRF custom
header to a WebSocket handshake, so a REST-minted ticket carries proof of the
normal cookie+header auth forward instead of relying on Origin-header parsing).

In-memory by design: the dev/prod compose topology runs a single API process
(ARCHITECTURE §1), and a ticket only needs to survive the few seconds between
minting and the WS handshake. This would need to move to Postgres or similar if
the API ever runs multiple processes/replicas.
"""

import secrets
import time
import uuid
from dataclasses import dataclass

_TICKET_TTL_SECONDS = 30


@dataclass
class _Ticket:
    user_id: uuid.UUID
    expires_at: float


_tickets: dict[str, _Ticket] = {}


def _sweep_expired() -> None:
    now = time.monotonic()
    expired = [token for token, ticket in _tickets.items() if ticket.expires_at < now]
    for token in expired:
        del _tickets[token]


def issue_ticket(user_id: uuid.UUID) -> str:
    _sweep_expired()
    token = secrets.token_urlsafe(32)
    _tickets[token] = _Ticket(user_id=user_id, expires_at=time.monotonic() + _TICKET_TTL_SECONDS)
    return token


def redeem_ticket(token: str) -> uuid.UUID | None:
    """Single-use: valid tickets are consumed on first use, whether or not the
    caller goes on to pass the case-role check."""
    ticket = _tickets.pop(token, None)
    if ticket is None or ticket.expires_at < time.monotonic():
        return None
    return ticket.user_id
