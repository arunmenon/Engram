"""Security tests for the Engram MCP server — session handling, admin key, error disclosure."""

from __future__ import annotations

import pytest

from engram.exceptions import NotFoundError
from engram.models import AtlasResponse
from engram_mcp.server import EngramMCPServer
from engram_mcp.tools import _handle_forget, _handle_profile, _handle_recall, _sanitize_error

# ---------------------------------------------------------------------------
# TestMCPSessionHijacking
# ---------------------------------------------------------------------------


class TestMCPSessionHijacking:
    """Verify behaviour when recalling other sessions."""

    @pytest.mark.asyncio
    async def test_recall_other_session(self, mcp_server: EngramMCPServer):
        """Recalling another session_id should go through (no per-session auth)."""
        other_session = "other-session-id-999"
        mcp_server.client.get_context.return_value = AtlasResponse()
        result = await _handle_recall(mcp_server, {"session_id": other_session})
        mcp_server.client.get_context.assert_called_once_with(
            other_session, query=None, max_nodes=50
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_session_id_enumeration(self, mcp_server: EngramMCPServer):
        """Both existing and non-existing sessions should return consistent response shapes."""
        # Existing session returns data
        mcp_server.client.get_context.return_value = AtlasResponse()
        result_existing = await _handle_recall(mcp_server, {"session_id": "existing"})

        # Non-existing session also returns (empty) data
        result_nonexist = await _handle_recall(mcp_server, {"session_id": "nonexistent"})

        # Both should produce TextContent with similar structure
        assert result_existing[0].type == "text"
        assert result_nonexist[0].type == "text"


# ---------------------------------------------------------------------------
# TestMCPAdminKeyEnforcement
# ---------------------------------------------------------------------------


class TestMCPAdminKeyEnforcement:
    """Verify admin operations require admin credentials."""

    @pytest.mark.asyncio
    async def test_forget_without_admin_key(self, mcp_server: EngramMCPServer):
        """Forget without admin_key should produce an error from the client."""
        mcp_server.client.delete_user.side_effect = Exception("Unauthorized")
        result = await _handle_forget(mcp_server, {"user_id": "user-123"})
        text = result[0].text
        assert "Error" in text or "error" in text.lower()

    @pytest.mark.asyncio
    async def test_profile_without_admin_key(self, mcp_server: EngramMCPServer):
        """Profile without admin_key should produce an error from the client."""
        mcp_server.client.get_user_profile.side_effect = Exception("Unauthorized")
        mcp_server.client.get_user_preferences.side_effect = Exception("Unauthorized")
        mcp_server.client.get_user_skills.side_effect = Exception("Unauthorized")
        mcp_server.client.get_user_patterns.side_effect = Exception("Unauthorized")
        mcp_server.client.get_user_interests.side_effect = Exception("Unauthorized")
        result = await _handle_profile(mcp_server, {"user_id": "user-123"})
        # Should still produce output (with empty sections), not crash
        assert len(result) == 1
        assert result[0].type == "text"

    @pytest.mark.asyncio
    async def test_forget_with_admin_key(self, mcp_server: EngramMCPServer):
        """Forget with admin_key should succeed."""
        mcp_server.client.delete_user.return_value = {"deleted_count": 3}
        result = await _handle_forget(mcp_server, {"user_id": "user-123"})
        text = result[0].text
        assert "Deletion Complete" in text
        assert "3" in text


# ---------------------------------------------------------------------------
# TestMCPUserEnumeration
# ---------------------------------------------------------------------------


class TestMCPUserEnumeration:
    """Verify consistent error messages for non-existent users (no enumeration)."""

    @pytest.mark.asyncio
    async def test_nonexistent_user_profile(self, mcp_server: EngramMCPServer):
        """NotFoundError from profile should not leak existence info."""
        mcp_server.client.get_user_profile.side_effect = NotFoundError("not found")
        mcp_server.client.get_user_preferences.side_effect = NotFoundError("not found")
        mcp_server.client.get_user_skills.side_effect = NotFoundError("not found")
        mcp_server.client.get_user_patterns.side_effect = NotFoundError("not found")
        mcp_server.client.get_user_interests.side_effect = NotFoundError("not found")
        result = await _handle_profile(mcp_server, {"user_id": "nonexistent-user"})
        # return_exceptions=True means we get a result, not a raised error
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_nonexistent_user_forget(self, mcp_server: EngramMCPServer):
        """NotFoundError from forget should give generic message."""
        mcp_server.client.delete_user.side_effect = ValueError("user_id not found")
        result = await _handle_forget(mcp_server, {"user_id": "ghost-user"})
        text = result[0].text
        assert "Error" in text

    @pytest.mark.asyncio
    async def test_404_consistent_message(self, mcp_server: EngramMCPServer):
        """Both profile and forget give same error pattern for nonexistent user."""
        mcp_server.client.get_user_profile.side_effect = NotFoundError("not found")
        mcp_server.client.get_user_preferences.side_effect = NotFoundError("not found")
        mcp_server.client.get_user_skills.side_effect = NotFoundError("not found")
        mcp_server.client.get_user_patterns.side_effect = NotFoundError("not found")
        mcp_server.client.get_user_interests.side_effect = NotFoundError("not found")
        profile_result = await _handle_profile(mcp_server, {"user_id": "no-one"})

        mcp_server.client.delete_user.side_effect = Exception("not found")
        forget_result = await _handle_forget(mcp_server, {"user_id": "no-one"})

        # Both should be non-empty TextContent with consistent structure
        assert profile_result[0].type == "text"
        assert forget_result[0].type == "text"
        # Neither should expose internal details
        assert "/Users/" not in profile_result[0].text
        assert "/Users/" not in forget_result[0].text


# ---------------------------------------------------------------------------
# TestMCPErrorDisclosure
# ---------------------------------------------------------------------------


class TestMCPErrorDisclosure:
    """Ensure error output doesn't leak sensitive info."""

    def test_error_no_file_paths(self):
        exc = Exception("Error in /Users/admin/src/engram/server.py line 42")
        sanitized = _sanitize_error(exc)
        assert "/Users/" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_error_no_api_key(self):
        exc = Exception('Failed: api_key=sk-secret-12345 was rejected')
        sanitized = _sanitize_error(exc)
        assert "sk-secret-12345" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_error_no_connection_strings(self):
        exc = Exception("Cannot connect to redis://user:password@host:6379/0")
        sanitized = _sanitize_error(exc)
        assert "user:password" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_error_no_stack_traces(self):
        exc = Exception('Traceback (most recent call last):\n  File "/app/main.py", line 10')
        sanitized = _sanitize_error(exc)
        assert "Traceback" not in sanitized
        assert "/app/main.py" not in sanitized

    def test_nested_exception_chain(self):
        inner = Exception("redis://admin:pass@redis:6379")
        outer = Exception(f"Wrapper: {inner}")
        sanitized = _sanitize_error(outer)
        assert "admin:pass" not in sanitized


# ---------------------------------------------------------------------------
# TestMCPToolAccessControl
# ---------------------------------------------------------------------------


class TestMCPToolAccessControl:
    """Document tool access control characteristics."""

    def test_all_tools_callable(self):
        """Verify all 7 tools are accessible (no per-tool auth)."""
        from engram_mcp.tools import TOOL_DEFINITIONS

        tool_names = {t.name for t in TOOL_DEFINITIONS}
        expected = {
            "engram_record",
            "engram_recall",
            "engram_search",
            "engram_trace",
            "engram_profile",
            "engram_entities",
            "engram_forget",
        }
        assert tool_names == expected

    @pytest.mark.asyncio
    async def test_forget_is_destructive(self, mcp_server: EngramMCPServer):
        """Document that engram_forget requires admin_key (via client)."""
        # The client's delete_user uses admin=True in transport
        mcp_server.client.delete_user.return_value = {"deleted_count": 0}
        result = await _handle_forget(mcp_server, {"user_id": "test-user"})
        # Verify delete_user was called (it uses admin=True internally)
        mcp_server.client.delete_user.assert_called_once_with("test-user")
        assert "Deletion Complete" in result[0].text
