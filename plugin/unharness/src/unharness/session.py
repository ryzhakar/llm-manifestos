"""Read the files a project adds around the constitution: its preamble override and its session files."""

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from unharness.config import PREAMBLE_PATH, TEXT_ENCODING

SHIPPED_PREAMBLE = "shipped"


@dataclass(frozen=True)
class Preamble:
    source: str
    text: str


def read_if_present(path: Path) -> str | None:
    """Return the file's text, None when it does not exist."""
    return path.read_text(encoding=TEXT_ENCODING) if path.is_file() else None


def load_preamble(directory: Path) -> Preamble:
    """Return the project's preamble override when it has one, else the preamble unharness ships."""
    override = read_if_present(directory / PREAMBLE_PATH)
    if override is not None:
        return Preamble(PREAMBLE_PATH, override)
    return Preamble(SHIPPED_PREAMBLE, files("unharness").joinpath("preamble.md").read_text(encoding=TEXT_ENCODING))
