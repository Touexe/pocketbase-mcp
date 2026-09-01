"""Section 11 — live enhancement verification: the three prompts render against a real schema."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]

_FIELDS = [{"name": "title", "type": "text", "required": True}]


def _joined(rendered) -> str:
    parts: list[str] = []
    for message in rendered.messages:
        content = message.content
        parts.append(content if isinstance(content, str) else getattr(content, "text", str(content)))
    return " ".join(parts)


async def test_all_prompts_listed(live_client) -> None:
    """11.6 — inspect_then_query, safe_delete, create_with_validation are all listed."""
    names = {p.name for p in await live_client.list_prompts()}
    assert {"inspect_then_query", "safe_delete", "create_with_validation"} <= names


async def test_prompts_render_naming_their_target_tool(live_client, live_collection) -> None:
    """11.6 — each prompt renders non-empty messages that name the tool it steers toward."""
    name = await live_collection("prompt", _FIELDS)

    cases = [
        ("inspect_then_query", {"collection": name}, "find_records"),
        ("safe_delete", {"collection": name, "filter_description": "title = 'x'"}, "delete_records"),
        ("create_with_validation", {"collection": name}, "write_record"),
    ]
    for prompt_name, args, target_tool in cases:
        rendered = await live_client.get_prompt(prompt_name, args)
        assert rendered.messages, f"{prompt_name} rendered no messages"
        text = _joined(rendered)
        assert name in text
        assert target_tool in text, f"{prompt_name} did not name {target_tool}"
