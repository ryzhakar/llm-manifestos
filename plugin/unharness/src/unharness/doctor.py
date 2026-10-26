"""Check that a project's unharness setup will work, one Finding per check, without the network."""

import json
import shutil
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from unharness.compile import (
    FULL_FILES,
    MINIFIED_FILES,
    STACK_BLOCK,
    SessionFiles,
    agent_files,
    constitution_block,
    harness_block,
    session_file_problem,
)
from unharness.config import (
    EMPTY_STACK_MESSAGE,
    PROJECT_FOLDER,
    SKILL_SOURCE,
    TEXT_ENCODING,
    Config,
    Element,
    UnharnessError,
    load,
    old_layout,
)
from unharness.digests import (
    Digest,
    DigestMode,
    Located,
    constitution_blocks,
    digest_mode,
    locate_single,
    locate_stacks,
    missing_message,
    require_usable,
    select_cover,
    slugs_of,
    stack_hashes,
    stack_slugs,
)
from unharness.resolve import (
    MANIFESTO_PLUGIN,
    PLUGIN_SKILL_SEPARATOR,
    Document,
    locate,
    manifesto_plugin_dir,
    resolve_stack,
    version_key,
)
from unharness.session import load_preamble, read_if_present
from unharness.switches import Switch, choose_version, newest_version, parse_version, require_version

MINIMUM_MANIFESTO_VERSION = "3.6.0"
INSTALLED_PLUGINS_FILE = Path("plugins") / "installed_plugins.json"
VERSION_FLAG = "--version"
VERSION_TIMEOUT_SECONDS = 10
CLAUDE_BINARY = "claude"
UV_BINARY = "uv"
UVX_BINARY = "uvx"
MARKETPLACE_SEPARATOR = "@"
STACKS_WITH_OVERLAP = DigestMode(stacks=True, overlap=True)
NO_DIGESTS = "none"


