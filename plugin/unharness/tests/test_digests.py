import json
import random
import re
from hashlib import sha256
from itertools import combinations
from pathlib import Path

import pytest
from helpers import deadline, write
from unharness.cli import main
from unharness.compile import stack_block, stack_view
from unharness.config import Element, UnharnessError, load
from unharness.digests import Cover, Digest, DigestMode, choose_cover, select_cover
from unharness.resolve import resolve_stack

SLUGS = ("alpha", "beta", "gamma", "delta")
PURPOSES = {"alpha": "first rule", "beta": "second rule", "gamma": "third rule", "delta": None}


def source_hash(body: str) -> str:
    return sha256(body.strip().encode()).hexdigest()


class World:
    """A plugin folder with four manifestos, and a project whose config names them in order."""

    def __init__(self, root: Path, order=None, purposes=PURPOSES, tail: str = "", names: dict | None = None, slugs=SLUGS):
        self.root = root
        self.plugin = root / "plugin"
        self.project = root / "project"
        self.login = root / "login"
        order = order or slugs
        self.bodies = {slug: f"# {slug}\n\nThe {slug} manifesto." for slug in slugs}
        for slug, body in self.bodies.items():
            write(self.plugin / "manifestos" / f"{slug}.md", f"---\ntitle: {slug}\n---\n\n{body}\n")
        names = names or {}
        entries = "".join(
            f"  - name: {names.get(slug, slug)}\n"
            + (f"    source: manifesto {slug}\n" if slug in names else "")
            + (f"    purpose: {purposes[slug]}\n" if purposes.get(slug) else "")
            for slug in order
        )
        self.config = write(self.project / ".manifestos/config.yaml", f"manifesto_dir: ../plugin\n\nyou:\n{entries}{tail}")

    def digest(self, stem: str, text: str, place: str = "plugin", index: bool = True, hashes: dict | None = None) -> Path:
        slugs = stem.split("+")
        folder = self.plugin / "digests" if place == "plugin" else self.project / ".manifestos" / "digests"
        path = write((folder / "stacks" if place == "plugin" and len(slugs) > 1 else folder) / f"{stem}.md", text)
        if index:
            self.index(folder, {stem: hashes or {slug: source_hash(self.bodies[slug]) for slug in slugs}})
        return path

    def index(self, folder: Path, entries: dict) -> None:
        index_path = folder / "index.json"
        known = json.loads(index_path.read_text()) if index_path.is_file() else {}
        write(index_path, json.dumps({**known, **entries}))

    def write_session_files(self) -> None:
        config = load(self.config)
        stack = stack_block(resolve_stack(config.you, config.directory, config.registry, self.login))
        write(self.project / ".manifestos/interplay.md", f"{stack}\n\n<interplay>\nAgree.\n</interplay>\n")
        write(self.project / ".manifestos/commitments.md", f"{stack}\n\n<commitments>\nI must, and I will.\n</commitments>\n")

    def write_minified_files(self) -> None:
        config = load(self.config)
        stack = stack_block(resolve_stack(config.you, config.directory, config.registry, self.login))
        write(self.project / ".manifestos/interplay.min.md", f"{stack}\n\n<interplay>\nAgree, briefly.\n</interplay>\n")
        write(self.project / ".manifestos/commitments.min.md", f"{stack}\n\n<commitments>\nI must, briefly.\n</commitments>\n")

    def run(self, monkeypatch, capsys, *arguments: str) -> tuple[int, str, str]:
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(self.login))
        self.write_session_files()
        self.write_minified_files()
        status = main([*arguments[:1], "--config", str(self.config), *arguments[1:]])
        captured = capsys.readouterr()
        return status, captured.out, captured.err

    def prompt(self, monkeypatch, capsys, *flags: str) -> tuple[int, str, str]:
        return self.run(monkeypatch, capsys, "prompt", *flags)


