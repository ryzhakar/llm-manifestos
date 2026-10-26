"""The unharness command: print the compiled prompt, the stack a session binds to, or the strip table, or launch a session."""

import argparse
import os
import sys
from pathlib import Path

from unharness.compile import FULL_FILES, MINIFIED_FILES, SessionFiles, agent_files, compile_prompt, session_file_diff, stack_view
from unharness.config import CONFIG_PATH, EMPTY_STACK_MESSAGE, Config, Element, UnharnessError, fail, falls_through_to_default, load, subagent_key
from unharness.digests import DIGESTS_FLAG, OVERLAP_FLAG, STACK_DIGESTS_FLAG, constitution_blocks, digest_mode, stamp_digest
from unharness.doctor import Modes, claude_version, doctor, has_failed
from unharness.launch import Options, cache_home, execute_launcher, launch, reopen_terminal, version_output, terminal_device
from unharness.resolve import login_dir, manifesto_elements, manifesto_plugin_dir, resolve_stack
from unharness.session import load_preamble, read_if_present
from unharness.switches import shipped_switches, strip_table

PROMPT_VERB = "prompt"
STACK_VERB = "stack"
STAMP_VERB = "stamp"
LAUNCH_VERB = "launch"
DOCTOR_VERB = "doctor"
SWITCHES_VERB = "switches"
CLAUDE_VERSION_FLAG = "--claude-version"
MINIFIED_FLAG = "--minified"
AGENT_FLAG = "--agent"
DIFF_FLAG = "--diff"
MODE_FLAGS = (DIGESTS_FLAG, STACK_DIGESTS_FLAG, OVERLAP_FLAG, MINIFIED_FLAG)
LAUNCHER_SEPARATOR = "--"


def main(argv: list[str] | None = None) -> int:
    """Run the verb named in argv; print its output, fail in one line with exit status 1, or exit 0 quietly when stdout closes early."""
    try:
        status = _run(sys.argv[1:] if argv is None else argv)
        sys.stdout.flush()
    except BrokenPipeError:
        _discard_stdout()
        return 0
    return status


def _discard_stdout() -> None:
    """Point stdout at the null device, so the interpreter's flush at exit finds nothing to fail on."""
    os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())


