# .manifestos/config.yaml Schema Reference

## Format variants

### Flat list (backwards compatible, orchestrator-only)

Root is a YAML list. All elements bind to the orchestrator. No subagent bindings.

```yaml
- only-fluff-die
- first-principles
- agentic-delegation
```

### Grouped mapping (full form)

Root is a YAML mapping with `you:` and/or `subagents:` keys. Supports optional top-level fields.

```yaml
manifesto_dir: /path/to/a/folder/with/a/manifestos/subfolder
you:
  - only-fluff-die
  - name: first-principles
    purpose: reasoning methodology
  - name: agentic-delegation
    purpose: orchestration operating model
    source: skill orchestration:agentic-delegation

subagents:
  instruction-writer:
    - name: first-principles
    - name: strunk-spr-v3
      purpose: writing compression standard
      source: file standards/strunk_spr_v3_complete.xml
  other:
    - first-principles
```

---

## Where the config lives

1. Hooks: `.manifestos/config.yaml` in `$CLAUDE_PROJECT_DIR`, else in the current folder. `unharness`: the `--config` path, default `.manifestos/config.yaml` in the current folder.
2. Only when that file is absent: the `## Active Manifestos` section of the `CLAUDE.md` in the project folder, the folder that holds `.manifestos/`, up to the next `## ` heading, read as the same YAML.
3. Neither: the hooks stay silent; `unharness` stops with `no config: tried <path> and the Active Manifestos section of <CLAUDE.md path>`.

One module reads it: `unharness/src/unharness/config.py`. The hooks run it with `python3 <config> --json --project <folder>`, which prints `directory` (the project folder), `registry` (the resolved `manifesto_dir`, or empty), and each element's `name`, `purpose`, `source_type`, and `reference`; `unharness` imports it. It needs only the standard library and runs on Python 3.9 or later when run as a script.

---

## Element forms

Each element in any list is one of:

**String** — a registry manifesto by name.

```yaml
- only-fluff-die
```

A colon not followed by a space belongs to the name: `- agent-conduct:write-well` is the name `agent-conduct:write-well`.

**Mapping** — `name`, and optionally `purpose` and `source`. Other keys are dropped.

```yaml
- name: first-principles
  purpose: reasoning methodology
  source: manifesto first-principles
```

**Null** (`~`, `null`, or an empty item) — dropped. An empty or absent list is an empty stack.

---

## Fields

### Top-level mapping fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `you` | list of elements | no | empty | The orchestrator's constitution. |
| `subagents` | mapping of role to list of elements | no | empty | Constitutions by agent type. A role with no value is an empty list. |
| `manifesto_dir` | string (path) | no | hooks: `${CLAUDE_PLUGIN_ROOT}`; `unharness`: the manifesto plugin at its highest version in the plugin cache | The folder whose `manifestos/` subfolder is the registry. Ignored in the flat list form. A relative path resolves against the config's folder, to an absolute path with symlinks followed, in the hooks and in `unharness` alike. |

Any other top-level key is ignored.

### Element fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes, except for a `file` source | The label and tag, with no whitespace. For a `file` source it defaults to the file's stem. |
| `purpose` | no | Freeform text. Hooks inject it as natural language; `unharness` puts it in `governs`. |
| `source` | no | A source type and its reference, below. Absent means a registry manifesto named `name`. |

### Source types

| Source | Resolves to |
|--------|-------------|
| none, or `manifesto <name>` | `<registry>/manifestos/<name>.md` (the reference is `name` when no source is given) |
| `skill <plugin>:<skill>` | `skills/<skill>/SKILL.md` of the plugin at its highest version under `<login>/plugins/cache/<marketplace>/<plugin>/<version>/` |
| `skill <skill>` | `<login>/skills/<skill>/SKILL.md` |
| `file <path>` | the file, relative to the folder holding the config |
| any other first word (a bare path, a URL, a hint), or `manifesto`, `skill`, or `file` with no reference | stops the load, naming the `file <path>` form |

The login folder is `$CLAUDE_CONFIG_DIR`, else `~/.claude`. Versions compare by number, so `1.10.0` is above `1.9.0`. `unharness` strips a text file's frontmatter, only when the line after the opening `---` starts a `key:` line, so a block of prose between two rules stays; it replaces `${CLAUDE_PLUGIN_ROOT}` with the registry's plugin folder or the skill's version folder; a user skill and a file keep the placeholder as written.

---

## Errors

Every error is one line, except the old-layout error, which holds one line per command. `unharness` prints `unharness: <message>` on stderr and exits 1. When `config.py --json` exits 1, or a config, parse, or resolve error otherwise stops a hook, SessionStart, PostCompact, and SubagentStart each print the whole message on stderr, then one line on stdout in the hook's own output form, plain text for SessionStart and `hookSpecificOutput.additionalContext` for the other two, and exit 0. The line enters the session's context:

    No manifesto bound: <the message's first line>; run unharness doctor for the fix.

