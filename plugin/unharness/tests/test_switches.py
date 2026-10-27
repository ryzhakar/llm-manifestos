import json
from pathlib import Path

import pytest
from unharness.cli import main
from unharness.config import UnharnessError
from unharness.switches import parse_switches, shipped_switches, strip_table

SHIPPED_NAMES = [
    "CLAUDE_CODE_ATTRIBUTION_HEADER",
    "CLAUDE_CODE_DISABLE_CLAUDE_MDS",
    "CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS",
    "CLAUDE_CODE_DISABLE_AUTO_MEMORY",
    "CLAUDE_CODE_SILENT_TURN_REMINDER",
    "CLAUDE_CODE_TODO_REMINDER_MODE",
    "CLAUDE_CODE_TOTAL_TOKENS_REMINDER",
    "--disallowedTools",
    "includeGitInstructions",
    "attribution",
    "autoMemoryEnabled",
    "outputStyle",
    "disableAllHooks",
    "autoCompactEnabled",
    "autoCompactWindow",
    "idleCompaction",
]


def entry(**overrides) -> dict:
    return {
        "name": "SWITCH_ONE", "kind": "env", "value": "1", "removes": "Some text",
        "documented": True, "control": True, "verified": ["2.1.309"], "default": True, "option": None,
        **overrides,
    }


def text_of(*entries: dict) -> str:
    return json.dumps(list(entries))


def test_the_shipped_registry_holds_the_thirteen_switches_3_6_1_passes_then_the_three_compaction_settings():
    assert [switch.name for switch in shipped_switches()] == SHIPPED_NAMES


def test_every_shipped_entry_is_verified_at_the_same_versions_so_no_version_drops_a_switch():
    assert len({switch.verified for switch in shipped_switches()}) == 1


def test_the_shipped_registry_marks_what_the_spec_marks():
    by_name = {switch.name: switch for switch in shipped_switches()}

    undocumented = {name for name, switch in by_name.items() if not switch.documented}
    uncontrolled = {name for name, switch in by_name.items() if not switch.control}
    assert undocumented == {"CLAUDE_CODE_SILENT_TURN_REMINDER", "CLAUDE_CODE_TODO_REMINDER_MODE", "CLAUDE_CODE_TOTAL_TOKENS_REMINDER"}
    assert uncontrolled == {
        "attribution", "outputStyle", "autoMemoryEnabled", "CLAUDE_CODE_DISABLE_AUTO_MEMORY",
        "autoCompactEnabled", "autoCompactWindow", "idleCompaction",
    }
    assert {name: switch.option for name, switch in by_name.items() if switch.option} == {
        "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "--keep-claude-md",
        "--disallowedTools": "--keep-web-search",
        "disableAllHooks": "--no-hooks",
        "autoCompactEnabled": "--autocompact",
        "autoCompactWindow": "--autocompact",
        "idleCompaction": "--autocompact",
    }
    assert [name for name, switch in by_name.items() if not switch.default] == ["disableAllHooks", "autoCompactWindow"]
    assert {name: (switch.kind, switch.value, switch.given, switch.removes) for name, switch in by_name.items() if switch.option == "--autocompact"} == {
        "autoCompactEnabled": ("settings", False, True, "Automatic compaction"),
        "autoCompactWindow": ("settings", None, "<size>", "Automatic compaction window"),
        "idleCompaction": ("settings", False, True, "Idle compaction"),
    }


def test_a_valid_text_loads_each_kind_with_its_value():
    switches = parse_switches(text_of(
        entry(),
        entry(name="--bare", kind="flag", value=None, removes="Other", default=False, option="--no-hooks"),
        entry(name="key", kind="settings", value={"a": [1]}, removes="Third"),
    ))

    assert [(switch.kind, switch.value) for switch in switches] == [("env", "1"), ("flag", None), ("settings", {"a": [1]})]


@pytest.mark.parametrize(("entries", "message"), [
    ([{key: value for key, value in entry().items() if key != "kind"}], "switches.json entry 0: kind is missing"),
    ([entry(), {**entry(name="B", removes="B"), "extra": 1}], "switches.json entry 1: extra is not a key of an entry"),
    ([entry(kind="header")], 'switches.json entry 0: kind must be "env", "flag", or "settings"'),
    ([entry(name="")], "switches.json entry 0: name must be a non-empty string"),
    ([entry(removes="")], "switches.json entry 0: removes must be a non-empty string"),
    ([entry(value=1)], "switches.json entry 0: value must be a string"),
    ([entry(kind="flag", value=1)], "switches.json entry 0: value must be a string or null"),
    ([entry(kind="env", value=None)], "switches.json entry 0: value must be a string"),
    ([entry(documented="yes")], "switches.json entry 0: documented must be true or false"),
    ([entry(control=1)], "switches.json entry 0: control must be true or false"),
    ([entry(default=None)], "switches.json entry 0: default must be true or false"),
    ([entry(option="--other")], 'switches.json entry 0: option must be null, "--keep-claude-md", "--keep-web-search", "--no-hooks", or "--autocompact"'),
    ([entry(kind="settings", value=False, option="--autocompact")], "switches.json entry 0: given is missing"),
    ([entry(kind="settings", value=False, given=None, option="--autocompact")], "switches.json entry 0: given must not be null"),
    ([entry(given=True)], "switches.json entry 0: given belongs only to an entry whose option is --autocompact"),
    ([entry(kind="settings", value=None, given=True, option="--autocompact")], "switches.json entry 0: value must be null exactly when default is false"),
    ([entry(kind="settings", value=False, given=True, default=False, option="--autocompact")], "switches.json entry 0: value must be null exactly when default is false"),
    ([entry(kind="settings", value=None, given=True, default=1, option="--autocompact")], "switches.json entry 0: default must be true or false"),
    ([entry(verified=[])], "switches.json entry 0: verified must be a non-empty array of distinct X.Y.Z strings in ascending order"),
    ([entry(verified="2.1.309")], "switches.json entry 0: verified must be a non-empty array of distinct X.Y.Z strings in ascending order"),
    ([entry(verified=["2.1"])], "switches.json entry 0: verified must be a non-empty array of distinct X.Y.Z strings in ascending order"),
    ([entry(verified=["2.1.309", "2.1.309"])], "switches.json entry 0: verified must be a non-empty array of distinct X.Y.Z strings in ascending order"),
    ([entry(verified=["2.1.310", "2.1.309"])], "switches.json entry 0: verified must be a non-empty array of distinct X.Y.Z strings in ascending order"),
    ([entry(verified=["2.1.10", "2.1.9"])], "switches.json entry 0: verified must be a non-empty array of distinct X.Y.Z strings in ascending order"),
    (["text"], "switches.json entry 0: is not an object"),
    ([entry(), entry(removes="Other")], "switches.json entry 1: name repeats entry 0, which has the same kind"),
    ([entry(), entry(name="B", control=False)], "switches.json entry 1: control differs from entry 0, which has the same removes"),
    ([entry(), entry(name="B", default=False)], "switches.json entry 1: default differs from entry 0, which has the same removes"),
    ([entry(), entry(name="B", option="--no-hooks")], "switches.json entry 1: option differs from entry 0, which has the same removes"),
])
def test_a_file_that_breaks_the_schema_is_refused_with_the_entry_index_and_the_problem(entries, message):
    with pytest.raises(UnharnessError) as refusal:
        parse_switches(json.dumps(entries))

    assert str(refusal.value) == message


