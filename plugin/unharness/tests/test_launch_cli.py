import json
import os
import pty
import shlex
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest
from helpers import write

PROMPT = "You are bound.\n"
FAKE_LAUNCHER = '#!/bin/sh\nprintf "%s\\n" "$@" > "$DUMP/argv"\nenv > "$DUMP/env"\nexit 3\n'
VERSIONED_LAUNCHER = (
    '#!/bin/sh\ncase "$*" in\n*--version) printf "%s\\n" "$VERSION_OUTPUT"; exit 0;;\nesac\n'
    'printf "%s\\n" "$@" > "$DUMP/argv"\nenv > "$DUMP/env"\nexit 3\n'
)
VERSIONED_SHELL = (
    '#!/bin/sh\nprintf "%s\\n" "$2" >> "$DUMP/shell-log"\ncase "$2" in\n*--version*) printf "banner\\n2.1.312 (Claude Code)\\n";;\n*) exit 5;;\nesac\n'
)
FAKE_SHELL = '#!/bin/sh\nprintf "%s\\n" "$@" > "$DUMP/shell-argv"\nexit 5\n'


def run_launch(tmp_path: Path, *arguments: str, stdin: str = "", **extra_env: str) -> subprocess.CompletedProcess:
    env = {
        "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin", "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "DUMP": str(tmp_path), **extra_env,
    }
    return subprocess.run(
        [sys.executable, "-m", "unharness.cli", "launch", *arguments],
        input=stdin, capture_output=True, text=True, env=env,
    )


def fake_launcher(tmp_path: Path, name: str = "fakeclaude") -> None:
    script = write(tmp_path / "bin" / name, FAKE_LAUNCHER)
    script.chmod(0o755)


def cached(tmp_path: Path, prompt: str = PROMPT) -> Path:
    return tmp_path / "cache" / "unharness" / f"{sha256(prompt.encode()).hexdigest()}.md"


def test_a_launcher_on_the_path_replaces_the_process_and_its_status_comes_back(tmp_path):
    fake_launcher(tmp_path)

    run = run_launch(tmp_path, PROMPT, "--", "fakeclaude", "extra", "--flag")

    assert run.returncode == 3
    argv = (tmp_path / "argv").read_text().splitlines()
    assert argv[:2] == ["extra", "--flag"]
    assert argv[2:5] == ["--system-prompt-file", str(cached(tmp_path)), "--disallowedTools"]
    assert json.loads(argv[-1])["outputStyle"] == "default"
    launcher_environment = (tmp_path / "env").read_text().splitlines()
    assert "UNHARNESS=1" in launcher_environment
    assert "CLAUDE_CODE_DISABLE_CLAUDE_MDS=1" in launcher_environment


def test_the_prompt_comes_from_stdin_when_no_argument_gives_it(tmp_path):
    fake_launcher(tmp_path)

    run = run_launch(tmp_path, "--keep-claude-md", "--", "fakeclaude", stdin=PROMPT)

    assert run.returncode == 3
    assert cached(tmp_path).read_text() == PROMPT
    assert "CLAUDE_CODE_DISABLE_CLAUDE_MDS=1" not in (tmp_path / "env").read_text().splitlines()


def test_an_empty_prompt_fails_in_one_line_with_status_1(tmp_path):
    run = run_launch(tmp_path, stdin="")

    assert (run.returncode, run.stdout, run.stderr) == (1, "", "unharness: the prompt is empty\n")


def test_without_a_launcher_the_verb_prints_the_command_and_runs_nothing(tmp_path):
    run = run_launch(tmp_path, PROMPT)

    assert run.returncode == 0
    line = shlex.split(run.stdout.removesuffix(" </dev/tty\n"))
    assert line[0] == "env" and "claude" in line and str(cached(tmp_path)) in line


def test_a_launcher_not_on_the_path_runs_through_the_shell_with_the_quoted_command(tmp_path):
    shell = write(tmp_path / "fake-shell", FAKE_SHELL)
    shell.chmod(0o755)

    run = run_launch(tmp_path, PROMPT, "--", "claude@meta", "--model", "opus", SHELL=str(shell))

    assert run.returncode == 5
    flag, command = (tmp_path / "shell-argv").read_text().split("\n", 1)
    assert flag == "-ic"
    assert shlex.split(command)[:3] == ["claude@meta", "--model", "opus"]
    assert shlex.split(command)[3:5] == ["--system-prompt-file", str(cached(tmp_path))]


@pytest.mark.skipif(not Path("/bin/bash").exists(), reason="needs /bin/bash")
def test_a_shell_function_defined_in_the_interactive_rc_file_is_the_launcher(tmp_path):
    write(tmp_path / "home" / ".bashrc", f'claude@meta() {{ printf "%s\\n" "$@" > {tmp_path}/function-argv; return 9; }}\n')

    run = run_launch(tmp_path, PROMPT, "--", "claude@meta", "--model", "opus", SHELL="/bin/bash", HOME=str(tmp_path / "home"))

    assert run.returncode == 9
    assert (tmp_path / "function-argv").read_text().splitlines()[:3] == ["--model", "opus", "--system-prompt-file"]


