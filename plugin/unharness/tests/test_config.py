import json
import subprocess
import sys
from pathlib import Path

import pytest
from helpers import write

from unharness.config import Config, Element, UnharnessError, load, old_layout, subagent_key
from unharness.resolve import resolve_stack

CONFIG_SCRIPT = Path(__file__).parent.parent / "src" / "unharness" / "config.py"


def write_config(folder: Path, text: str) -> Path:
    path = folder / ".manifestos" / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_a_bare_string_names_a_registry_manifesto(tmp_path):
    config = load(write_config(tmp_path, "you:\n  - dry\n  - name: kiss\n    purpose: the code\n"))

    assert config == Config(
        you=[Element("dry", None, None, None), Element("kiss", "the code", None, None)],
        subagents={},
        directory=tmp_path,
        registry=None,
    )


def test_subagent_roles_and_manifesto_dir_load_beside_the_you_stack(tmp_path):
    config = load(write_config(tmp_path, (
        "manifesto_dir: /plugins/manifesto\n"
        "you:\n  - dry\n"
        "subagents:\n  implementer:\n    - kiss\n    - name: yagni\n  other:\n    - dry\n"
    )))

    assert config.registry == Path("/plugins/manifesto")
    assert config.subagents == {
        "implementer": [Element("kiss", None, None, None), Element("yagni", None, None, None)],
        "other": [Element("dry", None, None, None)],
    }


def test_a_root_list_is_the_you_stack(tmp_path):
    config = load(write_config(tmp_path, "- dry\n- kiss\n"))

    assert [element.name for element in config.you] == ["dry", "kiss"]
    assert config.subagents == {}
    assert config.registry is None


def test_each_source_type_is_kept_as_written_and_a_file_is_named_by_its_stem(tmp_path):
    config = load(write_config(tmp_path, (
        "you:\n"
        "  - name: write-well\n    source: skill agent-conduct:write-well\n"
        "  - name: mine\n    source: skill my-skill\n"
        "  - name: kiss\n    purpose: the code\n    source: manifesto kiss\n"
        "  - source: file notes/house-rules.md\n"
    )))

    assert config.you == [
        Element("write-well", None, "skill", "agent-conduct:write-well"),
        Element("mine", None, "skill", "my-skill"),
        Element("kiss", "the code", "manifesto", "kiss"),
        Element("house-rules", None, "file", "notes/house-rules.md"),
    ]


def test_null_items_are_dropped_and_an_empty_file_is_an_empty_stack(tmp_path):
    assert load(write_config(tmp_path, "you:\n  - ~\n  - dry\n  -\n")).you == [Element("dry", None, None, None)]
    assert load(write_config(tmp_path, "# nothing here\n")) == Config([], {}, tmp_path, None)


def test_an_element_with_no_name_and_no_file_source_stops_the_load(tmp_path):
    path = write_config(tmp_path, "you:\n  - purpose: orphan\n    source: skill a:b\n")

    with pytest.raises(UnharnessError, match=r"element 1 of you has no name"):
        load(path)


def test_trailing_comments_are_not_part_of_a_value(tmp_path):
    config = load(write_config(tmp_path, (
        "manifesto_dir: /plugins/manifesto  # the registry\n"
        "you:  # the stack\n  - name: \"dry\" # knowledge\n    purpose: 'one home' # why\n    source: skill a:b # where\n"
    )))

    assert config.registry == Path("/plugins/manifesto")
    assert config.you == [Element("dry", "one home", "skill", "a:b")]


def test_a_config_that_is_not_a_list_of_elements_stops_the_load(tmp_path):
    with pytest.raises(UnharnessError, match=r"you must be a list"):
        load(write_config(tmp_path, "you: [dry, kiss]\n"))
    with pytest.raises(UnharnessError, match=r"subagents.other must be a list"):
        load(write_config(tmp_path, "subagents:\n  other: dry\n"))
    with pytest.raises(UnharnessError, match=r"subagents must be a mapping of role to list"):
        load(write_config(tmp_path, "subagents: dry\n"))


def test_a_colon_without_a_space_after_it_is_part_of_a_bare_name(tmp_path):
    config = load(write_config(tmp_path, "you:\n  - agent-conduct:write-well\n  - name: a\n    source: skill b:c\n"))

    assert config.you == [Element("agent-conduct:write-well", None, None, None), Element("a", None, "skill", "b:c")]


def test_without_a_config_file_the_active_manifestos_section_of_claude_md_is_the_config(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Notes\n\n## Active Manifestos\n- dry\n- kiss\n\n## Other\n- yagni\n")

    assert [element.name for element in load(tmp_path / ".manifestos/config.yaml").you] == ["dry", "kiss"]


def test_a_missing_config_names_every_place_it_looked(tmp_path):
    with pytest.raises(UnharnessError) as failure:
        load(tmp_path / ".manifestos/config.yaml")

    assert str(failure.value) == (
        f"no config: tried {tmp_path / '.manifestos/config.yaml'} and the Active Manifestos section of {tmp_path / 'CLAUDE.md'}"
    )


def run_config_script(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(CONFIG_SCRIPT), *arguments], capture_output=True, text=True
    )


