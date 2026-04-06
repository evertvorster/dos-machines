from __future__ import annotations

import re


_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")


def parse_config_text(text: str) -> tuple[dict[str, dict[str, str]], list[str]]:
    sections: dict[str, dict[str, str]] = {}
    autoexec_lines: list[str] = []
    current_section: str | None = None

    for raw_line in text.splitlines():
        section_match = _SECTION_RE.match(raw_line)
        if section_match:
            current_section = section_match.group(1).strip().lower()
            if current_section != "autoexec":
                sections.setdefault(current_section, {})
            continue
        if current_section == "autoexec":
            autoexec_lines.append(raw_line)
            continue
        if current_section is None:
            continue
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("#", ";")) or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        sections[current_section][key.strip().lower()] = value.strip()
    return sections, autoexec_lines
