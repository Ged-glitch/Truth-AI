# Truth-AI

Truth-AI is a deterministic truth kernel and continuity ledger for LLM agents.

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
```

## CLI Quickstart

Verify the canonical minimal pack against the strict rule pack and write
accepted facts to an explicit ledger path:

```bash
uv run truth verify fixtures/golden/m1/minimal-supported.pack.json rulepacks/strict-default/rulepack.json .truth-ledger
```

Inspect the resulting ledger:

```bash
uv run truth ledger facts .truth-ledger
uv run truth ledger show .truth-ledger --json
uv run truth ledger snapshot .truth-ledger --json
```

Replay committed fixtures:

```bash
uv run truth replay fixtures/golden --runs 30 --byte-equal
```

Author a deterministic fixture bundle:

```bash
uv run truth fixtures make fixtures/golden/m1/minimal-supported.pack.json rulepacks/strict-default/rulepack.json ./tmp/minimal.bundle.json
```

Run the HTTP sidecar:

```bash
uv run truth serve http .truth-ledger rulepacks/strict-default/rulepack.json --host 127.0.0.1 --port 8000
```

Run the line-delimited MCP session server:

```bash
uv run truth serve mcp .truth-ledger rulepacks/strict-default/rulepack.json
```

Advisory adapter contracts live under `src/adapters/`, with committed frozen
artefacts stored under `adapters/`.

Run the integration demos:

```bash
uv run truth demo openclaw --json
uv run truth demo hermes --json
uv run truth demo dcir --json
```

Generate the M10 evaluation report:

```bash
uv run truth report --output-dir reports/m10 --json
```

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