def test_a_shell_hook_reads_the_stack_as_json_by_running_the_module_by_path(tmp_path):
    path = write_config(tmp_path, "manifesto_dir: /m\nyou:\n  - dry\nsubagents:\n  other:\n    - name: kiss\n      purpose: p\n")

    run = run_config_script("--json", "--project", str(path.parent.parent))

    assert run.returncode == 0
    assert json.loads(run.stdout) == {
        "you": [{"name": "dry", "purpose": None, "source_type": None, "reference": None}],
        "subagents": {"other": [{"name": "kiss", "purpose": "p", "source_type": None, "reference": None}]},
        "directory": str(tmp_path),
        "registry": "/m",
    }


def test_a_script_run_on_a_broken_config_prints_one_line_and_exits_1(tmp_path):
    run = run_config_script("--json", "--project", str(write_config(tmp_path, "you: [dry]\n").parent.parent))

    assert (run.returncode, run.stdout) == (1, "")
    assert run.stderr == "unharness: you must be a list of elements\n"


def test_a_script_run_with_no_config_prints_one_line_and_exits_2_so_a_hook_can_tell_it_apart(tmp_path):
    run = run_config_script("--json", "--project", str(tmp_path))

    assert (run.returncode, run.stdout) == (2, "")
    assert run.stderr.startswith("unharness: no config: tried ")
    assert len(run.stderr.splitlines()) == 1


@pytest.mark.parametrize("text, line", [
    ("you:\n  - dry\n   - kiss\n", "- kiss"),
    ("you:\n  - name: a\n     purpose: p\n", "purpose: p"),
    ("you:\n- dry\n", "- dry"),
])
def test_a_line_the_reader_cannot_place_stops_the_load_and_is_named(tmp_path, text, line):
    with pytest.raises(UnharnessError, match=f"cannot place the line '{line}'"):
        load(write_config(tmp_path, text))


def test_a_tab_in_the_indent_stops_the_load(tmp_path):
    with pytest.raises(UnharnessError, match="indented with a tab"):
        load(write_config(tmp_path, "you:\n\t- dry\n"))


def test_a_repeated_key_stops_the_load(tmp_path):
    with pytest.raises(UnharnessError, match="key 'you' appears twice"):
        load(write_config(tmp_path, "you:\n  - dry\nyou:\n  - kiss\n"))


@pytest.mark.parametrize("source", ["https://x", "./a.md", "some hint", "file", "skill "])
def test_a_source_that_is_not_manifesto_skill_or_file_with_a_reference_stops_the_load(tmp_path, source):
    path = write_config(tmp_path, f"you:\n  - name: x\n    source: {source}\n")

    with pytest.raises(UnharnessError, match=r"element 1 of you has source '.*' that is none of manifesto <name>, skill <plugin>:<skill>, skill <skill>, or file <path>; write a path as file <path>"):
        load(path)


def test_a_relative_manifesto_dir_resolves_once_against_the_config_folder(login, tmp_path):
    project = tmp_path / "project"
    path = write_config(project, "manifesto_dir: ../registry\nyou:\n  - nope\n")
    registry = (tmp_path / "registry").resolve()

    run = run_config_script("--json", "--project", str(path.parent.parent))
    with pytest.raises(UnharnessError) as failure:
        config = load(path)
        resolve_stack(config.you, config.directory, config.registry, login)

    assert json.loads(run.stdout)["registry"] == str(registry)
    assert str(failure.value) == f"element nope did not resolve; tried {registry / 'manifestos' / 'nope.md'}"


def test_a_name_with_whitespace_stops_the_load(tmp_path):
    path = write_config(tmp_path, "you:\n  - source: file my notes.md\n")

    with pytest.raises(UnharnessError, match=r"element 1 of you name 'my notes' must hold no whitespace; add name:"):
        load(path)


BLOCK_INDICATORS = [">", "|", ">-", "|+", "|2"]


@pytest.mark.parametrize("indicator", BLOCK_INDICATORS)
def test_a_block_scalar_as_a_mapping_value_stops_the_load_naming_the_key(tmp_path, indicator):
    path = write_config(tmp_path, f"you:\n  - name: dry\n    purpose: {indicator}\n      one home\n")

    with pytest.raises(UnharnessError) as failure:
        load(path)

    assert str(failure.value) == "key 'purpose' holds a block scalar; block scalars are not supported; write the value on one line"


@pytest.mark.parametrize("indicator", BLOCK_INDICATORS)
def test_a_block_scalar_as_a_list_item_stops_the_load_naming_the_line(tmp_path, indicator):
    path = write_config(tmp_path, f"you:\n  - {indicator}\n    one home\n")

    with pytest.raises(UnharnessError) as failure:
        load(path)

    assert str(failure.value) == f"the line '- {indicator}' holds a block scalar; block scalars are not supported; write the value on one line"


def test_a_value_that_merely_starts_with_a_fold_sign_still_reads_as_text(tmp_path):
    config = load(write_config(tmp_path, "you:\n  - name: dry\n    purpose: > 3 homes\n"))

    assert config.you[0].purpose == "> 3 homes"


