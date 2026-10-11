"""Collect a Spicy Lyrics secret key using Music Assistant's secure setup flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from music_assistant_models.config_entries import ConfigEntry
from music_assistant_models.enums import ConfigEntryType

if TYPE_CHECKING:
    from music_assistant.models.setup_flow import SetupSession


async def run_setup(session: SetupSession) -> None:
    """Store credentials without returning the existing secret to the browser."""
    setup_data = dict(session.context.setup_data)
    errors: dict[str, str] | None = None
    while True:
        submitted = await session.form(
            [
                ConfigEntry(
                    key="api_key",
                    type=ConfigEntryType.SECURE_STRING,
                    required=not bool(setup_data.get("api_key")),
                )
            ],
            step_id="credentials",
            errors=errors,
            last_step=True,
        )
        new_key = str(submitted.get("api_key") or "").strip()
        if new_key:
            if not new_key.startswith("sl_sk_"):
                errors = {"base": "invalid_api_key"}
                continue
            setup_data["api_key"] = new_key
        if not setup_data.get("api_key"):
            errors = {"base": "invalid_api_key"}
            continue
        await session.finish(setup_data)
        return
