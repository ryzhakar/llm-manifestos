import errno
import os
import signal
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from stat import S_IMODE

import pytest

NOT_UTF_8_BYTES = b"Caf\xe9\n"
NO_PERMISSIONS = 0o000
LONG_NAME = "n" * 300 + ".md"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@contextmanager
def not_utf_8_file(folder: Path) -> Iterator[str]:
    """Yield the name of a file in the folder that holds the byte 0xE9 standing alone, which no UTF-8 text holds."""
    name = "latin-1.md"
    (folder / name).write_bytes(NOT_UTF_8_BYTES)
    yield name


@contextmanager
def file_at_mode_000(folder: Path) -> Iterator[str]:
    """Yield the name of a file in the folder at mode 000, which the system refuses to open for anyone but root."""
    name = "refused.md"
    write(folder / name, "Refused.\n").chmod(NO_PERMISSIONS)
    yield name


@contextmanager
def file_in_folder_at_mode_000(folder: Path) -> Iterator[str]:
    """Yield the path of a file inside a folder held at mode 000 until the block ends, so that the system refuses to look it up."""
    locked = folder / "locked"
    write(locked / "notes.md", "Notes.\n")
    mode = S_IMODE(locked.stat().st_mode)
    locked.chmod(NO_PERMISSIONS)
    try:
        yield "locked/notes.md"
    finally:
        locked.chmod(mode)


@contextmanager
def file_with_long_name(folder: Path) -> Iterator[str]:
    """Yield a file name of 300 characters, which the system refuses to look up in any folder as too long."""
    yield LONG_NAME


SKIPPED_AS_ROOT = pytest.mark.skipif(os.geteuid() == 0, reason="root opens what mode 000 refuses")
UNREADABLE_FILES = [
    pytest.param(not_utf_8_file, "not UTF-8 text", id="not-utf-8"),
    pytest.param(file_at_mode_000, os.strerror(errno.EACCES), id="mode-000", marks=SKIPPED_AS_ROOT),
    pytest.param(file_in_folder_at_mode_000, os.strerror(errno.EACCES), id="folder-at-mode-000", marks=SKIPPED_AS_ROOT),
    pytest.param(file_with_long_name, os.strerror(errno.ENAMETOOLONG), id="300-character-name"),
]


@contextmanager
def deadline(seconds: int) -> Iterator[None]:
    """Raise TimeoutError in the block when it runs longer than the seconds."""

    def expire(signum, frame):
        raise TimeoutError(f"the block ran past {seconds} seconds")

    previous = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