@pytest.fixture
def world(tmp_path) -> World:
    return World(tmp_path)


def constitution_of(output: str) -> str:
    return output.split("<constitution>\n", 1)[1].split("\n</constitution>", 1)[0]


def single_block(slug: str, text: str, purpose: str | None = None) -> str:
    governs = f' governs="{purpose}"' if purpose else ""
    return f"<{slug}{governs}>\n{text}\n</{slug}>"


def test_digests_replace_each_manifesto_with_its_single_digest_in_config_order(world, monkeypatch, capsys):
    for slug in SLUGS:
        world.digest(slug, f"  {slug.upper()} DIGEST \n\n")

    status, out, _ = world.prompt(monkeypatch, capsys, "--digests")

    assert status == 0
    assert constitution_of(out) == "\n".join(single_block(slug, f"{slug.upper()} DIGEST", PURPOSES[slug]) for slug in SLUGS)


def test_overlap_without_stack_digests_stops_with_its_message(world, monkeypatch, capsys):
    status, out, err = world.prompt(monkeypatch, capsys, "--overlap")

    assert (status, out) == (1, "")
    assert err == "unharness: --overlap requires --stack-digests\n"


def test_stack_digests_alone_selects_digests_for_every_manifesto(world, monkeypatch, capsys):
    for slug in SLUGS:
        world.digest(slug, f"{slug.upper()} DIGEST")

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 0
    assert "ALPHA DIGEST" in out and "The alpha manifesto." not in out


MODE_FLAGS = ["--digests", "--stack-digests", "--overlap", "--minified"]


@pytest.mark.parametrize("flag", MODE_FLAGS)
def test_stack_rejects_the_mode_flags(world, monkeypatch, capsys, flag):
    with pytest.raises(SystemExit) as stopped:
        world.run(monkeypatch, capsys, "stack", flag)

    assert stopped.value.code == 2


def stale_hashes(world, slug: str) -> dict:
    return {slug: source_hash("an earlier text")}


def test_a_local_digest_wins_over_the_plugins_for_its_stem(world, monkeypatch, capsys):
    for slug in SLUGS:
        world.digest(slug, f"PLUGIN {slug}")
    world.digest("beta", "LOCAL beta", place="local")

    status, out, _ = world.prompt(monkeypatch, capsys, "--digests")

    assert status == 0
    assert "LOCAL beta" in out and "PLUGIN beta" not in out and "PLUGIN alpha" in out


def test_a_stale_local_entry_refuses_even_when_the_plugin_copy_is_current(world, monkeypatch, capsys):
    for slug in SLUGS:
        world.digest(slug, f"PLUGIN {slug}")
    local = world.digest("beta", "LOCAL beta", place="local", hashes=stale_hashes(world, "beta"))

    status, out, err = world.prompt(monkeypatch, capsys, "--digests")

    assert (status, out) == (1, "")
    assert err == f"unharness: {local} is stale (changed: beta); run /compile-digest beta\n"


def test_a_manifesto_without_a_digest_refuses_naming_both_places_tried(world, monkeypatch, capsys):
    for slug in ("alpha", "beta", "delta"):
        world.digest(slug, f"{slug} digest")

    status, out, err = world.prompt(monkeypatch, capsys, "--digests")

    local, plugin = world.project / ".manifestos" / "digests" / "gamma.md", world.plugin / "digests" / "gamma.md"
    assert (status, out) == (1, "")
    assert err == f"unharness: no digest for gamma: tried {local} and {plugin}; run /compile-digest gamma\n"


def test_a_digest_without_an_index_entry_refuses_naming_stamp(world, monkeypatch, capsys):
    for slug in SLUGS:
        world.digest(slug, f"{slug} digest")
    unindexed = world.digest("gamma", "gamma digest", index=False)
    (world.plugin / "digests" / "index.json").write_text(json.dumps({s: {s: source_hash(world.bodies[s])} for s in ("alpha", "beta", "delta")}))

    status, _, err = world.prompt(monkeypatch, capsys, "--digests")

    assert status == 1
    assert err == f"unharness: {unindexed} has no entry in {world.plugin / 'digests' / 'index.json'}; run unharness stamp {unindexed}\n"


