import importlib.util
import json
import re
import socket
from pathlib import Path

import pytest
from helpers import write
from unharness.cli import main
from unharness.compile import stack_block
from unharness.config import load
from unharness.resolve import resolve_stack
from unharness.switches import parse_switches, shipped_switches

TESTED_CLAUDE = "2.1.309"
STUB_VERSION = '#!/bin/sh\necho "{version} (Claude Code)"\n'
STUB_SILENT = "#!/bin/sh\nexit 0\n"
CACHE = Path("plugins") / "cache" / "marketplace"
SWITCH_NAMES = [f"switch {switch.kind} {switch.name}" for switch in shipped_switches()]


def install_stub(folder: Path, name: str, body: str) -> Path:
    path = write(folder / name, body)
    path.chmod(0o755)
    return path


def record_installed(login: Path, **versions: str) -> None:
    plugins = {f"{plugin}@marketplace": [{"scope": "user", "version": version}] for plugin, version in versions.items()}
    write(login / "plugins" / "installed_plugins.json", json.dumps({"version": 2, "plugins": plugins}))


@pytest.fixture
def host(tmp_path, monkeypatch) -> Path:
    """A fake host: claude, uv, and uvx stubs alone on PATH, and a login recording the manifesto plugin."""
    bin_folder = tmp_path / "bin"
    install_stub(bin_folder, "claude", STUB_VERSION.format(version=TESTED_CLAUDE))
    install_stub(bin_folder, "uv", STUB_SILENT)
    install_stub(bin_folder, "uvx", STUB_SILENT)
    login = tmp_path / "login"
    record_installed(login, manifesto="3.6.0")
    monkeypatch.setenv("PATH", str(bin_folder))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(login))
    return tmp_path


def doctor(capsys, *arguments: str) -> tuple[int, list[str]]:
    status = main(["doctor", *arguments])
    return status, capsys.readouterr().out.splitlines()


def test_a_missing_config_fails_and_leaves_only_the_three_checks_that_need_no_config(host, capsys):
    status, lines = doctor(capsys, "--config", str(host / "project" / ".manifestos/config.yaml"))

    assert status == 1
    assert [line.split(":")[0] for line in lines] == [
        "OK layout", "FAIL config", "OK claude", "OK switch registry", *(f"OK {name}" for name in SWITCH_NAMES), "OK uv", "OK manifesto plugin",
    ]
    assert lines[0] == f"OK layout: {host / 'project' / '.manifestos'}"
    assert lines[1].startswith(f"FAIL config: no config: tried {host / 'project' / '.manifestos/config.yaml'}")
    assert lines[2] == f"OK claude: {host / 'bin' / 'claude'} {TESTED_CLAUDE}"
    assert lines[-2] == f"OK uv: {host / 'bin' / 'uv'} {host / 'bin' / 'uvx'}"
    assert lines[-1] == "OK manifesto plugin: 3.6.0"


@pytest.fixture
def missing_config(host) -> list[str]:
    return ["--config", str(host / "project" / ".manifestos/config.yaml")]


def finding(lines: list[str], name: str) -> str:
    return next(line for line in lines if line.startswith(f"{name}: ", line.index(" ") + 1))


def test_an_old_layout_fails_one_line_per_move_and_leaves_out_the_config_checks(host, capsys):
    project = host / "project"
    write(project / ".manifestos.yaml", CONFIG)
    write(project / ".manifestos.preamble.md", "Mine.\n")

    status, lines = doctor(capsys, "--config", str(project / ".manifestos/config.yaml"))

    assert status == 1
    assert lines[:3] == [
        "FAIL layout: mkdir -p .manifestos",
        "FAIL layout: mv .manifestos.yaml .manifestos/config.yaml",
        "FAIL layout: mv .manifestos.preamble.md .manifestos/preamble.md",
    ]
    assert [line.split(":")[0] for line in lines[3:]] == [
        "OK claude", "OK switch registry", *(f"OK {name}" for name in SWITCH_NAMES), "OK uv", "OK manifesto plugin",
    ]


