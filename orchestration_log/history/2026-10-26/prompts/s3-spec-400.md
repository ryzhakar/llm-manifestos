# S3 — spec part "4.0.0: subagent prompts, one project folder, settings merge, stack diff"

1. Role: you write the design spec other agents implement from.
2. Context: unharness 3.7.2 is on main. The owner's order and the answered decisions are queue entries 48, 58-63 and the "Round of 2026-10-26" paragraph in /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/history/2026-10-23/queue-long-run.md; read them first, they bind. Read also: the spec /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/history/2026-10-23/spec-unharness.md (whole); plugin/SCHEMA.md (subagents:, `other:`, the SubagentStart cascade); plugin/hooks/*.sh and *.py (where each hook reads the config and the compiled files); plugin/unharness/src/unharness/*.py (cli, config, compile, session, digests, doctor, launch); the plugin skills compile-commitments and compile-digest under plugin/skills/.
3. Task: append a part "4.0.0" to the spec with:
   (a) Layout: every path in the `.manifestos/` folder (config.yaml, interplay.md, commitments.md and their .min.md, agents/<key>/ with the same four, digests/ with index.json); `<key>` is the config key under `subagents:`, `other` included. List every reader and writer of each path (package, hooks, skills, README, SCHEMA.md).
   (b) Old layout: how doctor and each hook detect it and the exact `mv` lines they print; no fallback read.
   (c) `unharness prompt --agent <type>`: the cascade (exact key, the part after the last `:`, a key the type ends with, then `other:`), the one stderr warning on fall-through to `other:` (wording, naming the type and calling it the default stack), exit 1 when nothing matches and no `other:` exists (wording naming the type and the keys). Say how the cascade keeps one home between the hook and the package, or, if the hook cannot import the package, how one test pins the two to the same answers.
   (d) Per-agent session files: how `/compile-commitments` writes them for one key (argument form), how `unharness stack --agent` prints that stack's fingerprint, and how `prompt --agent` checks their signatures, as the main stack does today.
   (e) `--settings` merge and `stack --diff` from queue 48: read what 48 and the earlier spec say; specify both minimally (inputs, exact output, error cases). If 48 leaves a choice open, decide it and list it under decisions.
   (f) Doctor lines for agents and the layout; a test list; a "Decisions made in the spec" list.
   Under 180 added lines. Keep existing parts untouched.
4. Output: the spec file, edited in place.
5. Reply: 3-sentence summary and the decisions beyond the queue.
6. Scope: spec only; no code.
7. Tools: Read, Edit, Grep, Glob.
8. Write every sentence by Strunk's rules (skill agent-conduct:write-well).