def test_an_entry_with_an_extra_slug_counts_as_missing(world, monkeypatch, capsys):
    for slug in SLUGS:
        world.digest(slug, f"{slug} digest")
    extra = {"alpha": source_hash(world.bodies["alpha"]), "beta": source_hash(world.bodies["beta"])}
    world.index(world.plugin / "digests", {"alpha": extra})

    status, _, err = world.prompt(monkeypatch, capsys, "--digests")

    path = world.plugin / "digests" / "alpha.md"
    assert status == 1
    assert err == f"unharness: {path} has no entry in {world.plugin / 'digests' / 'index.json'}; run unharness stamp {path}\n"


def test_a_stale_digest_names_the_changed_manifestos_and_compile_digest(world, monkeypatch, capsys):
    for slug in SLUGS:
        world.digest(slug, f"{slug} digest")
    world.bodies["delta"] = "changed"
    (world.plugin / "manifestos" / "delta.md").write_text("changed\n")

    status, _, err = world.prompt(monkeypatch, capsys, "--digests")

    path = world.plugin / "digests" / "delta.md"
    assert status == 1
    assert err == f"unharness: {path} is stale (changed: delta); run /compile-digest delta\n"


@pytest.mark.parametrize("content", ["not json", "[]", '{"alpha": "text"}', '{"alpha": {"alpha": 1}}'])
def test_an_index_that_is_not_stems_to_slug_hashes_refuses(world, monkeypatch, capsys, content):
    for slug in SLUGS:
        world.digest(slug, f"{slug} digest")
    index = world.plugin / "digests" / "index.json"
    index.write_text(content)

    status, _, err = world.prompt(monkeypatch, capsys, "--digests")

    assert status == 1
    assert err == f"unharness: {index} is not a JSON object of stems to slug hashes; fix or delete it, then run unharness stamp on each digest it covers\n"


def stack_block_of(names: list[str], text: str) -> str:
    purposes = [PURPOSES[name] for name in names if PURPOSES[name]]
    governs = f' governs="{"; ".join(purposes)}"' if purposes else ""
    tag = "+".join(names)
    return f"<{tag}{governs}>\n{text}\n</{tag}>"


def digest_all_singles(world, length: int = 10) -> None:
    for slug in SLUGS:
        world.digest(slug, slug[0].upper() * length)


def test_a_shorter_stack_digest_replaces_its_singles_at_its_first_members_position(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "AB")

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 0
    assert constitution_of(out) == "\n".join([
        stack_block_of(["alpha", "beta"], "AB"), single_block("gamma", "G" * 10, "third rule"), single_block("delta", "D" * 10),
    ])


def test_a_longer_stack_digest_loses_to_its_singles(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "X" * 21)

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 0
    assert "alpha+beta" not in out and "A" * 10 in out


def test_digests_alone_ignore_stack_digests(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "AB")

    status, out, _ = world.prompt(monkeypatch, capsys, "--digests")

    assert status == 0 and "alpha+beta" not in out


def test_a_stack_digest_alone_covers_a_manifesto_that_has_no_single(world, monkeypatch, capsys):
    for slug in ("gamma", "delta"):
        world.digest(slug, slug[0].upper() * 10)
    world.digest("alpha+beta", "X" * 50)

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 0
    assert constitution_of(out).startswith(stack_block_of(["alpha", "beta"], "X" * 50))


def test_a_manifesto_that_only_a_stack_digest_covers_refuses_under_digests(world, monkeypatch, capsys):
    for slug in ("gamma", "delta"):
        world.digest(slug, slug[0].upper() * 10)
    world.digest("alpha+beta", "X" * 50)

    status, _, err = world.prompt(monkeypatch, capsys, "--digests")

    assert status == 1
    assert err.startswith("unharness: no digest for alpha: tried ")