class Status(StrEnum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class Finding:
    status: Status
    name: str
    detail: str

    @property
    def line(self) -> str:
        return f"{self.status} {self.name}: {self.detail}"


@dataclass(frozen=True)
class Modes:
    digests: bool
    stack_digests: bool
    overlap: bool
    minified: bool


def doctor(
    config_path: Path, modes: Modes, login: Path, environ: Mapping[str, str], version_of: Callable[[Path], str],
    switches: Sequence[Switch], claude_version_override: str | None,
) -> list[Finding]:
    """Return one Finding per check, in the order the spec lists them; the override replaces the detected claude version in the switch lines."""
    override = None if claude_version_override is None else require_version(claude_version_override)
    binary = _on_path(CLAUDE_BINARY, environ)
    detected = None if binary is None else parse_version(version_of(binary))
    host = [
        _claude_finding(binary, detected, switches),
        *_switch_findings(switches, override or detected),
        _uv_finding(environ),
        _manifesto_plugin_finding(login),
    ]
    layout = _layout_findings(config_path.absolute().parent.parent)
    if has_failed(layout):
        return [*layout, *host]
    try:
        config = load(config_path)
    except UnharnessError as error:
        return [*layout, Finding(Status.FAIL, "config", str(error)), *host]
    plugin = manifesto_plugin_dir(config.registry, login)
    outcomes = [_resolve_element(element, config, login) for element in config.you]
    documents = [document for _, document in outcomes]
    stack = None if not documents or None in documents else documents
    skills = [
        _skill_finding(element, config, login)
        for element, document in zip(config.you, documents)
        if document and _is_plugin_skill(element)
    ]
    mode, flag_error = _flagged_mode(modes)
    on_stack = [] if stack is None else [
        *_digest_findings(config.you, stack, config.directory, plugin, mode),
        _cover_finding(config.you, stack, config.directory, plugin, mode, flag_error),
        *_session_findings(stack, config.directory, modes),
    ]
    size = [] if stack is None else [_prompt_size_finding(config.you, stack, config.directory, plugin)]
    return [
        *layout,
        Finding(Status.OK, "config", str(config_path.resolve())),
        *[finding for finding, _ in outcomes],
        _stack_finding("stack you", _elements_problem(outcomes, EMPTY_STACK_MESSAGE), len(outcomes)),
        *skills,
        *on_stack,
        *_subagent_findings(config, login, modes),
        _preamble_finding(config.directory),
        *host,
        *size,
    ]


def has_failed(findings: list[Finding]) -> bool:
    """Say whether any finding is a FAIL."""
    return any(finding.status is Status.FAIL for finding in findings)


def _layout_findings(project: Path) -> list[Finding]:
    """Report the project folder's layout: one FAIL per command that moves an old path, else one OK."""
    commands = old_layout(project)
    if not commands:
        return [Finding(Status.OK, "layout", str(project / PROJECT_FOLDER))]
    return [Finding(Status.FAIL, "layout", command) for command in commands]


def _resolve_element(element: Element, config: Config, login: Path) -> tuple[Finding, Document | None]:
    """Resolve one element; return its finding, and its Document when it resolved."""
    name = f"element {element.name}"
    try:
        document = resolve_stack([element], config.directory, config.registry, login)[0]
    except UnharnessError as error:
        return Finding(Status.FAIL, name, str(error)), None
    return Finding(Status.OK, name, str(locate(element, config.directory, config.registry, login)[0])), document


def _elements_problem(outcomes: list[tuple[Finding, Document | None]], empty_message: str) -> str | None:
    """Return the empty message for no elements, else the first resolver message, None when every element resolved."""
    if not outcomes:
        return empty_message
    return next((finding.detail for finding, document in outcomes if document is None), None)


def _stack_finding(name: str, problem: str | None, count: int) -> Finding:
    """Report a stack that resolved its elements, or fail with the problem."""
    if problem:
        return Finding(Status.FAIL, name, problem)
    return Finding(Status.OK, name, f"{count} elements resolved")


def _subagent_findings(config: Config, login: Path, modes: Modes) -> list[Finding]:
    """Report each subagents key's stack in config order."""
    return [_subagent_finding(key, elements, config, login, modes) for key, elements in config.subagents.items()]


def _subagent_finding(key: str, elements: list[Element], config: Config, login: Path, modes: Modes) -> Finding:
    """Report the first problem in the key's elements, its empty list, and its four files, else that all is current."""
    name = f"stack subagents.{key}"
    outcomes = [_resolve_element(element, config, login) for element in elements]
    problem = _elements_problem(outcomes, f"subagents.{key} is empty")
    if problem:
        return Finding(Status.WARN, name, problem)
    documents = [document for _, document in outcomes]
    for pair in (FULL_FILES, MINIFIED_FILES):
        files = agent_files(pair, key)
        for path in files.paths:
            problem = session_file_problem(path, read_if_present(config.directory / path), documents, files.fix_command)
            if problem:
                return Finding(Status.WARN, name, problem)
    return Finding(Status.OK, name, f"{len(documents)} elements resolved; session files current")


def _skill_finding(element: Element, config: Config, login: Path) -> Finding:
    """Compare the cached version a plugin skill resolves to with the version installed_plugins.json records."""
    plugin = element.reference.partition(PLUGIN_SKILL_SEPARATOR)[0]
    cached = locate(element, config.directory, config.registry, login)[1].name
    recorded = _installed_versions(login, plugin)
    name = f"skill {element.reference}"
    if cached in recorded:
        return Finding(Status.OK, name, cached)
    seen = f"records {', '.join(recorded)}" if recorded else f"has no record of {plugin}"
    return Finding(Status.WARN, name, f"cached {cached}, {INSTALLED_PLUGINS_FILE.name} {seen}")


def _digest_findings(
    elements: list[Element], documents: list[Document], directory: Path, plugin: Path, mode: DigestMode | None,
) -> list[Finding]:
    """Check each manifesto's single digest, then each candidate stack digest; a problem fails where the flags load the digest."""
    slugs = _manifesto_slugs(elements)
    hashes = stack_hashes(elements, documents)
    singles = [_single_finding(slug, directory, plugin, hashes, mode) for slug in slugs]
    stacks = [
        _usable_finding(located, hashes, loaded=mode is not None and mode.stacks)
        for located in locate_stacks(slugs, directory, plugin)
    ]
    return [*singles, *stacks]


def _cover_finding(
    elements: list[Element], documents: list[Document], directory: Path, plugin: Path,
    mode: DigestMode | None, flag_error: UnharnessError | None,
) -> Finding:
    """Report the cover the flags choose, else the one with stack digests and overlap; a refusal fails only when the flags choose."""
    if flag_error:
        return Finding(Status.FAIL, "cover", str(flag_error))
    try:
        cover = select_cover(elements, documents, directory, plugin, mode or STACKS_WITH_OVERLAP)
    except UnharnessError as error:
        return Finding(Status.FAIL if mode else Status.WARN, "cover", str(error))
    chosen = _in_render_order(_manifesto_slugs(elements), [*cover.stacks, *cover.singles.values()])
    stems = ", ".join(digest.stem for digest in chosen) or NO_DIGESTS
    return Finding(Status.OK, "cover", f"{stems}; {_word_count(digest.text for digest in chosen)} words")


def _prompt_size_finding(elements: list[Element], documents: list[Document], directory: Path, plugin: Path) -> Finding:
    """Count the words of the full prompt and of the shortest one; warn when the shortest cannot compile."""
    name = "prompt size"
    preamble = harness_block(load_preamble(directory).text)
    full = _word_count([preamble, constitution_block(documents), *_session_bodies(directory, FULL_FILES)])
    try:
        shortest_blocks = constitution_blocks(elements, documents, directory, plugin, STACKS_WITH_OVERLAP)
    except UnharnessError as error:
        return Finding(Status.WARN, name, f"shortest mode cannot compile: {error}")
    shortest = _word_count([preamble, constitution_block(shortest_blocks), *_session_bodies(directory, MINIFIED_FILES)])
    return Finding(Status.OK, name, f"full {full} words; shortest {shortest} words")


def _session_findings(documents: list[Document], directory: Path, modes: Modes) -> list[Finding]:
    """Check the four session files against the stack; a problem fails for the pair the flags load, else warns."""
    return [
        _session_finding(name, directory, documents, loaded=pair == (MINIFIED_FILES if modes.minified else FULL_FILES))
        for pair in (FULL_FILES, MINIFIED_FILES)
        for name in (pair.interplay, pair.commitments)
    ]


def _preamble_finding(directory: Path) -> Finding:
    """Report which preamble the prompt will carry."""
    return Finding(Status.OK, "preamble", load_preamble(directory).source)


def claude_version(binary: Path) -> str:
    """Run the binary with --version and return what it prints, empty when it cannot run."""
    try:
        run = subprocess.run([binary, VERSION_FLAG], capture_output=True, text=True, timeout=VERSION_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return run.stdout


def _claude_finding(binary: Path | None, detected: str | None, switches: Sequence[Switch]) -> Finding:
    """Report the claude on PATH and whether the switch registry holds its version."""
    if binary is None:
        return Finding(Status.WARN, CLAUDE_BINARY, "not on PATH; a shell function can still launch it")
    if detected is None:
        return Finding(Status.WARN, CLAUDE_BINARY, f"{binary} printed no version")
    chosen = choose_version(switches, detected)
    if chosen != detected:
        return Finding(Status.WARN, CLAUDE_BINARY, f"{binary} {detected}, not in the switch registry; launch uses switches verified at {chosen}")
    return Finding(Status.OK, CLAUDE_BINARY, f"{binary} {detected}")


def _switch_findings(switches: Sequence[Switch], version: str | None) -> list[Finding]:
    """Report the registry, then each switch against the version launch would choose for the version in use, None when unknown."""
    newest = newest_version(switches)
    chosen = newest if version is None else choose_version(switches, version)
    registry = Finding(Status.OK, "switch registry", f"newest {newest}; {len(switches)} switches")
    return [registry, *(_switch_finding(switch, chosen, version) for switch in switches)]


def _switch_finding(switch: Switch, chosen: str, version: str | None) -> Finding:
    name = f"switch {switch.kind} {switch.name}"
    if chosen not in switch.verified:
        return Finding(Status.WARN, name, f"left out; last verified at {switch.verified[-1]}")
    if version is None:
        return Finding(Status.WARN, name, f"verified at {chosen}, claude version unknown")
    if chosen != version:
        return Finding(Status.WARN, name, f"verified at {chosen}, not at {version}")
    return Finding(Status.OK, name, f"verified at {chosen}")


def _uv_finding(environ: Mapping[str, str]) -> Finding:
    """Find uv and uvx on PATH; the plugin launches unharness through uvx."""
    uv, uvx = _on_path(UV_BINARY, environ), _on_path(UVX_BINARY, environ)
    if uvx is None:
        return Finding(Status.FAIL, UV_BINARY, f"{UVX_BINARY} is not on PATH; install uv, which ships it")
    return Finding(Status.OK, UV_BINARY, " ".join(str(path) for path in (uv, uvx) if path))


def _manifesto_plugin_finding(login: Path) -> Finding:
    """Check the installed manifesto plugin is recent enough for every hook to stand down under unharness."""
    name = "manifesto plugin"
    versions = _installed_versions(login, MANIFESTO_PLUGIN)
    if not versions:
        return Finding(Status.FAIL, name, f"absent from {login / INSTALLED_PLUGINS_FILE}")
    newest = max(versions, key=version_key)
    if version_key(newest) < version_key(MINIMUM_MANIFESTO_VERSION):
        return Finding(Status.FAIL, name, f"{newest} is below {MINIMUM_MANIFESTO_VERSION}, whose hooks do not all stand down")
    return Finding(Status.OK, name, newest)


def _installed_versions(login: Path, plugin: str) -> list[str]:
    """Return the versions of the plugin recorded in the login's installed_plugins.json, none when it records none."""
    path = login / INSTALLED_PLUGINS_FILE
    try:
        records = json.loads(path.read_text(encoding=TEXT_ENCODING))["plugins"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    if not isinstance(records, dict):
        return []
    return [
        entry["version"]
        for key, entries in records.items()
        if key.partition(MARKETPLACE_SEPARATOR)[0] == plugin and isinstance(entries, list)
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("version"), str)
    ]


def _flagged_mode(modes: Modes) -> tuple[DigestMode | None, UnharnessError | None]:
    """Return the digest mode the flags name, or the refusal that the flags earn."""
    try:
        return digest_mode(modes.digests, modes.stack_digests, modes.overlap), None
    except UnharnessError as error:
        return None, error


def _manifesto_slugs(elements: list[Element]) -> list[str]:
    return list(dict.fromkeys(stack_slugs(elements)))


def _single_finding(slug: str, directory: Path, plugin: Path, hashes: dict[str, str], mode: DigestMode | None) -> Finding:
    located = locate_single(slug, directory, plugin)
    if located is None:
        loaded = mode is not None and not mode.stacks
        return Finding(Status.FAIL if loaded else Status.WARN, f"digest {slug}", missing_message(slug, directory, plugin))
    return _usable_finding(located, hashes, loaded=mode is not None)


def _usable_finding(located: Located, hashes: dict[str, str], loaded: bool) -> Finding:
    name = f"digest {located.stem}"
    try:
        require_usable(located, hashes)
    except UnharnessError as error:
        return Finding(Status.FAIL if loaded else Status.WARN, name, str(error))
    return Finding(Status.OK, name, f"{located.place}, current")


def _in_render_order(slugs: list[str], digests: list[Digest]) -> list[Digest]:
    return sorted(digests, key=lambda digest: (min(slugs.index(slug) for slug in slugs_of(digest.stem)), digest.stem))


def _session_bodies(directory: Path, files: SessionFiles) -> list[str]:
    texts = [read_if_present(directory / name) for name in (files.interplay, files.commitments)]
    return [STACK_BLOCK.sub("", text, count=1) for text in texts if text is not None]


def _word_count(texts: Iterable[str]) -> int:
    return sum(len(text.split()) for text in texts)


def _session_finding(name: str, directory: Path, documents: list[Document], loaded: bool) -> Finding:
    problem = session_file_problem(name, read_if_present(directory / name), documents)
    if problem is None:
        return Finding(Status.OK, name, "current")
    return Finding(Status.FAIL if loaded else Status.WARN, name, problem)


def _is_plugin_skill(element: Element) -> bool:
    return element.source_type == SKILL_SOURCE and PLUGIN_SKILL_SEPARATOR in element.reference


def _on_path(binary: str, environ: Mapping[str, str]) -> Path | None:
    found = shutil.which(binary, path=environ.get("PATH", ""))
    return Path(found) if found else None
