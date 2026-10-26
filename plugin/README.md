# manifesto

Create concentrated manifesto declarations and bind Claude behavior to user-provided manifestos through identity-assumption protocols.

`manifesto` `behavioral-binding` `identity` `writing` 
## Skills

### [compile-commitments](skills/compile-commitments/SKILL.md)

Write the interplay file and the commitments file that a session's system prompt carries, and their min pair, from the stack the session binds to, or from one subagents key's stack. Use it as `/compile-commitments`, or as `/compile-commitments <key>` for a key under `subagents:`, or after any change to the stack.


---

### [compile-digest](skills/compile-digest/SKILL.md)

Write a local digest, the short body-only text unharness loads in place of one or more full manifestos, and stamp it against their current hashes. Use it as `/compile-digest <slug>...`, or when an unharness message names `/compile-digest`, such as `no digest for <slug>`, `is stale`, or `no cover without overlap`.


---

### [manifesto-oath](skills/manifesto-oath/SKILL.md)

Binds Claude's operating identity to constitutions, manifestos, and principle sets through identity construction — not theatrical oaths. Triggers on oath/binding requests or when hooks inject constitution elements at session boundaries.


---

### [manifesto-writing](skills/manifesto-writing/SKILL.md)

Trigger when users request manifestos or manifesto tone. Name the enemy, strip hedging, compress to sharp distinctions, end with stark choice.


---

## Agents

### [maximalist-reviewer](agents/maximalist-reviewer.md)

Review a set of files against one manifesto at the manifesto's strongest literal reading, with no allowance for cost, convention, or proportion, and write a report file listing every violation with a compliant rewrite. Use it for an ad-hoc review against a chosen manifesto, outside any mandatory review loop. Examples:

<example>
Context: The user wants a module held to the DRY manifesto without exceptions.
user: "Review src/billing against the dry manifesto, maximally"
assistant: "I'll launch the maximalist-reviewer agent with the dry manifesto and the billing paths."
</example>

<example>
Context: A diff should be checked against a writing standard at full strictness.
user: "Hold this diff to Strunk, no mercy"
assistant: "I'll launch the maximalist-reviewer agent with the Strunk source and the diff range."
</example>


**Model:** `inherit` · **Tools:** Read, Write, Grep, Glob, Bash

---

## Unharness

The system prompt carries the stack, its interplay, and its commitments; since the prompt is not part of the conversation, compaction cannot erase the binding, and one captured compaction left the prompt unchanged. Launch switches off the instructions Claude Code adds around it, and `unharness` compiles the prompt and launches Claude Code with it.

A project keeps every file of ours in `.manifestos/`, and the project folder is the folder that holds it. `.manifestos/` holds:

- `config.yaml`, which lists the stacks and whose schema is in [SCHEMA.md](SCHEMA.md); `--config PATH` names another config file, and its folder's parent becomes the project folder.
- `interplay.md` and `commitments.md`, written by `/compile-commitments`, each opening with a `<stack>` block that lists every element with its sha256.
- `interplay.min.md` and `commitments.min.md`, the min pair, which `/compile-commitments` writes in the same run, each opening with the same `<stack>` block and holding in its body, the text after that block, at most a third of the words of its full counterpart's body. `--minified` loads them in place of the full pair.
- `agents/<key>/`, one folder per `subagents:` key, holding the same four files for that key's stack, written by `/compile-commitments <key>`.
- `preamble.md`, optional, which replaces the preamble that tells the model what each text the application adds is, and how to weigh it.
- `digests/`, optional, which holds the digests `/compile-digest` writes and their `index.json`.

On a project still in the old layout, with `.manifestos.yaml` and the files beside it, `unharness` stops with `old layout in <project folder>; run these there:` and the `mkdir` and `mv` lines that move each file, and each hook binds nothing and points to `unharness doctor`; no reader falls back to an old path.

```
/compile-commitments
uvx unharness prompt | uvx unharness launch -- claude
```

The launcher's input is reopened on the terminal, so the session reads the keyboard after the pipe. Any launcher goes after `--`; a name that is not a program on PATH, such as the zsh function `claude@meta`, runs through `$SHELL -ic`. With nothing after `--`, `launch` prints the command it would run and runs nothing.