def test_a_manifesto_with_neither_digest_refuses_naming_its_slug_under_stack_digests(world, monkeypatch, capsys):
    for slug in ("beta", "gamma", "delta"):
        world.digest(slug, slug[0].upper() * 10)
    world.digest("beta+gamma", "BG")

    status, _, err = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 1
    assert err.startswith("unharness: no digest for alpha: tried ")


def test_a_stack_digest_in_the_plugin_root_is_no_candidate(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "AB")
    (world.plugin / "digests" / "stacks" / "alpha+beta.md").rename(world.plugin / "digests" / "alpha+beta.md")

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 0 and "alpha+beta" not in out


def test_a_stack_digest_with_a_slug_outside_the_stack_never_enters(world, tmp_path, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "AB")
    smaller = World(tmp_path / "smaller", order=("alpha", "gamma", "delta"))
    for slug in SLUGS:
        smaller.digest(slug, slug[0].upper() * 10)
    smaller.digest("alpha+beta", "AB", hashes={"alpha": "stale", "beta": "stale"})

    status, out, _ = smaller.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 0 and "alpha+beta" not in out


def test_chosen_stack_digests_stay_disjoint_without_overlap(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "AB")
    world.digest("beta+gamma", "BGBGBG")

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 0
    assert constitution_of(out) == "\n".join([
        stack_block_of(["alpha", "beta"], "AB"), single_block("gamma", "G" * 10, "third rule"), single_block("delta", "D" * 10),
    ])


def test_chosen_stack_digests_share_a_member_with_overlap_and_both_tags_name_it(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "AB")
    world.digest("beta+gamma", "BGBGBG")

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests", "--overlap")

    assert status == 0
    assert constitution_of(out) == "\n".join([
        stack_block_of(["alpha", "beta"], "AB"), stack_block_of(["beta", "gamma"], "BGBGBG"), single_block("delta", "D" * 10),
    ])


def test_equal_characters_go_to_the_cover_with_fewer_files(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "X" * 20)

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 0 and "alpha+beta" in out


def test_equal_characters_and_files_go_to_the_smaller_sorted_stems(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "XX")
    world.digest("beta+gamma", "YY")

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 0
    assert constitution_of(out) == "\n".join([
        single_block("alpha", "A" * 10, "first rule"), stack_block_of(["beta", "gamma"], "YY"), single_block("delta", "D" * 10),
    ])


def test_coverage_that_only_overlapping_stack_digests_reach_refuses_without_overlap(world, monkeypatch, capsys):
    world.digest("delta", "D" * 10)
    world.digest("alpha+beta", "AB")
    world.digest("beta+gamma", "BG")

    status, out, err = world.prompt(monkeypatch, capsys, "--stack-digests")
    overlapping, _, _ = world.prompt(monkeypatch, capsys, "--stack-digests", "--overlap")

    assert (status, out) == (1, "")
    assert err == "unharness: no cover without overlap; add --overlap or run /compile-digest <slug> for each of: alpha, beta, gamma\n"
    assert overlapping == 0


def test_a_stack_digest_block_omits_governs_without_purposes_and_replaces_quotes(tmp_path, monkeypatch, capsys):
    purposes = {"alpha": 'say "one"', "beta": None, "gamma": None, "delta": None}
    bare = {slug: None for slug in SLUGS}
    for root, given, expected in (("quoted", purposes, "say 'one'"), ("bare", bare, None)):
        world = World(tmp_path / root, purposes=given)
        digest_all_singles(world)
        world.digest("alpha+beta", "AB")

        status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests")

        governs = f' governs="{expected}"' if expected else ""
        assert status == 0
        assert constitution_of(out).startswith(f"<alpha+beta{governs}>\nAB\n</alpha+beta>\n")


