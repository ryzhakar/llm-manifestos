# U1 — unharness 4.0.0 core: project folder, old layout, subagent cascade, prompt/stack --agent, stack --diff

1. Role: you implement part of release 4.0.0 of unharness by TDD, in /Users/ryzhakar/LLM_MANIFESTOS.worktrees/core (branch feat/4.0.0-core). Work only there.
2. Context: the spec part "4.0.0" at the end of /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/history/2026-10-23/spec-unharness.md is the law; read its decisions list. Package: plugin/unharness (src/unharness/*.py). Suite: `uv run --project plugin/unharness pytest -q plugin/unharness` (290 at start); hook suite `python3 -m unittest discover -s plugin/tests`. Git: `type(scope): subject`, at most 10 words, no body, no trailer; one commit per step; no push. Another agent changes launch.py for the `--settings` merge on another branch; do not touch launch.py.
3. Steps:
   (a) config.py: the layout names, the project folder, `--config` default `.manifestos/config.yaml`, `file` sources and `manifesto_dir` resolving against the project folder, `old_layout(project)` and `load` stopping with its multi-line message, the subagents key refusal, `subagent_key(agent_type, keys)`, and `--json --project <folder>` for the hooks. Also: a `>` or `|` block scalar in the config stops with "block scalars are not supported; write the value on one line" naming the line (queue 65).
   (b) compile.py, session.py, digests.py, cli.py read every path from config.py's names (`.manifestos/` files, `.manifestos/preamble.md`, `.manifestos/digests/`).
   (c) `prompt --agent TYPE` and `stack --agent TYPE` per spec, with the fall-through warning, the no-match exit 1, the empty-list refusal, per-agent session files under `.manifestos/agents/<key>/`, and the key-named staleness messages.
   (d) `stack --diff [--agent TYPE]` per spec.
   Leave doctor, the hooks, the skills, and the docs to later units; keep doctor's existing tests passing with the new paths.
4. Output: commits; report /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-10-26/u1-report.md (per step: sha, test count, anything the spec left unclear and what you chose).
5. Reply: shas, test count, 3 sentences.
6. Scope: the steps alone.
7. Load the skill dev-discipline:tdd first and follow it.
