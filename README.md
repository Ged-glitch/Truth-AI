# Truth-AI

Truth-AI is a deterministic truth kernel and continuity ledger for LLM agents.

This repository is currently at **M0 scaffold**. Application logic starts in later
milestones after the project contract, gate, and CI surface are in place.

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
