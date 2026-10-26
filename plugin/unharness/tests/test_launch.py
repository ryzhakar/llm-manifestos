import json
import os
import pty
import shlex
import stat
from hashlib import sha256
from pathlib import Path

import pytest
from unharness.config import UnharnessError
from unharness.launch import Options, cache_home, launch, reopen_terminal, terminal_device, version_output
from unharness.switches import parse_switches, shipped_switches

DEFAULT_ENVIRONMENT = [
    "CLAUDE_CODE_ATTRIBUTION_HEADER=0",
    "CLAUDE_CODE_DISABLE_CLAUDE_MDS=1",
    "CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1",
    "CLAUDE_CODE_DISABLE_AUTO_MEMORY=1",
    "CLAUDE_CODE_SILENT_TURN_REMINDER=0",
    "CLAUDE_CODE_TODO_REMINDER_MODE=off",
    "CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off",
    "UNHARNESS=1",
]
DEFAULT_SETTINGS = {
    "includeGitInstructions": False,
    "attribution": {"commit": "", "pr": ""},
    "autoMemoryEnabled": False,
    "outputStyle": "default",
}
PROMPT = "You are bound.\n"
TERMINAL = "/dev/ttys042"
COMMAND_OF_3_6_1 = (
    "env CLAUDE_CODE_ATTRIBUTION_HEADER=0 CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1"
    " CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 CLAUDE_CODE_SILENT_TURN_REMINDER=0 CLAUDE_CODE_TODO_REMINDER_MODE=off"
    " CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off UNHARNESS=1 claude --system-prompt-file {prompt_file}"
    " --disallowedTools WebSearch --settings"
    " '{{\"includeGitInstructions\":false,\"attribution\":{{\"commit\":\"\",\"pr\":\"\"}},"
    "\"autoMemoryEnabled\":false,\"outputStyle\":\"default\"{hooks}}}' <{terminal}\n"
)


TESTED_VERSION = "2.1.309"


def never(*_):
    raise AssertionError("nothing may run")


def at_tested(*_) -> str:
    return f"{TESTED_VERSION} (Claude Code)\n"


def cached_prompt(cache_home: Path, prompt: str = PROMPT) -> Path:
    return cache_home / "unharness" / f"{sha256(prompt.encode()).hexdigest()}.md"


def printed_command(options: Options, cache_home: Path, capsys) -> list[str]:
    assert launch(PROMPT, options, shipped_switches(), {}, cache_home, TERMINAL, never, never, at_tested) == 0
    line = capsys.readouterr().out
    assert line.endswith(f" <{TERMINAL}\n") and line.count("\n") == 1
    return shlex.split(line.removesuffix(f" <{TERMINAL}\n"))


def test_without_a_launcher_it_prints_the_command_for_claude_and_runs_nothing(tmp_path, capsys):
    command = printed_command(Options(False, False, False, []), tmp_path, capsys)

    settings = json.dumps(DEFAULT_SETTINGS, separators=(",", ":"))
    assert command == [
        "env", *DEFAULT_ENVIRONMENT,
        "claude", "--system-prompt-file", str(cached_prompt(tmp_path)),
        "--disallowedTools", "WebSearch", "--settings", settings,
    ]


def test_the_prompt_is_cached_under_its_sha256_with_a_private_file_and_folder(tmp_path):
    previous_umask = os.umask(0)
    try:
        launch(PROMPT, Options(False, False, False, []), shipped_switches(), {}, tmp_path, TERMINAL, never, never, at_tested)
    finally:
        os.umask(previous_umask)

    file = cached_prompt(tmp_path)
    assert file.read_text() == PROMPT
    assert stat.S_IMODE(file.stat().st_mode) == 0o600
    assert stat.S_IMODE(file.parent.stat().st_mode) == 0o700


def test_an_empty_prompt_stops_before_anything_is_written(tmp_path):
    with pytest.raises(UnharnessError, match="^the prompt is empty$"):
        launch(" \n", Options(False, False, False, []), shipped_switches(), {}, tmp_path, TERMINAL, never, never, at_tested)

    assert list(tmp_path.iterdir()) == []


