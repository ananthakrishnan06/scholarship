"""Opaque session tokens protect persistent conversation data."""

import hashlib
import secrets

from apps.navigator.models import ConversationMessage, UserSession
from django.core.exceptions import ValidationError
from django.db import transaction


def create_session() -> tuple[UserSession, str]:
    token = secrets.token_urlsafe(32)
    session = UserSession.objects.create(token_hash=hashlib.sha256(token.encode()).hexdigest())
    return session, token


def get_session(session_id: str, token: str) -> UserSession:
    try:
        session = UserSession.objects.get(pk=session_id)
    except (UserSession.DoesNotExist, ValueError, ValidationError):
        raise PermissionError("Session not found or token invalid.") from None
    supplied = hashlib.sha256(token.encode()).hexdigest()
    if not secrets.compare_digest(supplied, session.token_hash):
        raise PermissionError("Session not found or token invalid.")
    return session


def context(session: UserSession) -> dict:
    messages = list(session.messages.order_by("-id")[:8])
    last_ids = []
    for message in messages:
        if message.role == "assistant" and message.content.get("status") in (
            "success",
            "insufficient_evidence",
        ):
            ids = list(dict.fromkeys(s["scheme_id"] for s in message.content.get("sources", [])))
            if ids:
                last_ids = ids
                break
    return {
        "scheme_ids": last_ids,
        "messages": [{"role": m.role, "content": m.content} for m in reversed(messages)],
    }


@transaction.atomic
def save_turn(session, question, answer):
    ConversationMessage.objects.create(session=session, role="user", content={"question": question})
    ConversationMessage.objects.create(session=session, role="assistant", content=answer)
    session.save(update_fields=["updated_at"])
