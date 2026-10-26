"""Read a project's .manifestos.yaml into a Config, with the YAML subset reader the file needs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

TEXT_ENCODING = "utf-8"
LIST_MARKER = "- "
MANIFESTO_SOURCE = "manifesto"
SKILL_SOURCE = "skill"
FILE_SOURCE = "file"
CLAUDE_MD = "CLAUDE.md"
EMPTY_STACK_MESSAGE = "the stack is empty"
ACTIVE_MANIFESTOS_SECTION = re.compile(r"^## Active Manifestos\n(.*?)(?=^## |\Z)", re.M | re.S)
SOURCE = re.compile(rf"^({MANIFESTO_SOURCE}|{SKILL_SOURCE}|{FILE_SOURCE}) (\S.*)$")
MISSING_CONFIG_STATUS = 2
MAPPING_ENTRY = re.compile(r":(?:\s|$)")
WHITESPACE = re.compile(r"\s")
TAB_INDENT = re.compile(r" *\t")
YAML_NULLS = ("", "~", "null")
QUOTED_SCALAR = re.compile(r"""^(["'])(.*?)\1(?:\s+#.*)?$""")
TRAILING_COMMENT = re.compile(r"(?:^|\s+)#.*$")
BLOCK_SCALAR = re.compile(r"^[>|](?:[-+]\d?|\d[-+]?)?(?:\s+#.*)?$")
BLOCK_SCALAR_CAUSE = "block scalars are not supported; write the value on one line"


class UnharnessError(Exception):
    """A failure whose one-line message tells the owner what to fix."""


class MissingConfigError(UnharnessError):
    """No config file and no CLAUDE.md section: a project that does not use manifestos."""


@dataclass(frozen=True)
class Element:
    name: str
    purpose: str | None
    source_type: str | None
    reference: str | None


@dataclass(frozen=True)
class Config:
    you: list[Element]
    subagents: dict[str, list[Element]]
    directory: Path
    registry: Path | None


def fail(error: UnharnessError, status: int = 1) -> int:
    """Print the failure as one line on stderr and return the exit status."""
    print(f"unharness: {error}", file=sys.stderr)
    return status


def main(argv: list[str]) -> int:
    """Print the config at argv's path as JSON for a shell hook; fail in one line, with status 2 when no config exists."""
    parser = argparse.ArgumentParser(description="Print a .manifestos.yaml as JSON.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true", required=True)
    try:
        config = load(parser.parse_args(argv).path)
    except MissingConfigError as error:
        return fail(error, MISSING_CONFIG_STATUS)
    except UnharnessError as error:
        return fail(error)
    print(json.dumps({
        "you": [asdict(element) for element in config.you],
        "subagents": {role: [asdict(element) for element in elements] for role, elements in config.subagents.items()},
        "directory": str(config.directory),
        "registry": str(config.registry) if config.registry else "",
    }))
    return 0


def load(path: Path) -> Config:
    """Read the config file at path into a Config."""
    root = parse_yaml(_config_text(path))
    if isinstance(root, list):
        root = {"you": root}
    root = root or {}
    roles = root.get("subagents") or {}
    if not isinstance(roles, dict):
        raise UnharnessError("subagents must be a mapping of role to list of elements")
    return Config(
        you=_elements(root.get("you") or [], "you"),
        subagents={role: _elements(items or [], f"subagents.{role}") for role, items in roles.items()},
        directory=path.parent,
        registry=(path.parent / root["manifesto_dir"]).resolve() if root.get("manifesto_dir") else None,
    )


def _config_text(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding=TEXT_ENCODING)
    claude_md = path.parent / CLAUDE_MD
    section = ACTIVE_MANIFESTOS_SECTION.search(claude_md.read_text(encoding=TEXT_ENCODING)) if claude_md.is_file() else None
    if not section:
        raise MissingConfigError(f"no config: tried {path} and the Active Manifestos section of {claude_md}")
    return section.group(1)


def _elements(items: list, list_label: str) -> list[Element]:
    if not isinstance(items, list):
        raise UnharnessError(f"{list_label} must be a list of elements")
    present = [item for item in items if item is not None]
    return [_element(item, f"element {number} of {list_label}") for number, item in enumerate(present, 1)]


def _element(item: str | dict, label: str) -> Element:
    fields = item if isinstance(item, dict) else {"name": item}
    source_type, reference = _source(fields.get("source"), label)
    name = fields.get("name") or (Path(reference).stem if source_type == FILE_SOURCE else None)
    if not name:
        raise UnharnessError(f"{label} has no name; add name: or a file source")
    if WHITESPACE.search(name):
        raise UnharnessError(f"{label} name {name!r} must hold no whitespace; add name:")
    return Element(name, fields.get("purpose"), source_type, reference)


def _source(source: str | None, label: str) -> tuple[str | None, str | None]:
    """Split a source into its type and reference; a missing source is a registry manifesto, named by the element."""
    if source is None:
        return None, None
    parsed = SOURCE.match(source)
    if not parsed:
        raise UnharnessError(
            f"{label} has source {source!r} that is none of {MANIFESTO_SOURCE} <name>, "
            f"{SKILL_SOURCE} <plugin>:<skill>, {SKILL_SOURCE} <skill>, or {FILE_SOURCE} <path>; "
            f"write a path as {FILE_SOURCE} <path>"
        )
    return parsed.group(1), parsed.group(2)


def parse_yaml(text: str):
    """Return the structure of block-style YAML text: mappings, lists, and string scalars; None if empty."""
    lines = [line.rstrip() for line in text.split("\n") if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        return None
    for line in lines:
        if TAB_INDENT.match(line):
            raise UnharnessError(f"the line {line.strip()!r} is indented with a tab; indent with spaces")
    value, consumed = _parse_block(lines, 0, _indent(lines[0]))
    _require_consumed(lines, consumed)
    return value


def _require_consumed(lines: list[str], consumed: int) -> None:
    if consumed < len(lines):
        raise UnharnessError(f"cannot place the line {lines[consumed].strip()!r}; check its indent")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _scalar(text: str) -> str | None:
    text = text.strip()
    quoted = QUOTED_SCALAR.match(text)
    if quoted:
        return quoted.group(2)
    text = TRAILING_COMMENT.sub("", text)
    return None if text in YAML_NULLS else text


def _split_entry(text: str) -> tuple[str, str]:
    entry = MAPPING_ENTRY.search(text)
    return (text[:entry.start()], text[entry.end():]) if entry else (text, "")


def _refuse_block_scalar(text: str, subject: str) -> None:
    if BLOCK_SCALAR.match(text.strip()):
        raise UnharnessError(f"{subject} holds a block scalar; {BLOCK_SCALAR_CAUSE}")


def _is_item(line: str) -> bool:
    stripped = line.lstrip()
    return stripped == LIST_MARKER.strip() or stripped.startswith(LIST_MARKER)


def _parse_block(lines: list[str], i: int, indent: int):
    if _is_item(lines[i]):
        return _parse_list(lines, i, indent)
    return _parse_mapping(lines, i, indent)


def _parse_list(lines: list[str], i: int, indent: int):
    result = []
    item_indent = indent + len(LIST_MARKER)
    while i < len(lines) and _indent(lines[i]) == indent and _is_item(lines[i]):
        content = lines[i].lstrip()[len(LIST_MARKER):]
        if not MAPPING_ENTRY.search(content):
            _refuse_block_scalar(content, f"the line {lines[i].strip()!r}")
            result.append(_scalar(content))
            i += 1
            continue
        block = [" " * item_indent + content]
        i += 1
        while i < len(lines) and _indent(lines[i]) >= item_indent:
            block.append(lines[i])
            i += 1
        value, consumed = _parse_block(block, 0, item_indent)
        _require_consumed(block, consumed)
        result.append(value)
    return result, i


def _parse_mapping(lines: list[str], i: int, indent: int):
    result = {}
    while i < len(lines) and _indent(lines[i]) == indent and not _is_item(lines[i]):
        key, rest = _split_entry(lines[i].lstrip())
        key = _scalar(key)
        if key in result:
            raise UnharnessError(f"key {key!r} appears twice")
        _refuse_block_scalar(rest, f"key {key!r}")
        value = _scalar(rest)
        if value is not None:
            result[key] = value
            i += 1
        elif i + 1 < len(lines) and _indent(lines[i + 1]) > indent:
            result[key], i = _parse_block(lines, i + 1, _indent(lines[i + 1]))
        else:
            result[key] = None
            i += 1
    return result, i


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