UserPromptSubmit prints the message on stderr alone. A missing config is the exception: the hooks stay silent on both streams, and `config.py` exits 2 instead of 1 so they can tell it apart.

| Line | Cause |
|------|-------|
| `no config: tried ...` | no config file and no CLAUDE.md section |
| `<list> must be a list of elements` | `you` or a role holds a scalar or a flow list such as `[a, b]` |
| `subagents must be a mapping of role to list of elements` | `subagents` holds a scalar or a list |
| `element N of <list> has no name; add name: or a file source` | a mapping without `name` and without a `file` source; `<list>` is `you` or `subagents.<role>` |
| `element X did not resolve; tried <path>` | the one path the source names does not exist; with no cached plugin the path shows the pattern `plugins/cache/*/<plugin>/*/...` |
| `element N of <list> has source 'S' that is none of manifesto <name>, skill <plugin>:<skill>, skill <skill>, or file <path>; write a path as file <path>` | a legacy or malformed source |
| `element N of <list> name 'X' must hold no whitespace; add name:` | a name, or a file stem used as one, that holds whitespace |
| `cannot place the line 'L'; check its indent`, `the line 'L' is indented with a tab; indent with spaces`, `key 'K' appears twice` | the YAML reader refuses a line it cannot place, a tab indent, or a repeated key |
| `old layout in <project folder>; run these there:` and then one command per line | an old path such as `.manifestos.yaml` or `.claude/digests` exists in the project folder; a `# both <old> and <new> exist; keep one and delete the other` line stands for a pair whose new path exists |
| `key 'K' holds a block scalar; block scalars are not supported; write the value on one line`, `the line 'L' holds a block scalar; ...` | a value that is `>` or `|` with an optional `-` or `+` and digit, as a mapping value or a list item, in the config or in manifesto frontmatter |
| `subagents key 'K' cannot name a folder` | a `subagents:` key that holds `/` or is `.` or `..` |
| `the stack is empty` | `unharness prompt`, or `stack` with no slug, and no element in `you` |
| `<file> is missing`, `<file> is stale (...)`, `<file> has no <stack> block` | a session file of `unharness prompt`, the min pair under `--minified`; each names the file by its path under the project folder and ends `run /compile-commitments`, or `run /compile-commitments <key>` for `.manifestos/agents/<key>/` under `--agent` |
| `<type> matches no subagents key and the config has no other:; keys: <key>, <key>` | `--agent` with a type no key matches and no `other:`; `keys: none` when the config has no subagents |
| `subagents.<key> is empty` | the matched `subagents:` key holds no element |
| `<type> matches no subagents key; using other:, the default stack` | not an error: the one line `--agent` prints on stderr when the type lands on `other:` by the last step |
| `--agent takes no slugs`, `--diff takes no slugs` | `stack --agent` or `stack --diff` with slugs |
| `pass --settings once after --` | two or more `--settings` after `--` in `launch` |
| `--settings file <path> cannot be read: <reason>`, `--settings <value> is not a JSON object` | the owner's `--settings` names an unreadable file, or holds text that is no JSON object |
| `your --settings sets <key>; the strip's value is left out` | not an error: the note `launch` prints on stderr for each key the owner's `--settings` shares with the strip |
| `--overlap requires --stack-digests` | `--overlap` without `--stack-digests` |
| `manifesto <slug> appears twice in the stack; digest modes need each once` | a digest flag on a stack that lists one manifesto twice |
| `no digest for <slug>: tried <local path> and <plugin path>; run /compile-digest <slug>` | a digest flag, and no single or stack digest covers the manifesto |
| `<digest path> has no entry in <index path>; run unharness stamp <digest path>` | a digest the flags load, and its index lacks its stem or holds an entry for other slugs |
| `<digest path> is stale (changed: <slug>, ...); run /compile-digest <slug> ...` | a manifesto changed since its digest was stamped |
| `<index path> is not a JSON object of stems to slug hashes; fix or delete it, then run unharness stamp on each digest it covers` | a malformed `index.json` |
| `no cover without overlap; add --overlap or run /compile-digest <slug> for each of: <slugs>` | stack digests cover a manifesto that has no single digest, and every choice of them overlaps |
| `no digest at <path>`, `<name> is not named by sorted, distinct slugs joined by +` | `unharness stamp` on a missing file, or on a stem with unsorted or repeated slugs |

---

## YAML subset

Block mappings and lists of string scalars, indented with spaces. A list must be indented deeper than its key; a list written at its key's own indent stops the load. Whole-line and trailing `#` comments are dropped. A quoted scalar loses one pair of quotes. `~`, `null`, and an empty value are null. Flow collections, anchors, and block scalars (`>` and `|`) are not supported; a block scalar stops the load with its own error. A line the reader cannot place, such as a mis-indented list item or element field, a tab in the indent, and a repeated key, stops the load with an error that names the line or key. Manifesto frontmatter is read by the same reader.