@pytest.mark.parametrize(("version", "chosen"), [("2.1.308", "2.1.309"), ("2.1.312", "2.1.309"), ("2.2.0", "2.1.309")])
def test_a_claude_version_outside_the_registry_warns_and_names_the_version_launch_uses(host, missing_config, capsys, version, chosen):
    install_stub(host / "bin", "claude", STUB_VERSION.format(version=version))

    _, lines = doctor(capsys, *missing_config)

    assert finding(lines, "claude") == (
        f"WARN claude: {host / 'bin' / 'claude'} {version}, not in the switch registry; launch uses switches verified at {chosen}"
    )


def test_a_claude_that_prints_no_version_warns(host, missing_config, capsys):
    install_stub(host / "bin", "claude", STUB_SILENT)

    _, lines = doctor(capsys, *missing_config)

    assert finding(lines, "claude") == f"WARN claude: {host / 'bin' / 'claude'} printed no version"


def test_a_claude_missing_from_path_warns_since_a_shell_function_can_launch(host, missing_config, capsys):
    (host / "bin" / "claude").unlink()

    _, lines = doctor(capsys, *missing_config)

    assert finding(lines, "claude") == "WARN claude: not on PATH; a shell function can still launch it"


def test_a_missing_uvx_fails(host, missing_config, capsys):
    (host / "bin" / "uvx").unlink()

    status, lines = doctor(capsys, *missing_config)

    assert finding(lines, "uv").startswith("FAIL uv: uvx is not on PATH")
    assert status == 1


def test_a_manifesto_plugin_absent_from_installed_plugins_fails(host, missing_config, capsys):
    record_installed(host / "login", other="1.0.0")

    _, lines = doctor(capsys, *missing_config)

    assert finding(lines, "manifesto plugin") == f"FAIL manifesto plugin: absent from {host / 'login' / 'plugins' / 'installed_plugins.json'}"


def test_a_manifesto_plugin_below_3_6_0_fails_since_its_hooks_do_not_all_stand_down(host, missing_config, capsys):
    record_installed(host / "login", manifesto="3.5.9")

    _, lines = doctor(capsys, *missing_config)

    assert finding(lines, "manifesto plugin") == "FAIL manifesto plugin: 3.5.9 is below 3.6.0, whose hooks do not all stand down"


def test_the_newest_recorded_manifesto_version_counts_when_several_scopes_record_one(host, missing_config, capsys):
    write(host / "login" / "plugins" / "installed_plugins.json", json.dumps({"plugins": {
        "manifesto@marketplace": [{"version": "3.4.0"}, {"version": "3.10.0"}],
    }}))

    _, lines = doctor(capsys, *missing_config)

    assert finding(lines, "manifesto plugin") == "OK manifesto plugin: 3.10.0"


CONFIG = "you:\n  - name: dry\n    purpose: one home\n  - name: write-well\n    source: skill agent-conduct:write-well\n"
MANIFESTO_PLUGIN_VERSION = "3.6.0"
SKILL_PLUGIN_VERSION = "1.10.0"


@pytest.fixture
def project(host) -> Path:
    """A project whose stack is the dry manifesto and the write-well skill, both in the host's plugin cache."""
    login = host / "login"
    write(login / CACHE / "manifesto" / MANIFESTO_PLUGIN_VERSION / "manifestos" / "dry.md", "---\ntitle: Dry\n---\n\n# Dry\n\nOne home.\n")
    write(login / CACHE / "agent-conduct" / SKILL_PLUGIN_VERSION / "skills" / "write-well" / "SKILL.md", "---\nname: write-well\n---\nWell.\n")
    record_installed(login, manifesto=MANIFESTO_PLUGIN_VERSION, **{"agent-conduct": SKILL_PLUGIN_VERSION})
    return write(host / "project" / ".manifestos/config.yaml", CONFIG)


def test_each_element_reports_the_path_it_resolved_to(host, project, capsys):
    _, lines = doctor(capsys, "--config", str(project))

    login = host / "login"
    assert finding(lines, "element dry") == f"OK element dry: {login / CACHE / 'manifesto' / MANIFESTO_PLUGIN_VERSION / 'manifestos' / 'dry.md'}"
    assert finding(lines, "element write-well") == (
        f"OK element write-well: {login / CACHE / 'agent-conduct' / SKILL_PLUGIN_VERSION / 'skills' / 'write-well' / 'SKILL.md'}"
    )