def settings_of(command: list[str]) -> dict:
    return json.loads(command[command.index("--settings") + 1])


def test_keep_claude_md_omits_only_the_claude_md_variable(tmp_path, capsys):
    command = printed_command(Options(True, False, False, []), tmp_path, capsys)

    assert command[1:command.index("claude")] == [name for name in DEFAULT_ENVIRONMENT if "CLAUDE_MDS" not in name]


def test_keep_web_search_drops_the_disallow(tmp_path, capsys):
    command = printed_command(Options(False, True, False, []), tmp_path, capsys)

    assert "--disallowedTools" not in command and "WebSearch" not in command


def test_no_hooks_adds_disable_all_hooks_to_the_settings(tmp_path, capsys):
    command = printed_command(Options(False, False, True, []), tmp_path, capsys)

    assert settings_of(command) == {**DEFAULT_SETTINGS, "disableAllHooks": True}


def test_all_three_flags_combine(tmp_path, capsys):
    command = printed_command(Options(True, True, True, []), tmp_path, capsys)

    assert command == [
        "env", *[name for name in DEFAULT_ENVIRONMENT if "CLAUDE_MDS" not in name],
        "claude", "--system-prompt-file", str(cached_prompt(tmp_path)),
        "--settings", json.dumps({**DEFAULT_SETTINGS, "disableAllHooks": True}, separators=(",", ":")),
    ]


def test_with_a_launcher_it_reopens_stdin_then_executes_the_launcher_with_the_stripped_environment(tmp_path, capsys):
    calls = []
    status = launch(
        PROMPT, Options(False, False, False, ["fake", "extra"]), shipped_switches(), {"KEPT": "yes"}, tmp_path, TERMINAL,
        lambda device: calls.append(("reopen", device)),
        lambda argv, env: calls.append((argv, env)) or 7,
        at_tested,
    )

    assert status == 7
    assert capsys.readouterr().out == ""
    assert calls[0] == ("reopen", TERMINAL)
    argv, env = calls[1]
    assert argv == [
        "fake", "extra", "--system-prompt-file", str(cached_prompt(tmp_path)),
        "--disallowedTools", "WebSearch", "--settings", json.dumps(DEFAULT_SETTINGS, separators=(",", ":")),
    ]
    assert env == {"KEPT": "yes", **dict(pair.split("=") for pair in DEFAULT_ENVIRONMENT)}


def test_stdin_is_redirected_onto_the_device_it_is_given(tmp_path):
    opened, redirects = [], []
    terminal = tmp_path / "terminal"
    terminal.write_text("")

    def open_device(device):
        opened.append(device)
        return terminal.open()

    reopen_terminal(TERMINAL, lambda: False, open_device, lambda source, target: redirects.append((type(source), target)))

    assert (opened, redirects) == ([TERMINAL], [(int, 0)])


def test_without_a_terminal_stdin_stays_as_it_is():
    def no_terminal(device):
        raise OSError("no controlling terminal")

    reopen_terminal(TERMINAL, lambda: False, no_terminal, lambda *_: pytest.fail("stdin must not move"))


def test_stdin_that_is_already_a_terminal_is_left_alone():
    def must_not_open(device):
        raise AssertionError("the terminal must not be opened")

    reopen_terminal(TERMINAL, lambda: True, must_not_open, lambda *_: pytest.fail("stdin must not move"))


@pytest.fixture
def pseudo_terminal():
    master, slave = pty.openpty()
    read_end, write_end = os.pipe()
    yield slave, write_end
    for descriptor in (master, slave, read_end, write_end):
        os.close(descriptor)


def test_the_device_is_the_one_stdout_is_on(pseudo_terminal):
    terminal, pipe = pseudo_terminal

    assert terminal_device((terminal, pipe)) == os.ttyname(terminal)


def test_the_device_is_the_one_stderr_is_on_when_stdout_is_not_a_terminal(pseudo_terminal):
    terminal, pipe = pseudo_terminal

    assert terminal_device((pipe, terminal)) == os.ttyname(terminal)


