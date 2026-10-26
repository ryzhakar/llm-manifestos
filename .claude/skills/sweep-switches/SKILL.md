---
name: sweep-switches
description: "Sweep one Claude Code version for new or changed switches, the env names and settings keys that govern injected text, and verify them by capture before the registry changes. \"sweep switches\", \"new Claude Code version\", \"is this version in the registry\", or a doctor WARN that the version is not in the registry."
---

<run-the-sweep>
Run `python3 -I .claude/skills/sweep-switches/sweep.py <X.Y.Z>` from the repo root, adding `--docs DIR` when the docs are local and `--tarball PATH` when the package is local.
Never run it from another folder.
The script writes `.claude/switch-sweeps/<X.Y.Z>.json`, prints a markdown report, and never edits `plugin/unharness/src/unharness/switches.json`.
Never edit the registry from the sweep alone.
</run-the-sweep>

<read-the-report>
Read the four report sections: undocumented env names, undocumented settings candidates, names new and gone since the previous sweep, and registry switches the version's code no longer holds.
A settings candidate is a key the schema pattern matched, so it may be a tool-input key; never treat one as a switch before reading its source.
Read the extracted source around each name that suggests injected text, such as `REMINDER`, `PROMPT`, `ATTACH`, `DISABLE`, `MEMORY`, or `INSTRUCTIONS`; never judge a name by its spelling alone.
</read-the-report>

<capture-each-candidate>
Capture every candidate worth testing and every registry switch the report lists as absent, once with the switch and once without it, changing only that switch between the two captures.
Run `env -i <strip> CLAUDE_CODE_ENABLE_TELEMETRY=1 OTEL_LOG_RAW_API_BODIES=file:<dir> claude -p --system-prompt-file <f> 'reply ok'`, with `<strip>` the environment and settings the unharness strip sets.
Diff the system array and the first user message between the two captures; never compare only the model's reply.
A switch is confirmed when the text it names is present without the switch and absent with it.
Mark a switch whose capture shows no difference as failed; never carry it forward as untested.
Confirm a switch that changes behavior and no request text, such as a compaction setting, by a binary check in place of a capture: the settings-schema literal, its validator, and its reader in the version's binary. Record such a switch with `control` false.
</capture-each-candidate>

<record-the-result>
Add the version to the `verified` list of each registry entry its captures confirm, and edit nothing else in the entry unless a capture shows the entry wrong.
Never add a version to an entry whose capture failed or never ran.
Commit the new sweep file and the registry change together with a `type(scope): subject` message of at most ten words.
Then run `unharness switches`, paste its output between the README markers, and run the test suite.
</record-the-result>

<keep-the-sweep-honest>
Run `python3 -I .claude/skills/sweep-switches/test_sweep.py` after any change to `sweep.py`; never change the script with the tests unrun.
Never promote a switch because a sweep names it.
</keep-the-sweep-honest>
