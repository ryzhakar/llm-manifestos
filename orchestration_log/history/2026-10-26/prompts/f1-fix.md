# F1 — fix three spec-review findings of unharness 4.0.0

1. Role: you fix findings by TDD, in /Users/ryzhakar/LLM_MANIFESTOS.worktrees/fix (branch feat/4.0.0-fix, from feat/4.0.0-core c03d2dd). Work only there. Never merge another branch into yours.
2. Context: findings 2, 3, and 4 of /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-10-26/d1-spec.md, against the spec part "4.0.0" of /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/history/2026-10-23/spec-unharness.md. Findings 1 and 5 are settled elsewhere; leave them. Suites: `uv run --project plugin/unharness pytest -q plugin/unharness` and `python3 -m unittest discover -s plugin/tests`. Git: `type(scope): subject`, at most 10 words, no body, no trailer; one commit per finding; no push.
3. Steps: (2) a bare `--settings` as the last word after `--` stops with `--settings after -- needs a value`, with a test; (3) one test writes a fixed, pre-recorded `<stack>` block with a literal hash for a `file` element into `.manifestos/interplay.md` and `.manifestos/commitments.md` and gets exit 0 from `prompt`; (4) one `prompt --agent --digests` and one `prompt --agent --stack-digests` test whose digests swap into the matched key's constitution.
4. Output: commits; report /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-10-26/f1-report.md (per finding: sha, both suites' counts).
5. Reply: shas and suite counts.
6. Scope: these three findings alone.
7. Load the skill dev-discipline:tdd first and follow it.
