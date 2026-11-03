"""Resolve each config element to the text it contributes, by its explicit source type."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from stat import S_ISREG

from unharness.config import MANIFESTO_SOURCE, SKILL_SOURCE, TEXT_ENCODING, Block, Element, UnharnessError, block_path

PLUGIN_ROOT_PLACEHOLDER = "${CLAUDE_PLUGIN_ROOT}"
FRONTMATTER = re.compile(r"\A---\n(?=[A-Za-z_][\w-]*:).*?\n---\n", re.S)
LOGIN_VARIABLE = "CLAUDE_CONFIG_DIR"
MANIFESTO_PLUGIN = "manifesto"
PLUGIN_SKILL_SEPARATOR = ":"
NOT_UTF_8_TEXT = "not UTF-8 text"


@dataclass(frozen=True)
class Document:
    name: str
    purpose: str | None
    text: str
    sha256: str | None = None


def login_dir(environ: Mapping[str, str], home: Path) -> Path:
    """Return the login folder: CLAUDE_CONFIG_DIR, else .claude in the home folder."""
    return Path(environ[LOGIN_VARIABLE]) if environ.get(LOGIN_VARIABLE) else home / ".claude"


def manifesto_slug(element: Element) -> str | None:
    """Return the registry stem the element names, None for a skill or a file."""
    return (element.reference or element.name) if element.source_type in (None, MANIFESTO_SOURCE) else None


def manifesto_elements(slugs: list[str]) -> list[Element]:
    """Return one registry-manifesto element per slug, named by the slug."""
    return [Element(slug, None, MANIFESTO_SOURCE, slug) for slug in slugs]


def manifesto_plugin_dir(registry: Path | None, login: Path) -> Path:
    """Return the folder holding manifestos/ and digests/: the configured one, else the manifesto plugin's highest cached version."""
    return registry or _highest_version_dir(login, MANIFESTO_PLUGIN)


def resolve_stack(elements: list[Element], directory: Path, registry: Path | None, login: Path) -> list[Document]:
    """Resolve each element, in order, to its Document; stop at the first that does not resolve."""
    return [_resolve_element(element, directory, registry, login) for element in elements]


def resolve_block(block: Block, agent_label: str, directory: Path) -> Document:
    """Return the agent's block as a Document without a purpose, its line or its file's text read as a file element's, stripped."""
    if block.file is None:
        return Document(block.name, None, block.line.strip())
    path = locate_block(block, directory)
    place = block_path(agent_label, block.name)
    if not _is_file(path, place):
        raise UnharnessError(f"{place} did not resolve; tried {path}")
    text = _body(path, place)
    if not text:
        raise UnharnessError(f"{place} has no text in {path}")
    return Document(block.name, None, text)


def locate_block(block: Block, directory: Path) -> Path:
    """Return the file a file block names, against the project folder, as a file element's path resolves."""
    return directory / block.file


def _resolve_element(element: Element, directory: Path, registry: Path | None, login: Path) -> Document:
    path, plugin_root = locate(element, directory, registry, login)
    place = f"element {element.name}"
    if not _is_file(path, place):
        raise UnharnessError(f"{place} did not resolve; tried {path}")
    body = _body(path, place)
    return Document(
        element.name,
        element.purpose,
        body.replace(PLUGIN_ROOT_PLACEHOLDER, str(plugin_root)) if plugin_root else body,
        sha256(body.encode()).hexdigest(),
    )


def _is_file(path: Path, place: str) -> bool:
    """Say whether a file is at the path, False when nothing or no file is there, and stop with the cannot-be-read line when the system refuses to look."""
    try:
        return S_ISREG(path.stat().st_mode)
    except (FileNotFoundError, NotADirectoryError, ValueError):
        return False
    except OSError as error:
        raise _unreadable(place, path, error.strerror) from None


def _body(path: Path, place: str) -> str:
    """Return the file's text with its frontmatter removed, stripped, else stop with the cannot-be-read line when the system refuses the file or the file is not UTF-8 text."""
    try:
        text = path.read_text(encoding=TEXT_ENCODING)
    except UnicodeDecodeError:
        raise _unreadable(place, path, NOT_UTF_8_TEXT) from None
    except OSError as error:
        raise _unreadable(place, path, error.strerror) from None
    return FRONTMATTER.sub("", text).strip()


def _unreadable(place: str, path: Path, reason: str) -> UnharnessError:
    """Return the cannot-be-read error, which names the place, the path, and the reason the file cannot be read."""
    return UnharnessError(f"{place} file {path} cannot be read: {reason}")


def locate(element: Element, directory: Path, registry: Path | None, login: Path) -> tuple[Path, Path | None]:
    """Return the file the element names, and the plugin folder that ${CLAUDE_PLUGIN_ROOT} stands for, if any."""
    kind = element.source_type or MANIFESTO_SOURCE
    reference = element.reference or element.name
    if kind == MANIFESTO_SOURCE:
        plugin_root = manifesto_plugin_dir(registry, login)
        return plugin_root / "manifestos" / f"{manifesto_slug(element)}.md", plugin_root
    if kind == SKILL_SOURCE and PLUGIN_SKILL_SEPARATOR in reference:
        plugin, _, skill = reference.partition(PLUGIN_SKILL_SEPARATOR)
        plugin_root = _highest_version_dir(login, plugin)
        return plugin_root / "skills" / skill / "SKILL.md", plugin_root
    if kind == SKILL_SOURCE:
        return login / "skills" / reference / "SKILL.md", None
    return directory / reference, None


def _highest_version_dir(login: Path, plugin: str) -> Path:
    """Return the plugin's highest cached version folder, or the pattern that matched none."""
    pattern = f"plugins/cache/*/{plugin}/*"
    return max(login.glob(pattern), key=lambda version_dir: version_key(version_dir.name), default=login / pattern)


def version_key(version: str) -> tuple[int, ...]:
    """Return the numbers in a version name, for ordering versions."""
    return tuple(int(number) for number in re.findall(r"\d+", version))
