"""Load the switch registry, the one home of every switch launch passes, and print its strip table."""

import json
import re
from dataclasses import dataclass
from collections.abc import Sequence
from importlib.resources import files
from typing import Any

from unharness.config import TEXT_ENCODING, UnharnessError
from unharness.resolve import version_key

REGISTRY_FILE = "switches.json"
KINDS = ("env", "flag", "settings")
VALUED_OPTION = "--autocompact"
OPTIONS = ("--keep-claude-md", "--keep-web-search", "--no-hooks", VALUED_OPTION)
KEYS = ("name", "kind", "value", "removes", "documented", "control", "verified", "default", "option")
GIVEN_KEY = "given"
SIZE_PLACEHOLDER = "<size>"
BOOLEAN_KEYS = ("documented", "control", "default")
SHARED_ROW_KEYS = ("control", "default", "option")
VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")
LINE_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+", re.MULTILINE)
TABLE_HEADER = "| Injected text | Switch | Default |"
TABLE_RULE = "|---|---|---|"
VERSIONS_PROBLEM = "must be a non-empty array of distinct X.Y.Z strings in ascending order"


@dataclass(frozen=True)
class Switch:
    name: str
    kind: str
    value: Any
    removes: str
    documented: bool
    control: bool
    verified: tuple[str, ...]
    default: bool
    option: str | None
    given: Any = None


def shipped_switches() -> list[Switch]:
    """Return the registry unharness ships, refused when it breaks the schema."""
    return parse_switches(files("unharness").joinpath(REGISTRY_FILE).read_text(encoding=TEXT_ENCODING))


def parse_switches(text: str) -> list[Switch]:
    """Return the entries of a registry text in order, refusing a text that breaks the schema."""
    try:
        entries = json.loads(text)
    except json.JSONDecodeError as error:
        raise UnharnessError(f"{REGISTRY_FILE} is not JSON: {error}") from error
    if not isinstance(entries, list):
        raise UnharnessError(f"{REGISTRY_FILE} is not one JSON array")
    switches = [_switch(index, entry) for index, entry in enumerate(entries)]
    _refuse_repeats(switches)
    return switches


def strip_table(switches: Sequence[Switch]) -> str:
    """Return the markdown strip table, one row per distinct removed text in order of first appearance."""
    rows = {}
    for switch in switches:
        rows.setdefault(switch.removes, []).append(switch)
    lines = [TABLE_HEADER, TABLE_RULE]
    lines += [f"| {removes} | {_switch_cell(row)} | {_default_cell(row[0])} |" for removes, row in rows.items()]
    return "\n".join(lines)


def registry_versions(switches: Sequence[Switch]) -> list[str]:
    """Return every version some entry is verified at, oldest first, refusing a registry with no entry."""
    versions = sorted({version for switch in switches for version in switch.verified}, key=version_key)
    if not versions:
        raise UnharnessError(f"{REGISTRY_FILE} holds no entry")
    return versions


def newest_version(switches: Sequence[Switch]) -> str:
    """Return the newest version some entry is verified at."""
    return registry_versions(switches)[-1]


def choose_version(switches: Sequence[Switch], detected: str) -> str:
    """Return the detected version when the registry holds it, else the newest below it, else the oldest."""
    versions = registry_versions(switches)
    below = [version for version in versions if version_key(version) <= version_key(detected)]
    return below[-1] if below else versions[0]


def parse_version(output: str) -> str | None:
    """Return the first X.Y.Z that opens a line of the output, None when no line opens with one."""
    found = LINE_VERSION_PATTERN.search(output)
    return found.group() if found else None


def require_version(value: str) -> str:
    """Return the value when it is exactly X.Y.Z, else refuse as --claude-version does."""
    if not VERSION_PATTERN.fullmatch(value):
        raise UnharnessError(f"--claude-version takes X.Y.Z, got {value}")
    return value


def _switch(index: int, entry: Any) -> Switch:
    if not isinstance(entry, dict):
        raise _refusal(index, "is not an object")
    for key in KEYS:
        if key not in entry:
            raise _refusal(index, f"{key} is missing")
    for key in entry:
        if key not in (*KEYS, GIVEN_KEY):
            raise _refusal(index, f"{key} is not a key of an entry")
    if entry["kind"] not in KINDS:
        raise _refusal(index, 'kind must be "env", "flag", or "settings"')
    option = _option(index, entry["option"])
    if option == VALUED_OPTION:
        _refuse_unpaired_value(index, entry)
    return Switch(
        name=_text(index, entry, "name"),
        kind=entry["kind"],
        value=_value(index, entry),
        removes=_text(index, entry, "removes"),
        documented=_boolean(index, entry, "documented"),
        control=_boolean(index, entry, "control"),
        verified=_versions(index, entry["verified"]),
        default=_boolean(index, entry, "default"),
        option=option,
        given=_given(index, entry, option),
    )


