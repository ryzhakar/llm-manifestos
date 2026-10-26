"""Compile resolved documents and the session's own files into the system prompt."""

import difflib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from unharness.config import (
    AGENTS_PATH,
    COMMITMENTS_PATH,
    INTERPLAY_PATH,
    MINIFIED_COMMITMENTS_PATH,
    MINIFIED_INTERPLAY_PATH,
    UnharnessError,
)
from unharness.resolve import Document

STACK_BLOCK = re.compile(r"\A<stack>\n(.*?)\n</stack>\n*", re.S)
DOUBLE_QUOTE = '"'
SINGLE_QUOTE = "'"
WRITING_SKILL = "/compile-commitments"
CURRENT_LABEL = "current"


@dataclass(frozen=True)
class SessionFiles:
    interplay: str
    commitments: str
    fix_command: str = WRITING_SKILL

    @property
    def paths(self) -> tuple[str, str]:
        """The two session file paths, interplay first."""
        return self.interplay, self.commitments


FULL_FILES = SessionFiles(INTERPLAY_PATH, COMMITMENTS_PATH)
MINIFIED_FILES = SessionFiles(MINIFIED_INTERPLAY_PATH, MINIFIED_COMMITMENTS_PATH)


def agent_files(files: SessionFiles, key: str) -> SessionFiles:
    """Return the pair of session files the subagents key has beside the main pair, with the command that rewrites them."""
    return SessionFiles(*(f"{AGENTS_PATH}/{key}/{PurePosixPath(name).name}" for name in files.paths), f"{WRITING_SKILL} {key}")


def compile_prompt(
    documents: list[Document], preamble: str, interplay: str | None, commitments: str | None,
    constitution: Sequence[Document] | None = None, files: SessionFiles = FULL_FILES,
) -> str:
    """Return the system prompt: preamble, constitution, interplay, commitments; stop if a session file is stale."""
    session_files = [
        _current_body(files.interplay, interplay, documents, files.fix_command),
        _current_body(files.commitments, commitments, documents, files.fix_command),
    ]
    return "\n\n".join([harness_block(preamble), constitution_block(documents if constitution is None else constitution), *session_files])


def harness_block(preamble: str) -> str:
    """Return the preamble in its tags, the first block of the system prompt."""
    return f"<harness>\n{preamble.strip()}\n</harness>"


def stack_view(documents: list[Document]) -> str:
    """Return the stack block, then the constitution: what a session binds to."""
    return f"{stack_block(documents)}\n\n{constitution_block(documents)}"


def stack_block(documents: list[Document]) -> str:
    """Return the stack block: one line per document, in order."""
    return "<stack>\n" + "\n".join(_stack_lines(documents)) + "\n</stack>"


def constitution_block(blocks: Sequence[Document]) -> str:
    """Return the constitution block: one tagged text per block, in order."""
    return "<constitution>\n" + "\n".join(_tagged(block) for block in blocks) + "\n</constitution>"


def _stack_lines(documents: list[Document]) -> list[str]:
    return [f"{document.name} {document.sha256} {document.purpose or ''}".rstrip() for document in documents]


def _tagged(block: Document) -> str:
    governs = f' governs="{block.purpose.replace(DOUBLE_QUOTE, SINGLE_QUOTE)}"' if block.purpose else ""
    return f"<{block.name}{governs}>\n{block.text}\n</{block.name}>"


def _current_body(file_name: str, text: str | None, documents: list[Document], fix_command: str) -> str:
    """Return the session file without its stack block, or stop if the file is missing or stale."""
    if text is None:
        raise UnharnessError(f"{file_name} is missing; run {fix_command}")
    recorded = STACK_BLOCK.match(text)
    if not recorded:
        raise UnharnessError(f"{file_name} has no <stack> block; run {fix_command}")
    current_lines = _stack_lines(documents)
    recorded_lines = recorded.group(1).split("\n")
    if recorded_lines != current_lines:
        raise UnharnessError(f"{file_name} is stale ({_difference(recorded_lines, current_lines)}); run {fix_command}")
    return text[recorded.end():].strip()


def _difference(recorded_lines: list[str], current_lines: list[str]) -> str:
    changed = sorted({line.split(" ")[0] for line in set(recorded_lines) ^ set(current_lines)})
    return f"changed: {', '.join(changed)}" if changed else "reordered"


def session_file_diff(file_name: str, text: str | None, documents: list[Document]) -> list[str]:
    """Return the lines showing how the session file's recorded stack differs from the documents', none when it is current."""
    if text is None:
        return [f"{file_name}: missing"]
    recorded = STACK_BLOCK.match(text)
    if not recorded:
        return [f"{file_name}: no <stack> block"]
    return list(difflib.unified_diff(
        recorded.group(1).split("\n"), _stack_lines(documents), fromfile=file_name, tofile=CURRENT_LABEL, lineterm="", n=0,
    ))


def session_file_problem(file_name: str, text: str | None, documents: list[Document], fix_command: str) -> str | None:
    """Return why the session file would stop the prompt, None when it is current."""
    try:
        _current_body(file_name, text, documents, fix_command)
    except UnharnessError as error:
        return str(error)
    return None
