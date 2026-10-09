"""The agent seam. Ticket 003 supplies the real, tool-using implementation;
the skeleton ships a deterministic fake so the API is testable without models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from partner_scrape.sidecar.sessions import Session


@dataclass
class AgentTurn:
    reply: str
    #: The full proposed-hint list after this turn, or None to leave unchanged.
    proposed_hints: list[dict[str, Any]] | None = None
    notices: list[str] = field(default_factory=list)


class Agent(Protocol):
    def respond(self, session: Session, text: str) -> AgentTurn: ...


class EchoAgent:
    """Fake agent: acknowledges the message and proposes nothing."""

    def respond(self, session: Session, text: str) -> AgentTurn:
        return AgentTurn(reply=f"Thanks. I noted: {text[:200]}")