def test_an_element_that_does_not_resolve_fails_with_the_resolvers_message(host, project, capsys):
    write(project, CONFIG + "  - name: kiss\n")

    status, lines = doctor(capsys, "--config", str(project))

    expected = host / "login" / CACHE / "manifesto" / MANIFESTO_PLUGIN_VERSION / "manifestos" / "kiss.md"
    assert finding(lines, "element kiss") == f"FAIL element kiss: element kiss did not resolve; tried {expected}"
    assert status == 1


def test_a_plugin_skill_whose_cached_version_matches_the_installed_one_is_ok(host, project, capsys):
    _, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, "skill agent-conduct:write-well") == f"OK skill agent-conduct:write-well: {SKILL_PLUGIN_VERSION}"


def test_a_plugin_skill_whose_cached_version_differs_from_the_installed_one_warns(host, project, capsys):
    record_installed(host / "login", manifesto=MANIFESTO_PLUGIN_VERSION, **{"agent-conduct": "1.9.0"})

    _, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, "skill agent-conduct:write-well") == (
        f"WARN skill agent-conduct:write-well: cached {SKILL_PLUGIN_VERSION}, installed_plugins.json records 1.9.0"
    )


def test_a_plugin_skill_with_no_installed_record_warns(host, project, capsys):
    record_installed(host / "login", manifesto=MANIFESTO_PLUGIN_VERSION)

    _, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, "skill agent-conduct:write-well") == (
        f"WARN skill agent-conduct:write-well: cached {SKILL_PLUGIN_VERSION}, installed_plugins.json has no record of agent-conduct"
    )


def test_a_plugin_skill_that_does_not_resolve_fails_as_an_element_and_gets_no_version_line(host, project, capsys):
    write(project, CONFIG + "  - name: absent\n    source: skill nowhere:absent\n")

    status, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, "element absent").startswith("FAIL element absent: element absent did not resolve")
    assert not [line for line in lines if " skill nowhere:absent:" in line]


FULL_PAIR = (".manifestos/interplay.md", ".manifestos/commitments.md")
MINIFIED_PAIR = (".manifestos/interplay.min.md", ".manifestos/commitments.min.md")
WRITING_SKILL = "/compile-commitments"


def write_session_files(project: Path, login: Path, names: tuple[str, ...], body: str = "Bound.\n") -> None:
    config = load(project)
    block = stack_block(resolve_stack(config.you, config.directory, config.registry, login))
    for name in names:
        write(project.parent.parent / name, f"{block}\n\n{body}")


def test_the_shipped_preamble_is_reported_when_the_project_has_no_override(host, project, capsys):
    _, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, "preamble") == "OK preamble: shipped"


def test_a_preamble_override_is_reported_by_its_file_name(host, project, capsys):
    write(project.parent.parent / ".manifestos/preamble.md", "Mine.\n")

    _, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, "preamble") == "OK preamble: .manifestos/preamble.md"


def test_current_session_files_are_ok(host, project, capsys):
    write_session_files(project, host / "login", FULL_PAIR + MINIFIED_PAIR)

    _, lines = doctor(capsys, "--config", str(project))

    assert [finding(lines, name) for name in FULL_PAIR + MINIFIED_PAIR] == [f"OK {name}: current" for name in FULL_PAIR + MINIFIED_PAIR]


def test_a_missing_full_file_fails_while_a_missing_min_file_only_warns_without_the_minified_flag(host, project, capsys):
    status, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, FULL_PAIR[0]) == f"FAIL {FULL_PAIR[0]}: {FULL_PAIR[0]} is missing; run {WRITING_SKILL}"
    assert finding(lines, MINIFIED_PAIR[1]) == f"WARN {MINIFIED_PAIR[1]}: {MINIFIED_PAIR[1]} is missing; run {WRITING_SKILL}"
    assert status == 1


def test_under_the_minified_flag_a_missing_min_file_fails_and_a_missing_full_file_only_warns(host, project, capsys):
    _, lines = doctor(capsys, "--config", str(project), "--minified")

    assert finding(lines, MINIFIED_PAIR[0]).startswith(f"FAIL {MINIFIED_PAIR[0]}: ")
    assert finding(lines, FULL_PAIR[1]).startswith(f"WARN {FULL_PAIR[1]}: ")


