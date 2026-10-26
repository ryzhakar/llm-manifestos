"""Locate, validate, and choose the digests that stand in for manifesto texts, and stamp their index."""

import json
from dataclasses import dataclass
from pathlib import Path

from unharness.config import DIGESTS_PATH, TEXT_ENCODING, Element, UnharnessError
from unharness.resolve import Document, manifesto_elements, manifesto_slug, resolve_stack

PLUGIN_FOLDER = "digests"
STACKS_FOLDER = "stacks"
INDEX_FILE = "index.json"
COMPILE_DIGEST_COMMAND = "/compile-digest"
STEM_SEPARATOR = "+"
PURPOSE_SEPARATOR = "; "
DIGESTS_FLAG = "--digests"
OVERLAP_FLAG = "--overlap"
STACK_DIGESTS_FLAG = "--stack-digests"
LOCAL = "local"
PLUGIN = "plugin"


@dataclass(frozen=True)
class DigestMode:
    stacks: bool
    overlap: bool


@dataclass(frozen=True)
class Located:
    stem: str
    path: Path
    place: str


@dataclass(frozen=True)
class Digest:
    stem: str
    text: str


@dataclass(frozen=True)
class Cover:
    stacks: tuple[Digest, ...]
    singles: dict[str, Digest]


def digest_mode(digests: bool, stack_digests: bool, overlap: bool) -> DigestMode | None:
    """Return the digest mode the flags name, None when they name none; refuse --overlap without --stack-digests."""
    if overlap and not stack_digests:
        raise UnharnessError(f"{OVERLAP_FLAG} requires {STACK_DIGESTS_FLAG}")
    if not (digests or stack_digests):
        return None
    return DigestMode(stack_digests, overlap)


def constitution_blocks(
    elements: list[Element], documents: list[Document], directory: Path, plugin_folder: Path, mode: DigestMode | None,
) -> list[Document]:
    """Return the constitution's blocks in config order: full texts, or the cover's digests under a mode."""
    if mode is None:
        return list(documents)
    return _layout(elements, documents, select_cover(elements, documents, directory, plugin_folder, mode))


def select_cover(
    elements: list[Element], documents: list[Document], directory: Path, plugin_folder: Path, mode: DigestMode,
) -> Cover:
    """Return the cover the mode chooses for the stack, or stop with the refusal that names its fix."""
    hashes = stack_hashes(elements, documents)
    slugs = stack_slugs(elements)
    _require_each_once(slugs)
    singles = _usable_singles(slugs, hashes, directory, plugin_folder)
    stacks = _usable_stacks(slugs, hashes, directory, plugin_folder) if mode.stacks else []
    _require_every_slug_covered(slugs, singles, stacks, directory, plugin_folder)
    return choose_cover(slugs, singles, stacks, mode)


def stack_slugs(elements: list[Element]) -> list[str]:
    """Return the slug of each manifesto element, in config order."""
    return [slug for slug in map(manifesto_slug, elements) if slug]


def stack_hashes(elements: list[Element], documents: list[Document]) -> dict[str, str]:
    """Return the current source hash of each manifesto element, by slug."""
    return {slug: document.sha256 for element, document in zip(elements, documents) if (slug := manifesto_slug(element))}


def slugs_of(stem: str) -> list[str]:
    """Return the member slugs a stem names."""
    return stem.split(STEM_SEPARATOR)


def index_path_of(digest_path: Path) -> Path:
    """Return the index that covers the digest: beside it, or beside its stacks folder."""
    folder = digest_path.parent
    return (folder.parent if folder.name == STACKS_FOLDER else folder) / INDEX_FILE


def locate_single(slug: str, directory: Path, plugin_folder: Path) -> Located | None:
    """Return the single digest of the slug, the local one before the plugin's, None when neither exists."""
    for place, path in _single_paths(slug, directory, plugin_folder):
        if path.is_file():
            return Located(slug, path, place)
    return None


def _single_paths(slug: str, directory: Path, plugin_folder: Path) -> tuple[tuple[str, Path], tuple[str, Path]]:
    """Return the two places a single digest may live, as (place, path), the local one first."""
    file_name = f"{slug}.md"
    return (LOCAL, directory / DIGESTS_PATH / file_name), (PLUGIN, plugin_folder / PLUGIN_FOLDER / file_name)


