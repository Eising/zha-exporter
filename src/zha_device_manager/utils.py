"""Utilities."""

import logging
import textwrap
from typing import Any

LOG = logging.getLogger(__name__)

def format_like_cisco(obj_name: str, obj: dict[str, Any], primary_key: str | None = None, keydict: dict[str, str] | None = None) -> str:
    """Format an object like a cisco device."""
    ind = " " * 2
    lines: list[str] = []
    if not keydict:
        keydict = {}
    if not primary_key and "name" in obj:
        primary_key = "name"
    if primary_key:
        primary_key_val = str(obj.get(primary_key, ""))
        lines.append(f"{obj_name} {primary_key_val}")
    else:
        lines.append(f"{obj_name}")

    for key, value in obj.items():
        if not value:
            continue
        if primary_key and key == primary_key:
            continue
        if not isinstance(value, (list, dict)):
            lines.append(f"{ind}{key} {value}")
            continue
        if isinstance(value, dict):
            next_key = keydict.get(key)
            lines.append(textwrap.indent(format_like_cisco(key, value, next_key), ind))
            continue
        if isinstance(value[0], dict):
            next_key = keydict.get(key)
            for nested in value:
                lines.append(textwrap.indent(format_like_cisco(key, nested, next_key), ind))
        elif isinstance(value[0], (str, int, float, bool)):
            valuestr = ", ".join(value)
            lines.append(f"{ind}{key} {valuestr}")
        else:
            LOG.warn("Unable to serialize {value !r}")

    lines.append("!")

    return "\n".join(lines)
