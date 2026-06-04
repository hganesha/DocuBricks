"""
apps/lib/genie.py
-----------------
Client for the Databricks AI/BI Genie Conversation API.

Genie conversations are asynchronous: you POST to start a conversation, then
poll GET until the message reaches a terminal state (COMPLETED / FAILED /
CANCELLED).  This module wraps that lifecycle into a single blocking call and
exposes a clean ``GenieError`` exception for callers.

Environment variables required
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``DATABRICKS_HOST``   – workspace URL  (``https://…``)
``DATABRICKS_TOKEN``  – PAT or OAuth token
"""
from __future__ import annotations

import os
import time

import httpx


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class GenieError(Exception):
    """Raised when a Genie conversation fails, is cancelled, or times out."""

    def __init__(self, message: str, space_id: str) -> None:
        super().__init__(message)
        self.message = message
        self.space_id = space_id

    def __str__(self) -> str:  # pragma: no cover
        return f"GenieError(space_id={self.space_id!r}): {self.message}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    token = os.environ["DATABRICKS_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    host = os.environ["DATABRICKS_HOST"].rstrip("/")
    return host


def _extract_text(message: dict) -> str:
    """
    Pull human-readable text out of a completed Genie message.

    The Genie API returns attachments which may be either plain text or a SQL
    query + description pair.  We prefer text; fall back to SQL + description;
    fall back to the message ``content`` field.
    """
    attachments = message.get("attachments", [])
    for att in attachments:
        if att.get("text"):
            return att["text"]["content"]
        if att.get("query"):
            query_block = att["query"]
            sql = query_block.get("query", "")
            desc = query_block.get("description", "")
            parts = []
            if sql:
                parts.append(f"```sql\n{sql}\n```")
            if desc:
                parts.append(desc)
            return "\n\n".join(parts)
    # Fallback: top-level content field
    return message.get("content", "(no content)")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ask_genie(space_id: str, question: str, timeout: int = 60) -> str:
    """
    Ask a natural-language *question* to the Genie space identified by
    *space_id* and return the answer as a plain string.

    The function blocks until Genie responds or *timeout* seconds elapse.

    Parameters
    ----------
    space_id:   Genie space ID (from ``GENIE_SPACE_ID_*`` env vars)
    question:   natural-language question
    timeout:    maximum seconds to wait before raising :class:`GenieError`

    Returns
    -------
    str
        The text content of the first attachment, or the SQL query string and
        its description if Genie returns a query result.

    Raises
    ------
    GenieError
        If the conversation reaches ``FAILED`` / ``CANCELLED`` status, or if
        *timeout* is exceeded without a terminal state.
    httpx.HTTPStatusError
        If the initial POST or any poll request returns a non-2xx status.
    """
    base = _base_url()
    hdrs = _headers()

    # 1. Start conversation
    start_resp = httpx.post(
        f"{base}/api/2.0/genie/spaces/{space_id}/start-conversation",
        headers=hdrs,
        json={"content": question},
        timeout=30.0,
    )
    start_resp.raise_for_status()
    body = start_resp.json()
    conversation_id = body["conversation_id"]
    message_id = body["message_id"]

    poll_url = (
        f"{base}/api/2.0/genie/spaces/{space_id}"
        f"/conversations/{conversation_id}/messages/{message_id}"
    )

    # 2. Poll until terminal state or timeout
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        poll_resp = httpx.get(poll_url, headers=hdrs, timeout=15.0)
        poll_resp.raise_for_status()
        msg = poll_resp.json()
        status = msg.get("status", "")

        if status == "COMPLETED":
            return _extract_text(msg)

        if status in ("FAILED", "CANCELLED"):
            error_detail = msg.get("error", msg.get("content", "unknown error"))
            raise GenieError(
                f"Genie conversation ended with status={status}: {error_detail}",
                space_id=space_id,
            )

        time.sleep(1)

    raise GenieError(
        f"Genie did not respond within {timeout} seconds for question: {question!r}",
        space_id=space_id,
    )
