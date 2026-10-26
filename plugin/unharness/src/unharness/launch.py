"""Write the prompt to the cache and run the launcher with the harness text stripped."""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import IO

from unharness.config import TEXT_ENCODING, UnharnessError
from unharness.switches import SIZE_PLACEHOLDER, VALUED_OPTION, Switch, choose_version, newest_version, parse_version, require_version

CACHE_FOLDER = "unharness"
CACHE_VARIABLE = "XDG_CACHE_HOME"
DEFAULT_SHELL = "/bin/sh"
FOLDER_MODE = 0o700
FILE_MODE = 0o600
DEFAULT_LAUNCHER = "claude"
CONTROLLING_TERMINAL = "/dev/tty"
STDIN_DESCRIPTOR = 0
OUTPUT_DESCRIPTORS = (1, 2)
STAND_DOWN_MARKER = {"UNHARNESS": "1"}
SYSTEM_PROMPT_FLAG = "--system-prompt-file"
SETTINGS_FLAG = "--settings"
VERSION_FLAG = "--version"
VERSION_TIMEOUT_SECONDS = 10
INTERACTIVE_COMMAND_FLAG = "-ic"
OPTION_ATTRIBUTES = {
    "--keep-claude-md": "keep_claude_md", "--keep-web-search": "keep_web_search", "--no-hooks": "no_hooks", "--autocompact": "autocompact",
}
AUTOCOMPACT_THOUSANDS = (100, 1000)
TOKENS_PER_THOUSAND = 1000
SIZE_PATTERN = re.compile(r"([0-9]+)[kK]?")


@dataclass(frozen=True)
class Options:
    keep_claude_md: bool
    keep_web_search: bool
    no_hooks: bool
    launcher: list[str]
    claude_version: str | None = None
    autocompact: str | None = None


def read_text_file(path: str) -> str:
    """Return the file's text, read as UTF-8."""
    return Path(path).read_text(encoding=TEXT_ENCODING)


def launch(
    prompt: str,
    options: Options,
    switches: Sequence[Switch],
    environ: Mapping[str, str],
    cache_home: Path,
    terminal: str,
    reopen_stdin: Callable[[str], None],
    execute: Callable[[list[str], dict[str, str]], int],
    version_of: Callable[[list[str], Mapping[str, str]], str],
    read_file: Callable[[str], str],
) -> int:
    """Cache the prompt, then print the launch command, or run the launcher and return its status."""
    if not prompt.strip():
        raise UnharnessError("the prompt is empty")
    autocompact_tokens = _autocompact_tokens(options.autocompact)
    owner_words, owner_settings = _split_owner_settings(options.launcher[1:], read_file)
    chosen = _chosen_version(switches, options, environ, version_of)
    prompt_file = _write_prompt(prompt, cache_home)
    passed = _passed_switches(switches, options, chosen, autocompact_tokens)
    _note_autocompact_unverified(passed, autocompact_tokens, chosen)
    variables = _strip_environment(passed)
    settings, overridden_keys = _merged_settings(owner_settings, _strip_settings(passed))
    _note_overridden_settings(overridden_keys)
    arguments = _strip_arguments(prompt_file, passed, settings)
    assignments = [f"{name}={value}" for name, value in variables.items()]
    if not options.launcher:
        print(shlex.join(["env", *assignments, DEFAULT_LAUNCHER, *arguments]), f"<{terminal}")
        return 0
    reopen_stdin(terminal)
    return execute([*options.launcher[:1], *owner_words, *arguments], {**environ, **variables})


def cache_home(environ: Mapping[str, str], home: Path) -> Path:
    """Return XDG_CACHE_HOME, else .cache in the home folder."""
    return Path(environ[CACHE_VARIABLE]) if environ.get(CACHE_VARIABLE) else home / ".cache"


def execute_launcher(argv: list[str], env: dict[str, str]) -> int:
    """Replace this process with the launcher when it is on PATH; else run it through the interactive shell."""
    if _on_path(argv[0], env):
        os.execvpe(argv[0], argv, env)
    return subprocess.run(_through_shell(argv, env), env=env).returncode


