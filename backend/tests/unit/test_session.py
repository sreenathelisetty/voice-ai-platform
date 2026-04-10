"""Session manager unit tests using fakeredis."""

import pytest

from app.session.manager import SessionManager
from app.session.models import ConversationTurn, SessionStatus
from app.utils.exceptions import SessionNotFoundError


@pytest.mark.asyncio
async def test_create_and_get_session(mock_redis):
    mgr = SessionManager()
    state = await mgr.create("test-session-1", user_id="user-1")
    assert state.session_id == "test-session-1"
    assert state.user_id == "user-1"

    fetched = await mgr.get("test-session-1")
    assert fetched.session_id == "test-session-1"


@pytest.mark.asyncio
async def test_get_missing_session_raises(mock_redis):
    mgr = SessionManager()
    with pytest.raises(SessionNotFoundError):
        await mgr.get("nonexistent-session")


@pytest.mark.asyncio
async def test_update_and_get_history(mock_redis):
    mgr = SessionManager()
    await mgr.create("hist-session")
    await mgr.update_history("hist-session", ConversationTurn(role="user", content="hello"))
    await mgr.update_history("hist-session", ConversationTurn(role="assistant", content="hi there"))

    history = await mgr.get_history("hist-session")
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "assistant"


@pytest.mark.asyncio
async def test_mark_disconnected_and_can_reconnect(mock_redis):
    mgr = SessionManager()
    await mgr.create("reconnect-session")
    assert not await mgr.can_reconnect("reconnect-session")

    await mgr.mark_disconnected("reconnect-session")
    assert await mgr.can_reconnect("reconnect-session")