---

## Scope keys

| Key | Meaning |
|-----|---------|
| `you:` | Orchestrator constitution. Injected by SessionStart and PostCompact hooks as natural language prose. |
| `subagents:` | Mapping of agent-type keys. Each key names a list of elements for that agent type. |
| `other:` (under `subagents:`) | The default stack: the key for agents matching no specific key. |

---

## Hook behavior

### SessionStart / PostCompact

Read the config through `config.py --json`, render `you:` elements as natural language prose, one sentence per element: `"<name>" governs your <purpose>` or `"<name>" is part of your constitution`, then `— <where>`. The where depends on the element's source:

| Source | Where |
|--------|-------|
| `file <path>` | `read it from <absolute path beside the config>` |
| `manifesto <name>` | `read it from <manifesto_dir>/manifestos/<name>.md` |
| `skill <plugin>:<skill>` or `skill <skill>` | `read it from skill <plugin>:<skill>`, or `skill <skill>`, as written |
| none | `resolve its location via the tiered protocol before binding` |

Compose output from three parts: hook-specific preamble + shared binding core + inline footer. NEVER inject raw YAML.

The footer includes a SUBAGENT BINDING REINFORCEMENT block instructing the orchestrator to use first-person user voice in dispatch prompts, so subagents receive binding directives as owner instructions rather than forwarded AI text.

The orchestrator is NOT responsible for supplying base subagent bindings — SubagentStart handles that automatically. The orchestrator MAY augment subagent bindings via dispatch prompts.

### SubagentStart

Reads `agent_type` from stdin JSON. Matches against `subagents:` keys in `.manifestos/config.yaml` with `subagent_key` from `config.py`, which `unharness prompt --agent` calls too, so the hook and the package cannot disagree. The cascade:

1. Exact key match
2. Prefix-strip match (the part after the last `:`)
3. Suffix match (the first key in config order, `other` excepted, that `agent_type` ends with)
4. `other:`, the default stack; an empty `agent_type` goes straight here
5. Static fallback (no key matches and the config has no `other:`)

Injects the FULL binding ceremony — same resolution protocol, transitive reading, interplay analysis, and manifesto-oath mandate as the orchestrator hooks. This is a real binding injection, not a reminder.

The ceremony carries element names, purposes, and configured sources — never element content. Subagents read or fetch each element themselves; dispatch prompts carry sources for elements the config omits.

Tier 2 resolution injects the plugin cache path so subagents can resolve skills from the installed plugin location without knowing the absolute path at authoring time.

### UserPromptSubmit

Fires on every user message. Looks up the file `<manifesto_dir>/manifestos/<reference>.md` for each `you:` element with no source or a `manifesto` source, the reference being the element's name when no source is given, and prints that file's frontmatter tagline; any other element, and a file with no tagline, prints bare. Injects the taglines as a brief drift-prevention reminder into the hook output.

Output accumulates in conversation history (platform behavior) — this is intentional. Each injection reinforces the active constitution without re-running the full binding ceremony.

### Standing down under unharness

When `UNHARNESS` is set and not `0`, SessionStart, PostCompact, and UserPromptSubmit each print nothing and exit 0, because the compiled system prompt already carries the binding. SubagentStart runs as in a plain session, since a subagent's prompt is not the compiled prompt.

### Launch switches

`unharness launch` passes the switches that `plugin/unharness/src/unharness/switches.json` records. The strip table in the Unharness section of [`README.md`](README.md) lists each one and says whether a Claude Code docs page names it; a release may drop an undocumented switch. `launch` picks the entries verified at one registry version, chosen from the launcher's version or from `--claude-version X.Y.Z`; the Unharness section of [`README.md`](README.md) states the rule and its fallbacks.

### Template architecture

Composable parts live in `hooks/templates/parts/`:

| File | Used by |
|------|---------|
| `preamble-session.txt` | SessionStart |
| `preamble-compact.txt` | PostCompact |
| `preamble-subagent.txt` | SubagentStart |
| `binding-core.txt` | All three hooks (shared) |

Footers are inlined in the shell scripts, not extracted to files. The element sentences come from `hooks/describe_elements.py`, which all three binding hooks call.

---

## Bundled manifestos

The plugin carries `manifestos/` and `digests/` in its own folder. Every hook reads `${CLAUDE_PLUGIN_ROOT}/manifestos` (or the `manifesto_dir` override) directly; no hook clones, pulls, or touches the network.

---

## Parsing rules

1. Root is a list → treat as `you:` section; no subagent bindings.
2. Root is a mapping → read `you:`, `subagents:`, and `manifesto_dir:`.
3. String node in any list → `{name: <string>}`.
4. Mapping node → `{name:, purpose:, source_type:, reference:}`, the source split into its type and reference; a file source supplies the name when `name` is absent.
5. Null node → dropped.
