# Truth-AI

Truth-AI is an open-source deterministic truth kernel and continuity ledger for
LLM agents. It verifies model-emitted claims against evidence, standards and an
append-only ledger, then emits replayable decisions and repair contracts.

- Live demo: https://www.truthai.tech
- Licence: MIT, see `LICENSE`
- Runtime rule: model calls and network access stay outside `src/truthkernel/`
- Determinism rule: identical committed inputs must replay byte-for-byte

## Quickstart

Install the project:

```bash
uv sync
```

Run the full local gate:

```bash
make gate
```

On Windows without `make`, run the equivalent commands:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src/
uv run pytest -q
uv run truth replay fixtures/golden --runs 30 --byte-equal
uv run python tools/schema_freeze_check.py
```

Verify a sample pack:

```bash
uv run truth verify fixtures/golden/m1/minimal-supported.pack.json rulepacks/strict-default/rulepack.json .truth-ledger
```

Inspect the ledger:

```bash
uv run truth ledger facts .truth-ledger
uv run truth ledger show .truth-ledger --json
uv run truth ledger snapshot .truth-ledger --json
```

Replay committed fixtures:

```bash
uv run truth replay fixtures/golden --runs 30 --byte-equal
```

## Local App Preview

The browser UI is a static DreamCanvas export served through route pages. Serve
the repo root so `/app/*` and `/api/*` routes resolve:

```bash
uv run python -m http.server 4174
```

Then open:

```text
http://127.0.0.1:4174/
http://127.0.0.1:4174/app/overview/
http://127.0.0.1:4174/app/truth-output/
http://127.0.0.1:4174/app/rulepacks/
```

## Verified Chat Adapter

Run the adapter service used by the console input/output pages:

```bash
uv run truth-verified-chat --store-root adapters/verified-chat --rulepack rulepacks/strict-default/rulepack.json --host 127.0.0.1 --port 8010
```

Or with `make`:

```bash
make adapter
```

The browser always calls `/api/verified-chat/*`. In local development that route
falls back to `http://127.0.0.1:8010`; in Vercel production it proxies to the
deployed backend when `VERIFIED_CHAT_BACKEND_URL` is configured.

For the live site, set `VERIFIED_CHAT_BACKEND_URL` in Vercel to:

```text
https://www.truthai.tech/api/verified-chat-backend
```

The adapter keeps live model calls outside `src/truthkernel/`, writes frozen
request, response, extraction and run artefacts under the store root, and only
passes canonical artefacts into the deterministic kernel.

## Supabase Auth And Persistence

Sign-in lives at `/app/sign-in` and reads public Supabase config from
`/api/public-config`.

Required Vercel environment variables:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
PUBLIC_SITE_ORIGIN=https://www.truthai.tech
VERIFIED_CHAT_BACKEND_URL=https://www.truthai.tech/api/verified-chat-backend
```

Optional server-only variable:

```text
SUPABASE_SERVICE_ROLE_KEY
```

Keep `SUPABASE_SERVICE_ROLE_KEY` server-side only. The frontend never needs it.
Do not commit real API keys, provider keys or service-role credentials.

When `SUPABASE_URL` and `SUPABASE_ANON_KEY` are configured, the verified-chat
backend mirrors each frozen run into `public.verified_chat_runs` using the
signed-in user's bearer token. Apply this migration in Supabase:

```text
supabase/migrations/20260621_verified_chat_runs.sql
```

Local secrets belong in `.env.local` or another ignored `.env.*` file. Use
`.env.example` only as a template.

## Standards And Evaluators

Sample standards sources live in:

```text
standards/library/sample-standard-library.json
```

The Rule Packs page loads this catalogue and lets users register official
standards links, including paid sources such as BSI, ISO and IEC. Paid or
institutional standards must be linked or uploaded under an existing licence,
not scraped.

Advisory evaluator sources live in:

```text
standards/evaluators/sample-evaluator-library.json
```

DeepEval, Ragas and Open RAG Eval style checks are advisory. Their scores can be
frozen as artefacts, but the deterministic Truth Kernel still makes the
replayable decision.

## Development Rules

Read these before changing kernel behaviour:

- `AGENTS.md`
- `TRUTH-AI_SPEC.md`
- `CODEX_HARNESS.md`

Core constraints:

- no LLM calls, network calls or hidden filesystem state in `src/truthkernel/`
- no clock, randomness, UUIDs or environment reads in hashed-output paths
- content hashes are the only identifiers for hashed artefacts
- canonical JSON is required for every hashed payload
- schemas and golden fixtures are evidence, not scratch files
- run `make gate` before proposing a release or merge

## Contributing

See `CONTRIBUTING.md` for local setup, issue workflow and pull request rules.
See `SECURITY.md` for vulnerability reporting and key-handling policy.

## Roadmap

See `ROADMAP.md` for the short public roadmap.