def version_output(argv: list[str], environ: Mapping[str, str]) -> str:
    """Run argv as launch runs a launcher and return its stdout, empty when it cannot run or outlasts ten seconds."""
    command = argv if _on_path(argv[0], environ) else _through_shell(argv, environ)
    try:
        run = subprocess.run(
            command, env=dict(environ), stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace",
            timeout=VERSION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return run.stdout


def terminal_device(descriptors: tuple[int, ...] = OUTPUT_DESCRIPTORS) -> str:
    """Return the device of the first descriptor that is a terminal, else the controlling terminal, /dev/tty."""
    for descriptor in descriptors:
        try:
            return os.ttyname(descriptor)
        except OSError:
            continue
    return CONTROLLING_TERMINAL


def reopen_terminal(
    device: str,
    stdin_is_terminal: Callable[[], bool] = lambda: os.isatty(STDIN_DESCRIPTOR),
    open_terminal: Callable[[str], IO] = open,
    redirect: Callable[[int, int], None] = os.dup2,
) -> None:
    """Point stdin at the device, so an interactive session survives a piped prompt; keep stdin if it is a terminal or the device will not open."""
    if stdin_is_terminal():
        return
    try:
        with open_terminal(device) as terminal:
            redirect(terminal.fileno(), STDIN_DESCRIPTOR)
    except OSError:
        pass


def _autocompact_tokens(size: str | None) -> int | None:
    """Return the --autocompact SIZE in tokens, None when the option is absent, refusing a SIZE outside Claude Code's bounds."""
    if size is None:
        return None
    matched = SIZE_PATTERN.fullmatch(size)
    lowest, highest = AUTOCOMPACT_THOUSANDS
    if matched is None or not lowest <= int(matched.group(1)) <= highest:
        raise UnharnessError(f"--autocompact takes a whole number of thousands of tokens from {lowest} to {highest}, such as 500k; got {size}")
    return int(matched.group(1)) * TOKENS_PER_THOUSAND


def _on_path(program: str, environ: Mapping[str, str]) -> bool:
    return bool(shutil.which(program, path=environ.get("PATH")))


def _through_shell(argv: list[str], environ: Mapping[str, str]) -> list[str]:
    return [environ.get("SHELL", DEFAULT_SHELL), INTERACTIVE_COMMAND_FLAG, shlex.join(argv)]


def _chosen_version(
    switches: Sequence[Switch], options: Options, environ: Mapping[str, str], version_of: Callable[[list[str], Mapping[str, str]], str],
) -> str:
    """Return the registry version whose switches launch passes, writing a note on stderr when it is not the version in use."""
    newest = newest_version(switches)
    launcher = options.launcher or [DEFAULT_LAUNCHER]
    if options.claude_version is not None:
        detected = require_version(options.claude_version)
    else:
        detected = parse_version(version_of([*launcher, VERSION_FLAG], environ))
    if detected is None:
        print(f"unharness: {shlex.join(launcher)} {VERSION_FLAG} printed no version; using switches verified at {newest}", file=sys.stderr)
        return newest
    chosen = choose_version(switches, detected)
    if chosen != detected:
        print(f"unharness: claude {detected} is not in the switch registry; using switches verified at {chosen}", file=sys.stderr)
    return chosen


def _passed_switches(switches: Sequence[Switch], options: Options, chosen: str, autocompact_tokens: int | None) -> list[Switch]:
    """Return the switches verified at the chosen version that pass under the options, each holding the value it passes."""
    verified = [switch for switch in switches if chosen in switch.verified]
    return [_with_passed_value(switch, options, autocompact_tokens) for switch in verified if _passes(switch, options)]


def _note_autocompact_unverified(passed: Sequence[Switch], autocompact_tokens: int | None, chosen: str) -> None:
    """Write a note on stderr when --autocompact is given and no switch of it is verified at the chosen version."""
    if autocompact_tokens is not None and not any(switch.option == VALUED_OPTION for switch in passed):
        print(f"unharness: {VALUED_OPTION} has no switch verified at {chosen}; it passes nothing", file=sys.stderr)


def _passes(switch: Switch, options: Options) -> bool:
    """Return whether a switch passes: its default inverted by its given option, or, for the valued option, its default or the option given."""
    if switch.option == VALUED_OPTION:
        return switch.default or _option_given(switch, options)
    return switch.default != _option_given(switch, options)


def _with_passed_value(switch: Switch, options: Options, autocompact_tokens: int | None) -> Switch:
    """Return the switch holding its given value, the size in tokens for the placeholder, when its valued option is given."""
    if switch.option != VALUED_OPTION or not _option_given(switch, options):
        return switch
    return replace(switch, value=autocompact_tokens if switch.given == SIZE_PLACEHOLDER else switch.given)


def _option_given(switch: Switch, options: Options) -> bool:
    return switch.option is not None and getattr(options, OPTION_ATTRIBUTES[switch.option])


def _strip_environment(passed: Sequence[Switch]) -> dict[str, str]:
    return {**{switch.name: switch.value for switch in passed if switch.kind == "env"}, **STAND_DOWN_MARKER}


def _strip_settings(passed: Sequence[Switch]) -> dict:
    return {switch.name: switch.value for switch in passed if switch.kind == "settings"}


def _strip_arguments(prompt_file: Path, passed: Sequence[Switch], settings: dict) -> list[str]:
    flags = [word for switch in passed if switch.kind == "flag" for word in _flag_words(switch)]
    settings_words = [SETTINGS_FLAG, json.dumps(settings, separators=(",", ":"))] if settings else []
    return [SYSTEM_PROMPT_FLAG, str(prompt_file), *flags, *settings_words]


def _merged_settings(owner: dict, strip: dict) -> tuple[dict, list[str]]:
    """Return the owner's keys in their order, then each strip key the owner did not set, with the strip keys the owner set."""
    overridden_keys = [key for key in strip if key in owner]
    return {**owner, **{key: value for key, value in strip.items() if key not in owner}}, overridden_keys


def _note_overridden_settings(keys: list[str]) -> None:
    """Write one note on stderr for each strip key the owner's settings replaced."""
    for key in keys:
        print(f"unharness: your {SETTINGS_FLAG} sets {key}; the strip's value is left out", file=sys.stderr)


def _split_owner_settings(words: list[str], read_file: Callable[[str], str]) -> tuple[list[str], dict]:
    """Return the words without the owner's --settings, and its object, empty when the owner passed none."""
    rest: list[str] = []
    values: list[str] = []
    index = 0
    while index < len(words):
        word = words[index]
        if word == SETTINGS_FLAG:
            if index + 1 == len(words):
                raise UnharnessError(f"{SETTINGS_FLAG} after -- needs a value")
            values.append(words[index + 1])
            index += 2
            continue
        if word.startswith(SETTINGS_FLAG + "="):
            values.append(word.removeprefix(SETTINGS_FLAG + "="))
        else:
            rest.append(word)
        index += 1
    if len(values) > 1:
        raise UnharnessError(f"pass {SETTINGS_FLAG} once after --")
    return rest, _owner_object(values[0], read_file) if values else {}


def _owner_object(value: str, read_file: Callable[[str], str]) -> dict:
    """Return the object in the value read as JSON text when it opens with a brace, else as a file path."""
    text = value if value.lstrip().startswith("{") else _file_text(value, read_file)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if not isinstance(parsed, dict):
        raise UnharnessError(f"{SETTINGS_FLAG} {value} is not a JSON object")
    return parsed


def _file_text(path: str, read_file: Callable[[str], str]) -> str:
    try:
        return read_file(path)
    except (OSError, UnicodeDecodeError) as error:
        reason = error.strerror if isinstance(error, OSError) and error.strerror else str(error)
        raise UnharnessError(f"{SETTINGS_FLAG} file {path} cannot be read: {reason}") from error


def _flag_words(switch: Switch) -> list[str]:
    return [switch.name] if switch.value is None else [switch.name, switch.value]


def _write_prompt(prompt: str, cache_home: Path) -> Path:
    folder = cache_home / CACHE_FOLDER
    folder.mkdir(mode=FOLDER_MODE, parents=True, exist_ok=True)
    path = folder / f"{sha256(prompt.encode()).hexdigest()}.md"
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, FILE_MODE), "w", encoding=TEXT_ENCODING) as file:
        file.write(prompt)
    return path