def test_a_stale_session_file_reports_the_changed_element(host, project, capsys):
    write_session_files(project, host / "login", FULL_PAIR + MINIFIED_PAIR)
    write(host / "login" / CACHE / "manifesto" / MANIFESTO_PLUGIN_VERSION / "manifestos" / "dry.md", "# Dry\n\nChanged.\n")

    _, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, FULL_PAIR[0]) == f"FAIL {FULL_PAIR[0]}: {FULL_PAIR[0]} is stale (changed: dry); run {WRITING_SKILL}"
    assert finding(lines, MINIFIED_PAIR[0]).startswith(f"WARN {MINIFIED_PAIR[0]}: {MINIFIED_PAIR[0]} is stale")


needs_digests = pytest.mark.skipif(importlib.util.find_spec("unharness.digests") is None, reason="C1 has not landed unharness.digests")
DIGESTED_CONFIG = "you:\n  - name: dry\n    purpose: one home\n  - name: kiss\n  - name: write-well\n    source: skill agent-conduct:write-well\n"
LONG_BODY = " ".join(f"word{number}" for number in range(40))
DRY_DIGEST = "Dry in five plain words."
KISS_DIGEST = "Kiss in five plain words."
STACK_DIGEST = "Both in four words."
STEMS = ("dry", "kiss", "dry+kiss")


def plugin_folder(host: Path) -> Path:
    return host / "login" / CACHE / "manifesto" / MANIFESTO_PLUGIN_VERSION


def stamp(host: Path, project: Path, folder: Path, *stems: str) -> None:
    """Write the index entries for the stems in the folder's index, with the manifestos' current hashes."""
    config = load(project)
    hashes = {document.name: document.sha256 for document in resolve_stack(config.you, config.directory, config.registry, host / "login")}
    index_path = folder / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    for stem in stems:
        index[stem] = {slug: hashes[slug] for slug in stem.split("+")}
    write(index_path, json.dumps(index))


@pytest.fixture
def healthy(host, project) -> Path:
    """A project with every artifact current: three elements, three plugin digests with their index, and all four session files."""
    for slug in ("dry", "kiss"):
        write(plugin_folder(host) / "manifestos" / f"{slug}.md", f"# {slug}\n\n{LONG_BODY}\n")
    write(project, DIGESTED_CONFIG)
    digests = plugin_folder(host) / "digests"
    write(digests / "dry.md", DRY_DIGEST)
    write(digests / "kiss.md", KISS_DIGEST)
    write(digests / "stacks" / "dry+kiss.md", STACK_DIGEST)
    stamp(host, project, digests, *STEMS)
    write_session_files(project, host / "login", FULL_PAIR + MINIFIED_PAIR)
    return project


@needs_digests
def test_a_healthy_project_gives_one_ok_line_per_check_and_exits_0(host, healthy, capsys):
    status, lines = doctor(capsys, "--config", str(healthy))

    assert status == 0
    assert [line.split(": ")[0] for line in lines] == [
        "OK layout", "OK config", "OK element dry", "OK element kiss", "OK element write-well", "OK skill agent-conduct:write-well",
        "OK digest dry", "OK digest kiss", "OK digest dry+kiss", "OK cover",
        *(f"OK {name}" for name in FULL_PAIR + MINIFIED_PAIR),
        "OK preamble", "OK claude", "OK switch registry", *(f"OK {name}" for name in SWITCH_NAMES), "OK uv", "OK manifesto plugin",
        "OK prompt size",
    ]


@needs_digests
def test_a_digest_line_names_where_the_digest_lives_and_that_it_is_current(host, healthy, capsys):
    _, lines = doctor(capsys, "--config", str(healthy))

    assert [finding(lines, f"digest {stem}") for stem in STEMS] == [f"OK digest {stem}: plugin, current" for stem in STEMS]


