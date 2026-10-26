from pathlib import Path

import pytest
from unharness.switches import shipped_switches, strip_table

PLUGIN_FOLDER = Path(__file__).resolve().parents[2]
PLUGIN_README = PLUGIN_FOLDER / "README.md"
PACKAGE_README = PLUGIN_FOLDER / "unharness" / "README.md"
SCHEMA = PLUGIN_FOLDER / "SCHEMA.md"
OPENING_MARKER = "<!-- switches -->"
CLOSING_MARKER = "<!-- /switches -->"
TABLE_POINTER = "strip table in the Unharness section of"


def between_markers(text: str) -> tuple[str, str]:
    """Return the table the markers enclose and the text after the closing marker."""
    before, rest = text.split(f"{OPENING_MARKER}\n")
    table, after = rest.split(f"\n{CLOSING_MARKER}\n")
    return table, after


def test_the_readme_table_between_the_markers_equals_the_output_of_the_switches_verb():
    table, _ = between_markers(PLUGIN_README.read_text())

    assert table == strip_table(shipped_switches())


def test_the_sentence_above_the_markers_names_the_system_prompt_flag():
    above = PLUGIN_README.read_text().split(OPENING_MARKER)[0].rstrip().splitlines()[-1]

    assert "`--system-prompt-file`" in above


def test_the_paragraph_below_the_markers_names_no_switch_and_defines_the_table_words():
    _, after = between_markers(PLUGIN_README.read_text())
    paragraph = after.lstrip().split("\n\n")[0]

    assert not [switch.name for switch in shipped_switches() if switch.name in paragraph]
    assert all(word in paragraph for word in ("stripped", "set", "undocumented", "a release may drop"))


@pytest.mark.parametrize("document", [PACKAGE_README, SCHEMA])
def test_the_package_readme_and_the_schema_point_at_the_table_and_name_no_variable(document):
    text = document.read_text()

    assert TABLE_POINTER in text
    assert not [switch.name for switch in shipped_switches() if switch.name.startswith("CLAUDE_CODE_") and switch.name in text]


@pytest.mark.parametrize("document", [PLUGIN_README, PACKAGE_README])
@pytest.mark.parametrize("verb", ["launch", "doctor"])
def test_each_readme_lists_claude_version_in_the_synopsis_of_launch_and_doctor(document, verb):
    synopsis = next(line for line in document.read_text().splitlines() if line.startswith(f"- `unharness {verb} "))

    assert "[--claude-version X.Y.Z]" in synopsis


@pytest.mark.parametrize("document", [PLUGIN_README, PACKAGE_README])
def test_each_readme_states_how_launch_picks_the_version_and_what_it_falls_back_to(document):
    text = " ".join(document.read_text().split())

    for statement in (
        "ARGS... --version", "`$SHELL -ic`", "nearest registry version below", "oldest registry version", "newest registry version",
        "is not in the switch registry", "printed no version",
    ):
        assert statement in text, statement


def test_the_plugin_readme_describes_the_switch_lines_of_doctor():
    text = " ".join(PLUGIN_README.read_text().split())

    for statement in ("`switch registry`", "`switch <kind> <name>`", "never FAIL", "`--claude-version X.Y.Z` replaces the detected version"):
        assert statement in text, statement
    assert "tested range" not in text


def test_the_schema_points_at_the_readme_for_the_version_rule():
    text = " ".join(SCHEMA.read_text().split())

    assert "`--claude-version X.Y.Z`" in text and "picks the entries verified at one registry version" in text


COMPACTION_PARAGRAPH = (
    "**Compaction.** Without `--autocompact`, launch turns automatic and idle compaction off. `--autocompact 500k` turns both on and"
    " sets the window to 500000 tokens; `500` means the same, and the size runs from 100k to 1000k. Claude Code compacts when the"
    " conversation reaches the window less the room it keeps for the summary, not at the window itself. Idle compaction compacts a"
    " long conversation while the session sits idle, and Claude Code takes its mode from a server flag that unharness cannot force:"
    " `\"idleCompaction\": false` turns it off, but `true` cannot turn it on, so `--autocompact` only leaves it unblocked, and a login"
    " whose flag reads off never compacts while idle."
)


@pytest.mark.parametrize("document", [PLUGIN_README, PACKAGE_README])
def test_each_readme_lists_autocompact_in_the_synopsis_of_launch(document):
    synopsis = next(line for line in document.read_text().splitlines() if line.startswith("- `unharness launch "))

    assert "[--no-hooks] [--autocompact SIZE] [--claude-version X.Y.Z]" in synopsis


def test_the_compaction_paragraph_follows_the_version_paragraph():
    paragraphs = PLUGIN_README.read_text().split("\n\n")
    version = next(index for index, paragraph in enumerate(paragraphs) if paragraph.startswith("**Version.**"))

    assert paragraphs[version + 1] == COMPACTION_PARAGRAPH


def test_the_paragraph_below_the_markers_says_what_passes_means():
    _, after = between_markers(PLUGIN_README.read_text())

    assert "`passes` gives the value a valued option sends in place of the default." in after.lstrip().split("\n\n")[0]


def test_the_doctor_excerpt_counts_the_shipped_switches():
    assert f"OK switch registry: newest 2.1.309; {len(shipped_switches())} switches" in PLUGIN_README.read_text()
