# U6 — unharness 4.0.1: the subagent hook binds under unharness

1. Role: you implement release 4.0.1 of unharness and the manifesto plugin by TDD, in /Users/ryzhakar/LLM_MANIFESTOS.worktrees/hook (branch feat/4.0.1-hook, cut from main). Work only there.
2. Context: the spec part "4.0.1" in /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/history/2026-10-23/spec-unharness.md is the law (read it whole, with its decisions; read part 4.0.0's hook sections for context). Suites: `uv run --project plugin/unharness pytest -q plugin/unharness` (406 at 4.0.0) and `python3 -m unittest discover -s plugin/tests` (30). Git: `type(scope): subject`, at most 10 words, no body, no trailer; one commit per step; no push; never merge.
3. Steps:
   (a) Hook tests first: StandDownUnderUnharness split per the spec's Tests section; then subagent-start.sh stops standing down.
   (b) Doctor: floor 4.0.1, the OK and FAIL details verbatim, the docstring.
   (c) Docs: plugin/README.md, plugin/SCHEMA.md, the unharness README, as the spec's Docs section words them.
   (d) Version 4.0.1 in every place 4.0.0 was set for the release (grep the 4.0.0 release commit on main for the list; `git log --grep 4.0.0` on main finds it).
4. Output: commits; report /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-10-26/u6-report.md (per step: sha, test counts, anything the spec left unclear and what you chose).
5. Reply: shas, test counts, 3 sentences.
6. Scope: the steps alone.
7. Load the skill dev-discipline:tdd first and follow it. Write every sentence of docs by Strunk's rules (skill agent-conduct:write-well).
