# Answers to the owner, 2026-10-27

## "how is there a default? the absence must have meant no autocompaction at all." / "how do we turn compaction off? did we think this through?"

Without the flag there is no compaction except the kind you type. My report said "default" twice. The first was the strip table's `default` field. The second was your login named "default" (~/.claude), whose idle-compaction flag reads off. Neither means a default compaction.

How it turns off: launch passes `--settings` with `"autoCompactEnabled": false` and `"idleCompaction": false`. In the Claude Code 2.1.310 binary, one function, `Hp()`, returns autoCompactEnabled, and returns false when DISABLE_COMPACT or DISABLE_AUTO_COMPACT is set. Every automatic path checks `Hp()`:
- threshold compaction, at the window: `Hp()` first;
- reactive compaction, on a prompt-too-long error: its gate `iRo` requires `Hp()&&lF()`;
- idle compaction, both the cache-expiry timer (`tXo`: `if(!Hp())return"compaction_off"`) and the sleep compactor (`#m`: the same line).
`idleCompaction: false` is a second lock on the idle paths. Manual `/compact` stays, since only DISABLE_COMPACT removes it, and that would take away your own command.

What could still turn it on: your own `--settings` naming `autoCompactEnabled: true`, which wins with one stderr note; a managed policy setting, if one is ever installed; or a future registry version that drops these three entries. A test now fails if any shipped entry lacks a version another entry holds.

What I did not think through, and have not done:
1. No live session confirmed it. The evidence is the binary's code and the settings schema, read in the 2.1.300-2.1.310 binaries; no capture shows a session with the setting refusing to compact. The check: run a long session under `unharness launch` and confirm `/context` or the status line shows no auto-compact countdown, and that a prompt-too-long ends in an error, not a summary.
2. The setting reaches Claude Code through `--settings` (flag settings). I read that `js("autoCompactEnabled")` resolves across setting sources, flag settings included, but did not trace the source order.
3. Belt and braces: launch could also set the env `DISABLE_AUTO_COMPACT=1`, which `Hp()` honours independently of every settings source, including a policy file. That is a one-entry registry change for a 4.1.1, if you want it.
