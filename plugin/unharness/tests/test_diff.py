from pathlib import Path

import pytest
from helpers import write
from test_agent import CONFIG as AGENT_CONFIG
from test_cli import CONFIG, unharness
from unharness.compile import stack_block
from unharness.config import load
from unharness.resolve import resolve_stack

SESSION_FILES = ("interplay.md", "commitments.md", "interplay.min.md", "commitments.min.md")


@pytest.fixture
def project(tmp_path) -> Path:
    folder = tmp_path / "project"
    write(folder / ".manifestos" / "config.yaml", CONFIG)
    return folder


def current_lines(project: Path, login: Path, key: str | None = None) -> list[str]:
    config = load(project / ".manifestos" / "config.yaml")
    elements = config.you if key is None else config.subagents[key]
    return stack_block(resolve_stack(elements, config.directory, config.registry, login)).split("\n")[1:-1]


def write_session_files(folder: Path, lines: list[str]) -> None:
    for name in SESSION_FILES:
        write(folder / name, "<stack>\n" + "\n".join(lines) + "\n</stack>\n\n<body>\nText.\n</body>\n")


def test_all_current_files_print_nothing_and_exit_0(login, project):
    write_session_files(project / ".manifestos", current_lines(project, login))

    run = unharness(login, "stack", "--diff", cwd=project)

    assert (run.returncode, run.stdout, run.stderr) == (0, "", "")


def test_a_changed_hash_prints_its_hunk_as_a_pair_and_exits_1(login, project):
    lines = current_lines(project, login)
    write_session_files(project / ".manifestos", lines)
    stale = [f"dry {'0' * 64} one home", *lines[1:]]
    write(project / ".manifestos" / "commitments.md", "<stack>\n" + "\n".join(stale) + "\n</stack>\n")

    run = unharness(login, "stack", "--diff", cwd=project)

    assert run.returncode == 1
    assert run.stdout == f"--- .manifestos/commitments.md\n+++ current\n@@ -1 +1 @@\n-{stale[0]}\n+{lines[0]}\n"
    assert run.stderr == ""


def test_a_changed_purpose_an_added_element_and_a_reorder_each_print_their_hunk(login, project):
    lines = current_lines(project, login)
    folder = project / ".manifestos"
    write_session_files(folder, lines)
    write(folder / "interplay.md", "<stack>\n" + lines[0].replace("one home", "other") + "\n" + lines[1] + "\n</stack>\n")
    write(folder / "commitments.md", "<stack>\n" + lines[0] + "\n</stack>\n")
    write(folder / "interplay.min.md", "<stack>\n" + lines[1] + "\n" + lines[0] + "\n</stack>\n")

    run = unharness(login, "stack", "--diff", cwd=project)

    assert run.returncode == 1
    assert run.stdout == (
        "--- .manifestos/interplay.md\n+++ current\n@@ -1 +1 @@\n"
        f"-{lines[0].replace('one home', 'other')}\n+{lines[0]}\n"
        "--- .manifestos/commitments.md\n+++ current\n@@ -1,0 +2 @@\n"
        f"+{lines[1]}\n"
        "--- .manifestos/interplay.min.md\n+++ current\n@@ -0,0 +1 @@\n"
        f"+{lines[0]}\n@@ -2 +2,0 @@\n-{lines[0]}\n"
    )


def test_a_missing_file_and_a_file_without_a_block_print_their_lines_and_exit_1(login, project):
    folder = project / ".manifestos"
    write_session_files(folder, current_lines(project, login))
    (folder / "interplay.md").unlink()
    write(folder / "commitments.min.md", "No block.\n")

    run = unharness(login, "stack", "--diff", cwd=project)

    assert run.returncode == 1
    assert run.stdout == ".manifestos/interplay.md: missing\n.manifestos/commitments.min.md: no <stack> block\n"


def test_diff_agent_compares_the_four_files_of_the_matched_key(login, tmp_path):
    project = tmp_path / "agents"
    write(project / ".manifestos" / "config.yaml", AGENT_CONFIG)
    write_session_files(project / ".manifestos" / "agents" / "reviewer", current_lines(project, login, "reviewer"))

    current = unharness(login, "stack", "--diff", "--agent", "reviewer", cwd=project)
    missing = unharness(login, "stack", "--diff", "--agent", "dev-cycle:implementer", cwd=project)

    assert (current.returncode, current.stdout) == (0, "")
    assert missing.returncode == 1
    assert missing.stdout.splitlines()[0] == ".manifestos/agents/implementer/interplay.md: missing"


def test_diff_refuses_slugs_and_an_empty_stack(login, project, tmp_path):
    slugs = unharness(login, "stack", "--diff", "dry", cwd=project)
    write(tmp_path / ".manifestos" / "config.yaml", "you:\n")
    empty = unharness(login, "stack", "--diff", cwd=tmp_path)

    assert (slugs.returncode, slugs.stdout, slugs.stderr) == (1, "", "unharness: --diff takes no slugs\n")
    assert (empty.returncode, empty.stdout, empty.stderr) == (1, "", "unharness: the stack is empty\n")
