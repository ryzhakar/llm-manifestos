# U7 — unharness 4.1.0: launch --autocompact

1. Role: you implement release 4.1.0 of unharness by TDD, in /Users/ryzhakar/LLM_MANIFESTOS.worktrees/autocompact (branch feat/4.1.0-autocompact, cut from main 59fc9c0). Work only there.
2. Context: the spec part "4.1.0" in /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/history/2026-10-23/spec-unharness.md is the law (read it whole, with its decisions; read part 3.7.0 for the registry and part 4.0.0 for the --settings merge). Another agent builds 4.0.1 (subagent hook, doctor floor 4.0.1, docs about hooks) on feat/4.0.1-hook in parallel; this branch will be rebased onto it, so do not touch the hooks, the doctor floor, or the hook paragraphs of the READMEs, and do not raise the version: the release step does. Suite: `uv run --project plugin/unharness pytest -q plugin/unharness` (406 at start); `python3 -m unittest discover -s plugin/tests`. Git: `type(scope): subject`, at most 10 words, no body, no trailer; one commit per step; no push; never merge.
3. Steps:
   (a) The binary check of the spec's "Verifying the three entries" step 1, over all five binaries in ~/.local/share/claude/versions/; write orchestration_log/recon/2026-10-26/autocompact-binary-check.md in the main checkout /Users/ryzhakar/LLM_MANIFESTOS (records, not your branch; do not commit it). Stop and report if 2.1.309 fails.
   (b) switches.py: the valued option, `given`, the three refusals, selection; switches.json: the three entries; the shipped-versions test.
   (c) cli.py and launch.py: `--autocompact SIZE` parsing, bounds, refusal wording, the no-entry note, composition.
   (d) The strip table rendering, the README blocks, the compaction paragraph, synopses, doctor's count, and the sweep-switches skill sentence.
4. Output: commits; report /Users/ryzhakar/LLM_MANIFESTOS/orchestration_log/recon/2026-10-26/u7-report.md (per step: sha, test counts, anything the spec left unclear and what you chose).
5. Reply: shas, test counts, 3 sentences.
6. Scope: the steps alone.
7. Load the skill dev-discipline:tdd first and follow it. Write every sentence of docs by Strunk's rules (skill agent-conduct:write-well).
