from __future__ import annotations


class ContextTemplate:
    """Context template — requires server-side /v1/templates endpoints (not yet implemented).

    This is a placeholder for Phase 3 of ADR-0015. Templates will support:
    - %{events limit=N intent=TYPE}
    - %{lineage node=NODE_ID depth=N}
    - %{entities limit=N types=[TYPE,...]}
    - %{user_profile}
    - %{user_preferences limit=N}
    - %{user_skills limit=N}
    - %{proactive limit=N}
    - %{summary session=SESSION_ID}
    """

    def __init__(self, template_string: str) -> None:
        self._template = template_string

    @property
    def template(self) -> str:
        return self._template

    def render_preview(self) -> str:
        """Return the raw template string (rendering requires server-side support)."""
        return self._template