@needs_digests
def test_a_local_digest_wins_over_the_plugins(host, healthy, capsys):
    write(healthy.parent.parent / ".manifestos" / "digests" / "dry.md", "Local dry.")
    stamp(host, healthy, healthy.parent.parent / ".manifestos" / "digests", "dry")

    _, lines = doctor(capsys, "--config", str(healthy))

    assert finding(lines, "digest dry") == "OK digest dry: local, current"


@needs_digests
def test_a_missing_single_digest_warns_without_flags_and_fails_under_digests(host, healthy, capsys):
    (plugin_folder(host) / "digests" / "kiss.md").unlink()
    expected = (
        f"digest kiss: no digest for kiss: tried {healthy.parent.parent / '.manifestos' / 'digests' / 'kiss.md'} "
        f"and {plugin_folder(host) / 'digests' / 'kiss.md'}; run /compile-digest kiss"
    )

    _, plain = doctor(capsys, "--config", str(healthy))
    status, flagged = doctor(capsys, "--config", str(healthy), "--digests")

    assert finding(plain, "digest kiss") == f"WARN {expected}"
    assert finding(flagged, "digest kiss") == f"FAIL {expected}"
    assert status == 1


@needs_digests
def test_a_missing_single_that_a_stack_digest_covers_only_warns_under_stack_digests(host, healthy, capsys):
    (plugin_folder(host) / "digests" / "kiss.md").unlink()

    status, lines = doctor(capsys, "--config", str(healthy), "--stack-digests")

    assert finding(lines, "digest kiss").startswith("WARN digest kiss: no digest for kiss")
    assert finding(lines, "cover") == "OK cover: dry+kiss; 4 words"
    assert status == 0


@needs_digests
def test_a_stale_single_digest_warns_without_flags_and_fails_under_digests(host, healthy, capsys):
    write(plugin_folder(host) / "manifestos" / "dry.md", "# dry\n\nChanged.\n")
    write_session_files(healthy, host / "login", FULL_PAIR + MINIFIED_PAIR)
    path = plugin_folder(host) / "digests" / "dry.md"
    expected = f"digest dry: {path} is stale (changed: dry); run /compile-digest dry"

    _, plain = doctor(capsys, "--config", str(healthy))
    _, flagged = doctor(capsys, "--config", str(healthy), "--digests")

    assert finding(plain, "digest dry") == f"WARN {expected}"
    assert finding(flagged, "digest dry") == f"FAIL {expected}"


@needs_digests
def test_a_stack_digest_without_an_index_entry_fails_only_under_stack_digests(host, healthy, capsys):
    index_path = plugin_folder(host) / "digests" / "index.json"
    index = json.loads(index_path.read_text())
    del index["dry+kiss"]
    write(index_path, json.dumps(index))
    stack_path = plugin_folder(host) / "digests" / "stacks" / "dry+kiss.md"
    expected = f"digest dry+kiss: {stack_path} has no entry in {index_path}; run unharness stamp {stack_path}"

    _, singles_only = doctor(capsys, "--config", str(healthy), "--digests")
    _, with_stacks = doctor(capsys, "--config", str(healthy), "--stack-digests")

    assert finding(singles_only, "digest dry+kiss") == f"WARN {expected}"
    assert finding(with_stacks, "digest dry+kiss") == f"FAIL {expected}"


@needs_digests
def test_a_malformed_index_gives_its_message_on_every_digest_line_it_covers(host, healthy, capsys):
    index_path = plugin_folder(host) / "digests" / "index.json"
    write(index_path, "[]")

    _, lines = doctor(capsys, "--config", str(healthy))

    message = f"{index_path} is not a JSON object of stems to slug hashes; fix or delete it, then run unharness stamp on each digest it covers"
    assert [finding(lines, f"digest {stem}") for stem in STEMS] == [f"WARN digest {stem}: {message}" for stem in STEMS]


@needs_digests
def test_the_cover_line_names_the_chosen_stems_in_render_order_and_their_words(host, healthy, capsys):
    _, best_case = doctor(capsys, "--config", str(healthy))
    _, singles = doctor(capsys, "--config", str(healthy), "--digests")

    assert finding(best_case, "cover") == "OK cover: dry+kiss; 4 words"
    assert finding(singles, "cover") == "OK cover: dry, kiss; 10 words"