def test_two_stack_blocks_at_one_position_follow_stem_order(tmp_path, monkeypatch, capsys):
    world = World(tmp_path, order=("beta", "alpha", "gamma", "delta"))
    digest_all_singles(world)
    world.digest("alpha+beta", "AB")
    world.digest("beta+gamma", "BG")

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests", "--overlap")

    assert status == 0
    assert constitution_of(out).startswith("<beta+alpha governs=\"second rule; first rule\">\nAB\n</beta+alpha>\n<beta+gamma")


def test_skills_and_files_enter_in_full_in_every_mode(tmp_path, monkeypatch, capsys):
    write(tmp_path / "login" / "skills" / "my-skill" / "SKILL.md", "---\nname: my-skill\n---\nSKILL TEXT\n")
    write(tmp_path / "project" / "notes.md", "NOTES TEXT\n")
    world = World(tmp_path, tail="  - name: my-skill\n    source: skill my-skill\n  - source: file notes.md\n")
    digest_all_singles(world)

    status, out, _ = world.prompt(monkeypatch, capsys, "--digests")

    assert status == 0
    assert constitution_of(out).endswith("<my-skill>\nSKILL TEXT\n</my-skill>\n<notes>\nNOTES TEXT\n</notes>")


@pytest.mark.parametrize("flags", [["--digests"], ["--stack-digests"], ["--stack-digests", "--overlap"]])
def test_a_manifesto_named_twice_refuses_in_every_digest_mode(tmp_path, monkeypatch, capsys, flags):
    world = World(tmp_path, order=("alpha", "beta", "alpha"))
    digest_all_singles(world)

    status, out, err = world.prompt(monkeypatch, capsys, *flags)

    assert (status, out) == (1, "")
    assert err == "unharness: manifesto alpha appears twice in the stack; digest modes need each once\n"


def test_an_unusable_stack_digest_that_is_a_candidate_stops_the_compile(world, monkeypatch, capsys):
    digest_all_singles(world)
    stacked = world.digest("alpha+beta", "X" * 50, hashes={"alpha": "old", "beta": source_hash(world.bodies["beta"])})

    status, _, err = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 1
    assert err == f"unharness: {stacked} is stale (changed: alpha); run /compile-digest alpha beta\n"


def stamp(world, monkeypatch, capsys, digest: Path):
    return world.run(monkeypatch, capsys, "stamp", str(digest))


def test_stamp_creates_the_index_beside_a_local_digest_and_reports_it(world, monkeypatch, capsys):
    digest = write(world.project / ".manifestos" / "digests" / "beta.md", "BETA DIGEST")

    status, out, _ = stamp(world, monkeypatch, capsys, digest)

    index = digest.parent / "index.json"
    assert status == 0
    assert out == f"stamped beta in {index}\n"
    assert index.read_text() == json.dumps({"beta": {"beta": source_hash(world.bodies["beta"])}}, indent=2, sort_keys=True) + "\n"


def test_stamp_replaces_its_stems_entry_and_keeps_the_others(world, monkeypatch, capsys):
    digest = write(world.project / ".manifestos" / "digests" / "beta.md", "BETA DIGEST")
    world.index(digest.parent, {"beta": {"beta": "old"}, "alpha": {"alpha": "kept"}, "a+b": {"a": "1", "b": "2"}})

    stamp(world, monkeypatch, capsys, digest)

    assert json.loads((digest.parent / "index.json").read_text()) == {
        "a+b": {"a": "1", "b": "2"}, "alpha": {"alpha": "kept"}, "beta": {"beta": source_hash(world.bodies["beta"])},
    }