def test_the_device_is_dev_tty_when_neither_output_is_a_terminal(pseudo_terminal):
    _, pipe = pseudo_terminal

    assert terminal_device((pipe, pipe)) == "/dev/tty"


def test_the_cache_is_dot_cache_in_home_unless_xdg_cache_home_is_set_and_not_empty(tmp_path):
    assert cache_home({}, tmp_path) == tmp_path / ".cache"
    assert cache_home({"XDG_CACHE_HOME": ""}, tmp_path) == tmp_path / ".cache"
    assert cache_home({"XDG_CACHE_HOME": "/elsewhere"}, tmp_path) == Path("/elsewhere")


@pytest.mark.parametrize(("options", "hooks"), [
    (Options(False, False, False, []), ""),
    (Options(False, False, True, []), ',"disableAllHooks":true'),
])
def test_the_printed_command_equals_the_one_3_6_1_printed(options, hooks, tmp_path, capsys):
    assert launch(PROMPT, options, shipped_switches(), {}, tmp_path, TERMINAL, never, never, at_tested) == 0

    expected = COMMAND_OF_3_6_1.format(prompt_file=cached_prompt(tmp_path), hooks=hooks, terminal=TERMINAL)
    assert capsys.readouterr().out == expected


def entry(**overrides) -> dict:
    return {
        "name": "SWITCH_ONE", "kind": "env", "value": "1", "removes": "Some text",
        "documented": True, "control": True, "verified": ["2.1.309"], "default": True, "option": None,
        **overrides,
    }


def printed_command_of(entries: list[dict], options: Options, tmp_path, capsys) -> list[str]:
    launch(PROMPT, options, parse_switches(json.dumps(entries)), {}, tmp_path, TERMINAL, never, never, at_tested)
    return shlex.split(capsys.readouterr().out.removesuffix(f" <{TERMINAL}\n"))


def test_launch_composes_env_flags_and_settings_from_the_registry_in_its_order(tmp_path, capsys):
    command = printed_command_of([
        entry(name="FIRST", value="a"),
        entry(name="--bare", kind="flag", value=None, removes="Second"),
        entry(name="key", kind="settings", value={"nested": [1]}, removes="Third"),
        entry(name="--valued", kind="flag", value="v", removes="Fourth"),
        entry(name="SECOND", value="b", removes="Fifth"),
        entry(name="other", kind="settings", value=False, removes="Sixth"),
    ], Options(False, False, False, []), tmp_path, capsys)

    assert command == [
        "env", "FIRST=a", "SECOND=b", "UNHARNESS=1",
        "claude", "--system-prompt-file", str(cached_prompt(tmp_path)),
        "--bare", "--valued", "v", "--settings", '{"key":{"nested":[1]},"other":false}',
    ]


def test_launch_leaves_out_settings_when_no_settings_entry_passes(tmp_path, capsys):
    command = printed_command_of([entry()], Options(False, False, False, []), tmp_path, capsys)

    assert "--settings" not in command


def test_an_option_inverts_the_default_of_the_entry_it_names(tmp_path, capsys):
    entries = [
        entry(name="STRIPPED", option="--keep-claude-md"),
        entry(name="KEPT", removes="Other", default=False, option="--keep-web-search"),
        entry(name="UNNAMED", removes="Third", default=False),
    ]

    plain = printed_command_of(entries, Options(False, False, False, []), tmp_path, capsys)
    inverted = printed_command_of(entries, Options(True, True, False, []), tmp_path, capsys)

    assert plain[1:-3] == ["STRIPPED=1", "UNHARNESS=1"]
    assert inverted[1:-3] == ["KEPT=1", "UNHARNESS=1"]


def test_launch_passes_only_the_entries_verified_at_the_newest_registry_version(tmp_path, capsys):
    command = printed_command_of([
        entry(name="OLD", verified=["2.1.300"]),
        entry(name="CURRENT", removes="Other", verified=["2.1.300", "2.1.309"]),
    ], Options(False, False, False, []), tmp_path, capsys)

    assert command[1:-3] == ["CURRENT=1", "UNHARNESS=1"]


