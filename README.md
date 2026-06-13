# Truth-AI

Truth-AI is a deterministic truth kernel and continuity ledger for LLM agents.

This repository is at **M2 graph/replay**: validated packs can be turned into
deterministic typed graph dumps, and committed graph fixtures replay byte-equal.

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
uv run truth replay fixtures/golden --runs 30 --byte-equal
uv run python tools/schema_freeze_check.py
```

Replay runs committed golden graph fixtures 30 times and byte-compares their
canonical hashes, as required from M2 onward.