def test_stamp_writes_a_plugin_stack_digests_entry_in_the_parent_of_stacks(world, monkeypatch, capsys):
    digest = write(world.plugin / "digests" / "stacks" / "alpha+beta.md", "AB")

    status, out, _ = stamp(world, monkeypatch, capsys, digest)

    index = world.plugin / "digests" / "index.json"
    assert status == 0 and out == f"stamped alpha+beta in {index}\n"
    assert json.loads(index.read_text()) == {"alpha+beta": {slug: source_hash(world.bodies[slug]) for slug in ("alpha", "beta")}}


def test_stamp_hashes_equal_the_stack_blocks_hashes_for_the_same_manifestos(world, monkeypatch, capsys):
    digest = write(world.plugin / "digests" / "stacks" / "alpha+beta.md", "AB")
    stamp(world, monkeypatch, capsys, digest)
    _, stack_out, _ = world.run(monkeypatch, capsys, "stack")

    entry = json.loads((world.plugin / "digests" / "index.json").read_text())["alpha+beta"]

    for slug in ("alpha", "beta"):
        assert f"{slug} {entry[slug]} " in stack_out


def test_a_stamped_digest_loads_under_digests_without_further_steps(world, monkeypatch, capsys):
    for slug in SLUGS:
        stamp(world, monkeypatch, capsys, write(world.project / ".manifestos" / "digests" / f"{slug}.md", f"{slug} digest"))

    status, out, _ = world.prompt(monkeypatch, capsys, "--digests")

    assert status == 0 and "alpha digest" in out


@pytest.mark.parametrize("stem", ["beta+alpha", "alpha+alpha", "alpha++beta"])
def test_stamp_refuses_a_stem_that_is_not_sorted_distinct_slugs(world, monkeypatch, capsys, stem):
    digest = write(world.project / ".manifestos" / "digests" / f"{stem}.md", "text")

    status, out, err = stamp(world, monkeypatch, capsys, digest)

    assert (status, out) == (1, "")
    assert err == f"unharness: {stem}.md is not named by sorted, distinct slugs joined by +\n"
    assert not (digest.parent / "index.json").exists()


def test_stamp_refuses_a_slug_that_does_not_resolve_with_the_resolvers_message(world, monkeypatch, capsys):
    digest = write(world.project / ".manifestos" / "digests" / "ghost.md", "text")

    status, _, err = stamp(world, monkeypatch, capsys, digest)

    assert status == 1
    assert err == f"unharness: element ghost did not resolve; tried {world.plugin / 'manifestos' / 'ghost.md'}\n"


def test_stamp_refuses_a_missing_digest(world, monkeypatch, capsys):
    missing = world.project / ".manifestos" / "digests" / "beta.md"

    status, _, err = stamp(world, monkeypatch, capsys, missing)

    assert status == 1
    assert err == f"unharness: no digest at {missing}\n"


def test_stamp_refuses_a_malformed_index_instead_of_overwriting_it(world, monkeypatch, capsys):
    digest = write(world.project / ".manifestos" / "digests" / "beta.md", "text")
    index = write(digest.parent / "index.json", "not json")

    status, _, err = stamp(world, monkeypatch, capsys, digest)

    assert status == 1 and "is not a JSON object of stems to slug hashes" in err
    assert index.read_text() == "not json"


@pytest.mark.parametrize("flag", MODE_FLAGS)
def test_stamp_rejects_the_mode_flags(world, monkeypatch, capsys, flag):
    digest = write(world.project / ".manifestos" / "digests" / "beta.md", "text")

    with pytest.raises(SystemExit) as stopped:
        world.run(monkeypatch, capsys, "stamp", str(digest), flag)

    assert stopped.value.code == 2


def test_stack_given_slugs_prints_those_manifestos_alone_without_purposes(world, monkeypatch, capsys):
    status, out, _ = world.run(monkeypatch, capsys, "stack", "gamma", "alpha")

    config = load(world.config)
    expected = resolve_stack(
        [Element(slug, None, "manifesto", slug) for slug in ("gamma", "alpha")], config.directory, config.registry, world.login,
    )
    assert status == 0
    assert out == stack_view(expected) + "\n"
    assert "governs" not in out and "beta" not in out


