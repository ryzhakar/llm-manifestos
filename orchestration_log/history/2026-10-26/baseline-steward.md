# Baseline: steward, at closure 2026-10-26

Replaces the "After span 3" baseline in history/2026-10-23/baseline-long-run.md.

- origin/main and session/long-run at 643eaec plus this records commit; tags v4.0.0 and pypi-4.0.0 on 643eaec; PyPI serves unharness 4.0.0.
- plugin.json, marketplace.json, pyproject.toml read 4.0.0; `uv run --project plugin/unharness pytest -q plugin/unharness` passes 406; `python3 -m unittest discover -s plugin/tests` passes 30.
- This repo's project files live in `.manifestos/` (config.yaml, the four session files, agents/implementer/); no root `.manifestos.*` files remain.
- One worktree (the main checkout); no feature branches; no wake; no agents running. Local branch main is stale (behind origin/main).
