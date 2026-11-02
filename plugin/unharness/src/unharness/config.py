"""Name a project's files under .manifestos/ and read its config.yaml into a Config, with the YAML subset reader the file needs."""

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
PROJECT_FOLDER = ".manifestos"
CONFIG_PATH = f"{PROJECT_FOLDER}/config.yaml"
INTERPLAY_PATH = f"{PROJECT_FOLDER}/interplay.md"
COMMITMENTS_PATH = f"{PROJECT_FOLDER}/commitments.md"
MINIFIED_INTERPLAY_PATH = f"{PROJECT_FOLDER}/interplay.min.md"
MINIFIED_COMMITMENTS_PATH = f"{PROJECT_FOLDER}/commitments.min.md"
PREAMBLE_PATH = f"{PROJECT_FOLDER}/preamble.md"
DIGESTS_PATH = f"{PROJECT_FOLDER}/digests"
AGENTS_PATH = f"{PROJECT_FOLDER}/agents"
OLD_LAYOUT_MOVES = (
    (".manifestos.yaml", CONFIG_PATH),
    (".manifestos.interplay.md", INTERPLAY_PATH),
    (".manifestos.commitments.md", COMMITMENTS_PATH),
    (".manifestos.interplay.min.md", MINIFIED_INTERPLAY_PATH),
    (".manifestos.commitments.min.md", MINIFIED_COMMITMENTS_PATH),
    (".manifestos.preamble.md", PREAMBLE_PATH),
    (".claude/digests", DIGESTS_PATH),
)
MAKE_PROJECT_FOLDER = f"mkdir -p {PROJECT_FOLDER}"
YOU_KEY = "you"
SUBAGENTS_KEY = "subagents"
OTHER_KEY = "other"
NAMESPACE_SEPARATOR = ":"
FOLDER_KEY_PARTS = ("/",)
FOLDER_KEY_NAMES = (".", "..")
EMPTY_STACK_MESSAGE = "the stack is empty"
STACK_KEY = "stack"
BLOCKS_KEY = "blocks"
AGENT_KEYS = (STACK_KEY, BLOCKS_KEY)
BLOCK_FILE_KEY = "file"
RESERVED_BLOCK_NAMES = ("harness", "constitution", "interplay", "commitments", "stack")
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
class Block:
    """A named instruction block whose text is one line or the file at a path, exactly one of the two set."""

    name: str
    line: str | None
    file: str | None


@dataclass(frozen=True)
class Agent:
    """An agent's stack of elements and its blocks in declaration order."""

    stack: list[Element]
    blocks: list[Block]


@dataclass(frozen=True)
class Config:
    you: Agent
    subagents: dict[str, Agent]
    directory: Path
    registry: Path | None
    mapping_form: bool = False


@dataclass(frozen=True)
class KeyMatch:
    key: str
    by_default: bool


def fail(error: UnharnessError, status: int = 1) -> int:
    """Print the failure as one line on stderr and return the exit status."""
    print(f"unharness: {error}", file=sys.stderr)
    return status


def main(argv: list[str]) -> int:
    """Print the config of argv's project folder as JSON for a shell hook; fail with status 2 when no config exists."""
    parser = argparse.ArgumentParser(description="Print a project's .manifestos/config.yaml as JSON.")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--json", action="store_true", required=True)
    try:
        config = load(parser.parse_args(argv).project / CONFIG_PATH)
    except MissingConfigError as error:
        return fail(error, MISSING_CONFIG_STATUS)
    except UnharnessError as error:
        return fail(error)
    print(json.dumps({
        "you": [asdict(element) for element in config.you.stack],
        "subagents": {role: [asdict(element) for element in agent.stack] for role, agent in config.subagents.items()},
        "directory": str(config.directory),
        "registry": str(config.registry) if config.registry else "",
    }))
    return 0


def project_folder(config_path: Path) -> Path:
    """Return the project folder that holds the .manifestos folder of the config file."""
    return config_path.absolute().parent.parent


