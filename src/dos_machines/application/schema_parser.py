from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from dos_machines.domain.models import EngineSchema, SchemaOption, SchemaSection

SECTION_RE = re.compile(r"^\[(?P<name>[^\]]+)\]\s*$")
ASSIGNMENT_RE = re.compile(r"^\s*(?P<name>[A-Za-z0-9_]+)\s*=\s*(?P<value>.*)$")
HEADER_RE = re.compile(r"^\s*(?P<name>[A-Za-z0-9_]+):\s*(?P<text>.*)$")
VALUE_DOC_RE = re.compile(r"^\s*(?P<name>[A-Za-z0-9_<>\-+.%/, ]+):\s*(?P<text>.+)$")
POSSIBLE_VALUES_RE = re.compile(r"Possible values:\s*(?P<values>.+)$", re.IGNORECASE)

DYNAMIC_OPTIONS = {"glshader"}
COMPOUND_MARKERS = ("<value>", "WxH", "X,Y", "N%", "relative", "spaces, commas, or semicolons")


@dataclass(slots=True)
class ParsedSection:
    name: str
    lines: list[str]


class ConfigSchemaParser:
    def parse_file(self, path: Path, engine_id: str, display_name: str) -> EngineSchema:
        return self.parse_text(path.read_text(encoding="utf-8"), engine_id=engine_id, display_name=display_name)

    def parse_text(self, text: str, engine_id: str, display_name: str) -> EngineSchema:
        sections = [self._parse_section(section) for section in self._split_sections(text)]
        return EngineSchema(engine_id=engine_id, display_name=display_name, sections=sections)

    def _split_sections(self, text: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        current_name: str | None = None
        current_lines: list[str] = []
        for line in text.splitlines():
            section_match = SECTION_RE.match(line)
            if section_match:
                if current_name is not None:
                    sections.append(ParsedSection(name=current_name, lines=current_lines))
                current_name = section_match.group("name")
                current_lines = []
                continue
            if current_name is not None:
                current_lines.append(line)
        if current_name is not None:
            sections.append(ParsedSection(name=current_name, lines=current_lines))
        return sections

    def _parse_section(self, parsed: ParsedSection) -> SchemaSection:
        assignments: list[tuple[str, str]] = []
        first_assignment_index: int | None = None
        for index, line in enumerate(parsed.lines):
            match = ASSIGNMENT_RE.match(line)
            if not match:
                continue
            if first_assignment_index is None:
                first_assignment_index = index
            assignments.append((match.group("name"), match.group("value").strip()))
        comment_lines = parsed.lines[: first_assignment_index or 0]
        blocks = self._parse_comment_blocks(comment_lines, [name for name, _ in assignments])

        options = [
            self._build_option(parsed.name, name, default_value, blocks.get(name, []))
            for name, default_value in assignments
        ]
        return SchemaSection(name=parsed.name, options=options)

    def _parse_comment_blocks(self, lines: list[str], assignment_names: list[str]) -> dict[str, list[str]]:
        assignment_set = set(assignment_names)
        blocks: dict[str, list[str]] = {}
        current_name: str | None = None
        current_lines: list[str] = []
        for raw_line in lines:
            if not raw_line.startswith("#"):
                continue
            content = raw_line[1:]
            header_match = HEADER_RE.match(content)
            header_name = header_match.group("name") if header_match else None
            if header_name in assignment_set:
                if current_name is not None:
                    blocks[current_name] = current_lines
                current_name = header_name
                current_lines = [content.rstrip()]
                continue
            if current_name is not None:
                current_lines.append(content.rstrip())
        if current_name is not None:
            blocks[current_name] = current_lines
        return blocks

    def _build_option(
        self,
        section_name: str,
        option_name: str,
        default_value: str,
        comment_lines: list[str],
    ) -> SchemaOption:
        description = ""
        normalized_lines: list[str] = []
        choices: list[str] = []
        choice_help: dict[str, str] = {}
        possible_values: list[str] = []
        for index, line in enumerate(comment_lines):
            stripped = line.strip()
            if not stripped:
                normalized_lines.append("")
                continue
            if index == 0:
                header_match = HEADER_RE.match(line)
                if header_match:
                    description = header_match.group("text").strip()
                    normalized_lines.append(description)
                    continue
            normalized_lines.append(stripped)

            possible_match = POSSIBLE_VALUES_RE.search(stripped)
            if possible_match:
                possible_values = [item.strip().rstrip(".") for item in possible_match.group("values").split(",")]
                continue
            value_doc_match = VALUE_DOC_RE.match(line)
            if value_doc_match:
                value_name = value_doc_match.group("name").strip()
                if value_name != option_name:
                    choice_help[value_name] = value_doc_match.group("text").strip()
                    if value_name not in choices:
                        choices.append(value_name)

        if possible_values:
            choices = possible_values

        help_text = "\n".join(line for line in normalized_lines if line).strip()
        value_type = self._infer_type(option_name, default_value, choices, help_text)
        return SchemaOption(
            section=section_name,
            name=option_name,
            default_value=default_value,
            value_type=value_type,
            description=description or option_name,
            help_text=help_text,
            choices=choices,
            choice_help=choice_help,
            runtime_dependent=option_name in DYNAMIC_OPTIONS,
        )

    def _infer_type(self, option_name: str, default_value: str, choices: list[str], help_text: str) -> str:
        lowered = default_value.lower()
        if option_name in DYNAMIC_OPTIONS:
            return "dynamic"
        if lowered in {"true", "false"}:
            return "boolean"
        if any(marker in help_text for marker in COMPOUND_MARKERS):
            return "compound"
        if choices:
            if any(choice.startswith("<") or " " in choice for choice in choices):
                return "compound"
            return "enum"
        if self._is_number(default_value):
            return "number"
        return "text"

    def _is_number(self, value: str) -> bool:
        try:
            float(value)
        except ValueError:
            return False
        return True
