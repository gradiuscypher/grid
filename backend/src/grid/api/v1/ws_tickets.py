from fastapi import APIRouter
from pydantic import BaseModel

from grid.api.deps import CurrentActor
from grid.events.tickets import issue_ticket

router = APIRouter(prefix="/ws-tickets", tags=["ws"])


class WsTicketOut(BaseModel):
    ticket: str


@router.post("", response_model=WsTicketOut)
async def create_ws_ticket(actor: CurrentActor) -> WsTicketOut:
    return WsTicketOut(ticket=issue_ticket(actor.user.id))
