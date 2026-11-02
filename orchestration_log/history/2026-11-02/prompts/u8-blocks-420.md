# U8 — unharness 4.2.0: agent blocks and a minimal harness

1. Role: you implement release 4.2.0 of unharness by TDD, in /Users/ryzhakar/LLM_MANIFESTOS.worktrees/blocks (branch feat/4.2.0-blocks, cut from main 4e46c23). Work only there.
2. Context: the spec part "4.2.0" at the end of /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/history/2026-10-23/spec-unharness.md is the law; read it whole, with its decisions list and the amended preamble section. Read part 4.0.0 for the project folder and the `file` source rules. Suites: `uv run --project plugin/unharness pytest -q plugin/unharness` (447 at start) and `python3 -m unittest discover -s plugin/tests` (31 at start). Git: `type(scope): subject`, at most 10 words, no body, no trailer; one revertible commit per green change; no push; never merge. Do not raise the version (the release step does), and do not change `.manifestos/config.yaml` (queue 87: the installed 4.0.x hooks refuse the new shape).
3. Steps:
   (a) config.py: `Block`, `Agent`, `Config(mapping_form)`, the three agent forms, block values, and every refusal word for word; `--json` keeps its 4.1.0 shape; move every reader of `config.you` and `config.subagents[key]` to `.stack`. Tests first, in test_config.py and the callers' tests.
   (b) The rendering: `prompt` and `prompt --agent` print the agent's blocks between `<harness>` and `<constitution>` per the spec (compile.py and cli.py), reading block files after the stack resolves and before the session-file check.
   (c) preamble.md: the exact text of the spec's section "The shipped preamble"; copy it with a script from the spec file and diff, never retype it; update the limits test (at most 25 lines; no "unharness", "compil", or "constitution").
   (d) doctor.py: the block lines, the conditional plugin floor, the prompt-size count, per the spec.
   (e) The hook tests of the spec's Tests section in plugin/tests/test_hooks.py, and the four changed message assertions. The hook scripts need no change; if a test shows they do, stop and say why.
   (f) Docs per the spec's Docs section (plugin/SCHEMA.md, plugin/README.md, plugin/unharness/README.md), and `.manifestos/blocks/reading.md` with the spec's text, referenced by no config. Run `just readme` and commit any change it makes.
4. Output: commits; your reply carries the report (per step: sha, test counts, what the spec left unclear and what you chose); the orchestrator transcribes it to /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-11-02/u8-report.md.
5. Reply: shas, test counts, 3 sentences.
6. Scope: the steps alone.
7. Load the skill dev-discipline:tdd first and follow it. Write every sentence of docs and messages by Strunk's rules (skill agent-conduct:write-well).
