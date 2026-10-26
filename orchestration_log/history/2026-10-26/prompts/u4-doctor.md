# U4 — unharness 4.0.0: doctor

1. Role: you implement part of release 4.0.0 by TDD, in /Users/ryzhakar/LLM_MANIFESTOS.worktrees/doctor (branch feat/4.0.0-doctor). Work only there.
2. Context: the "Doctor" section, queue 64's per-stack lines, and decision 11 of the spec part "4.0.0" at the end of /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/history/2026-10-23/spec-unharness.md are the law. U1 already changed config.py, session.py, cli.py (layout, `old_layout`, `subagent_key`, `agent_files`); read /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-10-26/u1-report.md. Suite: `uv run --project plugin/unharness pytest -q plugin/unharness` (365 at start). Git: `type(scope): subject`, at most 10 words, no body, no trailer; one commit per step; no push. Another agent changes plugin/hooks, plugin/tests, and SCHEMA.md on another branch; touch only doctor.py, cli.py's doctor parser, their tests, and the doctor lines of plugin/unharness/README.md.
3. Steps: (a) the `layout` line first and the skipped config checks on an old layout; (b) `stack you` and one `stack subagents.<key>` line per key, with the FAIL/WARN rule; (c) `--agent TYPE` and the `agent match` line; (d) the manifesto plugin floor at 4.0.0; (e) README doctor lines.
4. Output: commits; report /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-10-26/u4-report.md (per step: sha, test count, any point the spec left open and what you chose).
5. Reply: shas, test count, 3 sentences.
6. Scope: the steps alone.
7. Load the skill dev-discipline:tdd first and follow it.
