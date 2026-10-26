# Spec: unharness

The one home of the design. The owner's brief is `task-long-run.md`; the owner's answers are in `queue-long-run.md` under "Resolved in a round" (cited below as round N); units and status live in `plan-long-run.md`. Items marked RESEARCH wait on the reports named in the plan.

## Purpose

Take a session's instructional foundation back from the harness. The system prompt carries the manifesto stack, its interplay, and its commitments as one instruction flow; launch switches strip what Claude Code injects, keeping only the tool, skill, and agent registries. Because the binding lives in the system prompt, auto-compaction cannot erase it (round 16).

## Usage

    # once per stack change, inside a session in the project:
    /compile-commitments        # writes .manifestos.interplay.md and .manifestos.commitments.md
    # each launch, in the owner's shell:
    uvx unharness prompt | uvx unharness launch -- claude@meta

## Files in a project (round 15, round 16)

- `.manifestos.yaml`: the stack, its `you:` list read by the plugin's hooks and by unharness alike.
- `.manifestos.interplay.md`, `.manifestos.commitments.md`: written by `/compile-commitments`; each opens with the `<stack>` block that `unharness stack` prints.
- `.manifestos.preamble.md`: optional; replaces the shipped preamble.

## Config schema, evolved (round 15)

Every element resolves by an explicit source type; nothing is guessed.

- A bare string, `- dry`, or a mapping without `source`: the manifesto `name` in the registry (legacy form, kept).
- `source: manifesto <name>`: the registry file whose stem is `<name>`.
- `source: skill <plugin>:<skill>`: that plugin's `skills/<skill>/SKILL.md` at the highest version present in the login's plugin cache, `<login>/plugins/cache/<marketplace>/<plugin>/<version>/`.
- `source: skill <skill>`: the user skill `<login>/skills/<skill>/SKILL.md`.
- `source: file <path>`: a local file, relative to the folder holding the config.
- Each element may carry `name` (the label and tag; for a file it defaults to the stem) and `purpose`; `name` is required except for a file source.
- Any other `source` form (a bare path, a URL, a hint) is refused at load with an error naming the `file` form, in `config.py` alone; `unharness` stops with that message and a hook prints it on stderr and exits 0 (triage decision c).
- The registry is `<manifesto_dir>/manifestos/` when the config sets `manifesto_dir`, else the installed manifesto plugin's `manifestos/` at its highest cached version. The login is `$CLAUDE_CONFIG_DIR`, else `~/.claude`.
- An element that does not resolve exactly stops the compile, naming the element and every path tried.
- One home: unharness and the hooks read the schema through one stdlib-only module, `plugin/unharness/src/unharness/config.py`, which the hooks run with `python3` by path; `plugin/hooks/parse_config.py` and `mini_yaml.py` are deleted once the hooks use it (C3).

## Builders

C1, C2, C3, C5 work in the worktree `/Users/ryzhakar/LLM_MANIFESTOS.worktrees/unharness` (branch `feat/unharness`); C4 works in `/Users/ryzhakar/LLM_MANIFESTOS.worktrees/oath` (branch `feat/unharness-oath`), so two agents never commit in one tree. Package: `plugin/unharness/pyproject.toml` with `uv_build`, src layout, console script `unharness`, Python >= 3.11, no runtime dependencies; tests with pytest under `plugin/unharness/tests/`.

## Compiled prompt (round 1)

