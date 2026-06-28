"""Unit tests for the worker poll loop (fake provider, no network)."""

from datetime import datetime, timezone

from regulatory_agent.email.models import InboundEmail, OutboundEmail
from regulatory_agent.worker import process_inbox_once


class FakeProvider:
    def __init__(self, inbound: list[InboundEmail]) -> None:
        self._inbound = inbound
        self.sent: list[OutboundEmail] = []
        self.marked: list[str] = []

    def poll_unread(self) -> list[InboundEmail]:
        return self._inbound

    def send(self, message: OutboundEmail) -> None:
        self.sent.append(message)

    def mark_processed(self, message_id: str) -> None:
        self.marked.append(message_id)


def _inbound(mid: str, sender: str = "user@example.com") -> InboundEmail:
    return InboundEmail(
        message_id=mid,
        thread_id=f"t-{mid}",
        sender=sender,
        subject="req",
        body_text="Other Documents for M12205",
        received_at=datetime(2026, 6, 28, tzinfo=timezone.utc),
    )


def test_processes_and_marks_each_message() -> None:
    provider = FakeProvider([_inbound("a"), _inbound("b")])

    def processor(inbound: InboundEmail) -> OutboundEmail:
        return OutboundEmail(to=inbound.sender, subject="ok", body_text="done")

    handled = process_inbox_once(provider, processor=processor)

    assert handled == 2
    assert len(provider.sent) == 2
    assert provider.marked == ["a", "b"]


def test_processor_exception_still_marks_and_sends_error() -> None:
    provider = FakeProvider([_inbound("a")])

    def boom(inbound: InboundEmail) -> OutboundEmail:
        raise RuntimeError("kaboom")

    handled = process_inbox_once(provider, processor=boom)

    assert handled == 1
    assert provider.marked == ["a"]  # marked despite failure
    assert len(provider.sent) == 1
    assert "internal error" in provider.sent[0].body_text


def test_automated_sender_is_marked_but_not_replied() -> None:
    provider = FakeProvider([_inbound("a", sender="Google <no-reply@accounts.google.com>")])

    def must_not_send(inbound: InboundEmail) -> OutboundEmail:
        raise AssertionError("must not process automated senders")

    handled = process_inbox_once(provider, processor=must_not_send)

    assert handled == 1
    assert provider.sent == []  # no reply, no bounce loop
    assert provider.marked == ["a"]  # but marked read so it isn't re-fetched


def test_empty_inbox_handles_nothing() -> None:
    provider = FakeProvider([])
    assert process_inbox_once(provider, processor=lambda e: OutboundEmail("", "", "")) == 0
    assert provider.sent == []
    assert provider.marked == []
