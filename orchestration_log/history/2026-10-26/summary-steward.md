# Summary: span steward (2026-10-26) — unharness 4.0.0

The owner ordered `prompt --agent` with a warning on fall-through to the default stack, and an in-project folder. A short round settled queue 58-63 ("all at once": one 4.0.0 release carrying `--agent`, the `.manifestos/` folder, the `--settings` merge, and `stack --diff`). main 643eaec; tags v4.0.0 and pypi-4.0.0; publish run 40380419875 succeeded; PyPI serves unharness 4.0.0. 406 package tests, 30 hook tests.

## Shipped
- `.manifestos/` holds config.yaml, preamble.md, the four session files, agents/<key>/, and digests/; old layout stops with the exact `mv` lines (package, hooks, doctor); no fallback read.
- `prompt --agent` and `stack --agent` match by the hook's cascade, now one home in config.py (`subagent_key`) imported by the hook; fall-through to `other:` warns as the default stack; no match exits 1 naming the keys.
- `/compile-commitments <key>` writes per-agent session files; this repo compiled `implementer`.
- `--settings` merge in launch (owner keys win, one note per key; a bare trailing `--settings` stops).
- `stack --diff` shows stale signature lines as a unified diff.
- doctor: `layout`, `stack you`, `stack subagents.<key>`, `--agent` with `agent match`; manifesto plugin floor 4.0.0.
- Hooks print "No manifesto bound: …; run unharness doctor for the fix." into context on config errors (queue 67, from gym/trainer-u3's report); block scalars refused with the fix named (65).

## Process
Spec S3 (opus); units U1-U5; reviews: spec PASS after F1 and a docs amendment, quality ready after F3 and F4; release R1. Two agents hit the old login's session limit and resumed after the owner's /login.

## Open for the owner
- Queue 56 (sweep capture candidates), dismissed in the round, still unsolved.
- The installed manifesto plugin in the logins is 3.6.0; its hooks read the old layout, so this repo's sessions bind nothing from hooks until the plugin updates to 4.0.0.
- Solved entries 64-70 await review at a round.