- `unharness prompt [--config PATH] [--agent TYPE] [--digests] [--stack-digests] [--overlap] [--minified]` prints the compiled prompt; it stops when the interplay or commitments file is missing or its `<stack>` block differs from the current stack. Under `--minified` the same holds for the min pair. `--agent TYPE` compiles the stack of the `subagents:` key that TYPE matches, with the session files in `.manifestos/agents/<key>/`, and takes every mode flag.
- `unharness stack [--config PATH] [--agent TYPE] [--diff] [SLUG ...]` prints the `<stack>` block and the constitution, exactly what a session binds to. Given slugs, it prints those manifestos alone. It takes no mode flag, since a session always binds to full texts. `--agent TYPE` prints the matched key's stack instead of the main one. `--diff` prints, for each of the four session files that is stale, the zero-context unified diff of its recorded `<stack>` lines against the current ones, `<path>: missing` for a missing file, and `<path>: no <stack> block` for a file without one; it exits 0 when every file is current and 1 otherwise. `--agent` and `--diff` each refuse slugs.
- `unharness stamp DIGEST [--config PATH]` writes the digest's entry into its `index.json`.
- `unharness doctor [--config PATH] [--agent TYPE] [--digests] [--stack-digests] [--overlap] [--minified] [--claude-version X.Y.Z]` prints one line per check and exits 1 on any FAIL.
- `unharness switches` prints the strip table below, generated from the switch registry.
- `unharness launch [--keep-claude-md] [--keep-web-search] [--no-hooks] [--claude-version X.Y.Z] [PROMPT] [-- LAUNCHER [ARGS...]]` caches the prompt in `$XDG_CACHE_HOME/unharness/<sha256>.md`, or `~/.cache/unharness/` when unset, and runs the launcher with the switches below. The printed command ends in the terminal's own device, and in `/dev/tty` only when neither output is a terminal.

If ARGS hold one `--settings VALUE` or `--settings=VALUE`, `launch` merges it with its own: VALUE is JSON text when its first non-space character is `{`, else a file path relative to the working folder. The result passes as the one `--settings`, the owner's keys first in their order, then each strip key the owner did not set. The merge is shallow, so a key the owner sets replaces the strip's whole value, and `unharness: your --settings sets <key>; the strip's value is left out` goes on stderr for each. Two `--settings` stop with `pass --settings once after --`. A launcher that adds `--settings` inside itself stays unseen.

`/compile-commitments` reads `unharness stack`, reduces each element to its axioms, and writes the interplay and commitments files and their min pair.
Run it once after each change to the stack; `unharness prompt` stops until the full pair matches, and under `--minified` until the min pair matches. `unharness stack --diff` shows which elements changed.

`--agent TYPE` matches a key under `subagents:` by this cascade, the first match winning: a key equal to TYPE; when TYPE holds `:`, a key equal to the part after its last `:`; the first key in config order, `other` excepted, that TYPE ends with; and `other:`, the default stack. A fall to `other:` prints `unharness: <type> matches no subagents key; using other:, the default stack` on stderr; no match, with no `other:`, stops and names the keys. The subagent-start hook matches by the same cascade.

```
/compile-commitments implementer
unharness prompt --agent dev-cycle:implementer
unharness stack --diff --agent implementer
```

`/compile-commitments <key>` takes a key exactly as written, never a type, since the cascade could map a type to another key's folder.

**Digests.** A digest is the short text that stands in for a manifesto. Under `--digests` each manifesto element enters as its single digest; under `--stack-digests` it may enter inside a stack digest instead. Skills and files enter in full. A single digest is `<slug>.md`; a stack digest is `<a+b>.md`, named by its sorted slugs joined with `+`. unharness reads singles from `.manifestos/digests/`, then from the plugin's `digests/`, and stack digests from `.manifestos/digests/`, then from the plugin's `digests/stacks/`. The local file wins for its stem, even when its entry is stale, so a current plugin copy does not rescue it. The cover rule: unharness chooses, from the digests whose manifestos all belong to the stack, the set that covers every manifesto in the fewest characters, and a tie goes to fewer files, then to the smaller sorted list of stems. Chosen stack digests share no manifesto unless `--overlap` is set. A digest loads only when its index entry holds the current hash of each manifesto it covers; otherwise `prompt` stops with a message that names the fix.

