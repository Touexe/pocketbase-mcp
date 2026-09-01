"""Helpers for building pypocketbase param models.

``ParamsList`` / ``ParamsOne`` declare their optional query fields as ``str``
with an empty-string default and no ``None`` coercion, so passing ``None`` (the
natural value for an unset ``expand`` / ``filter`` / ``sort``) raises a pydantic
``ValidationError``. Drop the ``None`` keys before construction so the model
falls back to its own defaults.
"""

from __future__ import annotations

from typing import Any

from pocketbase.utils.params import ParamsList, ParamsOne


def params_list(**kwargs: Any) -> ParamsList:
    return ParamsList(**{k: v for k, v in kwargs.items() if v is not None})


def params_one(**kwargs: Any) -> ParamsOne:
    return ParamsOne(**{k: v for k, v in kwargs.items() if v is not None})
