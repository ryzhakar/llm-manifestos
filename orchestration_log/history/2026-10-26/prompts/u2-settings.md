# U2 — unharness 4.0.0: `--settings` merge in launch

1. Role: you implement part of release 4.0.0 of unharness by TDD, in /Users/ryzhakar/LLM_MANIFESTOS.worktrees/settings (branch feat/4.0.0-settings). Work only there.
2. Context: the section "`--settings` merge (queue 48)" and decision 9 of the spec part "4.0.0" at the end of /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/history/2026-10-23/spec-unharness.md are the law. Code: plugin/unharness/src/unharness/launch.py and its tests. Suite: `uv run --project plugin/unharness pytest -q plugin/unharness` (290 at start). Git: `type(scope): subject`, at most 10 words, no body, no trailer; one commit per step; no push. Another agent changes config.py, cli.py, compile.py, session.py, and digests.py on another branch; touch only launch.py, its tests, and the README lines describing launch (plugin/unharness/README.md, plugin/README.md Unharness section).
3. Steps: (a) find `--settings` in the ARGS after `--` (spaced and `=` forms; two or more refuse); (b) read VALUE as JSON text or a file, with the two error messages; (c) the shallow merge, owner keys first, one stderr note per shared key, one `--settings` passed; (d) a test that the printed command with no launcher stays byte for byte as today; (e) the README lines.
4. Output: commits; report /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-10-26/u2-report.md (per step: sha, test count, anything the spec left unclear and what you chose).
5. Reply: shas, test count, 3 sentences.
6. Scope: the steps alone.
7. Load the skill dev-discipline:tdd first and follow it.