REGISTRY_ENTRIES = [
    entry(name="OLDEST", verified=["2.1.300"]),
    entry(name="MIDDLE", removes="Two", verified=["2.1.300", "2.1.309"]),
    entry(name="NEWEST", removes="Three", verified=["2.1.309", "2.1.320"]),
]
NO_VERSION_NOTE = "unharness: {launcher} --version printed no version; using switches verified at {newest}\n"
UNKNOWN_VERSION_NOTE = "unharness: claude {detected} is not in the switch registry; using switches verified at {chosen}\n"


def reported(output: str):
    return lambda argv, environ: output


def passed_and_noted(version_of, tmp_path, capsys, options=Options(False, False, False, ["fakeclaude"])) -> tuple[list[str], str]:
    """Return the variables launch passes from REGISTRY_ENTRIES, and what it wrote on stderr."""
    environments = []
    launch(PROMPT, options, parse_switches(json.dumps(REGISTRY_ENTRIES)), {}, tmp_path, TERMINAL, lambda device: None,
           lambda argv, env: environments.append(env) or 0, version_of)
    passed = [f"{name}={value}" for name, value in environments[0].items() if name != "UNHARNESS"]
    return passed, capsys.readouterr().err


def test_the_version_is_asked_of_the_launcher_launch_runs(tmp_path):
    asked = []

    launch(PROMPT, Options(False, False, False, ["claude@meta", "--model", "opus"]), shipped_switches(), {"KEPT": "yes"},
           tmp_path, TERMINAL, lambda device: None, lambda argv, env: 0,
           lambda argv, environ: asked.append((argv, environ)) or at_tested())

    assert asked == [(["claude@meta", "--model", "opus", "--version"], {"KEPT": "yes"})]


def test_without_a_launcher_the_version_is_asked_of_claude(tmp_path):
    asked = []

    launch(PROMPT, Options(False, False, False, []), shipped_switches(), {}, tmp_path, TERMINAL, never, never,
           lambda argv, environ: asked.append(argv) or at_tested())

    assert asked == [["claude", "--version"]]


def test_a_version_on_a_later_line_is_the_one_taken(tmp_path, capsys):
    passed, noted = passed_and_noted(reported("shell banner\n2.1.309 (Claude Code)\n3.0.0\n"), tmp_path, capsys)

    assert (passed, noted) == (["MIDDLE=1", "NEWEST=1"], "")


@pytest.mark.parametrize("output", ["", "no digits here\n", "v2.1.309\n"])
def test_a_launcher_that_prints_no_version_gets_the_newest_registry_version_and_a_note(tmp_path, capsys, output):
    passed, noted = passed_and_noted(reported(output), tmp_path, capsys, Options(False, False, False, ["fakeclaude", "--flag"]))

    assert passed == ["NEWEST=1"]
    assert noted == NO_VERSION_NOTE.format(launcher="fakeclaude --flag", newest="2.1.320")


def test_without_a_launcher_the_note_names_claude(tmp_path, capsys):
    launch(PROMPT, Options(False, False, False, []), parse_switches(json.dumps(REGISTRY_ENTRIES)), {}, tmp_path, TERMINAL,
           never, never, reported(""))
    noted = capsys.readouterr().err

    assert noted == NO_VERSION_NOTE.format(launcher="claude", newest="2.1.320")


def test_claude_version_replaces_the_run_and_the_note(tmp_path, capsys):
    passed, noted = passed_and_noted(never, tmp_path, capsys, Options(False, False, False, ["claude@meta"], "2.1.300"))

    assert (passed, noted) == (["OLDEST=1", "MIDDLE=1"], "")


