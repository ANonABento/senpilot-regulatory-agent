"""Background worker: poll email → process → reply. See docs/EMAIL.md.

``process_inbox_once`` takes the provider (and processor) as arguments so it can
be driven by a fake provider in tests with no network.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from regulatory_agent.agent.runner import process_email
from regulatory_agent.config import settings
from regulatory_agent.email.models import InboundEmail, OutboundEmail
from regulatory_agent.email.provider import EmailProvider
from regulatory_agent.email.reply import build_error_reply

logger = logging.getLogger(__name__)

Processor = Callable[[InboundEmail], OutboundEmail]


def process_inbox_once(
    provider: EmailProvider, *, processor: Processor = process_email
) -> int:
    """Process every currently-unread email once. Returns the number handled."""
    handled = 0
    for inbound in provider.poll_unread():
        try:
            outbound = processor(inbound)
            provider.send(outbound)
        except Exception:  # noqa: BLE001 — one bad email must not stop the batch
            logger.exception("Failed to process message %s", inbound.message_id)
            _try_send_error(provider, inbound)
        finally:
            try:
                provider.mark_processed(inbound.message_id)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to mark %s processed", inbound.message_id)
        handled += 1
    return handled


def _try_send_error(provider: EmailProvider, inbound: InboundEmail) -> None:
    try:
        provider.send(
            OutboundEmail(
                to=inbound.sender,
                subject=f"Re: {inbound.subject}".strip(),
                body_text=build_error_reply("an internal error occurred. Please try again."),
                in_reply_to=inbound.message_id or None,
                thread_id=inbound.thread_id or None,
            )
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send error reply to %s", inbound.sender)


def run_forever(
    provider: EmailProvider,
    *,
    interval_sec: int | None = None,
    stop: Callable[[], bool] | None = None,
) -> None:
    """Poll the inbox on an interval until ``stop()`` returns True (or forever)."""
    interval = interval_sec if interval_sec is not None else settings.poll_interval_sec
    logger.info("Worker started; polling every %ds", interval)
    while not (stop and stop()):
        try:
            count = process_inbox_once(provider)
            if count:
                logger.info("Handled %d message(s)", count)
        except Exception:  # noqa: BLE001 — keep the loop alive across poll failures
            logger.exception("Poll cycle failed")
        if stop and stop():
            break
        time.sleep(interval)