@needs_digests
def test_a_cover_that_the_flags_cannot_reach_fails_and_without_flags_only_warns(host, healthy, capsys):
    (plugin_folder(host) / "digests" / "kiss.md").unlink()

    _, plain = doctor(capsys, "--config", str(healthy))
    status, flagged = doctor(capsys, "--config", str(healthy), "--digests")

    assert finding(plain, "cover").startswith("OK cover: dry+kiss")
    assert finding(flagged, "cover").startswith("FAIL cover: no digest for kiss")
    assert status == 1


@needs_digests
def test_a_cover_with_no_digest_for_a_manifesto_warns_without_flags(host, healthy, capsys):
    (plugin_folder(host) / "digests" / "stacks" / "dry+kiss.md").unlink()
    (plugin_folder(host) / "digests" / "kiss.md").unlink()

    status, lines = doctor(capsys, "--config", str(healthy))

    assert finding(lines, "cover").startswith("WARN cover: no digest for kiss")
    assert status == 0


@needs_digests
def test_overlap_without_stack_digests_fails_the_cover_line_with_the_flags_message(host, healthy, capsys):
    status, lines = doctor(capsys, "--config", str(healthy), "--overlap")

    assert finding(lines, "cover") == "FAIL cover: --overlap requires --stack-digests"
    assert status == 1


@needs_digests
def test_prompt_size_counts_the_full_prompt_and_the_shortest_one(host, healthy, capsys):
    _, lines = doctor(capsys, "--config", str(healthy))

    full, shortest = map(int, re.fullmatch(r"OK prompt size: full (\d+) words; shortest (\d+) words", finding(lines, "prompt size")).groups())
    assert shortest < full


@needs_digests
def test_a_shortest_mode_that_cannot_compile_warns_in_the_size_line_with_its_message(host, healthy, capsys):
    (plugin_folder(host) / "digests" / "stacks" / "dry+kiss.md").unlink()
    (plugin_folder(host) / "digests" / "kiss.md").unlink()

    _, lines = doctor(capsys, "--config", str(healthy))

    assert finding(lines, "prompt size").startswith("WARN prompt size: shortest mode cannot compile: no digest for kiss")



def test_an_empty_stack_fails_the_config_line_as_prompt_would(host, project, capsys):
    write(project, "you:\n")

    status, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, "config") == "FAIL config: the stack is empty"
    assert status == 1


def test_an_element_that_does_not_resolve_leaves_out_the_checks_that_need_the_stack(host, project, capsys):
    write(project, CONFIG + "  - name: kiss\n")

    _, lines = doctor(capsys, "--config", str(project))

    names = [line.split(": ")[0].split(" ", 1)[1] for line in lines]
    assert names == ["layout", "config", "element dry", "element write-well", "element kiss", "skill agent-conduct:write-well", "preamble", "claude", "switch registry", *SWITCH_NAMES, "uv", "manifesto plugin"]


@needs_digests
def test_warnings_alone_exit_0(host, healthy, capsys):
    install_stub(host / "bin", "claude", STUB_VERSION.format(version="2.1.312"))

    status, lines = doctor(capsys, "--config", str(healthy))

    assert finding(lines, "claude").startswith("WARN claude")
    assert status == 0


@needs_digests
def test_doctor_makes_no_network_call(host, healthy, capsys, monkeypatch):
    def refuse(*arguments, **keywords):
        raise AssertionError("doctor opened a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)

    status, _ = doctor(capsys, "--config", str(healthy))

    assert status == 0


@needs_digests
def test_a_stale_single_fails_under_stack_digests_since_the_flag_implies_digests(host, healthy, capsys):
    write(plugin_folder(host) / "manifestos" / "dry.md", "# dry\n\nChanged.\n")
    write_session_files(healthy, host / "login", FULL_PAIR + MINIFIED_PAIR)

    status, lines = doctor(capsys, "--config", str(healthy), "--stack-digests")

    assert finding(lines, "digest dry").startswith("FAIL digest dry: ")
    assert status == 1


@needs_digests
def test_prompt_size_equals_the_word_count_of_the_prompts_it_names(host, project, capsys):
    write(plugin_folder(host) / "manifestos" / "dry.md", "# dry\n\nOne two.\n")
    write(project, "you:\n  - name: dry\n")
    write(plugin_folder(host) / "digests" / "dry.md", "Short.")
    stamp(host, project, plugin_folder(host) / "digests", "dry")
    write_session_files(project, host / "login", FULL_PAIR + MINIFIED_PAIR)
    prompts = {}
    for key, flags in (("full", []), ("shortest", ["--stack-digests", "--overlap", "--minified"])):
        main(["prompt", "--config", str(project), *flags])
        prompts[key] = len(capsys.readouterr().out.split())

    _, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, "prompt size") == f"OK prompt size: full {prompts['full']} words; shortest {prompts['shortest']} words"