@pytest.mark.parametrize("value", ["2.1", "v2.1.309", "2.1.309 ", "2.1.309-beta", ""])
def test_a_claude_version_that_is_not_x_y_z_stops_launch_before_anything_is_written(tmp_path, value):
    with pytest.raises(UnharnessError, match=f"^--claude-version takes X.Y.Z, got {value}$"):
        launch(PROMPT, Options(False, False, False, [], value), shipped_switches(), {}, tmp_path, TERMINAL, never, never, never)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(("detected", "passed", "chosen"), [
    ("2.1.300", ["OLDEST=1", "MIDDLE=1"], None),
    ("2.1.309", ["MIDDLE=1", "NEWEST=1"], None),
    ("2.1.320", ["NEWEST=1"], None),
    ("2.1.312", ["MIDDLE=1", "NEWEST=1"], "2.1.309"),
    ("2.1.400", ["NEWEST=1"], "2.1.320"),
    ("2.1.299", ["OLDEST=1", "MIDDLE=1"], "2.1.300"),
    ("1.0.0", ["OLDEST=1", "MIDDLE=1"], "2.1.300"),
    ("2.1.1000", ["NEWEST=1"], "2.1.320"),
    ("2.1.99", ["OLDEST=1", "MIDDLE=1"], "2.1.300"),
])
def test_launch_chooses_the_exact_version_else_the_nearest_lower_else_the_oldest_and_says_so(tmp_path, capsys, detected, passed, chosen):
    passed_by_launch, noted = passed_and_noted(reported(f"{detected} (Claude Code)\n"), tmp_path, capsys)

    assert passed_by_launch == passed
    assert noted == ("" if chosen is None else UNKNOWN_VERSION_NOTE.format(detected=detected, chosen=chosen))


def test_a_program_on_the_path_is_run_directly_and_its_stdout_comes_back(tmp_path):
    program = stub_program(tmp_path, "stub", 'echo "$@"')

    assert version_output([program.name, "--version"], {"PATH": str(tmp_path)}) == "--version\n"


def test_a_program_off_the_path_is_run_through_the_shell_named_by_shell(tmp_path):
    shell = stub_program(tmp_path, "shell", 'echo "$1 | $2"')

    assert version_output(["claude@meta", "--version"], {"PATH": "", "SHELL": str(shell)}) == "-ic | claude@meta --version\n"


def test_a_program_that_cannot_start_gives_empty_output(tmp_path):
    broken = tmp_path / "broken"
    broken.write_text("#!/nonexistent/interpreter\n")
    broken.chmod(0o755)

    assert version_output([broken.name, "--version"], {"PATH": str(tmp_path)}) == ""


def test_a_program_that_outlasts_the_timeout_gives_empty_output(tmp_path, monkeypatch):
    stub_program(tmp_path, "slow", "exec sleep 5")
    monkeypatch.setattr("unharness.launch.VERSION_TIMEOUT_SECONDS", 0.2)

    assert version_output(["slow"], {"PATH": str(tmp_path)}) == ""


def stub_program(folder: Path, name: str, body: str) -> Path:
    path = folder / name
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)
    return path


def launched_with(owner_words: list[str], tmp_path, capsys, read_file=never) -> tuple[list[str], str]:
    """Return the command launch executes for a launcher given owner_words, and what it wrote on stderr."""
    commands = []
    launch(
        PROMPT, Options(False, False, False, ["fake", *owner_words]), shipped_switches(), {}, tmp_path, TERMINAL,
        lambda device: None, lambda argv, env: commands.append(argv) or 0, at_tested, read_file,
    )
    return commands[0], capsys.readouterr().err


def test_two_owner_settings_flags_stop_launch_before_the_launcher_runs(tmp_path, capsys):
    with pytest.raises(UnharnessError, match="^pass --settings once after --$"):
        launched_with(["--settings", "{}", "--settings={}"], tmp_path, capsys)


@pytest.mark.parametrize("owner_words", [["--settings", '{"model":"opus"}'], ['--settings={"model":"opus"}']])
def test_an_owner_settings_flag_leaves_the_arguments_and_passes_one_merged_settings(owner_words, tmp_path, capsys):
    argv, err = launched_with(["--print", *owner_words, "hello"], tmp_path, capsys)

    assert argv[:2] == ["fake", "--print"] and argv[2] == "hello"
    assert argv.count("--settings") == 1
    assert settings_of(argv) == {"model": "opus", **DEFAULT_SETTINGS}
    assert err == ""