def test_select_cover_returns_the_chosen_stacks_and_the_singles_they_leave(world):
    digest_all_singles(world)
    world.digest("alpha+beta", "AB")
    config = load(world.config)
    documents = resolve_stack(config.you, config.directory, config.registry, world.login)

    cover = select_cover(config.you, documents, config.directory, world.plugin, DigestMode(stacks=True, overlap=False))

    assert [digest.stem for digest in cover.stacks] == ["alpha+beta"]
    assert sorted(cover.singles) == ["delta", "gamma"]


def test_digests_key_by_slug_while_the_blocks_carry_the_element_names(tmp_path, monkeypatch, capsys):
    world = World(tmp_path, names={"alpha": "first-rule", "beta": "second-rule"})
    digest_all_singles(world)
    world.digest("alpha+beta", "AB")

    _, stacked, _ = world.prompt(monkeypatch, capsys, "--stack-digests")
    _, singles, _ = world.prompt(monkeypatch, capsys, "--digests")

    assert constitution_of(stacked).startswith('<first-rule+second-rule governs="first rule; second rule">\nAB\n</first-rule+second-rule>')
    assert single_block("first-rule", "A" * 10, "first rule") in constitution_of(singles)


def test_a_local_stack_digest_wins_over_the_plugins_for_its_stem(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "PP")
    world.digest("alpha+beta", "LLLL", place="local")

    status, out, _ = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert status == 0
    assert "LLLL" in out and "PP" not in out


def test_a_stale_local_stack_entry_refuses_even_when_the_plugin_copy_is_current(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "PP")
    local = world.digest("alpha+beta", "LLLL", place="local", hashes={"alpha": source_hash("an earlier text"), "beta": source_hash(world.bodies["beta"])})

    status, out, err = world.prompt(monkeypatch, capsys, "--stack-digests")

    assert (status, out) == (1, "")
    assert err == f"unharness: {local} is stale (changed: alpha); run /compile-digest alpha beta\n"


def test_the_minified_pair_loads_with_every_digest_flag_though_it_was_compiled_against_the_full_stack(world, monkeypatch, capsys):
    digest_all_singles(world)
    world.digest("alpha+beta", "AB")

    status, out, err = world.prompt(monkeypatch, capsys, "--stack-digests", "--overlap", "--minified")

    assert status == 0, err
    assert stack_block_of(["alpha", "beta"], "AB") in out
    assert out.endswith("<interplay>\nAgree, briefly.\n</interplay>\n\n<commitments>\nI must, briefly.\n</commitments>\n")


LARGE_STACK = tuple(f"m{number:02d}" for number in range(12))
STACK_DIGEST_TIMEOUT_SECONDS = 20


@pytest.mark.parametrize("flags", [("--stack-digests",), ("--stack-digests", "--overlap")])
def test_a_stack_of_twelve_with_every_pair_digest_picks_its_cover_in_seconds(tmp_path, monkeypatch, capsys, flags):
    world = World(tmp_path, slugs=LARGE_STACK, purposes={})
    for slug in LARGE_STACK:
        world.digest(slug, "S" * 10)
    for pair in combinations(LARGE_STACK, 2):
        world.digest("+".join(pair), "P" * 15)

    with deadline(STACK_DIGEST_TIMEOUT_SECONDS):
        status, out, err = world.prompt(monkeypatch, capsys, *flags)

    assert status == 0, err
    assert re.findall(r"^<(m\d\d\+m\d\d)>", constitution_of(out), re.MULTILINE) == [
        f"{first}+{second}" for first, second in zip(LARGE_STACK[::2], LARGE_STACK[1::2])
    ]


