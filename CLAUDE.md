# CLAUDE.md

Scientific modelling project (data science / energy / finance / economic).
Algorithm docs: `docs/algorithm-overview.md`, `docs/joint-equilibrium.md`. User
guide: `docs/joint-model-guide.md`. Module map: `MODULES.md`. Manual: `MANUAL.md`.

## Commands

```bash
uv sync --all-extras           # install
uv run pytest                  # tests
uv run pytest --cov=src        # tests + coverage
uv run ruff check . --fix      # lint + autofix
uv run ruff format .           # format
uv run mypy src/               # type-check
```

If `uv` is not yet adopted, fall back to `pip install -e ".[dev]"` and `pytest` / `ruff` / `mypy` directly. Don't introduce `setup.py`, `requirements.txt`, `flake8`, or `black` configs — `pyproject.toml` is the single source of truth.

## Conventions

- **Python 3.11+**, type hints mandatory on public functions, Google-style docstrings.
- **Math docstrings**: include an `Algorithm:` section with LaTeX (`$$...$$`) primary and an ASCII fallback line. Define every symbol with units.
- **Variable names**: descriptive in general (`temperature_kelvin`), but **single letters are OK** when they mirror equations (`T`, `x`, `ε`, `dt`, `i`, `j`). Don't fight the math.
- **No hardcoded values**: load via `src/<pkg>/config.py` from `.env`. Mirror every var into `.env.example`.
- **Reproducibility**: pin random seeds (`numpy.random.default_rng(seed)` over the legacy global API). Commit `uv.lock`. Pin upstream versions.
- **Units**: use `pint` for any quantity with physical units (energy, power, currency rates, time-of-day). Don't pass bare floats across module boundaries when units matter.
- **Numerical correctness**: when changing math, add a test against an analytical solution OR a captured baseline (`np.testing.assert_allclose` with explicit `rtol`/`atol`).

## Logging

Use `src/<pkg>/logger.py`. Log shape and dtype, never full arrays. Never log secrets, PII, or raw data rows.

| level | use for |
|-------|---------|
| DEBUG | branch decisions, scalar values, shapes |
| INFO  | milestones (data loaded, fit complete) |
| WARNING | recoverable degradation |
| ERROR | failure that returns or skips |
| CRITICAL | abort |

## Tests

Pytest. New features need tests. Aim for **meaningful** coverage of math correctness, not a line-coverage %. For numerical code, regression tests against analytical solutions beat 100% line coverage every time.

## Git workflow

- Feature branch → PR → CI green → merge to main → delete branch.
- **Conventional commits**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.
- **Self-review before merge**: re-read the diff. For math changes, paste before/after equations into the PR description. CI passing ≠ math correct.
- Never `--force` push to main. Use `git revert` to undo merged commits.

## Project layout

```
core/backend/     the `pe` package — kernel (core/), engine/ (dispatch, scc, joint),
                  config_io/, blocks/ (composer graph), web/, mcp/, registry/, analysis/
core/frontend/    Vite/React composer + pe-shell (dist/ is built and served in prod)
modules/<name>/   one feature each, fully isolated: backend/ (-> pe.features.<name>),
                  frontend/, doc/  (banking, price_controls, market_links, ccr, oba,
                  sectors, transmission, elastic_baseline, endogenous_investment, ...)
compat/ets/       ets->pe deprecation shims (backward-compat import mirror)
api/              Vercel serverless entry (serves core/frontend/dist)
examples/         scenario configs (the joint-equilibrium model is the centrepiece)
tests/            mirrors the source tree; golden baselines in tests/baselines/
docs/             algorithm-overview.md, joint-equilibrium.md (math),
                  joint-model-guide.md (user guide), platform/plan specs
.env, .env.example
pyproject.toml    single source of truth (package-dir remaps the split package)
```

See `MODULES.md` for the module map and `MANUAL.md` for the operator manual. The
conventions above are the source of truth — there is no separate handbook file.