def locate_stacks(slugs: list[str], directory: Path, plugin_folder: Path) -> list[Located]:
    """Return every stack digest whose slugs all belong to slugs, the local one before the plugin's for one stem."""
    members = set(slugs)
    found: dict[str, Located] = {}
    for place, folder in ((PLUGIN, plugin_folder / PLUGIN_FOLDER / STACKS_FOLDER), (LOCAL, directory / DIGESTS_PATH)):
        for path in sorted(folder.glob("*.md")):
            parts = slugs_of(path.stem)
            if len(parts) > 1 and parts == sorted(set(parts)) and members.issuperset(parts):
                found[path.stem] = Located(path.stem, path, place)
    return [found[stem] for stem in sorted(found)]


def require_usable(located: Located, current_hashes: dict[str, str]) -> None:
    """Stop with the refusal message unless the digest has an index entry whose hashes equal the current source hashes."""
    index_path = index_path_of(located.path)
    entry = read_index(index_path).get(located.stem)
    slugs = slugs_of(located.stem)
    if entry is None or set(entry) != set(slugs):
        raise UnharnessError(f"{located.path} has no entry in {index_path}; run unharness stamp {located.path}")
    changed = [slug for slug in slugs if entry[slug] != current_hashes[slug]]
    if changed:
        raise UnharnessError(f"{located.path} is stale (changed: {', '.join(changed)}); run {COMPILE_DIGEST_COMMAND} {' '.join(slugs)}")


def choose_cover(
    slugs: list[str], singles: dict[str, Digest], stacks: list[Digest], mode: DigestMode,
) -> Cover:
    """Return the cover of the fewest characters; refuse a slug nothing covers, or a stack no disjoint choice covers."""
    covers = [
        cover
        for chosen in _cheapest_choices(stacks, mode).values()
        if (cover := _cover_of(slugs, singles, chosen))
    ]
    if not covers:
        raise UnharnessError(_no_cover_message(slugs, singles))
    return min(covers, key=_cost)


def read_index(path: Path) -> dict[str, dict[str, str]]:
    """Return the index's stems mapped to their slug hashes, empty when the file is absent; stop on a malformed one."""
    if not path.is_file():
        return {}
    try:
        index = json.loads(path.read_text(encoding=TEXT_ENCODING))
    except json.JSONDecodeError:
        index = None
    if not _is_index(index):
        raise UnharnessError(
            f"{path} is not a JSON object of stems to slug hashes; fix or delete it, then run unharness stamp on each digest it covers"
        )
    return index


def _is_index(value: object) -> bool:
    return isinstance(value, dict) and all(
        isinstance(entry, dict) and all(isinstance(hash_, str) for hash_ in entry.values()) for entry in value.values()
    )


def missing_message(slug: str, directory: Path, plugin_folder: Path) -> str:
    (_, local), (_, plugin) = _single_paths(slug, directory, plugin_folder)
    return f"no digest for {slug}: tried {local} and {plugin}; run {COMPILE_DIGEST_COMMAND} {slug}"


def _require_each_once(slugs: list[str]) -> None:
    for slug in slugs:
        if slugs.count(slug) > 1:
            raise UnharnessError(f"manifesto {slug} appears twice in the stack; digest modes need each once")


def _usable_singles(slugs: list[str], hashes: dict[str, str], directory: Path, plugin_folder: Path) -> dict[str, Digest]:
    """Return the usable single digests of the slugs that have one; stop at an unusable one."""
    located = {slug: locate_single(slug, directory, plugin_folder) for slug in slugs}
    return {slug: _read_usable(found, hashes) for slug, found in located.items() if found}


def _usable_stacks(slugs: list[str], hashes: dict[str, str], directory: Path, plugin_folder: Path) -> list[Digest]:
    """Return the usable stack digests that are candidates for the slugs; stop at an unusable one."""
    return [_read_usable(found, hashes) for found in locate_stacks(slugs, directory, plugin_folder)]


def _read_usable(located: Located, hashes: dict[str, str]) -> Digest:
    require_usable(located, hashes)
    return read_digest(located)


def _require_every_slug_covered(
    slugs: list[str], singles: dict[str, Digest], stacks: list[Digest], directory: Path, plugin_folder: Path,
) -> None:
    covered = set(singles).union(*(slugs_of(digest.stem) for digest in stacks))
    for slug in slugs:
        if slug not in covered:
            raise UnharnessError(missing_message(slug, directory, plugin_folder))