def _switch_cell(row: Sequence[Switch]) -> str:
    return ", ".join(_switch_text(switch) + ("" if switch.documented else ", undocumented") for switch in row)


def _switch_text(switch: Switch) -> str:
    if switch.kind == "env":
        return f"env `{switch.name}={switch.value}`"
    if switch.kind == "settings":
        return f"setting `{switch.name}`" if switch.value is None else f"setting `{switch.name}: {json.dumps(switch.value)}`"
    return f"`{switch.name}`" if switch.value is None else f"`{switch.name} {switch.value}`"


def _default_cell(switch: Switch) -> str:
    state = "kept" if not switch.default else "stripped" if switch.control else "set"
    if switch.option is None:
        return state
    if switch.option == VALUED_OPTION:
        return f"{state}; `{VALUED_OPTION} {SIZE_PLACEHOLDER}` passes `{_given_text(switch.given)}`"
    return f"{state}; `{switch.option}` {'strips' if state == 'kept' else 'keeps'}"


def _given_text(given: Any) -> str:
    """Return the given value as the table shows it, the size placeholder bare and any other value as JSON."""
    return SIZE_PLACEHOLDER if given == SIZE_PLACEHOLDER else json.dumps(given)


def _refusal(index: int, problem: str) -> UnharnessError:
    return UnharnessError(f"{REGISTRY_FILE} entry {index}: {problem}")


def _text(index: int, entry: dict, key: str) -> str:
    if not isinstance(entry[key], str) or not entry[key]:
        raise _refusal(index, f"{key} must be a non-empty string")
    return entry[key]


def _boolean(index: int, entry: dict, key: str) -> bool:
    if not isinstance(entry[key], bool):
        raise _refusal(index, f"{key} must be true or false")
    return entry[key]


def _value(index: int, entry: dict) -> Any:
    value, kind = entry["value"], entry["kind"]
    if kind == "env" and not isinstance(value, str):
        raise _refusal(index, "value must be a string")
    if kind == "flag" and not (isinstance(value, str) or value is None):
        raise _refusal(index, "value must be a string or null")
    return value


def _option(index: int, option: Any) -> str | None:
    if option is not None and option not in OPTIONS:
        quoted = [f'"{name}"' for name in OPTIONS]
        raise _refusal(index, f"option must be null, {', '.join(quoted[:-1])}, or {quoted[-1]}")
    return option


def _given(index: int, entry: dict, option: str | None) -> Any:
    """Return the value an entry of the valued option passes when the option is given, None for any other entry."""
    if option != VALUED_OPTION:
        if GIVEN_KEY in entry:
            raise _refusal(index, f"given belongs only to an entry whose option is {VALUED_OPTION}")
        return None
    if GIVEN_KEY not in entry:
        raise _refusal(index, "given is missing")
    if entry[GIVEN_KEY] is None:
        raise _refusal(index, "given must not be null")
    return entry[GIVEN_KEY]


def _refuse_unpaired_value(index: int, entry: dict) -> None:
    """Refuse an entry of the valued option whose value is null other than exactly when its default is false."""
    if (entry["value"] is None) == _boolean(index, entry, "default"):
        raise _refusal(index, "value must be null exactly when default is false")


def _versions(index: int, versions: Any) -> tuple[str, ...]:
    well_formed = isinstance(versions, list) and bool(versions) and all(
        isinstance(version, str) and VERSION_PATTERN.fullmatch(version) for version in versions
    )
    if not well_formed or [version_key(version) for version in versions] != sorted({version_key(version) for version in versions}):
        raise _refusal(index, f"verified {VERSIONS_PROBLEM}")
    return tuple(versions)


def _refuse_repeats(switches: list[Switch]) -> None:
    for index, switch in enumerate(switches):
        for earlier_index, earlier in enumerate(switches[:index]):
            if (earlier.kind, earlier.name) == (switch.kind, switch.name):
                raise _refusal(index, f"name repeats entry {earlier_index}, which has the same kind")
            if earlier.removes == switch.removes:
                for key in SHARED_ROW_KEYS:
                    if getattr(earlier, key) != getattr(switch, key):
                        raise _refusal(index, f"{key} differs from entry {earlier_index}, which has the same removes")