- `--digests`: each manifesto enters as its single digest.
- `--stack-digests`: implies `--digests` and adds stack digests as candidates.
- `--overlap`: lets chosen stack digests share a manifesto; it requires `--stack-digests`.
- `--minified`: loads the min pair in place of the full pair; it combines with the other three.

`prompt` and `doctor` accept the four flags. `/compile-digest <slug>...` writes a local digest and stamps it; run `unharness stamp` on a digest written by hand.

```
unharness stamp .manifestos/digests/dry.md
stamped dry in .manifestos/digests/index.json
```

Each place keeps one `index.json`, in `.manifestos/digests/` and in the plugin's `digests/`, and that index covers every digest of that place, the plugin's `stacks/` included. It maps each stem to the sha256 of every manifesto the digest covers:

```json
{
  "dry": {"dry": "5dd350b8..."},
  "dry+kiss": {"dry": "5dd350b8...", "kiss": "669f4120..."}
}
```

`unharness doctor` reads files and runs `claude --version`, and makes no network call. Each line is `OK`, `WARN`, or `FAIL`, then the check and its detail. A problem with an artifact that `prompt` would load under the given flags is a FAIL; the same problem with an artifact it would not load is a WARN. The first line, `layout`, gives `.manifestos/` in the project folder, or one FAIL line per command that moves an old path, and then doctor skips `config` and every check that needs it. A `stack you` line follows the `element` lines. With `--agent TYPE`, an `agent match` line gives the key TYPE matches, a WARN when TYPE falls to `other:`, and a FAIL when nothing matches. Then one `stack subagents.<key>` line per key, in config order, gives the first problem among the key's elements, its empty list, and its four files in `.manifestos/agents/<key>/`, a FAIL for the matched key when `prompt --agent` would load the problem and a WARN otherwise. A `manifesto plugin` below 4.0.1 FAILs, since 4.0.1 is the first version whose subagent hook binds under unharness. An element that does not resolve leaves out the checks that need the stack: the digests, the cover, the session files, and the prompt size. After `claude`, a `switch registry` line gives the newest registry version and the entry count, and one `switch <kind> <name>` line per entry follows in registry order. These lines need no config and never FAIL. A switch line is `OK` when the entry is verified at the version launch chooses and that version is the one in use; it is `WARN` when the version in use differs, when the version is unknown, and when the entry is left out because it is not verified at the chosen version. `--claude-version X.Y.Z` replaces the detected version in the switch lines, for a launcher that is no program on PATH. An excerpt:

```
unharness doctor --digests
OK layout: /work/project/.manifestos
OK config: /work/project/.manifestos/config.yaml
OK stack you: 2 elements resolved
OK digest dry: plugin, current
OK cover: dry, kiss; 513 words
FAIL .manifestos/interplay.md: .manifestos/interplay.md is missing; run /compile-commitments
WARN .manifestos/interplay.min.md: .manifestos/interplay.min.md is missing; run /compile-commitments
WARN stack subagents.implementer: .manifestos/agents/implementer/commitments.md is stale (changed: dry); run /compile-commitments implementer
WARN claude: /usr/local/bin/claude 2.1.312, not in the switch registry; launch uses switches verified at 2.1.309
OK switch registry: newest 2.1.309; 13 switches
OK prompt size: full 3541 words; shortest 818 words
```

Launch replaces Claude Code's default system prompt with the cached prompt through `--system-prompt-file`, and passes `UNHARNESS=1`, so the session-start, post-compact, and per-prompt drift hooks of this plugin stand down, since the compiled prompt already carries the binding. The subagent-start hook still runs, because a subagent's prompt is not the compiled prompt: it binds each subagent to its stack exactly as in a plain session. `--no-hooks` silences it with every other hook, since `disableAllHooks` has no per-hook scope. The hook tests cover both, and no capture shows them. Launch passes every other switch from the registry `plugin/unharness/src/unharness/switches.json`, and `unharness switches` prints this table from it.