def every_subset_cover(slugs, singles, stacks, overlap):
    """The reference the cover search must equal: rank every subset of the stack digests by the spec's key."""
    best = None
    for size in range(len(stacks) + 1):
        for chosen in combinations(sorted(stacks, key=lambda digest: digest.stem), size):
            members = [digest.stem.split("+") for digest in chosen]
            covered = {slug for group in members for slug in group}
            if not overlap and sum(map(len, members)) != len(covered):
                continue
            left = [slug for slug in slugs if slug not in covered]
            if any(slug not in singles for slug in left):
                continue
            digests = [*chosen, *(singles[slug] for slug in left)]
            key = (sum(len(digest.text) for digest in digests), len(digests), sorted(digest.stem for digest in digests))
            if best is None or key < best[0]:
                best = (key, Cover(chosen, {slug: singles[slug] for slug in left}))
    return None if best is None else best[1]


@pytest.mark.parametrize("overlap", [False, True])
def test_the_cover_search_equals_the_ranking_of_every_subset_on_random_stacks(overlap):
    chance = random.Random(2026)
    slugs = [f"s{number}" for number in range(5)]
    for _ in range(300):
        singles = {slug: Digest(slug, "x" * chance.randint(1, 6)) for slug in slugs if chance.random() < 0.7}
        stems = {"+".join(sorted(chance.sample(slugs, chance.randint(2, 4)))) for _ in range(chance.randint(0, 7))}
        stacks = [Digest(stem, "y" * chance.randint(1, 9)) for stem in stems]
        expected = every_subset_cover(slugs, singles, stacks, overlap)
        try:
            found = choose_cover(slugs, singles, stacks, DigestMode(stacks=True, overlap=overlap))
        except UnharnessError:
            found = None
        assert found == expected


def test_a_flag_refusal_comes_before_an_unresolved_element_is_reported(tmp_path, monkeypatch, capsys):
    world = World(tmp_path, tail="  - name: ghost\n")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(world.login))

    status = main(["prompt", "--config", str(world.config), "--overlap"])

    captured = capsys.readouterr()
    assert (status, captured.out) == (1, "")
    assert captured.err == "unharness: --overlap requires --stack-digests\n"


REVIEWER_TAIL = "\nsubagents:\n  reviewer:\n    - alpha\n    - beta\n"


def agent_prompt(world, monkeypatch, capsys, *flags: str) -> tuple[int, str, str]:
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(world.login))
    config = load(world.config)
    stack = stack_block(resolve_stack(config.subagents["reviewer"], config.directory, config.registry, world.login))
    folder = world.project / ".manifestos" / "agents" / "reviewer"
    write(folder / "interplay.md", f"{stack}\n\n<interplay>\nAgree.\n</interplay>\n")
    write(folder / "commitments.md", f"{stack}\n\n<commitments>\nI will.\n</commitments>\n")
    status = main(["prompt", "--config", str(world.config), "--agent", "reviewer", *flags])
    captured = capsys.readouterr()
    return status, captured.out, captured.err


def test_prompt_agent_with_digests_swaps_the_matched_keys_manifestos_for_their_digests(tmp_path, monkeypatch, capsys):
    world = World(tmp_path, tail=REVIEWER_TAIL)
    for slug in SLUGS:
        world.digest(slug, slug[0].upper() * 10)

    status, out, _ = agent_prompt(world, monkeypatch, capsys, "--digests")

    assert status == 0
    assert constitution_of(out) == "\n".join([single_block("alpha", "A" * 10), single_block("beta", "B" * 10)])


def test_prompt_agent_with_stack_digests_swaps_the_matched_keys_members_for_their_stack_digest(tmp_path, monkeypatch, capsys):
    world = World(tmp_path, tail=REVIEWER_TAIL)
    for slug in SLUGS:
        world.digest(slug, slug[0].upper() * 10)
    world.digest("alpha+beta", "AB")

    status, out, _ = agent_prompt(world, monkeypatch, capsys, "--stack-digests")

    assert status == 0
    assert constitution_of(out) == "<alpha+beta>\nAB\n</alpha+beta>"
