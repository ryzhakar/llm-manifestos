# F3 — fix the quality findings of unharness 4.0.0

1. Role: you fix findings by TDD, in /Users/ryzhakar/LLM_MANIFESTOS.worktrees/fix3 (branch feat/4.0.0-fix3, from feat/4.0.0-core f351b5c). Work only there. Never merge another branch into yours.
2. Context: /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-10-26/d2-quality.md lists 3 critical, 9 important, and 5 minor findings. The spec part "4.0.0" of /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/history/2026-10-23/spec-unharness.md stays the law; doctor's rule is that a finding about what `prompt` would load under the given flags is a FAIL and any other a WARN. Suites: `uv run --project plugin/unharness pytest -q plugin/unharness` (389) and `python3 -m unittest discover -s plugin/tests` (29). Git: `type(scope): subject`, at most 10 words, no body, no trailer; one commit per finding or per tight group; no push.
3. Steps: fix every critical, important, and minor finding as the report says, except important 8: in place of `hypothesis`, add three example rows to the cascade table (keys that are suffixes of each other, a key holding `:`, a type `<ns>:other`) and one old_layout case where some old paths have their new path and some do not. Critical 1 first, with the missing test of important 9. For the shell comments, make the code say it (names, functions) and delete the comments.
4. Output: commits; report /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-10-26/f3-report.md (per finding: sha, both suites' counts).
5. Reply: shas and suite counts.
6. Scope: the report's findings alone.
7. Load the skill dev-discipline:tdd first and follow it.
