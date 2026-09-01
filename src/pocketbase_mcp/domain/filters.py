"""Filter template binding via pb.filter()."""

from __future__ import annotations

from typing import Any


def build_filter(pb_client: Any, template: str, params: dict[str, Any]) -> str:
    """Bind params into template using pb.filter(), raising ValueError on missing placeholders."""
    return pb_client.filter(template, **params)