def test_prompt_size_counts_the_preamble_the_constitution_and_the_session_file_bodies(host, project, capsys):
    write(plugin_folder(host) / "manifestos" / "dry.md", "# dry\n\nOne two.\n")
    write(project, "you:\n  - name: dry\n")
    write(plugin_folder(host) / "digests" / "dry.md", "Short.")
    stamp(host, project, plugin_folder(host) / "digests", "dry")
    write_session_files(project, host / "login", FULL_PAIR + MINIFIED_PAIR)
    write(project.parent.parent / ".manifestos/preamble.md", "Alpha beta.")

    _, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, "prompt size") == "OK prompt size: full 14 words; shortest 11 words"


MALFORMED_RECORDS = [
    "[]",
    '{"plugins": null}',
    '{"plugins": []}',
    '{"plugins": {"manifesto@marketplace": null}}',
    '{"plugins": {"manifesto@marketplace": [3]}}',
    '{"plugins": {"manifesto@marketplace": [{"scope": "user"}]}}',
]


@pytest.mark.parametrize("content", MALFORMED_RECORDS)
def test_a_malformed_installed_plugins_file_counts_as_no_record_instead_of_crashing(host, missing_config, capsys, content):
    write(host / "login" / "plugins" / "installed_plugins.json", content)

    status, lines = doctor(capsys, *missing_config)

    assert status == 1
    assert finding(lines, "manifesto plugin") == f"FAIL manifesto plugin: absent from {host / 'login' / 'plugins' / 'installed_plugins.json'}"


def test_an_unusable_record_of_one_plugin_leaves_the_records_of_the_others_standing(host, missing_config, capsys):
    write(host / "login" / "plugins" / "installed_plugins.json", json.dumps({"plugins": {
        "manifesto@marketplace": [{"version": "3.6.0"}],
        "other@marketplace": [{"scope": "user"}, 3],
    }}))

    _, lines = doctor(capsys, *missing_config)

    assert finding(lines, "manifesto plugin") == "OK manifesto plugin: 3.6.0"


def test_a_uvx_without_uv_prints_the_one_path_found(host, missing_config, capsys):
    (host / "bin" / "uv").unlink()

    _, lines = doctor(capsys, *missing_config)

    assert finding(lines, "uv") == f"OK uv: {host / 'bin' / 'uvx'}"


def test_the_config_line_prints_the_absolute_path_of_a_relative_config(host, project, capsys, monkeypatch):
    monkeypatch.chdir(project.parent)

    _, lines = doctor(capsys, "--config", project.name)

    assert lines[1] == f"OK config: {project.resolve()}"


def test_a_stack_of_skills_alone_reports_a_cover_of_none(host, project, capsys):
    write(project, "you:\n  - name: write-well\n    source: skill agent-conduct:write-well\n")

    _, lines = doctor(capsys, "--config", str(project))

    assert finding(lines, "cover") == "OK cover: none; 0 words"


def registry_of(monkeypatch, entries: list[dict]) -> None:
    monkeypatch.setattr("unharness.cli.shipped_switches", lambda: parse_switches(json.dumps(entries)))


def switch_entry(**overrides) -> dict:
    return {
        "name": "SWITCH_ONE", "kind": "env", "value": "1", "removes": "Some text", "documented": True, "control": True,
        "verified": [TESTED_CLAUDE], "default": True, "option": None, **overrides,
    }


def test_the_switch_registry_line_names_the_newest_version_and_the_entry_count(host, missing_config, capsys):
    _, lines = doctor(capsys, *missing_config)

    assert finding(lines, "switch registry") == "OK switch registry: newest 2.1.309; 13 switches"