def load(path: Path) -> Config:
    """Read the config file at path into a Config whose directory is the project folder; stop on an old layout."""
    project = project_folder(path)
    _require_new_layout(project)
    root = parse_yaml(_config_text(path, project))
    if isinstance(root, list):
        root = {YOU_KEY: root}
    root = root or {}
    roles = root.get(SUBAGENTS_KEY) or {}
    if not isinstance(roles, dict):
        raise UnharnessError("subagents must be a mapping of role to list of elements")
    for key in roles:
        _require_folder_name(key)
    you = root.get(YOU_KEY)
    return Config(
        you=_agent(you, agent_path(None)),
        subagents={role: _agent(value, agent_path(role)) for role, value in roles.items()},
        directory=project,
        registry=(project / root["manifesto_dir"]).resolve() if root.get("manifesto_dir") else None,
        mapping_form=any(isinstance(value, dict) for value in (you, *roles.values())),
    )


def old_layout(project: Path) -> list[str]:
    """Return the commands, run in the project folder, that move each old path present to its new place."""
    present = [(old, new) for old, new in OLD_LAYOUT_MOVES if (project / old).exists()]
    needs_folder = any(not (project / new).exists() for _, new in present)
    moves = [_move_command(project, old, new) for old, new in present]
    return ([MAKE_PROJECT_FOLDER] if needs_folder else []) + moves


def _move_command(project: Path, old: str, new: str) -> str:
    if (project / new).exists():
        return f"# both {old} and {new} exist; keep one and delete the other"
    return f"mv {old} {new}"


def _require_new_layout(project: Path) -> None:
    commands = old_layout(project)
    if commands:
        raise UnharnessError("\n".join([f"old layout in {project}; run these there:", *commands]))


def no_subagent_key_message(agent_type: str, keys: list[str]) -> str:
    """Return the message for an agent type that matches no subagents key and finds no other:."""
    return f"{agent_type} matches no subagents key and the config has no other:; keys: {', '.join(keys) or 'none'}"


def empty_key_message(key: str) -> str:
    """Return the message for a subagents key whose list holds no elements."""
    return f"{agent_path(key)} is empty"


def _require_folder_name(key: str) -> None:
    if any(part in key for part in FOLDER_KEY_PARTS) or key in FOLDER_KEY_NAMES:
        raise UnharnessError(f"subagents key '{key}' cannot name a folder")


def subagent_key(agent_type: str, keys: list[str]) -> str | None:
    """Return the first subagents key the agent type matches by exact name, last namespace part, suffix, or other, else None."""
    match = subagent_match(agent_type, keys)
    return None if match is None else match.key


def subagent_match(agent_type: str, keys: list[str]) -> KeyMatch | None:
    """Return the key the cascade picks and whether only the default other: took the type, else None."""
    default = KeyMatch(OTHER_KEY, by_default=True) if OTHER_KEY in keys else None
    if not agent_type:
        return default
    local_name = agent_type.rsplit(NAMESPACE_SEPARATOR, 1)[-1]
    suffix_keys = [key for key in keys if key != OTHER_KEY and agent_type.endswith(key)]
    named = next((key for key in [agent_type, local_name, *suffix_keys] if key in keys), None)
    return default if named is None else KeyMatch(named, by_default=False)


def _config_text(path: Path, project: Path) -> str:
    if path.is_file():
        return path.read_text(encoding=TEXT_ENCODING)
    claude_md = project / CLAUDE_MD
    section = ACTIVE_MANIFESTOS_SECTION.search(claude_md.read_text(encoding=TEXT_ENCODING)) if claude_md.is_file() else None
    if not section:
        raise MissingConfigError(f"no config: tried {path} and the Active Manifestos section of {claude_md}")
    return section.group(1)