<!-- switches -->
| Injected text | Switch | Default |
|---|---|---|
| Billing header block | env `CLAUDE_CODE_ATTRIBUTION_HEADER=0` | stripped |
| Every CLAUDE.md | env `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` | stripped; `--keep-claude-md` keeps |
| Git status snapshot; commit and PR text in the Bash tool description | env `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1`, setting `includeGitInstructions: false` | stripped |
| Auto memory section | env `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, setting `autoMemoryEnabled: false` | set |
| "The user hasn't heard from you in a while" note | env `CLAUDE_CODE_SILENT_TURN_REMINDER=0`, undocumented | stripped |
| Task-list and TodoWrite nudges | env `CLAUDE_CODE_TODO_REMINDER_MODE=off`, undocumented | stripped |
| Token-count line | env `CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off`, undocumented | stripped |
| WebSearch paragraph | `--disallowedTools WebSearch` | stripped; `--keep-web-search` keeps |
| Co-Authored-By trailer and PR footer | setting `attribution: {"commit": "", "pr": ""}` | set |
| Output style text | setting `outputStyle: "default"` | set |
| Hook output | setting `disableAllHooks: true` | kept; `--no-hooks` strips |
<!-- /switches -->

`stripped` means a capture without the switch showed the text and a capture with it did not. `set` means the docs and the binary implement the switch, but no capture without it showed the text, so its removal is inferred. `kept` means launch leaves the text in unless the option beside it strips it. `undocumented` means no Claude Code docs page names the switch, so a release may drop it. The `Hook output` row covers the subagent hook too.

**Version.** Each registry entry records the Claude Code versions at which a capture confirmed it. `launch` asks the launcher for its version by running `LAUNCHER ARGS... --version`, directly when the launcher is a program on PATH and through `$SHELL -ic` otherwise, and runs `claude --version` when no launcher follows `--`. It takes the first output line that opens with `X.Y.Z`. It then chooses one registry version, the detected version when the registry holds it, else the nearest registry version below it, else the oldest registry version, and passes the entries verified at that version. When the choice differs from the detected version, it writes `unharness: claude <D> is not in the switch registry; using switches verified at <C>` on stderr. When the launcher times out after ten seconds, fails to start, or prints no version, `launch` uses the newest registry version and writes `unharness: <launcher> --version printed no version; using switches verified at <newest>` on stderr. `--claude-version X.Y.Z` states the version and runs nothing, for a launcher such as `claude@meta` that cannot answer; any other value stops `launch` with `--claude-version takes X.Y.Z, got <value>`. At 2.1.309 the printed command equals the one 3.6.1 printed.

**What stays.** The harness adds each item below, and either no switch removes it or the only switch drops something kept on purpose. The evidence is in `orchestration_log/history/2026-10-23/verification-unharness.md`, with the captures d1-p-haiku and d1-p-opus (print mode), d1-tmux-haiku (interactive sessions), d1-flag-keepmd, d1-flag-nohooks, d1-flag-websearch, b2-full-haiku, and a3-c5.

- The identity line: `You are Claude Code, Anthropic's official CLI for Claude.` in interactive sessions, `You are a Claude agent, built on Anthropic's Claude Agent SDK.` in print mode.
- The context wrapper around the email line, in a user message; the date line sits outside it.
- File-changed notes: their one switch, `CLAUDE_CODE_DISABLE_ATTACHMENTS`, also drops the skill list.
- The Agent tool's worktree sentence and the other tool descriptions.
- MCP server instructions when MCP servers are configured.
- The tool, skill, and agent lists and the environment block, kept on purpose.

Run it from the package, or from git at a tag:

```
uvx unharness
uvx --from "git+https://github.com/ryzhakar/llm-manifestos@v4.0.1#subdirectory=plugin/unharness" unharness
```

Inside a session, `bin/unharness` runs the copy bundled with the plugin; `UNHARNESS_FROM`, a path or a git URL, runs another source.

## Install

```
/plugin marketplace add ryzhakar/llm-manifestos
/plugin install manifesto@llm-manifestos
```

## Tests

Run from the repository root:

```
python3 -I plugin/tests/test_hooks.py
uv run --project plugin/unharness pytest -q
```