def test_every_switch_verified_at_the_version_in_use_is_ok_in_registry_order(host, missing_config, capsys):
    _, lines = doctor(capsys, *missing_config)

    switch_lines = [line for line in lines if " switch " in line and "registry" not in line]
    assert switch_lines == [f"OK {name}: verified at {TESTED_CLAUDE}" for name in SWITCH_NAMES]


def test_a_version_off_the_registry_warns_on_every_switch_with_both_versions(host, missing_config, capsys):
    install_stub(host / "bin", "claude", STUB_VERSION.format(version="2.1.312"))

    status, lines = doctor(capsys, *missing_config)

    switch_lines = [line for line in lines if " switch " in line and "registry" not in line]
    assert switch_lines == [f"WARN {name}: verified at {TESTED_CLAUDE}, not at 2.1.312" for name in SWITCH_NAMES]


@pytest.mark.parametrize("claude_stub", [None, STUB_SILENT])
def test_a_claude_whose_version_is_unknown_warns_on_every_switch_with_the_newest_version(host, missing_config, capsys, claude_stub):
    if claude_stub is None:
        (host / "bin" / "claude").unlink()
    else:
        install_stub(host / "bin", "claude", claude_stub)

    _, lines = doctor(capsys, *missing_config)

    switch_lines = [line for line in lines if " switch " in line and "registry" not in line]
    assert switch_lines == [f"WARN {name}: verified at {TESTED_CLAUDE}, claude version unknown" for name in SWITCH_NAMES]


def test_a_switch_not_verified_at_the_chosen_version_is_left_out_and_names_its_last_version(host, missing_config, capsys, monkeypatch):
    registry_of(monkeypatch, [
        switch_entry(name="DROPPED", verified=["2.1.300"]),
        switch_entry(name="KEPT", removes="Other", verified=["2.1.300", TESTED_CLAUDE]),
    ])

    _, lines = doctor(capsys, *missing_config)

    assert finding(lines, "switch env DROPPED") == "WARN switch env DROPPED: left out; last verified at 2.1.300"
    assert finding(lines, "switch env KEPT") == f"OK switch env KEPT: verified at {TESTED_CLAUDE}"


def test_claude_version_replaces_the_detected_version_in_the_switch_lines_alone(host, missing_config, capsys, monkeypatch):
    registry_of(monkeypatch, [switch_entry(verified=["2.1.300", TESTED_CLAUDE])])
    (host / "bin" / "claude").unlink()

    _, lines = doctor(capsys, *missing_config, "--claude-version", "2.1.300")

    assert finding(lines, "claude") == "WARN claude: not on PATH; a shell function can still launch it"
    assert finding(lines, "switch env SWITCH_ONE") == "OK switch env SWITCH_ONE: verified at 2.1.300"


def test_claude_version_off_the_registry_chooses_the_nearest_lower_version(host, missing_config, capsys):
    _, lines = doctor(capsys, *missing_config, "--claude-version", "2.1.400")

    assert finding(lines, "switch env CLAUDE_CODE_ATTRIBUTION_HEADER") == (
        f"WARN switch env CLAUDE_CODE_ATTRIBUTION_HEADER: verified at {TESTED_CLAUDE}, not at 2.1.400"
    )


def test_a_malformed_claude_version_fails_in_one_line_with_status_1(host, missing_config, capsys):
    status = main(["doctor", *missing_config, "--claude-version", "latest"])

    captured = capsys.readouterr()
    assert (status, captured.out, captured.err) == (1, "", "unharness: --claude-version takes X.Y.Z, got latest\n")


def test_no_switch_line_fails_whatever_the_version(host, missing_config, capsys, monkeypatch):
    registry_of(monkeypatch, [switch_entry(verified=["2.1.300"]), switch_entry(name="TWO", verified=["2.1.300", "2.1.400"], removes="Other")])

    _, lines = doctor(capsys, *missing_config, "--claude-version", "1.0.0")

    assert [line for line in lines if line.startswith("FAIL switch")] == []
    assert len([line for line in lines if line.startswith("WARN switch env")]) == 2
