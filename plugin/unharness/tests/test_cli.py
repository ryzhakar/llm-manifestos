import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest
from helpers import write
from unharness.compile import compile_prompt, stack_block, stack_view
from unharness.config import load
from unharness.resolve import resolve_stack

CONFIG = "you:\n  - name: dry\n    purpose: one home\n  - name: write-well\n    source: skill agent-conduct:write-well\n"


@pytest.fixture
def project(tmp_path) -> Path:
    folder = tmp_path / "project"
    write(folder / ".manifestos/config.yaml", CONFIG)
    return folder


def unharness(login: Path, *arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "unharness.cli", *arguments],
        capture_output=True, text=True, cwd=cwd, env={"CLAUDE_CONFIG_DIR": str(login)},
    )


def documents_of(project: Path, login: Path):
    config = load(project / ".manifestos/config.yaml")
    return resolve_stack(config.you, config.directory, config.registry, login)


def test_the_stack_verb_prints_the_stack_block_and_the_constitution_of_the_config(login, project, tmp_path):
    run = unharness(login, "stack", "--config", str(project / ".manifestos/config.yaml"), cwd=tmp_path)

    assert run.returncode == 0
    assert run.stdout == stack_view(documents_of(project, login)) + "\n"


def write_session_files(project: Path, login: Path) -> None:
    stack = stack_block(documents_of(project, login))
    write(project / ".manifestos/interplay.md", f"{stack}\n\n<interplay>\nAgree.\n</interplay>\n")
    write(project / ".manifestos/commitments.md", f"{stack}\n\n<commitments>\nI must, and I will.\n</commitments>\n")


def test_the_prompt_verb_prints_the_compiled_prompt_with_the_shipped_preamble(login, project, tmp_path):
    write_session_files(project, login)
    documents = documents_of(project, login)
    shipped_preamble = files("unharness").joinpath("preamble.md").read_text()

    run = unharness(login, "prompt", "--config", str(project / ".manifestos/config.yaml"), cwd=tmp_path)

    assert run.returncode == 0
    assert run.stdout == compile_prompt(
        documents, shipped_preamble,
        (project / ".manifestos/interplay.md").read_text(), (project / ".manifestos/commitments.md").read_text(),
    ) + "\n"
    assert run.stdout.startswith(f"<harness>\n{shipped_preamble.strip()}\n</harness>\n\n<constitution>\n")
    assert run.stdout.endswith("<commitments>\nI must, and I will.\n</commitments>\n")


def test_a_project_preamble_replaces_the_shipped_one(login, project):
    write_session_files(project, login)
    write(project / ".manifestos/preamble.md", "My own preamble.\n")

    run = unharness(login, "prompt", cwd=project)

    assert run.stdout.startswith("<harness>\nMy own preamble.\n</harness>\n")


def test_a_failure_prints_one_line_on_stderr_and_exits_1_with_nothing_on_stdout(login, project):
    run = unharness(login, "prompt", cwd=project)

    assert (run.returncode, run.stdout) == (1, "")
    assert run.stderr == "unharness: .manifestos/interplay.md is missing; run /compile-commitments\n"


@pytest.mark.parametrize("verb", ["prompt", "stack"])
def test_an_empty_stack_stops_every_verb(login, tmp_path, verb):
    write(tmp_path / ".manifestos/config.yaml", "you:\n")

    run = unharness(login, verb, cwd=tmp_path)

    assert (run.returncode, run.stdout, run.stderr) == (1, "", "unharness: the stack is empty\n")


C_LOCALE = {"LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0", "PYTHONIOENCODING": "utf-8"}


def test_every_read_decodes_utf_8_whatever_the_locale(login, tmp_path):
    write(tmp_path / "rules.md", "Café rules\n")
    config = write(tmp_path / ".manifestos/config.yaml", "you:\n  - name: rules\n    purpose: café\n    source: file rules.md\n")

    stack = subprocess.run(
        [sys.executable, "-m", "unharness.cli", "stack", "--config", str(config)],
        capture_output=True, env={"CLAUDE_CONFIG_DIR": str(login), **C_LOCALE},
    )
    stack_block = stack.stdout.decode().split("</stack>")[0]
    write(tmp_path / ".manifestos/interplay.md", stack_block + "</stack>\n\n<interplay>\nCafé\n</interplay>\n")
    write(tmp_path / ".manifestos/commitments.md", stack_block + "</stack>\n\n<commitments>\nok\n</commitments>\n")
    prompt = subprocess.run(
        [sys.executable, "-m", "unharness.cli", "prompt", "--config", str(config)],
        capture_output=True, env={"CLAUDE_CONFIG_DIR": str(login), **C_LOCALE},
    )

    assert stack.returncode == 0, stack.stderr
    assert "Café rules" in stack.stdout.decode()
    assert prompt.returncode == 0, prompt.stderr
    assert "<interplay>\nCafé\n</interplay>" in prompt.stdout.decode()


