"""Inbound/outbound email dataclasses. See docs/EMAIL.md."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class InboundEmail:
    message_id: str
    thread_id: str
    sender: str
    subject: str
    body_text: str
    received_at: datetime

    @property
    def sender_name(self) -> str | None:
        """Best-effort display name from a ``Name <addr@host>`` sender string."""
        raw = self.sender.strip()
        if "<" in raw:
            name = raw.split("<", 1)[0].strip().strip('"')
            return name or None
        return None


@dataclass
class OutboundEmail:
    to: str
    subject: str
    body_text: str
    attachment_path: Path | None = None
    in_reply_to: str | None = None  # original Message-ID, for threading
    references: str | None = None
    thread_id: str | None = None  # Gmail threadId, for API-side threading