CASCADE = [
    ("implementer", ["implementer", "other"], "implementer"),
    ("dev-cycle:implementer", ["implementer", "other"], "implementer"),
    ("a:dev-cycle:implementer", ["implementer"], "implementer"),
    ("dev-cycle:implementer", ["dev-cycle:implementer", "implementer"], "dev-cycle:implementer"),
    ("code-reviewer", ["reviewer", "other"], "reviewer"),
    ("code-reviewer", ["viewer", "reviewer"], "viewer"),
    ("other", ["implementer", "other"], "other"),
    ("", ["implementer", "other"], "other"),
    ("explorer", ["implementer", "other"], "other"),
    ("explorer", ["implementer"], None),
    ("", [], None),
]


@pytest.mark.parametrize("agent_type, keys, expected", CASCADE)
def test_an_agent_type_matches_the_first_key_of_the_cascade(agent_type, keys, expected):
    assert subagent_key(agent_type, keys) == expected


@pytest.mark.parametrize("key", ["a/b", ".", ".."])
def test_a_subagents_key_that_cannot_name_a_folder_stops_the_load(tmp_path, key):
    path = write_config(tmp_path, f"subagents:\n  {key}:\n    - dry\n")

    with pytest.raises(UnharnessError) as failure:
        load(path)

    assert str(failure.value) == f"subagents key '{key}' cannot name a folder"


OLD_PATHS = [
    (".manifestos.yaml", ".manifestos/config.yaml"),
    (".manifestos.interplay.md", ".manifestos/interplay.md"),
    (".manifestos.commitments.md", ".manifestos/commitments.md"),
    (".manifestos.interplay.min.md", ".manifestos/interplay.min.md"),
    (".manifestos.commitments.min.md", ".manifestos/commitments.min.md"),
    (".manifestos.preamble.md", ".manifestos/preamble.md"),
    (".claude/digests", ".manifestos/digests"),
]


def make_old(project: Path, *paths: str) -> None:
    for path in paths:
        target = project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir() if path.endswith("digests") else target.write_text("x")


@pytest.mark.parametrize("old, new", OLD_PATHS)
def test_each_old_path_alone_yields_the_mkdir_and_its_own_move(tmp_path, old, new):
    make_old(tmp_path, old)

    assert old_layout(tmp_path) == ["mkdir -p .manifestos", f"mv {old} {new}"]


def test_every_old_path_yields_its_move_in_the_documented_order(tmp_path):
    make_old(tmp_path, *reversed([old for old, _ in OLD_PATHS]))

    assert old_layout(tmp_path) == ["mkdir -p .manifestos", *[f"mv {old} {new}" for old, new in OLD_PATHS]]


def test_a_project_in_the_new_layout_yields_no_commands(tmp_path):
    write_config(tmp_path, "you:\n  - dry\n")

    assert old_layout(tmp_path) == []


def test_an_existing_new_path_yields_a_both_line_in_place_of_the_move(tmp_path):
    make_old(tmp_path, ".manifestos.yaml", ".manifestos.preamble.md", ".manifestos/preamble.md")

    assert old_layout(tmp_path) == [
        "mkdir -p .manifestos",
        "mv .manifestos.yaml .manifestos/config.yaml",
        "# both .manifestos.preamble.md and .manifestos/preamble.md exist; keep one and delete the other",
    ]


def test_when_every_new_path_exists_there_is_no_mkdir(tmp_path):
    make_old(tmp_path, ".manifestos.yaml", ".manifestos/config.yaml")

    assert old_layout(tmp_path) == ["# both .manifestos.yaml and .manifestos/config.yaml exist; keep one and delete the other"]


def test_an_old_layout_stops_the_load_with_the_commands_before_it_looks_for_a_config(tmp_path):
    make_old(tmp_path, ".manifestos.yaml", ".claude/digests")

    with pytest.raises(UnharnessError) as failure:
        load(tmp_path / ".manifestos" / "config.yaml")

    assert str(failure.value) == (
        f"old layout in {tmp_path}; run these there:\n"
        "mkdir -p .manifestos\nmv .manifestos.yaml .manifestos/config.yaml\nmv .claude/digests .manifestos/digests"
    )


def test_a_script_run_on_an_old_layout_prints_the_commands_and_exits_1(tmp_path):
    make_old(tmp_path, ".manifestos.yaml")

    run = run_config_script("--json", "--project", str(tmp_path))

    assert (run.returncode, run.stdout) == (1, "")
    assert run.stderr == (
        f"unharness: old layout in {tmp_path}; run these there:\nmkdir -p .manifestos\nmv .manifestos.yaml .manifestos/config.yaml\n"
    )


def test_a_file_source_resolves_against_the_project_folder(login, tmp_path):
    write(tmp_path / "notes" / "rules.md", "Rules.\n")
    config = load(write_config(tmp_path, "you:\n  - source: file notes/rules.md\n"))

    documents = resolve_stack(config.you, config.directory, config.registry, login)

    assert documents[0].text.strip() == "Rules."
