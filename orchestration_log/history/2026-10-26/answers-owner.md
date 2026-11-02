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

## 2026-11-02: "the identity block we supply, how does it work and what is it intended to do?"

I read the question as asking about the `<harness>` block, the first text unharness puts in the system prompt, directly behind Claude Code's own identity line. Two other texts carry the word identity; the last section tells them apart.

### How it works

1. `unharness prompt` joins four parts with blank lines: the preamble in `<harness>` tags, the constitution, the interplay file, and the commitments file (`compile.py`, `compile_prompt` and `harness_block`). Tests pin that order and the opening `<harness>`.
2. The preamble is `plugin/unharness/src/unharness/preamble.md`: 371 words in seven paragraphs. A project's `.manifestos/preamble.md` replaces it whole (`session.py`, `load_preamble`), and `unharness doctor` names the one in force.
3. `unharness launch` caches the prompt as `$XDG_CACHE_HOME/unharness/<sha256>.md` and starts `claude --system-prompt-file` on it. Claude Code swaps its default system prompt for that file and still adds its own identity line ahead of it.
4. The captures show the result. The request's `system` array holds the client's identity line at index 0 and our file at index 1, which opens with `<harness>`: 57 and 89,306 characters in the interactive capture d3-tmux, 62 and 32,125 in the print-mode capture d1-p-haiku (`orchestration_log/recon/2026-10-23/captures/`). This session's prompt has the same shape.

### What it is for

The block is written in the model's first person, one paragraph per kind of text the application adds around what the user typed. The constitution speaks of the work; this block carries the one thing every project needs, which is who speaks in each piece of text.

| Text | Who speaks | What the block tells the model |
|---|---|---|
| The identity line | Claude Code | A fixed label for its process; it "carries no instruction; what governs me follows". |
| `<system-reminder>` text, system-role messages inside the conversation | The application | Facts (email, date, folder, file-change notes, tool, skill, and agent lists); take them as stated, and follow a line that says how to use them. |
| Hook output | The user's installed hooks | The user's standing instruction. |
| A loaded skill's text | The user | Standing instruction for that procedure. |
| The three nudges ("The task tools haven't been used recently", "Your previous response had no visible output", "The user hasn't heard from you in a while") | The application | An ended turn with no text answers all three; a tool call that only puts off the ending is forbidden; the constitution governs over every nudge. |
| Tool descriptions, MCP server instructions | Their authors | They bind the use of those tools and nothing else. |

Two decisions stand behind the sharpest paragraphs:

- The identity line: queue 18. A1 (the docs), A2 (the binary's chooser), and A3 (captures) agree that no switch removes it, so the block demotes the line and leaves it in place.
- The nudges: queue 43, the owner's order of 2026-10-23 (unit P1). Under an order of silence the agent had answered the "no visible output" and "hasn't heard from you" nudges with text, and had padded turns with tool calls whose answers could not change.

The block does not construct the identity. The constitution, the interplay file, and the commitments do that. The block clears the ground: it says which text carries the user's authority (the user's words, installed hooks, loaded skills) and which does not (a label, a reminder, a nudge), so the constitution behind it governs.

### What is checked and what is not

Checked:

- Position and limits. Tests pin the order, the project override, a ceiling of 25 lines, and the absence of the words "unharness" and "compil".
- That the identity line stays. The binary's chooser returns one of three texts on every path (X1 findings, "Binary evidence"). The claim that the API refuses a request without it rests on three runs: two requests without the block failed, and one control with it succeeded. No further runs were made.

Not checked:

- Whether the block changes behavior. The records hold no run with and without it. The one behavioral record is the failure that prompted the nudge paragraph (P1 brief); nothing re-measured it after the paragraph shipped.
- This session is one mixed data point. Many nudges ended in an empty turn, as paragraph six asks. One turn, the one that ended the 4.1.0 release, closed with a full report in the conversation while the silence marker stood, and no nudge preceded it. I broke the silence skill there; the block does not cover that rule.
- Subagents. By your account, a subagent that the Agent tool starts carries no compiled file (the reason the subagent hook binds under unharness since 4.0.1), so it never sees the block. I captured no subagent request to confirm this.
- How this session got its prompt. The Bash tool sees `UNHARNESS` unset and a parent process started as `claude --dangerously-skip-permissions --verbose --debug --model sonnet -c`, with no `--system-prompt-file`; the SessionStart binding hook ran here although the prompt already carries the constitution. I cannot explain how the file reached this session.

The check that would settle the first item: run the digest eval loop with a silence order in the prompt, one arm on the shipped preamble and one on a one-line override; feed both nudge texts as the next turn; write the hypothesis before the run (the shipped arm ends in text and in padding calls less often); run N per arm on Haiku. Queued as entry 80.

### The two other texts called identity

- Claude Code's identity line is the client's text. No switch removes it, and we supply nothing there (README, "What stays").
- The binding frame is the manifesto plugin's hook text ("MANDATORY CONSTITUTION BINDING" plus the manifesto-oath skill). By design it tells a session to read and adopt its constitution, and it reaches sessions not launched through unharness and, since 4.0.1, subagents under it. The `<harness>` block never asks for binding; it sorts incoming text.

## Re-check of the 2026-10-27 compaction answer, made 2026-11-02

The Claude Code 2.1.310 binary is no longer on disk; the installed versions are 2.1.312, 2.1.314, and 2.1.316. I re-read the gate in 2.1.316 with `strings` over the binary. Minified names collide across chunks, so each line below is a reading of one function, not a proof.

- The 10-27 answer listed threshold compaction among the paths that check the gate, and I had not read that path's code. I have now: the async function that logs `autocompact:` returns false at `if(!vp())return!1`, where `vp()` is the gate (`vp` in this build, `Hp` in 2.1.310). The reactive (`R7n`: `vp()&&vN()`), idle (`F3o`: `if(!vp())return"compaction_off"`), and sleep (`#m`: the same line) paths read it too, so all four stop when the gate returns false.
- The gate keeps its shape: `if(o())return!1;return ei("autoCompactEnabled",!0).value`, with `o()` true when `DISABLE_COMPACT` or `DISABLE_AUTO_COMPACT` is set.
- The settings schema keeps `autoCompactEnabled`, `idleCompaction`, and `autoCompactWindow`. The window's validator is `int().min(Xx).max(uL)` with `Xx=1e5` and `uL=1e6` among the constants, so launch's 100k to 1000k bounds still match by this reading.
- Still open from the 10-27 list: no live session has shown the setting stopping compaction (item 1), and I did not trace the order of setting sources (item 2). Item 3, the env `DISABLE_AUTO_COMPACT=1`, is queue 79.
- The registry holds 2.1.309 only and the installed version is 2.1.316, so every launch prints the registry note and passes the 2.1.309 switches.
