# unharness

Compile a project's manifesto stack into a Claude Code session's system prompt, and launch the session with the harness's own instructions switched off.

```
/compile-commitments
uvx unharness prompt | uvx unharness launch -- claude
```

To run the source at the v4.0.1 tag instead, use `uvx --from "git+https://github.com/ryzhakar/llm-manifestos@v4.0.1#subdirectory=plugin/unharness" unharness` in place of `uvx unharness`. The launcher's input is reopened on the terminal.

The strip table in the Unharness section of [`plugin/README.md`](https://github.com/ryzhakar/llm-manifestos/blob/v4.0.1/plugin/README.md) lists every switch launch passes, and `unharness switches` prints it.

A `pypi-<version>` tag on a commit whose `pyproject.toml` carries that version publishes it to PyPI; `v<version>` tags release the plugin and do not publish.

- `unharness prompt [--config PATH] [--agent TYPE] [--digests] [--stack-digests] [--overlap] [--minified]` prints the compiled prompt. `--config` defaults to `.manifestos/config.yaml`, the folder `.manifestos/` holding every project file. `--agent TYPE` compiles the stack of the `subagents:` key that TYPE matches, from the session files in `.manifestos/agents/<key>/`. `--digests` and `--stack-digests` swap manifesto texts for digests, `--overlap` lets stack digests share a manifesto, and `--minified` loads the min pair, the two `.min.md` session files; the Unharness section of [`plugin/README.md`](https://github.com/ryzhakar/llm-manifestos/blob/v4.0.1/plugin/README.md) states the cover rule.
- `unharness stack [--config PATH] [--agent TYPE] [--diff] [SLUG ...]` prints the `<stack>` block and the constitution; given slugs, it prints those manifestos alone. `--agent TYPE` prints the matched key's stack. `--diff` prints how each stale session file's recorded `<stack>` lines differ from the current ones, and exits 1 on any difference.
- `unharness stamp DIGEST [--config PATH]` writes the digest's entry into its `index.json`, as in `unharness stamp .manifestos/digests/dry.md`.
- `unharness doctor [--config PATH] [--agent TYPE] [--digests] [--stack-digests] [--overlap] [--minified] [--claude-version X.Y.Z]` prints one `OK`, `WARN`, or `FAIL` line per check and exits 1 on any FAIL; `--claude-version` replaces the detected claude version in its switch lines. The `layout` line comes first and fails with one line per command of the old-layout move, after which only the checks that need no config run. A `stack you` line and one `stack subagents.<key>` line per key report each stack's elements and, for a key, its session files under `.manifestos/agents/<key>/`. `--agent TYPE` adds an `agent match` line and makes the matched key's problems FAIL where the other keys' only WARN. The `manifesto plugin` line fails below 4.0.1, the first version whose subagent hook binds under unharness.
- `unharness switches` prints the strip table from the switch registry.
- `unharness launch [--keep-claude-md] [--keep-web-search] [--no-hooks] [--claude-version X.Y.Z] [PROMPT] [-- LAUNCHER [ARGS...]]` caches the prompt and runs the launcher, or prints the command when none follows `--`. Under unharness the manifesto plugin's subagent hook still binds subagents; `--no-hooks` silences it.

`launch` runs `LAUNCHER ARGS... --version`, directly for a program on PATH and through `$SHELL -ic` otherwise, and `claude --version` when no launcher follows `--`. It passes the switches verified at the detected version when the registry holds it, else at the nearest registry version below it, else at the oldest registry version, and writes `unharness: claude <D> is not in the switch registry; using switches verified at <C>` on stderr. A launcher that times out, fails to start, or prints no version gets the newest registry version and `unharness: <launcher> --version printed no version; using switches verified at <newest>` on stderr. `--claude-version X.Y.Z` states the version and runs nothing.

If ARGS hold one `--settings VALUE` or `--settings=VALUE`, `launch` merges it with its own: VALUE is JSON text when its first non-space character is `{`, else a file path relative to the working folder. The result passes as the one `--settings`, the owner's keys first in their order, then each strip key the owner did not set. The merge is shallow, so a key the owner sets replaces the strip's whole value, and `unharness: your --settings sets <key>; the strip's value is left out` goes on stderr for each. Two `--settings` stop with `pass --settings once after --`. A launcher that adds `--settings` inside itself stays unseen.

The config schema is in [`plugin/SCHEMA.md`](https://github.com/ryzhakar/llm-manifestos/blob/v4.0.1/plugin/SCHEMA.md). The strip table and the text that stays are in the Unharness section of [`plugin/README.md`](https://github.com/ryzhakar/llm-manifestos/blob/v4.0.1/plugin/README.md).

Test with `uv run --project plugin/unharness pytest -q` from the repository root.