def _run(argv: list[str]) -> int:
    """Parse argv, run its verb, and return the exit status."""
    argv, launcher = _split_launcher(argv)
    parser = argparse.ArgumentParser(prog="unharness")
    verbs = parser.add_subparsers(dest="verb", required=True)
    prompt_parser = verbs.add_parser(PROMPT_VERB)
    stack_parser = verbs.add_parser(STACK_VERB)
    stack_parser.add_argument("slugs", nargs="*")
    stack_parser.add_argument(DIFF_FLAG, action="store_true")
    for parser_of_verb in (prompt_parser, stack_parser):
        parser_of_verb.add_argument("--config", type=Path, default=CONFIG_PATH)
        parser_of_verb.add_argument(AGENT_FLAG)
    for flag in MODE_FLAGS:
        prompt_parser.add_argument(flag, action="store_true")
    stamp_parser = verbs.add_parser(STAMP_VERB)
    stamp_parser.add_argument("digest", type=Path)
    stamp_parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    launch_parser = verbs.add_parser(LAUNCH_VERB)
    launch_parser.add_argument("prompt", nargs="?")
    for flag in ("--keep-claude-md", "--keep-web-search", "--no-hooks"):
        launch_parser.add_argument(flag, action="store_true")
    launch_parser.add_argument(CLAUDE_VERSION_FLAG)
    verbs.add_parser(SWITCHES_VERB)
    doctor_parser = verbs.add_parser(DOCTOR_VERB)
    doctor_parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    doctor_parser.add_argument(CLAUDE_VERSION_FLAG)
    for flag in MODE_FLAGS:
        doctor_parser.add_argument(flag, action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.verb == LAUNCH_VERB:
            return _launch(arguments, launcher)
        if arguments.verb == DOCTOR_VERB:
            return _doctor(arguments)
        if arguments.verb == SWITCHES_VERB:
            print(strip_table(shipped_switches()))
            return 0
        login = login_dir(os.environ, Path.home())
        if arguments.verb == STACK_VERB and arguments.diff:
            return _diff(arguments, login)
        print(_stamp(arguments, login) if arguments.verb == STAMP_VERB else _output(arguments, login))
    except UnharnessError as error:
        return fail(error)
    return 0


def _split_launcher(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split a launch command line at its first --, into the verb's own arguments and the launcher with its arguments."""
    if argv[:1] != [LAUNCH_VERB] or LAUNCHER_SEPARATOR not in argv:
        return argv, []
    separator = argv.index(LAUNCHER_SEPARATOR)
    return argv[:separator], argv[separator + 1:]


def _launch(arguments: argparse.Namespace, launcher: list[str]) -> int:
    if arguments.prompt is None and sys.stdin.isatty():
        raise UnharnessError("no prompt: pass PROMPT or pipe unharness prompt")
    prompt = arguments.prompt if arguments.prompt is not None else sys.stdin.read()
    options = Options(arguments.keep_claude_md, arguments.keep_web_search, arguments.no_hooks, launcher, arguments.claude_version)
    return launch(prompt, options, shipped_switches(), os.environ, cache_home(os.environ, Path.home()), terminal_device(), reopen_terminal, execute_launcher, version_output)


def _stamp(arguments: argparse.Namespace, login: Path) -> str:
    index = stamp_digest(arguments.digest, load(arguments.config).registry, login)
    return f"stamped {arguments.digest.stem} in {index}"


def _doctor(arguments: argparse.Namespace) -> int:
    modes = Modes(arguments.digests, arguments.stack_digests, arguments.overlap, arguments.minified)
    findings = doctor(arguments.config, modes, login_dir(os.environ, Path.home()), os.environ, claude_version, shipped_switches(), arguments.claude_version)
    print("\n".join(finding.line for finding in findings))
    return 1 if has_failed(findings) else 0


def _diff(arguments: argparse.Namespace, login: Path) -> int:
    if arguments.slugs:
        raise UnharnessError(f"{DIFF_FLAG} takes no slugs")
    config = load(arguments.config)
    elements, key = _elements_to_bind(config, arguments.agent)
    documents = resolve_stack(elements, config.directory, config.registry, login)
    names = [name for minified in (False, True) for name in _session_files(key, minified).paths]
    differences = [line for name in names for line in session_file_diff(name, read_if_present(config.directory / name), documents)]
    if differences:
        print("\n".join(differences))
    return 1 if differences else 0


def _output(arguments: argparse.Namespace, login: Path) -> str:
    verb = arguments.verb
    mode = digest_mode(arguments.digests, arguments.stack_digests, arguments.overlap) if verb == PROMPT_VERB else None
    config = load(arguments.config)
    if verb == STACK_VERB and arguments.slugs:
        if arguments.agent is not None:
            raise UnharnessError(f"{AGENT_FLAG} takes no slugs")
        return stack_view(resolve_stack(manifesto_elements(arguments.slugs), config.directory, config.registry, login))
    elements, key = _elements_to_bind(config, arguments.agent)
    documents = resolve_stack(elements, config.directory, config.registry, login)
    if verb == STACK_VERB:
        return stack_view(documents)
    session_files = _session_files(key, arguments.minified)
    return compile_prompt(
        documents,
        load_preamble(config.directory).text,
        read_if_present(config.directory / session_files.interplay),
        read_if_present(config.directory / session_files.commitments),
        constitution_blocks(elements, documents, config.directory, manifesto_plugin_dir(config.registry, login), mode),
        session_files,
    )


def _elements_to_bind(config: Config, agent_type: str | None) -> tuple[list[Element], str | None]:
    """Return the elements to bind and the subagents key they came from, None for the main stack."""
    if agent_type is None:
        if not config.you:
            raise UnharnessError(EMPTY_STACK_MESSAGE)
        return config.you, None
    keys = list(config.subagents)
    key = subagent_key(agent_type, keys)
    if key is None:
        raise UnharnessError(f"{agent_type} matches no subagents key and the config has no other:; keys: {', '.join(keys) or 'none'}")
    if falls_through_to_default(agent_type, keys):
        print(f"unharness: {agent_type} matches no subagents key; using other:, the default stack", file=sys.stderr)
    if not config.subagents[key]:
        raise UnharnessError(f"subagents.{key} is empty")
    return config.subagents[key], key


def _session_files(key: str | None, minified: bool) -> SessionFiles:
    """Return the session files of the main stack, or of the subagents key, in the full or the minified pair."""
    pair = MINIFIED_FILES if minified else FULL_FILES
    return pair if key is None else agent_files(pair, key)


if __name__ == "__main__":
    sys.exit(main())
