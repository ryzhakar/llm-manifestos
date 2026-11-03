# Plan 4.2.0: agent blocks and a minimal harness (2026-11-02)

Order: the owner, journal lines 15:20 and 15:40 of 2026-11-02 and "good. nothing waits on my word. do this." Queue 80-88. Publish is part of the order; no peer is notified.

Units:
- S5 spec: s5-spec writes part "4.2.0" of spec-unharness.md (brief prompts/s5-spec-420.md).
- U8 build: one implementer, worktree LLM_MANIFESTOS.worktrees/blocks, branch feat/4.2.0-blocks from main, steps (a) config, (b) rendering and cli, (c) preamble, (d) doctor, (e) docs and the reading.md block file.
- D7 spec review, D8 quality review, with fix loops by message to u8.
- R release by the orchestrator: rebase on session/long-run, version commit 4.2.0 in the six files 87ed6ee touched, gates, ship, tags v4.2.0 and pypi-4.2.0, publish run.
- Post: when the installed manifesto plugin reads 4.2.0, convert this repo's .manifestos/config.yaml to the mapping form with the reading block (queue 87).

Status: DONE 2026-11-03, main 550dcc8, tags v4.2.0 + pypi-4.2.0 (publish run 41565308297). Queue 87 pending: convert .manifestos/config.yaml once the installed manifesto plugin reads 4.2.0.