def test_an_autocompact_entry_loads_with_the_value_it_passes_when_the_option_is_given():
    switches = parse_switches(text_of(
        entry(name="on", kind="settings", value=False, given=True, option="--autocompact"),
        entry(name="window", kind="settings", value=None, given="<size>", removes="Other", default=False, option="--autocompact"),
    ))

    assert [(switch.value, switch.given) for switch in switches] == [(False, True), (None, "<size>")]


def test_two_entries_of_different_kinds_may_share_a_name():
    parse_switches(text_of(entry(), entry(kind="settings", value=True, removes="Other")))


@pytest.mark.parametrize(("text", "message"), [
    ("{}", "switches.json is not one JSON array"),
    ("[", "switches.json is not JSON: Expecting value: line 1 column 2 (char 1)"),
])
def test_a_file_that_is_not_one_json_array_is_refused(text, message):
    with pytest.raises(UnharnessError) as refusal:
        parse_switches(text)

    assert str(refusal.value) == message


FIXTURE_TABLE = """\
| Injected text | Switch | Default |
|---|---|---|
| First text | env `A=1` | stripped |
| Second text | env `B=off`, undocumented | set; `--keep-claude-md` keeps |
| Third text | `--bare`, setting `key: {"a": ""}` | stripped; `--keep-web-search` keeps |
| Fourth text | `--valued v` | kept; `--no-hooks` strips |
| Fifth text | setting `flag: false` | kept |"""


def fixture_registry() -> str:
    return text_of(
        entry(name="A", value="1", removes="First text"),
        entry(name="B", value="off", removes="Second text", documented=False, control=False, option="--keep-claude-md"),
        entry(name="--bare", kind="flag", value=None, removes="Third text", option="--keep-web-search"),
        entry(name="key", kind="settings", value={"a": ""}, removes="Third text", option="--keep-web-search"),
        entry(name="--valued", kind="flag", value="v", removes="Fourth text", default=False, option="--no-hooks"),
        entry(name="flag", kind="settings", value=False, removes="Fifth text", default=False),
    )


def test_the_strip_table_has_one_row_per_removed_text_with_its_switches_and_default():
    assert strip_table(parse_switches(fixture_registry())) == FIXTURE_TABLE


def test_an_autocompact_row_names_a_null_valued_setting_bare_and_says_what_the_option_passes():
    switches = parse_switches(text_of(
        entry(name="on", kind="settings", value=False, given=True, control=False, removes="On", option="--autocompact"),
        entry(name="window", kind="settings", value=None, given="<size>", control=False, removes="Window", default=False, option="--autocompact"),
        entry(name="mode", kind="settings", value="off", given={"a": "<size>"}, removes="Mode", option="--autocompact"),
    ))

    assert strip_table(switches).splitlines()[2:] == [
        "| On | setting `on: false` | set; `--autocompact <size>` passes `true` |",
        "| Window | setting `window` | kept; `--autocompact <size>` passes `<size>` |",
        '| Mode | setting `mode: "off"` | stripped; `--autocompact <size>` passes `{"a": "<size>"}` |',
    ]


def test_the_switches_verb_prints_the_table_of_the_shipped_registry(capsys):
    assert main(["switches"]) == 0

    assert capsys.readouterr().out == strip_table(shipped_switches()) + "\n"


def test_the_switches_verb_takes_no_argument(capsys):
    with pytest.raises(SystemExit):
        main(["switches", "extra"])


def test_every_documented_registry_entry_appears_in_the_baseline_sweep_documented_lists():
    baseline = Path(__file__).resolve().parents[3] / ".claude" / "switch-sweeps" / "2.1.309.json"
    if not baseline.exists():
        pytest.skip("the baseline sweep is absent")
    sweep = json.loads(baseline.read_text())
    named = set(sweep["documented_env"]) | set(sweep["documented_settings"])

    assert [switch.name for switch in shipped_switches() if switch.documented and switch.kind != "flag" and switch.name not in named] == []