def test_without_a_prompt_and_with_a_terminal_on_stdin_it_stops_with_a_message(tmp_path):
    master, slave = pty.openpty()
    try:
        run = subprocess.run(
            [sys.executable, "-m", "unharness.cli", "launch", "--", "fakeclaude"],
            stdin=slave, capture_output=True, text=True, timeout=20,
            env={"PATH": "/usr/bin:/bin", "XDG_CACHE_HOME": str(tmp_path / "cache")},
        )
    finally:
        os.close(master)
        os.close(slave)

    assert (run.returncode, run.stdout) == (1, "")
    assert run.stderr == "unharness: no prompt: pass PROMPT or pipe unharness prompt\n"


def versioned_launcher(tmp_path: Path, name: str = "fakeclaude") -> None:
    write(tmp_path / "bin" / name, VERSIONED_LAUNCHER).chmod(0o755)


def test_a_launcher_on_the_path_is_asked_for_its_version_and_a_version_off_the_registry_gets_the_nearest_lower_set(tmp_path):
    versioned_launcher(tmp_path)

    run = run_launch(tmp_path, PROMPT, "--", "fakeclaude", "--flag", VERSION_OUTPUT="2.1.312 (Claude Code)")

    assert run.returncode == 3
    assert run.stderr == "unharness: claude 2.1.312 is not in the switch registry; using switches verified at 2.1.309\n"
    assert (tmp_path / "argv").read_text().splitlines()[:2] == ["--flag", "--system-prompt-file"]
    assert "CLAUDE_CODE_DISABLE_CLAUDE_MDS=1" in (tmp_path / "env").read_text().splitlines()


def test_a_launcher_on_the_path_that_prints_the_registry_version_gets_no_note(tmp_path):
    versioned_launcher(tmp_path)

    run = run_launch(tmp_path, PROMPT, "--", "fakeclaude", VERSION_OUTPUT="2.1.309 (Claude Code)")

    assert (run.returncode, run.stderr) == (3, "")


def test_a_launcher_that_prints_nothing_gets_the_newest_set_and_a_note(tmp_path):
    versioned_launcher(tmp_path)

    run = run_launch(tmp_path, PROMPT, "--", "fakeclaude", VERSION_OUTPUT="")

    assert run.returncode == 3
    assert run.stderr == "unharness: fakeclaude --version printed no version; using switches verified at 2.1.309\n"


def test_a_launcher_off_the_path_is_asked_for_its_version_through_the_interactive_shell(tmp_path):
    shell = write(tmp_path / "fake-shell", VERSIONED_SHELL)
    shell.chmod(0o755)

    run = run_launch(tmp_path, PROMPT, "--", "claude@meta", "--model", "opus", SHELL=str(shell))

    assert run.returncode == 5
    assert (tmp_path / "shell-log").read_text().splitlines()[0] == "claude@meta --model opus --version"
    assert run.stderr == "unharness: claude 2.1.312 is not in the switch registry; using switches verified at 2.1.309\n"


def test_claude_version_runs_nothing_to_find_the_version(tmp_path):
    fake_launcher(tmp_path)

    run = run_launch(tmp_path, PROMPT, "--claude-version", "2.1.309", "--", "fakeclaude")

    assert (run.returncode, run.stderr) == (3, "")
    assert (tmp_path / "argv").read_text().splitlines()[0] == "--system-prompt-file"


def test_a_malformed_claude_version_fails_in_one_line_with_status_1(tmp_path):
    run = run_launch(tmp_path, PROMPT, "--claude-version", "latest", "--", "fakeclaude")

    assert (run.returncode, run.stdout, run.stderr) == (1, "", "unharness: --claude-version takes X.Y.Z, got latest\n")


def test_a_size_out_of_bounds_fails_in_one_line_with_status_1_and_runs_nothing(tmp_path):
    fake_launcher(tmp_path)

    run = run_launch(tmp_path, PROMPT, "--autocompact", "1001k", "--", "fakeclaude")

    message = "unharness: --autocompact takes a whole number of thousands of tokens from 100 to 1000, such as 500k; got 1001k\n"
    assert (run.returncode, run.stdout, run.stderr) == (1, "", message)
    assert not (tmp_path / "cache").exists() and not (tmp_path / "argv").exists()


@pytest.mark.parametrize(("sizes", "status"), [(["99", "500k"], 3), (["500k", "99"], 1)])
def test_the_last_autocompact_given_is_the_one_that_counts(sizes, status, tmp_path):
    fake_launcher(tmp_path)

    run = run_launch(tmp_path, PROMPT, *(word for size in sizes for word in ("--autocompact", size)), "--claude-version", "2.1.309", "--", "fakeclaude")

    assert run.returncode == status
