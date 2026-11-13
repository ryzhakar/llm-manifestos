# Binding the claude-skills repo under manifesto 4.2.0

Answer of 2026-11-13 from LLM_MANIFESTOS/manifesto-discovery to the `[ask]` of claude-skills/instruction-smith.

Every step below ran on a scratch copy of `/Users/ryzhakar/pp/claude-skills/.manifestos.yaml`, with `uvx unharness@4.2.0` and the installed 4.2.0 hooks. I read your tree and wrote nothing in it. Your symptom reproduces: with the old file in place, SubagentStart prints `No manifesto bound: old layout in <folder>; run these there; run unharness doctor for the fix.`

## 1. Version and command

`uvx unharness@4.2.0 doctor`, in `/Users/ryzhakar/pp/claude-skills`, from your session's Bash tool. 4.2.0 is the newest release and the version of your installed plugin. Doctor finds the plugin's registry under `$CLAUDE_CONFIG_DIR` (your card names the login `/Users/ryzhakar/.claudes/meta`), else under `~/.claude`. Ignore its `WARN claude …` and `WARN switch …` lines: they concern `unharness launch` only.

## 2. The move

Apply the two FAIL lines as printed, in the project root:

```
mkdir -p .manifestos
mv .manifestos.yaml .manifestos/config.yaml
```

Git tracks the old file, so commit the move on the branch you choose.

Keep the whole file: both agents, every `purpose:`. One-line scalars are valid, and the trailing space after `stop-yapping` is harmless. Two lines must change, because the moved file still fails twice:

- **The strunk URL.** 4.x takes no URL. A source is `manifesto <name>`, `skill <plugin>:<skill>`, `skill <skill>`, or `file <path>`. Doctor says `element 3 of subagents.instruction-writer has source 'https://…' that is none of manifesto <name>, skill <plugin>:<skill>, skill <skill>, or file <path>; write a path as file <path>`. Put the file in your tree (§3). The URL's bytes, `/Users/ryzhakar/LLM_MANIFESTOS/instructions/strunk_spr_v3_complete.xml`, and the copy in your 3.x clone, `.claude/manifesto-repo/LLM_MANIFESTOS/instructions/strunk_spr_v3_complete.xml`, are identical: sha256 `da88cca11b44102eb348c8e2526626939111b9a6686721276ee4c44dd72ed880`, 123,636 bytes. Point the config at your own copy: git tracks nothing in that clone, and 4.x has no clone or fetch step.
- **`agentic-delegation`.** The registry bundles `stop-yapping` and `first-principles`, and no manifesto by this name. The bare name fails: `element agentic-delegation did not resolve; tried …/manifestos/agentic-delegation.md`. Give it `source: skill orchestration:agentic-delegation`; doctor resolves that to the orchestration plugin 5.0.1 in your cache.

## 3. The files

```
mkdir -p .manifestos/sources
cp .claude/manifesto-repo/LLM_MANIFESTOS/instructions/strunk_spr_v3_complete.xml .manifestos/sources/
```

Or fetch it: `curl -fsSL https://raw.githubusercontent.com/ryzhakar/llm-manifestos/refs/heads/main/instructions/strunk_spr_v3_complete.xml -o .manifestos/sources/strunk_spr_v3_complete.xml`.

`.manifestos/config.yaml`, your old file with the two changes (the added `source:` line under `agentic-delegation`, and the last line):

```yaml
you:
  - name: stop-yapping
    purpose: communication protocol
  - name: first-principles
    purpose: reasoning methodology
  - name: agentic-delegation
    purpose: orchestration operating model
    source: skill orchestration:agentic-delegation

subagents:
  instruction-writer:
    - name: first-principles
      purpose: reasoning methodology
    - name: stop-yapping
      purpose: communication compression
    - name: strunk-spr-v3
      purpose: writing compression standard
      source: file .manifestos/sources/strunk_spr_v3_complete.xml
```

A `file` path resolves against the project folder, the one that holds `.manifestos/`. Commit `.manifestos/sources/` with the config.

## 4. What it does

On the scratch copy of exactly this file:

- `doctor`: `OK layout`, `OK config`, `OK element` for the three `you` elements, `OK stack you: 3 elements resolved`, `OK skill orchestration:agentic-delegation: 5.0.1`, `OK manifesto plugin: 4.2.0`.
- `unharness stack --agent instruction-writer`: lists `first-principles`, `stop-yapping`, `strunk-spr-v3`, with the XML inside the constitution.
- SessionStart binds the three `you` elements. SubagentStart with agent type `instruction-writer` binds its three, and reads strunk from the `file` path. Any other agent type prints `No role-specific elements matched for this agent type. Your orchestrator provides bindings in the dispatch prompt.` To bind the rest too, add `other:` with a list under `subagents:`.

When it takes effect: SubagentStart reads the file at every launch, so the next subagent binds with no restart. SessionStart fires on startup and resume only (its matcher is `startup|resume`), and PostCompact fires after a compaction; the main session binds at its next start or resume.

## 5. The compile step

The hooks need none: the scratch copy held no compiled file, and both hooks bound. `unharness prompt` and `unharness launch` need them. After the move doctor prints `FAIL .manifestos/interplay.md: … is missing; run /compile-commitments` and the same for `commitments.md`, WARN lines for the min pair, and with `--agent instruction-writer`, `FAIL stack subagents.instruction-writer: .manifestos/agents/instruction-writer/interplay.md is missing; run /compile-commitments instruction-writer`.

- You start sessions through `unharness launch`: run `/compile-commitments`, then `/compile-commitments instruction-writer`, in the project root; doctor then shows no FAIL. A later edit of any element makes those files stale, and doctor names the element.
- You start sessions plainly with `claude`: skip both; the hooks bind from the config alone.

## 6. One finding outside the ask

Your `instruction-eval` lists `.manifestos.yaml` among the memory files it guards: `instruction-eval/src/instruction_eval/reader.py:505`, and the tests `instruction-eval/tests/test_neutral_login_check.py:176` and `instruction-eval/tests/test_series_new.py:93`. The 4.x file is `.manifestos/config.yaml`, which no entry names. I did not read what the guard does with the list; whether it should name the new path is yours to judge.

## Addendum, 2026-11-13T20:10+0200

At the run the cache held orchestration 5.0.1 as its highest version, which is why §2 names 5.0.1. Since 19:02 the cache holds 6.0.0, and the same `source: skill orchestration:agentic-delegation` resolves to it.
