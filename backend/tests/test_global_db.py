"""Unit tests for get_global_db async dependency.

Verifies that get_global_db:
  1. Yields an AsyncSession
  2. Does NOT execute SET LOCAL rls.tenant_id (no tenant injection)
  3. Commits on success, rolls back on exception

No real DB connection required — async_session_factory is mocked.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


@pytest.mark.asyncio
async def test_get_global_db_yields_session():
    """get_global_db yields the session from async_session_factory."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session

    with patch("app.core.db.async_session_factory", mock_factory):
        from app.core.db import get_global_db

        gen = get_global_db()
        session = await gen.__anext__()
        assert session is mock_session

        # Exhaust generator (commit path)
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass


@pytest.mark.asyncio
async def test_get_global_db_no_set_local():
    """get_global_db must NOT execute SET LOCAL rls.tenant_id."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session

    with patch("app.core.db.async_session_factory", mock_factory):
        from app.core.db import get_global_db

        gen = get_global_db()
        await gen.__anext__()

        # Exhaust generator
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    # Verify no call to session.execute contained SET LOCAL
    for c in mock_session.execute.call_args_list:
        args = c.args
        if args:
            sql_str = str(args[0]).upper()
            assert "SET LOCAL" not in sql_str, (
                f"get_global_db must not call SET LOCAL, but found: {args[0]}"
            )
            assert "RLS.TENANT_ID" not in sql_str, (
                f"get_global_db must not inject tenant_id, but found: {args[0]}"
            )


@pytest.mark.asyncio
async def test_get_global_db_commits_on_success():
    """get_global_db commits the session after yielding without exception."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session

    with patch("app.core.db.async_session_factory", mock_factory):
        from app.core.db import get_global_db

        gen = get_global_db()
        await gen.__anext__()

        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_global_db_rolls_back_on_exception():
    """get_global_db rolls back and re-raises on exception."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session

    with patch("app.core.db.async_session_factory", mock_factory):
        from app.core.db import get_global_db

        gen = get_global_db()
        await gen.__anext__()

        with pytest.raises(ValueError, match="simulated error"):
            await gen.athrow(ValueError("simulated error"))

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