def test_the_cached_prompt_is_utf_8_whatever_the_locale(tmp_path):
    script = (
        "from pathlib import Path\n"
        "from unharness.launch import Options, launch\n"
        "from unharness.switches import shipped_switches\n"
        f"launch('Caf\\u00e9\\n', Options(False, False, False, []), shipped_switches(), {{}}, Path({str(tmp_path)!r}), '/dev/tty', None, None, lambda *_: '2.1.309')\n"
    )

    run = subprocess.run([sys.executable, "-c", script], capture_output=True, env=C_LOCALE)

    assert run.returncode == 0, run.stderr
    [cached] = (tmp_path / "unharness").iterdir()
    assert cached.read_bytes() == "Café\n".encode()


def test_the_shipped_preamble_stays_within_25_lines_and_names_no_tool():
    preamble = files("unharness").joinpath("preamble.md").read_text(encoding="utf-8")

    assert len(preamble.splitlines()) <= 25
    assert "unharness" not in preamble.lower() and "compil" not in preamble.lower()


def write_minified_files(project: Path, login: Path) -> None:
    stack = stack_block(documents_of(project, login))
    write(project / ".manifestos/interplay.min.md", f"{stack}\n\n<interplay>\nAgree, briefly.\n</interplay>\n")
    write(project / ".manifestos/commitments.min.md", f"{stack}\n\n<commitments>\nI must, briefly.\n</commitments>\n")


def test_the_minified_flag_reads_the_condensed_pair_in_place_of_the_full_pair(login, project):
    write_session_files(project, login)
    write_minified_files(project, login)

    run = unharness(login, "prompt", "--minified", cwd=project)

    assert run.returncode == 0, run.stderr
    assert run.stdout.endswith("<interplay>\nAgree, briefly.\n</interplay>\n\n<commitments>\nI must, briefly.\n</commitments>\n")
    assert "Agree.\n" not in run.stdout


def test_a_missing_minified_file_stops_the_prompt_and_names_the_minified_file(login, project):
    write_session_files(project, login)
    write_minified_files(project, login)
    (project / ".manifestos/commitments.min.md").unlink()

    run = unharness(login, "prompt", "--minified", cwd=project)

    assert (run.returncode, run.stdout) == (1, "")
    assert run.stderr == "unharness: .manifestos/commitments.min.md is missing; run /compile-commitments\n"


def test_a_minified_file_made_for_another_stack_is_stale_though_the_full_pair_is_current(login, project):
    write_session_files(project, login)
    write_minified_files(project, login)
    write(project / ".manifestos/interplay.min.md", f"<stack>\ndry {'0' * 64} one home\n</stack>\n\n<interplay>\nOld.\n</interplay>\n")

    run = unharness(login, "prompt", "--minified", cwd=project)

    assert (run.returncode, run.stdout) == (1, "")
    assert run.stderr == "unharness: .manifestos/interplay.min.md is stale (changed: dry, write-well); run /compile-commitments\n"


def test_the_full_mode_ignores_the_minified_files_even_when_they_are_stale_or_absent(login, project):
    write_session_files(project, login)
    write(project / ".manifestos/interplay.min.md", "<stack>\nstale\n</stack>\n\n<interplay>\nOld.\n</interplay>\n")

    run = unharness(login, "prompt", cwd=project)

    assert run.returncode == 0, run.stderr
    assert "Old." not in run.stdout and "Agree.\n" in run.stdout


@pytest.mark.parametrize("arguments", [("stack",), ("prompt",), ("launch", "Be bound.", "--claude-version", "2.1.309"), ("doctor",)])
def test_every_verb_exits_quietly_with_status_0_when_its_reader_closes_stdout(login, project, tmp_path, arguments):
    write_session_files(project, login)
    reader, writer = os.pipe()
    os.close(reader)
    try:
        run = subprocess.run(
            [sys.executable, "-m", "unharness.cli", *arguments],
            stdout=writer, stderr=subprocess.PIPE, text=True, cwd=project, timeout=60,
            env={"CLAUDE_CONFIG_DIR": str(login), "XDG_CACHE_HOME": str(tmp_path / "cache"), "PATH": "/usr/bin:/bin"},
        )
    finally:
        os.close(writer)

    assert (run.returncode, run.stderr) == (0, "")


def test_an_old_layout_stops_every_verb_with_the_commands_to_run(login, tmp_path):
    write(tmp_path / ".manifestos.yaml", CONFIG)

    run = unharness(login, "prompt", cwd=tmp_path)

    assert run.returncode == 1
    assert run.stdout == ""
    assert run.stderr == (
        f"unharness: old layout in {tmp_path.resolve()}; run these there:\n"
        "mkdir -p .manifestos\nmv .manifestos.yaml .manifestos/config.yaml\n"
    )
