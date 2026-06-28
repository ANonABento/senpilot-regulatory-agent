"""Email provider protocol. See docs/EMAIL.md."""

from __future__ import annotations

from typing import Protocol

from regulatory_agent.email.models import InboundEmail, OutboundEmail


class EmailProvider(Protocol):
    """Transport abstraction — Gmail is the first concrete implementation."""

    def poll_unread(self) -> list[InboundEmail]:
        """Return unread request emails (newest-first not required)."""
        ...

    def send(self, message: OutboundEmail) -> None:
        """Send a reply, attaching ``message.attachment_path`` if set."""
        ...

    def mark_processed(self, message_id: str) -> None:
        """Mark a message handled (e.g. remove the UNREAD label)."""
        ...
