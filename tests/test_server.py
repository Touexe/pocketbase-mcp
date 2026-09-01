"""Tests for server lifespan and startup auth."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from result import Err, Ok

from pocketbase_mcp.server import pb_lifespan, settings


@pytest.mark.asyncio
async def test_lifespan_creates_client_in_loop_and_closes():
    """Client is created inside the running event loop and closed on exit."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("pocketbase_mcp.server.Client", return_value=mock_client):
        with patch("pocketbase_mcp.server.settings") as mock_settings:
            mock_settings.url = "http://127.0.0.1:8090"
            mock_settings.auto_auth = False
            async with pb_lifespan(None) as ctx:
                assert "pb" in ctx
                state = ctx["pb"]
                assert state.pb is mock_client

    mock_client.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_startup_auth_failure_does_not_abort():
    """Startup auth failure records the error but still yields the state."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    exc = MagicMock()
    exc.original_message = "wrong password"
    mock_client.superusers.auth_with_password = AsyncMock(return_value=Err(exc))

    with patch("pocketbase_mcp.server.Client", return_value=mock_client):
        with patch("pocketbase_mcp.server.settings") as mock_settings:
            mock_settings.url = "http://127.0.0.1:8090"
            mock_settings.auto_auth = True
            mock_settings.admin_email = "admin@example.com"
            mock_settings.admin_password = "bad"
            async with pb_lifespan(None) as ctx:
                state = ctx["pb"]
                assert state.startup_auth_error == "wrong password"
                assert state.identity == "anonymous"


@pytest.mark.asyncio
async def test_startup_auth_failure_logged():
    """Startup auth failure is logged via the module logger."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    exc = MagicMock()
    exc.original_message = "bad credentials"
    mock_client.superusers.auth_with_password = AsyncMock(return_value=Err(exc))

    with patch("pocketbase_mcp.server.Client", return_value=mock_client):
        with patch("pocketbase_mcp.server.settings") as mock_settings:
            mock_settings.url = "http://127.0.0.1:8090"
            mock_settings.auto_auth = True
            mock_settings.admin_email = "admin@example.com"
            mock_settings.admin_password = "wrong"
            with patch("pocketbase_mcp.server.logger") as mock_logger:
                async with pb_lifespan(None) as ctx:
                    pass
                mock_logger.error.assert_called_once()
                call_args = mock_logger.error.call_args[0]
                assert "bad credentials" in call_args[1]


@pytest.mark.asyncio
async def test_startup_auth_success_logged():
    """Successful startup auth is logged via the module logger."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mock_client.superusers.auth_with_password = AsyncMock(return_value=Ok(MagicMock()))

    with patch("pocketbase_mcp.server.Client", return_value=mock_client):
        with patch("pocketbase_mcp.server.settings") as mock_settings:
            mock_settings.url = "http://127.0.0.1:8090"
            mock_settings.auto_auth = True
            mock_settings.admin_email = "admin@example.com"
            mock_settings.admin_password = "correct"
            with patch("pocketbase_mcp.server.logger") as mock_logger:
                async with pb_lifespan(None) as ctx:
                    pass
                mock_logger.info.assert_called_once()