def _agent(value: list | dict | str | None, agent: str) -> Agent:
    """Read an agent's value, a list of elements, a mapping that lists them under stack:, or null, into its Agent."""
    if value is None:
        return Agent([], [])
    if isinstance(value, list):
        return Agent(_elements(value, agent), [])
    if not isinstance(value, dict):
        raise UnharnessError(f"{agent} must be a mapping with {STACK_KEY}: and optional {BLOCKS_KEY}:, or a list of elements")
    _require_agent_keys(value, agent)
    stack = value[STACK_KEY]
    elements = _elements([] if stack is None else stack, f"{agent}.{STACK_KEY}")
    return Agent(elements, _blocks(value.get(BLOCKS_KEY), agent))


def _require_agent_keys(fields: dict, agent: str) -> None:
    """Refuse a mapping agent's first key other than stack: and blocks:, then a mapping agent without stack:."""
    _refuse_unknown_key(fields, AGENT_KEYS, agent, "agent")
    if STACK_KEY not in fields:
        raise UnharnessError(f"no {STACK_KEY}: in {agent}; add {STACK_KEY}: and list its elements under it")


def _refuse_unknown_key(fields: dict, known: tuple[str, ...], place: str, kind: str) -> None:
    """Refuse the mapping's first key outside the known ones, naming it, the place, and the only keys a mapping of that kind holds."""
    unknown = [key for key in fields if key not in known]
    if unknown:
        held = " and ".join(f"{key}:" for key in known)
        only = "are the only keys" if len(known) > 1 else "is the only key"
        raise UnharnessError(f"unknown key '{unknown[0]}' in {place}; {held} {only} a mapping {kind} holds")


def _blocks(value: dict | list | str | None, agent: str) -> list[Block]:
    """Read the agent's blocks in declaration order, none when blocks: is absent or null."""
    if value is None:
        return []
    if not isinstance(value, dict):
        raise UnharnessError(f"{agent}.{BLOCKS_KEY} must map each block name to one line of text or {BLOCK_FILE_KEY}: <path>")
    return [_block(name, block, agent) for name, block in value.items()]


def _block(name: str | None, value: str | dict | list | None, agent: str) -> Block:
    """Read one block, its name before its value: a line of text, or a mapping whose file: holds a path."""
    _require_block_name(name, agent)
    place = block_path(agent, name)
    if isinstance(value, dict):
        _refuse_unknown_key(value, (BLOCK_FILE_KEY,), place, "block")
        return Block(name, None, _required_text(value[BLOCK_FILE_KEY], place))
    return Block(name, _required_text(value, place), None)


def _require_block_name(name: str | None, agent: str) -> None:
    """Refuse a block name that is not one word, then one that names a tag of the prompt or its session files."""
    blocks = f"{agent}.{BLOCKS_KEY}"
    if not name or WHITESPACE.search(name):
        raise UnharnessError(f"block name '{name or ''}' in {blocks} must be one word")
    if name in RESERVED_BLOCK_NAMES:
        reserved = f"{', '.join(RESERVED_BLOCK_NAMES[:-1])}, and {RESERVED_BLOCK_NAMES[-1]}"
        raise UnharnessError(f"block name '{name}' in {blocks} is reserved; the reserved names are {reserved}")


def _required_text(value: str | dict | list | None, place: str) -> str:
    """Return the value when it is text that holds more than whitespace; refuse anything else, naming the place."""
    if not isinstance(value, str) or not value.strip():
        raise UnharnessError(f"{place} must be one line of text or {BLOCK_FILE_KEY}: <path>")
    return value


def block_path(agent: str, name: str) -> str:
    """Return the YAML path of the agent's block of that name, as messages and doctor name it."""
    return f"{agent}.{BLOCKS_KEY}.{name}"


def agent_path(key: str | None) -> str:
    """Return the YAML path of the agent: you, or subagents.<key> for a subagents key."""
    return YOU_KEY if key is None else f"{SUBAGENTS_KEY}.{key}"


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