One flow in the agent's own voice, tags for structure, and no seams: nothing names how the prompt was made, and no label says manifesto, skill, file, source, or compiled.

    <harness>
    {preamble}
    </harness>

    <constitution>
    <{name} governs="{purpose}">
    {text with frontmatter removed and ${CLAUDE_PLUGIN_ROOT} replaced by the resolved plugin folder}
    </{name}>
    ...one per element, in config order...
    </constitution>

    {.manifestos.interplay.md without its <stack> block: the session's own <interplay> ... </interplay>}

    {.manifestos.commitments.md without its <stack> block: the session's own <commitments> ... </commitments>}

- `governs` is omitted when the element has no purpose.
- Only listed elements enter the prompt; a document an element refers to stays a reference (solved 14).
- `prompt` stops when either session-written file is missing, or its `<stack>` differs from the current one, naming `/compile-commitments` and each changed element (round 19).
- The `<stack>` block lists one line per element in order: name and the sha256 of its resolved text with its purpose (solved 13).

## Verbs (round 2, round 3, round 20; queue 33, 37, 41)

- `unharness prompt [--config PATH] [--digests] [--stack-digests] [--overlap] [--minified]`: prints the compiled prompt; the four mode flags pick the constitution's texts and the session files, as the 3.6.0 part below specifies.
- `unharness stack [--config PATH] [SLUG ...]`: prints the `<stack>` block and then the `<constitution>`, exactly what a session binds to; `/compile-commitments` uses it (solved 15). Given slugs, it prints the block and the constitution of those registry manifestos alone, in the given order and without purposes; `/compile-digest` uses that form. It takes no mode flag, since a session always binds to full texts.
- `unharness stamp DIGEST [--config PATH]`: writes DIGEST's entry into its digest index.
- `unharness doctor [--config PATH] [--digests] [--stack-digests] [--overlap] [--minified]`: prints one line per check and exits 1 on any FAIL.
- `unharness launch [--keep-claude-md] [--keep-web-search] [--no-hooks] [PROMPT] [-- LAUNCHER [ARGS...]]`: takes the prompt from PROMPT or stdin, refuses an empty prompt, and stops with a message when no PROMPT is given and stdin is a terminal; writes it to `${XDG_CACHE_HOME:-~/.cache}/unharness/<sha256>.md`; runs `LAUNCHER ARGS...` followed by its own arguments, with its own environment variables set; reopens the launcher's input on the terminal device of stdout, else stderr, and on `/dev/tty` only when neither is a terminal (`claude </dev/tty` crashes 2.1.309, D1); runs a launcher that is not a program on PATH, such as the zsh function `claude@meta`, through `$SHELL -ic`. With no launcher, it prints the command it would run with `claude` as the launcher, one shell-quoted line ending in `</dev/tty`, and runs nothing.

## Strip set (settled 2026-10-23 from A1-A3; B2 and D1 verify by capture)

Environment variables go straight into the launcher's environment; settings keys ride in one `--settings` JSON argument.

| Injected text | Switch | Default |
|---|---|---|
| Default system prompt | `--system-prompt-file <cache file>` | replaced |
| Billing header block | env `CLAUDE_CODE_ATTRIBUTION_HEADER=0` | stripped |
| Every CLAUDE.md | env `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` | stripped; `--keep-claude-md` keeps |
| Git status snapshot; commit and PR text in the Bash tool description | env `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1` and settings `includeGitInstructions: false` | stripped |
| Co-Authored-By trailer and PR footer | settings `attribution: {commit: "", pr: ""}` | stripped |
| Auto memory section | env `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and settings `autoMemoryEnabled: false` | stripped |
| Output style text | settings `outputStyle: "default"` | stripped |
| "The user hasn't heard from you in a while" note | env `CLAUDE_CODE_SILENT_TURN_REMINDER=0` (A2; fires only in interactive runs, so D3 verifies) | stripped |
| Task-list and TodoWrite nudges | env `CLAUDE_CODE_TODO_REMINDER_MODE=off` (X1 capture; undocumented, so a release may drop it) | stripped |
| Token-count line (`<total_tokens>`) | env `CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off` (X1 capture; undocumented, so a release may drop it) | stripped |
| WebSearch paragraph appended after the custom prompt | `--disallowedTools WebSearch` (B2: the only switch that removes it) | stripped with the tool; `--keep-web-search` keeps both |
| Hook output | hooks stay on (round 17); `--no-hooks` sets settings `disableAllHooks: true` | kept |
| Tool, skill, and agent lists; environment block (cwd, platform, date) | none; the brief keeps the lists, and the facts stay (solved 12) | kept |

Residue, text no switch removes without dropping what we keep (A1 docs silent; A2 binary; A3 captures), each named in the preamble and listed in the README with its capture:

- The identity line: interactive sessions get `You are Claude Code, Anthropic's official CLI for Claude.`; print mode gets `You are a Claude agent, built on Anthropic's Claude Agent SDK.`. The main loop always adds it; only internal side calls skip it. The owner's belief that a documented switch exists (round 5) is not supported: 55 docs pages are silent and the binary's chooser reads no such switch (solved 18).
- The context wrapper (`As you answer the user's questions, you can use the following context:` ... `Claude Code attached this context automatically`) around the email line, and the date line outside it (capture b2-full-haiku); the email line's only gate, `ANTHROPIC_UNIX_SOCKET`, changes the transport.
- File-changed notes: their only switch, `CLAUDE_CODE_DISABLE_ATTACHMENTS`, also drops the skill list. The task-list nudge has the narrower switch in the table above.
- The Agent tool description's worktree sentence and other tool descriptions.
- MCP server instructions, when MCP servers are configured.

## Manifesto plugin hooks under unharness (round 17, solved 16)

`launch` sets `UNHARNESS=1`. Every hook of the manifesto plugin, session-start, post-compact, subagent-start, and the per-prompt drift reminder, stands down when it is set, since the compiled prompt already carries the binding (changed in the 3.6.0 fix pass from queue 16, after the end-to-end capture showed the drift line in every request). Other plugins' hooks are untouched.

## Shipped preamble

`plugin/unharness/src/unharness/preamble.md`, at most 25 lines, plain, in the agent's voice, with no seams and no mention of unharness or compilation. It tells the model what each residue above is and how to weigh it: the identity line is the harness's fixed label and no instruction; a system reminder (text in `<system-reminder>` tags, or a system-role message inside the conversation) comes from the application, not from the user, and carries facts such as the email, the date, the working folder, file-change notes, and the skill and agent lists; hook output is text the owner's installed hooks add; a skill's text arrives in a user turn when the skill loads and is followed as the owner's standing instruction; a task-list nudge or a notice about the user not hearing from you is the harness's and not the user's word, and the constitution's own rules on speaking and silence, where it has them, govern over it. A fable agent writes it; it is reviewed against write-well and Raise the Bar.

## `/compile-commitments` (round 21)

Plugin skill `manifesto:compile-commitments` at `plugin/skills/compile-commitments/SKILL.md`, written to the memento:skill-creation rules by a fable agent. The session runs `unharness stack` into a file and reads it whole; reduces each element to its axioms; maps convergence and tension; resolves each tension with a rule; writes `.manifestos.interplay.md`, then `.manifestos.commitments.md` with the paired lines "I must ..., and I will ..." and "I must not ..., and I will not ...", each file opening with the `<stack>` block, all tagged as the session's own raw output; then runs `unharness prompt > /dev/null` to confirm the compile passes.

## Distribution (round 8) and release (round 9)

- Package `unharness` in `plugin/unharness/`: pyproject, src layout, tests, Python 3.11 or later, stdlib-only at runtime where possible.
- PyPI publish is the owner's step. Until then: `uvx --from "git+https://github.com/ryzhakar/llm-manifestos@v3.5.0#subdirectory=plugin/unharness" unharness`, or a shorter git form if RESEARCH A5 finds one.
- Inside sessions, `plugin/bin/unharness` runs the plugin's bundled copy, `${CLAUDE_PLUGIN_ROOT}/unharness`, through uvx; `UNHARNESS_FROM` (a path or a git URL) is the only way to run another source (triage decision a).
- Release: rebase on origin/main, fast-forward main, plugin 3.5.0 in `plugin/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, tag v3.5.0, push; the records keep the owner's publish commands.

## Acceptance

1. The pytest suite, the hook tests, `claude plugin validate` for the plugin and the marketplace, and `just readme` pass.
2. Captured request bodies (`OTEL_LOG_RAW_API_BODIES=file:<dir>`) of an unharnessed `-p` run and an interactive tmux run show the compiled prompt as the system prompt; no CLAUDE.md, git instructions, or attribution; the tool, skill, and agent registries present; and every residue listed in the README with its capture.
3. End to end in this repo: `/compile-commitments`, then `unharness prompt | unharness launch -- claude` in tmux; the session names the elements that govern it, and still does after `/compact`.
4. Code, prose, and spec-compliance reviews are triaged, and their accepted findings applied.

# 3.6.0: digests, minified session files, signatures, doctor

The owner's answers for this part are entries 27-41 of `queue-long-run.md`, cited below as queue N. Three flags trade full manifesto texts for shorter digests, a fourth picks condensed session files, and every compiled artifact loads only against the source hashes it was made for.

Terms used below:

- The plugin folder is `manifesto_dir` when the config sets it, else the manifesto plugin's highest cached version folder; it holds `manifestos/` and `digests/`.
- A manifesto element's slug is its registry stem: the reference of `source: manifesto <slug>`, else its `name`. Digests key by slug, never by element name.
- A source hash is the `sha256` that `resolve.py` computes for a `Document`: the hash of the body after frontmatter removal and stripping, before `${CLAUDE_PLUGIN_ROOT}` replacement.
- Words are whitespace-separated tokens; characters are Python string length.

## Digest sources and resolution (queue 32, 36-38)

A digest file's stem names its member set: the member slugs, sorted, distinct, and joined by `+`. A stem with one slug names a single digest; a stem with two or more names a stack digest.

| Kind | Local, beside the config | Plugin |
|---|---|---|
| Single | `.claude/digests/<slug>.md` | `<plugin folder>/digests/<slug>.md` |
| Stack | `.claude/digests/<a+b>.md` | `<plugin folder>/digests/stacks/<a+b>.md` |
| Index | `.claude/digests/index.json` | `<plugin folder>/digests/index.json` |

- Local wins: when both places hold a stem, unharness reads the local file against the local index alone, even when the local entry is stale.
- A digest is body-only markdown; its text enters the prompt stripped of surrounding whitespace and otherwise unchanged.
- Each index maps a stem to its members' source hashes, `{"<stem>": {"<slug>": "<sha256>", ...}, ...}`, and covers the digests of its own place; the plugin index covers `stacks/` too.
- A digest is usable when its index holds an entry for its stem, the entry's slugs equal the stem's slugs, and every hash equals that manifesto's current source hash. An entry whose slugs differ from the stem's counts as missing.
- A stack file whose stem is not sorted and distinct, and a stack digest placed in the plugin's `digests/` instead of `digests/stacks/`, are no candidates and raise nothing; decision 3 binds the files a mode considers.

`unharness stamp DIGEST [--config PATH]` (queue 37) reads DIGEST's stem and resolves each slug as a registry manifesto through `resolve_stack`, the one home for hashing. It writes the entry into the index of DIGEST's place: the `index.json` in DIGEST's folder, or in that folder's parent when the folder is `stacks`. It creates a missing index, replaces the stem's entry, keeps every other entry, writes `json.dumps(index, indent=2, sort_keys=True)` and a newline, and prints `stamped <stem> in <index path>`. It refuses, each after the `unharness: ` prefix, a missing DIGEST with `no digest at <path>`, a stem with unsorted, repeated, or empty slugs with `<file name> is not named by sorted, distinct slugs joined by +`, and a slug that does not resolve with the resolver's message.

A digest mode refuses with these messages, verbatim after the `unharness: ` prefix, each naming its fix:

    no digest for <slug>: tried <local path> and <plugin path>; run /compile-digest <slug>
    <digest path> has no entry in <index path>; run unharness stamp <digest path>
    <digest path> is stale (changed: <slug>, <slug>); run /compile-digest <every slug of the stem, space-separated>
    <index path> is not a JSON object of stems to slug hashes; fix or delete it, then run unharness stamp on each digest it covers

A stale digest names `/compile-digest` and not `unharness stamp`, because its manifesto changed under it and its text needs rewriting; `/compile-digest` stamps after it writes.

## Cover selection (queue 27, 28, 33, 35)

- No digest flag: every element enters in full, as in 3.5.0.
- `--digests`: every manifesto element enters as its single digest.
- `--stack-digests`, which implies `--digests`: the candidates add every stack digest whose slugs all belong to the stack's manifestos. Without `--overlap`, chosen stack digests share no slug; with it, they may. Single digests cover exactly the slugs that no chosen stack digest covers.
- `--overlap` without `--stack-digests` stops with `--overlap requires --stack-digests`.
- A manifesto counts as covered when a usable single digest or a usable candidate stack digest covers it (queue 28). A digest mode refuses only when some manifesto has neither, with the missing-digest message naming that slug. Under `--digests` alone only singles count, so each manifesto needs its single.
- Every digest file a mode considers, single or stack, must be usable; an unusable one stops the compile with its message.
- Without `--overlap`, a stack whose every manifesto is covered but which no disjoint choice covers stops with `no cover without overlap; add --overlap or run /compile-digest <slug> for each of: <slugs with no single digest, comma-separated>`.
- Every digest mode refuses a stack that names one slug twice: `manifesto <slug> appears twice in the stack; digest modes need each once`.
- The cover is the one with the fewest total characters across the chosen digest texts. A tie goes to fewer files, then to the lexicographically smaller sorted list of stems. unharness returns exactly this optimum; how it searches is its own, and a stack of twelve manifestos with a digest for every pair of them compiles in seconds.
- Skills and `file` elements enter in full in every mode (queue 28).

The constitution keeps one block per element, in config order, with two changes:

- A single digest renders in the shape of the full text: `<{name} governs="{purpose}">`, the digest text, `</{name}>`.
- A stack digest renders as one block at the position of its first member in config order; its other members render nothing at their own positions. Two stack blocks that fall at one position follow stem order.

      <{name1}+{name2} governs="{purpose1}; {purpose2}">
      {stack digest text}
      </{name1}+{name2}>

The tag joins the members' element names with `+` in config order. `governs` joins the purposes present, in the same order, with `; `; it is omitted when no member has a purpose, and a double quote in a purpose becomes a single quote. Under `--overlap`, a member that two chosen stack digests share appears in both tags. No tag or attribute names a digest, a stack, or a summary (round 1).

## Minified session files (queue 30, 40)

- `--minified` makes `prompt` read `.manifestos.interplay.min.md` and `.manifestos.commitments.min.md` in place of the full pair, and combines with every digest flag.
- Each min file opens with the same `<stack>` block as the full pair and goes stale by the same rule. A missing or stale min file stops `prompt` with the 3.5.0 message under the min file's name, naming `/compile-commitments`.
- `/compile-commitments` writes all four files in one run: the full pair unchanged, then the min pair condensed from it. Each min body, the text after the `<stack>` block, holds at most one third of the words of its full counterpart's body. One third scales with the stack, where a fixed 150 words would starve a stack of eleven elements.
- The min interplay keeps the rules that resolve tensions and the priority order, and drops the axioms, the convergences, and the quotations. The min commitments hold one `I must ..., and I will ...` line per element in stack order, with the prohibition folded in. Both keep the `<interplay>` and `<commitments>` tags and the session's first-person voice.
- The skill ends by running `unharness prompt > /dev/null` and `unharness prompt --minified > /dev/null`, and reports both exit codes.

## Signatures (queue 31, 32)

Every compiled artifact records the source hash of each source it was made for, and loads only when each recorded hash equals the current source hash. The session files, all four, record their sources in the `<stack>` block, one `name sha256 purpose` line per element in config order; a change to an element's text, its purpose, or the order makes them stale. A digest's index entry records one `slug: sha256` pair per member; only a change to a member manifesto's text makes it stale, since a digest carries no purpose. No mode changes a signature: `stack` prints one block in every mode, `prompt` checks the session files against that block in every mode, and no hash covers a digest's own text. Commitments compiled against the full stack therefore load under every digest flag.

## `unharness doctor` (queue 41)

`unharness doctor [--config PATH] [--digests] [--stack-digests] [--overlap] [--minified]` prints one line per check, `OK|WARN|FAIL <check>: <detail>`, in the order below. It exits 1 on any FAIL and 0 otherwise. It reads files and runs `claude --version`, and makes no network call. A finding about an artifact that `prompt` would load under the given flags is a FAIL; the same finding about an artifact `prompt` would not load is a WARN.

| Check | OK detail | Finding |
|---|---|---|
| `config` | the config path | FAIL with the load error; doctor then runs only `claude`, `uv`, and `manifesto plugin` |
| `element <name>` | the resolved path | FAIL with the resolver's message; the `digest`, `cover`, session-file, and `prompt size` checks, which need the whole stack, are left out while any element fails |
| `skill <plugin>:<skill>` | the resolved version | WARN when it differs from the version in `<login>/plugins/installed_plugins.json`, or no record exists |
| `digest <stem>` | `local` or `plugin`, current | the refusal message; one line per manifesto's single digest, then one per candidate stack digest |
| `cover` | stems in render order and their total words | the refusal message; the flags' digest mode, else `--stack-digests --overlap` |
| `.manifestos.interplay.md`, `.manifestos.commitments.md`, and the min pair | current | the missing or stale message, one line per file |
| `preamble` | `shipped` or `.manifestos.preamble.md` | none |
| `claude` | path and version | WARN when not on PATH, since a shell function can launch, when it prints no version, or when the version falls outside the tested range, 2.1.309–2.1.309 in 3.6.1 |
| `uv` | the paths of `uv` and `uvx` | FAIL when `uvx` is not on PATH |
| `manifesto plugin` | the installed version | FAIL when absent from `installed_plugins.json` or below 3.6.0, whose hooks do not all stand down |
| `prompt size` | `full <n> words; shortest <n> words` | WARN when the shortest mode cannot compile, with its message |

The `prompt size` check counts the preamble in its `<harness>` tags, the constitution, and whichever session files exist, ignoring staleness; full means no flag, and shortest means `--stack-digests --overlap --minified`. An excerpt of `unharness doctor --minified`:

    OK config: /work/proj/.manifestos.yaml
    OK element dry: /cache/llm-manifestos/manifesto/3.6.0/manifestos/dry.md
    WARN digest raise-the-bar: no digest for raise-the-bar: tried ...; run /compile-digest raise-the-bar
    FAIL .manifestos.commitments.min.md: .manifestos.commitments.min.md is missing; run /compile-commitments
    WARN claude: /usr/local/bin/claude 2.1.312, outside the tested range 2.1.309–2.1.309

## `/compile-digest` (queue 39)

Plugin skill `manifesto:compile-digest` at `plugin/skills/compile-digest/SKILL.md`, invoked as `/compile-digest <slug> [<slug>...]`, written to the memento:skill-creation rules by a fable agent, as `/compile-commitments` was.

1. Sort and dedupe the slugs; the stem joins them with `+`.
2. Run `${CLAUDE_PLUGIN_ROOT}/bin/unharness stack --config <path> <slugs>` into a temporary file and read it whole, never sending it into the conversation.
3. Bind to the manifestos in that file through `manifesto-oath`.
4. For one slug, write by the method the skill itself carries (3.6.1): each demand as one plain sentence, the manifesto's order kept, boundaries folded in, one standing line, Strunk applied, the draft checked against the source, under 350 words. For several, add the rules of write-stack-digest: converging demands merged, each tension replaced by its resolution, rules in priority order, each sentence scoped to its object, under 850 words. The skill carries these rules in its own text, since the repo's skills do not ship.
5. Write the body alone, with no header, frontmatter, or title, to `.claude/digests/<stem>.md` beside the config, creating the folder.
6. Run `${CLAUDE_PLUGIN_ROOT}/bin/unharness stamp .claude/digests/<stem>.md --config <path>` and report its exit code; on a failure, fix what the message names and run it again.

The skill composes a stack digest from the full manifestos, not from their single digests, because the signature hashes the manifestos. It writes no eval record and checks no gate, since the owner set digest quality aside (queue 29).

## CLI synopsis

The Verbs section above carries the 3.6.0 synopsis. `--stack-digests` implies `--digests`; `--overlap` requires `--stack-digests` (queue 35). `prompt` and `doctor` accept the four mode flags; `stack`, `stamp`, and `launch` accept none.

## Tests

Each test builds a plugin folder, a login, and a project under `tmp_path`; no test reads the real login.

- Flags: `--stack-digests` alone admits stack candidates; `--overlap` alone exits 1 with its message; `stack` and `stamp` reject mode flags.
- Resolution: a local stem wins over the plugin's; a stale local entry refuses even when the plugin copy is current; each of the four refusals prints its text verbatim; an entry with an extra slug counts as missing; a stack digest at `<plugin folder>/digests/<a+b>.md` is no candidate.
- Stamp: it creates an index; it replaces one entry and keeps the rest; it writes a plugin stack digest's entry in the parent of `stacks/`; it refuses unsorted and repeated stems and an unresolved slug; its hashes equal the `<stack>` block's for the same manifestos.
- Cover: `--digests` picks singles alone; a shorter stack digest beats its singles and a longer one loses; chosen stack digests stay disjoint without `--overlap` and share with it; ties go by file count, then by stem order; a stack digest with a slug outside the stack never enters; a stack digest alone covers a manifesto that has no single; a manifesto with neither refuses, naming its slug; under `--digests` a manifesto that only a stack digest covers refuses; coverage that only overlapping stack digests reach refuses without `--overlap` with the no-cover message; skills and files stay full; a repeated slug refuses.
- Rendering: a single digest block has the full block's shape; a stack block sits at its first member's position, with tag and `governs` joined in config order, `governs` omitted without purposes, and quotes replaced; two overlapping stack blocks both name the shared member.
- Minified: `--minified` reads the min pair; a missing and a stale min file each refuse, naming `/compile-commitments`; session files compiled against the full stack load under `--stack-digests --overlap --minified`.
- Stack slugs: `stack dry kiss` prints the block and constitution of those two manifestos alone, without purposes.
- Doctor: a fixture for each check yields its OK, WARN, and FAIL lines; one finding flips between FAIL and WARN with the flags; one FAIL exits 1 and WARNs alone exit 0; a config FAIL leaves only the three config-free checks; the suite stubs `claude --version` and runs doctor with sockets patched to raise.
- Skills: `claude plugin validate` passes with `compile-digest` and the four-file `compile-commitments`; end to end in this repo, `/compile-digest` writes and stamps a local digest, and `unharness prompt --stack-digests --overlap --minified` exits 0.

## Decisions made in the spec

1. The plugin folder holds both `manifestos/` and `digests/`, and digests key by registry slug, never by element name.
2. Without `--overlap`, a stack whose manifestos are each covered, but by no disjoint choice, stops with its own message, naming `--overlap` and the slugs that lack singles.
3. Every digest file a mode considers, single or stack, must be usable; an unusable one stops the compile instead of dropping out unseen.
4. Local wins per stem even when the local entry is stale.
5. A stale digest names `/compile-digest`; only a missing entry names `unharness stamp`.
6. A stack digest renders at its first member's position, its tag joining element names by `+` and its `governs` joining purposes by `; `, both in config order.
7. `unharness stack` takes slugs for `/compile-digest`, and takes no mode flag.
8. `/compile-digest` composes stack digests from full manifestos and writes no eval record.
9. A min body holds at most one third of its full body's words, and the min commitments hold one line per element.
10. Doctor FAILs on what the flags load and WARNs on the rest; a missing `claude` is a WARN; the `cover` line falls back to `--stack-digests --overlap`.
11. Stamp writes sorted, two-space-indented JSON and prints one line.

# 3.6.1: reminder switches, quiet pipes, one block type, doctor range, digest method

Source of the first item: `identity-line-findings.md`, "What unharness should change". The deferred items come from `reviews/digests-triage.md`: code N12 and the end-to-end `BrokenPipeError` line.

1. **Reminder switches.** `launch` adds `CLAUDE_CODE_TODO_REMINDER_MODE=off`, which removes the task-list and TodoWrite nudges and keeps the skill list, and `CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off`, which removes the token-count line. The printed command shows both. The docs name neither, so a release may drop them; the strip table, `plugin/README.md`, the unharness README, and `plugin/SCHEMA.md` say so. The preamble sentence on the task nudge stays, since the nudge may return.
2. **Quiet pipes.** Every verb, when its reader closes stdout early as in `unharness stack | head`, exits 0 with no traceback and no message.
3. **One block type.** `Block` and `Document` become one type when the merge changes no output: the constitution renders the same text for every mode.
4. **Doctor range.** One constant records the range of `claude` versions the package has been tested with; both ends read 2.1.309 today. `claude` WARNs with `claude: <path> <version>, outside the tested range <lo>–<hi>` when `claude --version` falls outside it; inside it the OK line is unchanged. This replaces the `claude` row's third WARN cause in the table above.
5. **`/compile-digest` method.** The plugin skill carries the digest method in its own voice: list every distinct demand, collapse restatements, write one plain complete sentence per demand, fold each boundary into the sentence it limits, keep the manifesto's own order, apply Strunk, check that every demand stands present or deliberately dropped, and name a drop in the stamp commit. It refers to no repo-local skill.
6. **Versions.** Package and plugin read 3.6.1. Doctor's floor for the manifesto plugin stays 3.6.0.

# 3.7.0: switch registry and discovery

The owner's order and the answers for this part are entries 51-54 of `queue-long-run.md`, cited below as queue N; entry 54 is the owner's ruling that the sweep skill stays in this repo. The capture form comes from `identity-line-findings.md`. One data file records every switch and the Claude Code versions at which a capture confirmed it, and launch, doctor, and the README's strip table all read that file.

## `switches.json` (queue 53)

The registry is `plugin/unharness/src/unharness/switches.json`, loaded through `importlib.resources` as `preamble.md` is. It is the one home of every switch: no switch name stays in a Python constant or in hand-written prose. Three items stay in `launch.py`: `--system-prompt-file`, whose value is the cached prompt; `--settings`, which carries the settings entries; and `UNHARNESS=1`, which addresses the manifesto plugin's hooks and not Claude Code.

The file holds one JSON array of entries in launch order. Each entry has exactly these keys:

| Key | Type | Meaning |
|---|---|---|
| `name` | string | the variable for `env`, the flag with its dashes for `flag`, the top-level key for `settings` |
| `kind` | `"env"`, `"flag"`, or `"settings"` | how launch passes the switch |
| `value` | a string for `env`; a string, or `null` for a bare flag, for `flag`; any JSON value for `settings` | what launch passes |
| `removes` | string | the injected text, as the strip table's first column names it |
| `documented` | boolean | a Claude Code docs page names the switch |
| `control` | boolean | a capture without the switch showed the text, so its removal was seen and not inferred |
| `verified` | a non-empty array of distinct `X.Y.Z` strings in ascending order | the versions at which a capture ran with the switch and its request bodies lacked the text |
| `default` | boolean | launch passes the switch when its option is absent |
| `option` | `null`, `"--keep-claude-md"`, `"--keep-web-search"`, or `"--no-hooks"` | the launch option that inverts `default` |

One entry of each kind:

    {"name": "CLAUDE_CODE_DISABLE_CLAUDE_MDS", "kind": "env", "value": "1", "removes": "Every CLAUDE.md", "documented": true, "control": true, "verified": ["2.1.309"], "default": true, "option": "--keep-claude-md"}
    {"name": "--disallowedTools", "kind": "flag", "value": "WebSearch", "removes": "WebSearch paragraph", "documented": true, "control": true, "verified": ["2.1.309"], "default": true, "option": "--keep-web-search"}
    {"name": "disableAllHooks", "kind": "settings", "value": true, "removes": "Hook output", "documented": true, "control": true, "verified": ["2.1.309"], "default": false, "option": "--no-hooks"}

The shipped file holds the thirteen switches 3.6.1 passes: the seven variables in 3.6.1's order, then `--disallowedTools`, then the five settings keys in 3.6.1's order. Each is verified at 2.1.309. `documented` is false for `CLAUDE_CODE_TODO_REMINDER_MODE` and `CLAUDE_CODE_TOTAL_TOKENS_REMINDER`. `control` is false for `attribution`, `outputStyle`, and both auto-memory switches, the rows the README marks "set"; X1 captured the silent-turn note with and without its switch, so that entry's `control` is true.

The loader refuses a file that breaks the table above with `switches.json entry <index>: <key> <problem>`. It also refuses two entries with one `kind` and `name`, and entries that share `removes` but differ in `default`, `option`, or `control`, since they form one table row.

## The strip table and `unharness switches`

`unharness switches` takes no argument and prints the strip table in markdown, with the header `| Injected text | Switch | Default |` and one row per distinct `removes`, in order of first appearance.

- The Switch cell joins the row's entries with `, `. An env entry renders as ``env `NAME=VALUE` ``, a flag as `` `NAME VALUE` `` or `` `NAME` ``, and a setting as ``setting `NAME: <json.dumps(VALUE)>` ``; an entry whose `documented` is false gains `, undocumented`.
- The Default cell reads `stripped` when `control` is true and `set` when it is false; it reads `kept` when `default` is false. An option appends ``; `<option>` keeps`` to `stripped` or `set`, and ``; `<option>` strips`` to `kept`.

In `plugin/README.md`, the table sits between the lines `<!-- switches -->` and `<!-- /switches -->`. A sentence above the markers names `--system-prompt-file`. The paragraph below them names no switch: it says what `stripped`, `set`, and `undocumented` mean, and that a release may drop an undocumented switch. The unharness README and `plugin/SCHEMA.md` replace their sentences naming the two undocumented variables with a pointer to the table. A test reads the lines between the markers and asserts that they equal the verb's output, so a changed registry fails the suite until the README carries the new table.

## Version and selection in `launch` (queue 53)

`unharness launch [--keep-claude-md] [--keep-web-search] [--no-hooks] [--claude-version X.Y.Z] [PROMPT] [-- LAUNCHER [ARGS...]]`

Detection. Without `--claude-version`, launch runs `LAUNCHER ARGS... --version` by the path it runs the launcher on: directly when LAUNCHER is on PATH, else through `$SHELL -ic`. With no launcher, it runs `claude --version` by the same rule, since the printed command names `claude`. It captures stdout under a 10-second timeout and takes the first line matching `^\d+\.\d+\.\d+`, because an interactive shell may print lines of its own first. A timeout, a launcher that fails to start, or output with no match makes launch use the registry's newest version, and it prints `unharness: <launcher> --version printed no version; using switches verified at <newest>` on stderr. `--claude-version` replaces the run; a value other than `X.Y.Z` stops launch with `--claude-version takes X.Y.Z, got <value>`.

Selection. The registry's versions are the union of every entry's `verified`. Launch chooses one version C for the detected version D:

1. When D is a registry version, C is D, and launch prints no note.
2. Otherwise C is the newest registry version below D, else the oldest registry version when D is older than all of them. Launch prints `unharness: claude <D> is not in the switch registry; using switches verified at <C>` on stderr.

Launch passes every entry verified at C whose `default`, inverted when its option is given, is true. An entry verified at an older version but not at C stays out, since the release may have dropped it.

Composition. Env entries become variables in registry order, followed by `UNHARNESS=1`. After `LAUNCHER ARGS...` come `--system-prompt-file <prompt file>`, each flag entry in registry order with its value as the next argument when the value is a string, and `--settings` with the settings entries in registry order as compact JSON. `--settings` is left out when no settings entry passes. At 2.1.309 with no option, the printed command equals the 3.6.1 command byte for byte, the last word naming the terminal device:

    env CLAUDE_CODE_ATTRIBUTION_HEADER=0 CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 CLAUDE_CODE_SILENT_TURN_REMINDER=0 CLAUDE_CODE_TODO_REMINDER_MODE=off CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off UNHARNESS=1 claude --system-prompt-file /home/u/.cache/unharness/<sha256>.md --disallowedTools WebSearch --settings '{"includeGitInstructions":false,"attribution":{"commit":"","pr":""},"autoMemoryEnabled":false,"outputStyle":"default"}' </dev/ttys003

## Doctor (queue 53)

The registry replaces 3.6.1's tested-range constant. `unharness doctor` gains `--claude-version X.Y.Z`, which replaces the detected version in the switch lines, for a launcher such as `claude@meta` that is no program on PATH. The new lines follow `claude` and precede `uv`. They need no config, so a config FAIL keeps them. Switch lines never FAIL, since launch still runs with the chosen set.

| Check | OK detail | WARN detail |
|---|---|---|
| `claude` | path and version, when the version is a registry version | not on PATH; printed no version; `<path> <D>, not in the switch registry; launch uses switches verified at <C>` |
| `switch registry` | `newest <version>; <m> switches` | none |
| `switch <kind> <name>`, one per entry in registry order | `verified at <C>`, when C equals D | `verified at <C>, not at <D>` when D differs; `verified at <C>, claude version unknown` when detection failed; `left out; last verified at <the entry's newest>` when the entry is not verified at C |

An excerpt, with claude 2.1.312 on PATH:

    WARN claude: /usr/local/bin/claude 2.1.312, not in the switch registry; launch uses switches verified at 2.1.309
    OK switch registry: newest 2.1.309; 13 switches
    WARN switch env CLAUDE_CODE_ATTRIBUTION_HEADER: verified at 2.1.309, not at 2.1.312

## Sweep skill (queue 51, 54)

`.claude/skills/sweep-switches/SKILL.md`, written to the memento:skill-creation rules, with `sweep.py` beside it, stdlib only and unshipped. The skill runs `python3 -I .claude/skills/sweep-switches/sweep.py <X.Y.Z> [--docs DIR] [--tarball PATH]` from the repo root, reads the report, and reads the extracted source around each candidate whose name suggests injected text. The script takes these steps:

1. It refuses a version that is not `X.Y.Z`.
2. In a new temporary folder, it runs `npm pack @anthropic-ai/claude-code@<v> --pack-destination <folder>`, or takes `--tarball`, and extracts the tarball with `tarfile`'s `data` filter.
3. It reads `package/cli.js`. When the tarball holds no `cli.js`, it reads every file over 1 MB under `package/` as bytes decoded as latin-1, the strings method A2 used on the native binary. The `source` field records which.
4. It extracts three sets. Env reads are the names in `process.env.NAME` and `process.env["NAME"]`. Env literals are every match of `\bCLAUDE_CODE_[A-Z0-9_]+\b`, which also catches reads through an alias such as A2's `i.CLAUDE_CODE_DISABLE_ATTACHMENTS`. Settings candidates are the keys of schema literals matching `[{,]([a-z][A-Za-z0-9]+):[\w$]{1,3}\.(boolean|string|number|enum|array|object|record|union|literal)\(`; this heuristic also catches tool-input keys, so the report calls them candidates.
5. It fetches `https://code.claude.com/docs/en/env-vars.md` and `https://code.claude.com/docs/en/settings-reference.md`, the two pages A1 found naming switches, or reads both files from `--docs DIR`. A name is documented when it appears in backticks on its page. A fetch failure stops the script, naming the URL and `--docs`.
6. It takes as the previous sweep the match of `orchestration_log/recon/*/switch-sweep-*.json` with the highest version below `<v>`, when one exists.
7. It writes `orchestration_log/recon/<date>/switch-sweep-<v>.json`, `<date>` being today's ISO date, with the keys `version`, `date`, `source`, `env_reads`, `env_literals`, `settings_candidates`, `documented_env`, and `documented_settings`, each set a sorted array.
8. It writes the report `switch-sweep-<v>.md` beside the JSON file and prints its path. The report holds five lists: env names in code and absent from the docs; settings candidates absent from the docs; names new since the previous sweep; names gone since it; and registry entries whose name the code no longer holds, read from `plugin/unharness/src/unharness/switches.json` under the repo root three folders above the script. An empty list prints `none`.

Both files land under `orchestration_log/recon/<date>/`, by the owner's correction to queue 54. Each sweep writes two files because the reader needs the markdown report, while the next sweep needs the sets as JSON data rather than parsed markdown. A version-keyed glob across the dated folders finds the previous sweep, and both files are committed.

Promotion is a human step, and a sweep never edits the registry. A switch enters `switches.json`, and a version enters an entry's `verified`, only after a capture in the X1 form: print mode under `env -i`, the unharness strip, `OTEL_LOG_RAW_API_BODIES=file:<dir>`, and one switch changed per capture from a base. `control` becomes true only when a capture without the switch shows the text. For a new Claude Code version, one run captures the full strip and checks each entry's text absent; the owner or a capture agent then adds the version to the `verified` of every entry the run confirms, in one commit. An entry that lacks a registry version therefore failed at that version and was never merely untested. The promoter then pastes the output of `unharness switches` between the README markers and runs the suite.

## Tests

- Registry: the shipped file loads; a missing key, an extra key, a bad kind, an unsorted, repeated, or empty `verified`, a repeated kind and name, and a row whose entries differ in `default`, `option`, or `control` each refuse with the entry's index.
- Table: `unharness switches` prints a fixture registry's table exactly, covering a bare flag, `undocumented`, `set`, `kept`, and both option forms; the README block between the markers equals the verb's output for the shipped file.
- Selection: an exact version, a version above the newest, one between two, and one below the oldest each choose the right C; an entry verified only at an older version stays out; each note prints verbatim.
- Detection: a launcher on PATH runs directly, and one off PATH runs through `$SHELL -ic`, both stubbed; a version on the second line of output parses; a timeout, an `OSError`, and output with no match each fall back to the newest with the note; `--claude-version` runs nothing; a malformed value refuses.
- Composition: the printed command at 2.1.309 with no option equals the line above; each option inverts its entry; a selection with no settings entry leaves `--settings` out; a fixture flag with a `null` value adds the bare flag.
- Doctor: each `claude` line; the `switch registry` line; the OK, differing, unknown, and left-out switch lines; `--claude-version` overrides detection; a config FAIL keeps the switch lines; no switch line FAILs.
- Sweep: `.claude/skills/sweep-switches/test_sweep.py`, run with `python3 -I`, builds a docs folder and a tarball holding a fixture `cli.js`, then runs the script with `--tarball` and `--docs`. It checks each extracted set, each report list, the previous-sweep diff, the native fallback, and each refusal. No test touches npm or the network.

## Decisions made in the spec

1. `--system-prompt-file`, `--settings`, and `UNHARNESS=1` stay in `launch.py`; every other switch lives in the registry alone.
2. `default` and `option` record the three launch options, so the registry carries opt-out and opt-in switches alike.
3. `control` keeps the README's line between `stripped` and `set`; the silent-turn row turns `stripped`, since X1 captured it both ways.
4. Launch chooses one registry version and passes only the entries verified at it, never an entry verified only earlier.
5. A version older than every registry version chooses the oldest, with the same note.
6. A version enters the registry only through a run of the full strip, so an entry's missing version means a failure, never a gap in testing.
7. With no launcher, launch detects through `claude`, the launcher it prints.
8. Doctor's `claude` line checks registry membership in place of the tested range; doctor gains `--claude-version`; switch lines never FAIL.
9. Doctor reads queue 53's "newest swept version" as the registry's newest verified version, since no sweep file ships with the package.
10. Each sweep writes `switch-sweep-<v>.json` for the next sweep and `switch-sweep-<v>.md` for the reader, both under `orchestration_log/recon/<date>/`.
11. A tarball without `cli.js` falls back to a byte scan; `--tarball` and `--docs` let the script run offline.
12. The README table is the one derived document; the unharness README and `SCHEMA.md` point to it and name no switch.
13. Entries that share `removes` form one row and share `default`, `option`, and `control`.

# 4.0.0: subagent prompts, one project folder, settings merge, stack diff

The owner's order and answers for this part are entries 48, 58-65, and 67 of `queue-long-run.md` and its "Round of 2026-10-26", cited below as queue N and the round. The round kept 58, 59, 61, and 62, took 60's alternative, and ships all four changes as one release, 4.0.0. Package and plugin read 4.0.0.

## Hook errors (queue 67)

When `config.py --json` exits 1, or a config, parse, or resolve error stops a hook otherwise, session-start, post-compact, and subagent-start each print the full message on stderr, then one line on stdout in the hook's own output form: plain for session-start, inside `hookSpecificOutput.additionalContext` for the other two. Each exits 0. The line enters the session's context:

    No manifesto bound: <the message's first line>; run unharness doctor for the fix.

A missing config, status 2, stays silent, and drift-reminder keeps stderr alone. This supersedes queue 22's silent stdout; SCHEMA.md's Errors paragraph and error table say so.

## The project folder (queue 58)

The project folder is the folder that holds `.manifestos/`; `.manifestos/` holds every project file of ours. `--config PATH` still names the config file, and now defaults to `.manifestos/config.yaml`; the project folder is the parent of the folder holding it.

| Path under the project folder | Writers | Readers |
|---|---|---|
| `.manifestos/config.yaml` | the owner | `config.py` (`load`, and `--json` for the hooks); `ensure-repo.sh`'s `detect_manifestos`, through which session-start, post-compact, subagent-start, and drift-reminder read it; `cli.py`'s `--config` default; doctor's `config`; the skills compile-commitments and compile-digest as `--config <path>`; `plugin/README.md`, `README.template.md`, and `plugin/SCHEMA.md` |
| `.manifestos/preamble.md` | the owner | `session.py`'s `load_preamble`; doctor's `preamble`; `plugin/README.md` |
| `.manifestos/interplay.md`, `commitments.md`, `interplay.min.md`, `commitments.min.md` | `/compile-commitments` | `compile.py` through `prompt`, `--minified` picking the min pair; `stack --diff`; doctor's session-file lines and `prompt size`; `plugin/README.md`; `SCHEMA.md`'s error table |
| `.manifestos/agents/<key>/` with the same four names | `/compile-commitments <key>` | `prompt --agent`; `stack --diff --agent`; doctor's `stack subagents.<key>` lines; `plugin/README.md` |
| `.manifestos/digests/<stem>.md` | `/compile-digest`; the repo-local skill write-stack-digest | `digests.py` (`locate_single`, `locate_stacks`); doctor's `digest` and `cover` lines; `plugin/README.md`; `README.template.md` |
| `.manifestos/digests/index.json` | `unharness stamp` | `digests.py`'s `read_index`; doctor's `digest` lines; `plugin/README.md` |

- `<key>` is a key under `subagents:` exactly as written, `other` included. Config load refuses a key that holds `/` or is `.` or `..`, with `subagents key '<key>' cannot name a folder`.
- No hook reads a compiled file; the hooks read `config.yaml` alone.
- A `file` source and `manifesto_dir` resolve against the project folder, as they resolved against the old config's folder. Moving the files therefore changes no element's text, no hash, and no `<stack>` line, and the moved session files load without a recompile.
- The `## Active Manifestos` section of `CLAUDE.md` in the project folder stays the fallback when `config.yaml` is absent.
- One home for the names: `config.py` holds the folder, file, and old-layout names and the cascade below, because the hooks import it by path and cannot import the package; `compile.py`, `session.py`, and `digests.py` import the names from it. The hooks call `python3 <config.py> --json --project <folder>`, so no shell script spells a path.

## Old layout (queue 59)

`config.py`'s `old_layout(project)` returns the commands that move each old path present in the project folder, run from that folder, in this order, a line appearing only when its old path exists:

    mkdir -p .manifestos
    mv .manifestos.yaml .manifestos/config.yaml
    mv .manifestos.interplay.md .manifestos/interplay.md
    mv .manifestos.commitments.md .manifestos/commitments.md
    mv .manifestos.interplay.min.md .manifestos/interplay.min.md
    mv .manifestos.commitments.min.md .manifestos/commitments.min.md
    mv .manifestos.preamble.md .manifestos/preamble.md
    mv .claude/digests .manifestos/digests

`mkdir` appears whenever any `mv` does. When the new path already exists, its line reads `# both <old> and <new> exist; keep one and delete the other` in place of the `mv`, since `mv` would overwrite a file or nest a folder.

- `load` calls `old_layout` before it reads anything, and stops when the list is not empty. The message is the one multi-line error: `old layout in <project folder>; run these there:` and then each command on its own line. No reader falls back to an old path.
- `unharness` prints it after `unharness: ` and exits 1. Each hook receives it from `config.py --json` with status 1 and reports it as every config error, by the next section. A project with an old config and no new one gets this message, never `no config`.
- Doctor prints it as lines, below.

## `unharness prompt --agent <type>` (queue 61, 62; the round on 60)

`prompt --agent TYPE` compiles the stack of the `subagents:` key that TYPE matches, in place of `you:`, with its session files from `.manifestos/agents/<key>/`. It takes every mode flag, and the preamble is the same.

`config.py`'s `subagent_key(agent_type, keys)` returns the first key that matches, in this cascade, or `None`:

1. a key equal to TYPE;
2. when TYPE holds `:`, a key equal to the part after its last `:`;
3. the first key in config order, `other` excepted, that TYPE ends with;
4. `other`, when the config has it.

An empty TYPE goes straight to step 4. The subagent-start hook replaces its inline `match_key` with an import of `subagent_key` from `config.py`, as `describe_elements.py` imports its constants, so the cascade has one home and the hook and the package cannot disagree.

- Landing on `other` by step 4 prints one line on stderr and goes on: `unharness: <type> matches no subagents key; using other:, the default stack`. A TYPE equal to `other` matches at step 1 and prints nothing.
- No match stops with exit 1: `unharness: <type> matches no subagents key and the config has no other:; keys: <key>, <key>`, the keys in config order, or `keys: none`.
- An empty matched list stops with `subagents.<key> is empty`.

## Per-agent session files

- `/compile-commitments <key>` runs the skill's steps against `unharness stack --agent <key> --config <path>` and writes the four files to `.manifestos/agents/<key>/`, creating the folder. `<key>` must be a key under `subagents:` as written; the skill refuses any other word, naming the keys, because the cascade could map a type to another key's folder. It confirms with `unharness prompt --agent <key>` and `unharness prompt --agent <key> --minified`, both to `/dev/null`, and reports both exit codes. Without an argument it writes the main four, as before.
- `unharness stack --agent TYPE` prints the matched stack's `<stack>` block, its fingerprint, and then its constitution, exactly as `stack` prints the main stack's, with the same warning and errors. `--agent` with slugs stops with `--agent takes no slugs`.
- `prompt --agent` checks each session file's `<stack>` block against the matched stack's, with the 3.5.0 messages. Every message names the file by its path under the project folder and the fix with the key: `.manifestos/agents/<key>/commitments.md is stale (changed: dry); run /compile-commitments <key>`. The main stack's messages read `.manifestos/commitments.md ...; run /compile-commitments`.

## `--settings` merge (queue 48)

Claude Code takes one `--settings`, and launch adds its own after `LAUNCHER ARGS...`, which today drops one the owner passes after `--`. Launch now merges the two.

- Launch finds `--settings VALUE` and `--settings=VALUE` among the ARGS after `--`. With none, nothing changes. With two or more, it stops with `pass --settings once after --`.
- VALUE is JSON text when its first non-space character is `{`, else a file path relative to the working folder, read as UTF-8 JSON, as Claude Code reads it. An unreadable file stops with `--settings file <path> cannot be read: <reason>`; text that is no JSON object stops with `--settings <VALUE> is not a JSON object`.
- Launch removes the owner's words from ARGS and passes one `--settings` in its own place. The merged object holds the owner's keys in their order, then each strip key the owner did not set, in registry order. The merge is shallow: a top-level key the owner sets replaces the strip's whole value, `attribution` included.
- The owner's value wins over the strip's, and launch prints `unharness: your --settings sets <key>; the strip's value is left out` on stderr for each such key.
- With no settings entry passing, the owner's object passes alone. With no launcher, launch prints the 3.7.1 command unchanged, since no ARGS exist. A launcher such as a shell function that adds `--settings` inside itself stays unseen.

## `unharness stack --diff` (queue 48)

`unharness stack --diff [--agent TYPE] [--config PATH]` shows why session files went stale. A session file records hashes, not texts, so the diff compares signatures and never element texts.

- For the main stack, or the matched agent's, it takes the four session files in the order full interplay, full commitments, min interplay, min commitments. A current file prints nothing. A missing file prints `<path>: missing`; a file without a block prints `<path>: no <stack> block`. A stale file prints `difflib.unified_diff(recorded_lines, current_lines, fromfile=<path>, tofile="current", lineterm="", n=0)`, line by line, so each changed hash, purpose, added element, removed element, or moved element shows as a `-` and `+` pair under its hunk header.
- It exits 0 when every file is current and 1 otherwise, as `diff` does, and prints no `unharness:` line for a difference. Resolution and config errors stop as in `stack`. `--diff` with slugs stops with `--diff takes no slugs`.

## Doctor

`unharness doctor` resolves every stack, `you:` and each `subagents:` key, one line per stack (queue 64), and gains `--agent TYPE`. The new lines keep the rule that a finding about what `prompt` would load under the given flags is a FAIL, and any other finding a WARN.

| Check | Place | OK detail | Finding |
|---|---|---|---|
| `layout` | first, before `config` | `<project folder>/.manifestos` | FAIL, one line per command of `old_layout`, as `FAIL layout: mv .manifestos.yaml .manifestos/config.yaml`; doctor then skips `config` and runs only the checks that need no config |
| `stack you` | after the `element` lines | `<n> elements resolved` | FAIL with the first resolver message, or with `the stack is empty` |
| `agent match` | after the main session-file lines, only with `--agent` | `<type> -> <key>` | WARN `<type> -> other, the default stack` on fall-through; FAIL with the no-match message |
| `stack subagents.<key>` | next, one per key in config order | `<n> elements resolved; session files current` | the first problem among the key's element resolutions, its empty list, and its four files, in that order; FAIL for the matched key when the problem lies in its elements or the pair the flags load, WARN otherwise |
| `manifesto plugin` | unchanged | the installed version | FAIL below 4.0.0, whose hooks read the old layout |

## Block scalars (queue 65)

`config.py`'s YAML reader refuses a value that is a block scalar indicator, `>` or `|` with an optional `-` or `+` and an optional digit, whether a mapping value or a list item, before it reads the indented lines below. The message names the key, or the list item's line, then the cause and the fix: `key '<key>' holds a block scalar; block scalars are not supported; write the value on one line`, or `the line '<line>' holds a block scalar; ...` with the same tail. The reader still reads frontmatter, so a manifesto whose frontmatter folds a value gets the same message through `parse_taglines.py`. SCHEMA.md's YAML subset section and its error table name the message.

## Docs

`plugin/README.md`, `README.template.md` (then `just readme`), the unharness README, and `plugin/SCHEMA.md` name the new paths; SCHEMA.md's title becomes `.manifestos/config.yaml Schema Reference`, its SubagentStart section points to `subagent_key` and calls `other:` the default stack, and its error table gains every message above. The skills compile-commitments, compile-digest, and manifesto-oath name `.manifestos/config.yaml` and `.manifestos/digests/`; the repo-local write-stack-digest skill saves to `.manifestos/digests/`. This repo moves its own files with the printed commands in the release commit.

## Tests

- Layout: each old path alone yields `mkdir` and its own line; all paths yield the order above; an existing new path yields the `# both` line; `load` stops with the multi-line message, exit 1, before a missing-config check; each hook prints it on stderr and exits 0; a `file` source resolves against the project folder; moved session files load without a recompile; a key with `/`, `.`, or `..` refuses.
- Hook errors: for an old layout, a parse error, and an unresolvable source, each binding hook exits 0, prints the full message on stderr, and prints the `No manifesto bound` line verbatim in its output form, session-start as plain text and the other two inside valid `hookSpecificOutput` JSON; a missing config leaves stdout and stderr empty.
- Cascade: one table of types and keys drives both `subagent_key` and the subagent-start hook, covering exact, the part after the last `:`, a suffix, the config-order tie between two suffix keys, an exact `other`, an empty type, the fall-through, and no match; the hook's named elements equal the package's choice for every row.
- `--agent`: the fall-through warning prints once and verbatim; no match exits 1 with the keys, and with `keys: none`; an empty list refuses; each mode flag combines; agent messages name the key's path and `/compile-commitments <key>`; `stack --agent` prints the matched block; `--agent` and `--diff` each refuse slugs.
- Settings: none, the spaced form, the `=` form, JSON text, a file path, two flags, an unreadable file, and a non-object each behave as above; owner keys come first; a shared key keeps the owner's value and prints its note; a nested object replaces whole; the printed command at 2.1.309 stays byte for byte.
- Diff: all current prints nothing and exits 0; a changed hash, a changed purpose, an added element, and a reorder each print their hunk; missing and blockless files print their lines; exit 1 on any difference.
- Block scalars: `>`, `|`, `>-`, `|+`, and `|2` each refuse with the message, as a mapping value and as a list item; a value that merely starts with `>` text, such as `> 3`, still reads as a string.
- Doctor: the `layout` OK and FAIL lines and the skipped `config`; one `stack` line for `you:` and one for each key, in config order, with and without `--agent`; an unresolvable element under a key that `--agent` does not name WARNs; `agent match` OK, WARN, and FAIL; a `stack subagents.<key>` problem FAILs for the matched key under its flags and WARNs otherwise; the 4.0.0 floor.
- Skills: `claude plugin validate` passes; end to end in this repo, `/compile-commitments implementer` writes its four files, and `unharness prompt --agent dev-cycle:implementer` and `unharness stack --diff --agent implementer` exit 0.

## Decisions made in the spec

1. `--config` still names the file; the project folder is its folder's parent, and `file` sources and `manifesto_dir` resolve against it, so the move needs no recompile.
2. `.manifestos.preamble.md` moves to `.manifestos/preamble.md`, since queue 58 puts every project file of ours in the folder.
3. The `CLAUDE.md` fallback stays, read from the project folder.
4. `config.py` holds every layout name, `old_layout`, and `subagent_key`; the hooks import it, so the cascade has one home and no shell script spells a path.
5. The old-layout message is the one multi-line error, so its commands paste as they print; a pair whose new path exists prints a `# both` line instead of a destructive `mv`.
6. A subagents key that holds `/` or is `.` or `..` refuses, since it names a folder.
7. `prompt --agent` keeps the shipped or project preamble and every mode flag.
8. `/compile-commitments <key>` takes a config key exactly, never a type.
9. In the `--settings` merge, the owner's value wins per top-level key, with one stderr note per key; the merge is shallow, and two owner `--settings` refuse.
10. `stack --diff` diffs the recorded and current `<stack>` lines as a zero-context unified diff, never element texts, and exits 1 on a difference, as `diff` does.
11. Doctor's stack lines are named `stack you` and `stack subagents.<key>`; the `element` lines for `you:` stay, and a key's line also carries its session files. Doctor gains `--agent`; a layout FAIL acts as a config FAIL; the manifesto plugin floor rises to 4.0.0.
12. A block scalar refuses by its indicator alone, `>` or `|` with an optional chomping sign and digit, so a one-line value that starts with `>` and goes on still reads as text.
13. The `No manifesto bound` line carries only the message's first line and points to `unharness doctor`, so the multi-line old-layout message stays on stderr and in doctor.
