# Truth-AI

Truth-AI is a deterministic truth kernel and continuity ledger for LLM agents.

This repository contains the deterministic Python kernel plus a static frontend
preview under `frontend/`.

## Setup

```bash
uv sync
```

## Gate

```bash
make gate
```

On Windows machines without `make`, run the equivalent commands directly:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src/
uv run pytest -q
uv run python tools/schema_freeze_check.py
```

The replay target is intentionally stubbed until M2, as defined in
`CODEX_HARNESS.md`.

## Frontend Preview

The copied UI is a static DreamCanvas export. Serve it over HTTP so component
imports work:

```bash
make frontend
```

Then open:

```text
http://127.0.0.1:4173/Truth-AI.dc.html
```

On Windows without `make`:

```powershell
uv run python -m http.server 4173 --directory frontend
```

## Supabase

The Supabase project is recorded under `supabase/`.

Local secrets belong in `.env`, using `.env.example` as the template. Do not
commit Supabase keys.