def _cheapest_choices(stacks: list[Digest], mode: DigestMode) -> dict[frozenset[str], tuple[Digest, ...]]:
    """Return the cheapest choice of stack digests for each set of slugs some choice covers; a choice shares no slug unless the mode allows overlap."""
    cheapest: dict[frozenset[str], tuple[Digest, ...]] = {frozenset(): ()}
    for digest in sorted(stacks, key=lambda candidate: candidate.stem):
        members = frozenset(slugs_of(digest.stem))
        for covered, chosen in list(cheapest.items()):
            extended = (*chosen, digest)
            reached = covered | members
            if (mode.overlap or covered.isdisjoint(members)) and (
                reached not in cheapest or _cost(Cover(extended, {})) < _cost(Cover(cheapest[reached], {}))
            ):
                cheapest[reached] = extended
    return cheapest


def _cover_of(slugs: list[str], singles: dict[str, Digest], chosen: tuple[Digest, ...]) -> Cover | None:
    """Return the cover the chosen stack digests make with the singles of the slugs they leave, None when they make none."""
    covered = {slug for digest in chosen for slug in slugs_of(digest.stem)}
    left = [slug for slug in slugs if slug not in covered]
    if any(slug not in singles for slug in left):
        return None
    return Cover(chosen, {slug: singles[slug] for slug in left})


def _cost(cover: Cover) -> tuple[int, int, list[str]]:
    """Return the ranking of a cover: total characters, then file count, then sorted stems; lower wins."""
    digests = [*cover.stacks, *cover.singles.values()]
    return sum(len(digest.text) for digest in digests), len(digests), sorted(digest.stem for digest in digests)


def _no_cover_message(slugs: list[str], singles: dict[str, Digest]) -> str:
    lacking = [slug for slug in slugs if slug not in singles]
    return f"no cover without overlap; add {OVERLAP_FLAG} or run {COMPILE_DIGEST_COMMAND} <slug> for each of: {', '.join(lacking)}"


def read_digest(located: Located) -> Digest:
    """Return the digest the file holds, stripped of surrounding whitespace."""
    return Digest(located.stem, located.path.read_text(encoding=TEXT_ENCODING).strip())


def _layout(elements: list[Element], documents: list[Document], cover: Cover) -> list[Document]:
    """Return one block per element in config order: a stack digest's block at its first member, a single digest in place of a text."""
    slugs = [manifesto_slug(element) for element in elements]
    stack_blocks: dict[int, list[Document]] = {}
    for digest in cover.stacks:
        members = [position for position, slug in enumerate(slugs) if slug in slugs_of(digest.stem)]
        stack_blocks.setdefault(members[0], []).append(_stack_block(digest, [documents[position] for position in members]))
    in_stack = {slug for digest in cover.stacks for slug in slugs_of(digest.stem)}
    blocks: list[Document] = []
    for position, (slug, document) in enumerate(zip(slugs, documents)):
        blocks.extend(stack_blocks.get(position, []))
        if slug is None:
            blocks.append(document)
        elif slug not in in_stack:
            blocks.append(Document(document.name, document.purpose, cover.singles[slug].text))
    return blocks


def _stack_block(digest: Digest, members: list[Document]) -> Document:
    purposes = [member.purpose for member in members if member.purpose]
    return Document(STEM_SEPARATOR.join(member.name for member in members), PURPOSE_SEPARATOR.join(purposes) or None, digest.text)


def stamp_digest(digest: Path, registry: Path | None, login: Path) -> Path:
    """Write the digest's entry into its index with the current source hashes, and return the index path."""
    if not digest.is_file():
        raise UnharnessError(f"no digest at {digest}")
    slugs = slugs_of(digest.stem)
    if slugs != sorted(set(slugs)) or "" in slugs:
        raise UnharnessError(f"{digest.name} is not named by sorted, distinct slugs joined by {STEM_SEPARATOR}")
    documents = resolve_stack(manifesto_elements(slugs), digest.parent, registry, login)
    index_path = index_path_of(digest)
    index = read_index(index_path) | {digest.stem: {document.name: document.sha256 for document in documents}}
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding=TEXT_ENCODING)
    return index_path
