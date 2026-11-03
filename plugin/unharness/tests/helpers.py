import os
import signal
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

NOT_UTF_8_BYTES = b"Caf\xe9\n"
NO_PERMISSIONS = 0o000


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def write_not_utf_8(path: Path) -> Path:
    """Write the file with the byte 0xE9 standing alone, which no UTF-8 text holds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(NOT_UTF_8_BYTES)
    return path


def write_refused(path: Path) -> Path:
    """Write the file at mode 000, which the system refuses to open for anyone but root."""
    write(path, "Refused.\n")
    path.chmod(NO_PERMISSIONS)
    return path


UNREADABLE_FILES = [
    pytest.param(write_not_utf_8, "not UTF-8 text", id="not-utf-8"),
    pytest.param(
        write_refused, "Permission denied", id="mode-000",
        marks=pytest.mark.skipif(os.geteuid() == 0, reason="root opens a file at mode 000"),
    ),
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
