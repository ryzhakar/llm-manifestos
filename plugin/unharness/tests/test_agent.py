from pathlib import Path

import pytest
from helpers import write
from test_cli import unharness
from unharness.compile import stack_block, stack_view
from unharness.config import load
from unharness.resolve import resolve_stack

CONFIG = (
    "you:\n  - name: dry\n    purpose: one home\n"
    "subagents:\n"
    "  implementer:\n    - name: write-well\n      source: skill agent-conduct:write-well\n"
    "  reviewer:\n    - dry\n"
    "  other:\n    - name: dry\n      purpose: the default\n"
    "  empty:\n"
)
FALL_THROUGH = "unharness: explorer matches no subagents key; using other:, the default stack\n"


@pytest.fixture
def project(tmp_path) -> Path:
    folder = tmp_path / "project"
    write(folder / ".manifestos" / "config.yaml", CONFIG)
    return folder


def documents_of(project: Path, login: Path, key: str):
    config = load(project / ".manifestos" / "config.yaml")
    return resolve_stack(config.subagents[key], config.directory, config.registry, login)


def write_agent_files(project: Path, login: Path, key: str, suffix: str = "") -> None:
    stack = stack_block(documents_of(project, login, key))
    folder = project / ".manifestos" / "agents" / key
    write(folder / f"interplay{suffix}.md", f"{stack}\n\n<interplay>\nAgree, {key}{suffix}.\n</interplay>\n")
    write(folder / f"commitments{suffix}.md", f"{stack}\n\n<commitments>\nI will, {key}{suffix}.\n</commitments>\n")


def test_stack_agent_prints_the_stack_of_the_key_the_type_matches(login, project):
    run = unharness(login, "stack", "--agent", "dev-cycle:implementer", cwd=project)

    assert run.returncode == 0, run.stderr
    assert run.stdout == stack_view(documents_of(project, login, "implementer")) + "\n"
    assert run.stderr == ""


def test_prompt_agent_binds_the_matched_stack_to_the_session_files_of_its_key(login, project):
    write_agent_files(project, login, "implementer")

    run = unharness(login, "prompt", "--agent", "implementer", cwd=project)

    assert run.returncode == 0, run.stderr
    assert "<write-well>" in run.stdout and "<dry" not in run.stdout
    assert run.stdout.endswith("<interplay>\nAgree, implementer.\n</interplay>\n\n<commitments>\nI will, implementer.\n</commitments>\n")


def test_prompt_agent_takes_the_minified_pair_of_the_key_under_the_minified_flag(login, project):
    write_agent_files(project, login, "implementer")
    write_agent_files(project, login, "implementer", ".min")

    run = unharness(login, "prompt", "--agent", "implementer", "--minified", cwd=project)

    assert run.returncode == 0, run.stderr
    assert run.stdout.endswith("<interplay>\nAgree, implementer.min.\n</interplay>\n\n<commitments>\nI will, implementer.min.\n</commitments>\n")


def test_prompt_agent_keeps_the_digest_mode_checks(login, project):
    write_agent_files(project, login, "implementer")

    run = unharness(login, "prompt", "--agent", "implementer", "--overlap", cwd=project)

    assert (run.returncode, run.stdout, run.stderr) == (1, "", "unharness: --overlap requires --stack-digests\n")


def test_a_type_that_lands_on_other_prints_the_fall_through_once_and_goes_on(login, project):
    write_agent_files(project, login, "other")

    run = unharness(login, "prompt", "--agent", "explorer", cwd=project)

    assert run.returncode == 0
    assert run.stderr == FALL_THROUGH
    assert "governs=\"the default\"" in run.stdout


def test_stack_agent_warns_on_the_fall_through_too(login, project):
    run = unharness(login, "stack", "--agent", "explorer", cwd=project)

    assert (run.returncode, run.stderr) == (0, FALL_THROUGH)


@pytest.mark.parametrize("agent_type", ["other", "x:other"])
def test_a_type_that_names_other_matches_it_without_a_warning(login, project, agent_type):
    run = unharness(login, "stack", "--agent", agent_type, cwd=project)

    assert (run.returncode, run.stderr) == (0, "")


def test_a_type_that_matches_no_key_and_has_no_other_stops_with_the_keys_in_config_order(login, tmp_path):
    write(tmp_path / ".manifestos" / "config.yaml", "you:\n  - dry\nsubagents:\n  implementer:\n    - dry\n  reviewer:\n    - dry\n")

    run = unharness(login, "stack", "--agent", "explorer", cwd=tmp_path)

    assert (run.returncode, run.stdout) == (1, "")
    assert run.stderr == "unharness: explorer matches no subagents key and the config has no other:; keys: implementer, reviewer\n"


def test_the_no_match_message_says_none_when_the_config_has_no_subagents(login, tmp_path):
    write(tmp_path / ".manifestos" / "config.yaml", "you:\n  - dry\n")

    run = unharness(login, "prompt", "--agent", "explorer", cwd=tmp_path)

    assert run.stderr == "unharness: explorer matches no subagents key and the config has no other:; keys: none\n"


@pytest.mark.parametrize("verb", ["prompt", "stack"])
def test_an_empty_matched_list_stops_the_verb(login, project, verb):
    run = unharness(login, verb, "--agent", "empty", cwd=project)

    assert (run.returncode, run.stdout, run.stderr) == (1, "", "unharness: subagents.empty is empty\n")


def test_a_missing_agent_file_names_its_path_and_the_compile_command_with_the_key(login, project):
    run = unharness(login, "prompt", "--agent", "implementer", cwd=project)

    assert run.stderr == "unharness: .manifestos/agents/implementer/interplay.md is missing; run /compile-commitments implementer\n"


def test_a_stale_agent_file_names_what_changed_and_the_key_to_recompile(login, project):
    write_agent_files(project, login, "implementer")
    write(project / ".manifestos" / "agents" / "implementer" / "commitments.md", f"<stack>\nstale\n</stack>\n\n<commitments>\nOld.\n</commitments>\n")

    run = unharness(login, "prompt", "--agent", "implementer", cwd=project)

    assert run.stderr == (
        "unharness: .manifestos/agents/implementer/commitments.md is stale (changed: stale, write-well); "
        "run /compile-commitments implementer\n"
    )


def test_an_agent_file_without_a_stack_block_names_the_key_to_recompile(login, project):
    write_agent_files(project, login, "implementer")
    write(project / ".manifestos" / "agents" / "implementer" / "interplay.md", "<interplay>\nNo block.\n</interplay>\n")

    run = unharness(login, "prompt", "--agent", "implementer", cwd=project)

    assert run.stderr == (
        "unharness: .manifestos/agents/implementer/interplay.md has no <stack> block; run /compile-commitments implementer\n"
    )


def test_stack_agent_refuses_slugs(login, project):
    run = unharness(login, "stack", "--agent", "implementer", "dry", cwd=project)

    assert (run.returncode, run.stdout, run.stderr) == (1, "", "unharness: --agent takes no slugs\n")
