# Contributing to Truth-AI

Truth-AI is open source, but the kernel is intentionally strict. Changes that
make replay output non-deterministic cannot be accepted.

## Local Setup

```bash
uv sync
make gate
```

On Windows without `make`:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src/
uv run pytest -q
uv run truth replay fixtures/golden --runs 30 --byte-equal
uv run python tools/schema_freeze_check.py
```

## Before Opening A Pull Request

1. Read `AGENTS.md`, `TRUTH-AI_SPEC.md` and `CODEX_HARNESS.md`.
2. Keep the change scoped to one milestone or one clear bug.
3. Add or update tests with the behaviour change.
4. Run the full gate locally.
5. Do not commit `.env`, provider keys, Supabase service-role keys, local ledger
   state, generated caches or private standards content.

## Kernel Rules

- No network calls, LLM calls or subprocess-to-network inside `src/truthkernel/`.
- No `datetime.now()`, randomness, UUIDs, locale reads or environment reads in
  any code path that contributes to hashed output.
- IDs are SHA-256 content hashes.
- Iterate sorted; do not rely on dict or set ordering.
- Canonical JSON is required for every hashed payload.
- Schema and golden fixture changes must be dedicated changes with a migration
  note and regenerated evidence.

## Good First Contributions

- Improve documentation clarity without changing semantics.
- Add focused tests for existing behaviour.
- Add standards catalogue metadata that links to official public sources.
- Improve static UI accessibility without weakening the deterministic backend.

## Pull Request Checklist

- [ ] The change is scoped and explained.
- [ ] Tests were added or updated where needed.
- [ ] `make gate` passed locally, or equivalent Windows commands passed.
- [ ] No secrets or private data are committed.
- [ ] Public behaviour is documented in `README.md` when relevant.
