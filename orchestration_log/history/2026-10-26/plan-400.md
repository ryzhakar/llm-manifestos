# Plan: unharness 4.0.0 — `prompt --agent`, `.manifestos/` folder, `--settings` merge, `stack --diff`

Owner order and answers: queue 58-63 and the round of 2026-10-26. One release, 4.0.0 ("all at once").
Branch: session/long-run for records; product work on feat/4.0.0 in a worktree; main and tag v4.0.0 + pypi-4.0.0 on verified completion.

Units:
- S3 (opus): spec part 4.0.0 (prompts/s3-spec-400.md). → spec is the one home.
- Then units from the spec: package (layout, --agent, stack --agent, settings, diff, doctor), hooks and SCHEMA.md, skills (compile-commitments per agent), docs; review; e2e capture; release.
- S3 done (spec part 4.0.0). U1 core (config, paths, --agent, stack --diff) on feat/4.0.0-core; U2 --settings merge on feat/4.0.0-settings; both launched.
- Next: U3 hooks + SCHEMA (on core after U1), U4 doctor (after U1), U5 skills + docs + repo's own move; merge U2 into core; D review; E2E; release 4.0.0 (main, tags v4.0.0 + pypi-4.0.0).
- Review items from U2: a trailing bare `--settings` with no value passes through untouched beside launch's own (likely two --settings reach claude); defaulted `read_file` parameter on launch to wire from cli.py; one red commit (9e62aa2) in history.
- U1 and U2 done, folded into core ae4c735 (365 tests). U3 hooks + SCHEMA and U4 doctor launched on their own branches from ae4c735. Next: merge both, U5 skills + docs + repo's own move, review, e2e, release.
- U3 done, core 9968e96. Before main: rebase core onto session/long-run to drop the agents' merge commits (linear main). Later briefs: no merges.
- U4 done, core c03d2dd (385 tests). D1 reviews (spec, quality) launched on the code; U5 docs running.
