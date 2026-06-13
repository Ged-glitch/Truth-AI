# Truth-AI Build Plan

## Current State

- Local workspace: `C:\Users\gedho\OneDrive\Documents\Truth Agent`
- Git state: `master` is populated and pushed to `origin`.
- GitHub target: `Ged-glitch/Truth-AI`.
- Latest frontend implementation head before this plan update: `d968951 Add verified chat and truth output screens`.
- Production site: `https://www.truthai.tech`, deployed through Vercel from the GitHub `master` branch.
- Authoritative local inputs:
  - `TRUTH-AI_SPEC.md` in the repo root, generated from `C:\Users\gedho\projects\Truth-AI\Codex\files\final_truth_ai_spec.md` with implementation-critical material merged from the older v0.1.3 draft.
  - `C:\Users\gedho\projects\Truth-AI\Codex\files\CODEX_HARNESS.md`
  - `C:\Users\gedho\projects\Truth-AI\Codex\files\AGENTS.md`

`TRUTH-AI_SPEC.md` is treated as the semantic source of truth. Its current SHA-256 pre-registration anchor is `95E23A474F349D6A58EADDE40A6687E591AAC6A2219A27CAB557031E5138395E`. `CODEX_HARNESS.md` is treated as the build discipline and milestone harness. `AGENTS.md` is treated as the standing rulebook for coding-agent sessions.

## Implementation State - 2026-06-13

### Pushed To GitHub

- `f2ad2ad` - initial Truth-AI scaffold with M1 schema contracts and canonical hashing.
- `091ad3a` - static frontend export committed under `frontend/`.
- `06442c1` - root Vercel entry point added so the site works when Vercel deploys from the repository root.
- `af8ee82` - console screens split into routed pages.
- `8cc22f2` - physical static app route pages added for Vercel.
- `111f90a` - mobile console layout improved.
- `14c9603` - landing-page content split into separate static pages.
- `d968951` - verified chat and clean truth-output screens added.

### Local Uncommitted Work

The workspace also contains local, uncommitted backend milestone work. Do not overwrite or discard it without explicit instruction.

- M2 graph/replay files and fixtures.
- M3 comparator and predicate files.
- Supabase notes and `.env.example`.
- README and Makefile updates related to local frontend preview and replay.

### Live Static Frontend

The current public UI is a static DreamCanvas export wrapped in route-loader pages. It is not yet wired to live model calls, Supabase persistence, or the deterministic kernel runtime.

Live marketing pages:

- `/` - home hero
- `/problem`
- `/workflow`
- `/features`
- `/integrity`
- `/use-cases`
- `/waitlist`

Live console pages:

- `/app/overview`
- `/app/chat`
- `/app/truth-output`
- `/app/assistant`
- `/app/claims`
- `/app/evidence`
- `/app/verifications`
- `/app/rulepacks`
- `/app/ledger`
- `/app/reports`
- `/app/connections`
- `/app/settings`

The verified chat screen is currently a product mock:

- default model selector shows Gemini Flash
- user can choose own provider key or local model in the UI
- prompt/spec input is represented
- model output is represented as passing through the truth kernel
- `/app/truth-output` shows a cleaned truthful version with kernel-change notes and a decision-bundle summary

The next major product task is to replace this mock with an adapter-backed flow that keeps stochastic model calls outside `src/truthkernel/` and passes committed/canonical artefacts into the kernel.

## Planning Notes

- The spec names the taxonomy `TC-01` through `TC-08`.
- The harness later uses `GC-00` through `GC-08` terminology.
- Before implementing predicates, we should reconcile this naming in documentation and code. The safest default is to preserve the spec-facing `TC-*` names and document any harness `GC-*` usage as legacy or implementation aliases.
- The project should be built as a deterministic Python 3.12+ package managed by `uv`.
- Kernel code must remain pure and replayable: no network, LLM calls, current clock reads, randomness, UUIDs, implicit environment reads, or hidden filesystem state in `src/truthkernel/`.
- Stochastic helpers belong outside the kernel under `adapters/`, and their outputs become committed, hashed inputs.

## Model And Token Tier Policy

Use a tiered model strategy per `CODEX_HARNESS.md` section 7:

| Tier | Use | Planned Work |
|---|---|---|
| T3 / high reasoning | Architecture, hashing, schemas, canonical serialisation, predicates, ledger, replay bugs | M1, M3, M4, M5, final review of major milestones |
| T2 / medium reasoning | Well-specified implementation with strong tests | M2, M6, M7, M8, M9, M10 |
| T1 / low reasoning | Mechanical scaffold, fixture generation, README edits, lint fixes, commit messages | M0 and chores |

Escalation rule: if a T2 pass fails the same milestone twice, preserve the failing diff and gate output, then escalate to T3 instead of retrying cheaply.

## Milestone Plan

### Current Milestone Status

- M0/M1 baseline is pushed in `f2ad2ad`.
- M2 graph/replay implementation exists locally and has been checked, but it has not yet been committed in the current working tree.
- M3 predicate/comparator implementation exists locally and has been checked, but it has not yet been committed in the current working tree.
- Static frontend/Vercel work is pushed through `d968951`.
- Real verified-chat execution is not implemented yet. The current UI is a routed static mock that defines the intended workflow.

### M0 - Repository Scaffold

Goal: establish a repo that can be safely built by coding agents.

Tasks:

- Configure local git remote as `origin = https://github.com/Ged-glitch/Truth-AI.git`.
- Import the project documents into the repo root:
  - `AGENTS.md`
  - `CODEX_HARNESS.md`
  - `TRUTH-AI_SPEC.md` copied from `final_truth_ai_spec.md`
- Add `CLAUDE.md` pointing to the same rules as `AGENTS.md`.
- Decide and record licence choice before adding a licence file.
- Initialise Python 3.12+ project with `uv`.
- Add pinned development dependencies:
  - `ruff`
  - `mypy`
  - `pytest`
  - `hypothesis`
  - `pydantic`
  - `typer`
  - `networkx`
- Add initial package layout under `src/truthkernel/`.
- Add `Makefile` with `gate`, `lint`, `type`, `test`, `replay`, and `freeze-check`; replay and freeze can be no-op stubs until the relevant milestones.
- Add GitHub Actions running `make gate` on push and pull request.
- Add pre-commit hooks for ruff, end-of-file, and basic hygiene.
- Add a minimal README with setup and gate commands.

Definition of done:

- Fresh clone can run `uv sync` and `make gate`.
- CI runs the same gate.
- No application logic beyond scaffold.

Model tier: T1, with T3 review only if dependency or CI architecture becomes ambiguous.

### M1 - Schemas v0.1 And Canonical Serialisation

Goal: freeze the core data contract.

Tasks:

- Implement Pydantic v2 models for claims, evidence, entities, links, packs, policy/rule packs, findings, repair contracts, and decision bundles.
- Implement canonical JSON and SHA-256 helpers.
- For hashed payloads:
  - sort keys deterministically
  - use fixed separators
  - encode UTF-8
  - serialise decimals as strings
  - reject binary floats, NaN, and infinity
- Export JSON Schema files.
- Add schema freeze check tooling.
- Add hand-written golden examples and hash fixtures.
- Add Hypothesis round-trip tests.

Definition of done:

- Schemas round-trip parse -> canonical serialise -> parse identically.
- Golden hashes are stable across repeated runs.
- Schema hash freeze file is committed.

Model tier: T3.

### M2 - Typed Graph Builder And Pre-Graph Validation

Goal: validated packs become deterministic graphs.

Tasks:

- Build typed graph representation from validated packs.
- Normalise node and edge ordering by content hash.
- Reject malformed packs before predicate evaluation.
- Add fixtures proving input order independence.
- Activate replay target for graph-level golden outputs.

Definition of done:

- Shuffling pack element order produces the same canonical graph hash.
- Malformed packs produce only the pre-graph validation finding.

Model tier: T2.

### M3 - Truth Class Predicates And Precedence

Goal: implement the deterministic kernel core.

Tasks:

- Implement one pure predicate module per Truth Class:
  - `TC-01` unsupported claim
  - `TC-02` stale evidence
  - `TC-03` unqualified critical claim
  - `TC-04` orphan claim
  - `TC-05` missing provenance
  - `TC-07` ledger contradiction
  - `TC-08` self-contradiction
- Keep `TC-06` as verifier-bank or human-review undecided until the verifier integration milestone.
- Implement typed comparators for exact decimals, dates, intervals, enums, and units.
- Implement fixed precedence rules.
- Add strict default policy pack.
- Add positive and negative fixtures for each predicate.
- Add mutation-style checks that fail when a predicate is deliberately broken.
- Add lint guard banning nondeterministic imports inside kernel predicate modules.

Definition of done:

- Each predicate has positive, negative, precedence, and mutation coverage.
- Predicate outputs are canonically ordered.
- Kernel predicate package remains pure.

Model tier: T3.

### M4 - Acceptance Gate And Repair Contracts

Goal: turn findings into deterministic accept/reject decisions and actionable repair contracts.

Tasks:

- Implement fault/count vectors.
- Implement lexicographic gate:
  - reject on critical findings
  - compare non-critical vectors against policy ceilings or previous iteration
  - apply fixed tie-breakers
- Emit repair contracts with required remedy type.
- Assemble decision bundles with hashes, policy id, taxonomy id, compiler id, verifier ids, findings, verdicts, and decision.
- Keep any signed timestamp envelope outside hashed payloads.

Definition of done:

- Gate truth-table tests pass.
- Repair contracts round-trip through schemas.
- Three decision-bundle golden fixtures are byte-identical across 30 runs.

Model tier: T3.

### M5 - Truth Ledger And Continuity Bridge

Goal: persist only accepted claims with tamper-evident continuity.

Tasks:

- Implement JSONL append-only event log.
- Implement SQLite + FTS5 index.
- Implement SHA-256 named blob store.
- Implement Merkle/hash chain with previous-head embedding.
- Implement accepted fact promotion from gate-passing decision bundles.
- Implement invalidation and supersession without deletion.
- Implement pinned snapshots by head hash.
- Implement context assembler for top-k accepted facts.
- Evaluate ledger contradiction against pinned snapshots.

Definition of done:

- Replaying ledger from genesis reproduces the same head hash.
- Contradiction fixtures identify exact conflicting facts.
- Supersession closes validity intervals correctly.
- Ledger writes only under an explicitly passed path.

Model tier: T3.

### M6 - Replay Harness Hardening

Goal: make determinism a CI property.

Tasks:

- Implement `truth replay` for N repeated verifications.
- Byte-compare decision bundles.
- Enforce runtime locale and timezone inside the tool.
- Add hash-seed independence test.
- Add CI matrix for Linux and macOS when practical.

Definition of done:

- `truth replay fixtures/golden --runs 30 --byte-equal` passes.
- Deliberate order-dependency test fixture is caught.

Model tier: T2.

### M7 - CLI

Goal: make the kernel usable from a terminal.

Tasks:

- Implement Typer commands:
  - `truth verify PACK --rulepack RP --ledger PATH`
  - `truth ledger facts`
  - `truth ledger show`
  - `truth ledger snapshot`
  - `truth replay`
  - `truth fixtures make`
- Support `--json` on user-facing commands.
- Use exit codes:
  - `0` accepted
  - `1` rejected
  - `2` execution or input error
- Add subprocess smoke tests.
- Keep README quickstart executable by tests.

Definition of done:

- CLI smoke tests pass.
- README commands are tested.

Model tier: T2.

### M8 - MCP Server And HTTP Sidecar

Goal: provide integration surfaces for agents and external tools.

Tasks:

- Expose MCP tools:
  - `verify_pack`
  - `get_repair_contract`
  - `query_facts`
  - `get_snapshot`
- Add minimal HTTP sidecar with equivalent behaviour.
- Default to loopback-only.
- Require bearer token for non-loopback access.
- Ensure server state is limited to explicitly supplied ledger path and configuration.

Definition of done:

- MCP session test passes.
- HTTP contract tests pass.
- Server does not create hidden global state.

Model tier: T2.

### M9 - Advisory Adapters

Goal: add stochastic and retrieval helpers outside the deterministic kernel.

Tasks:

- Add extraction adapter for free text to pack conversion.
- Add provenance fetch-and-hash adapter.
- Add grounding verifier adapter that writes static verdict files.
- Optionally add uncertainty adapter.
- Key adapter outputs by claim hash, evidence hash, model id, and settings hash.
- Prove the kernel can consume cached verifier outputs without importing adapter code.
- Record calibration results and freeze thresholds into policy packs.

Definition of done:

- Kernel imports nothing from `adapters/`.
- Replay stays byte-equal because adapter outputs are committed inputs.
- Cached grounding verdict can resolve a verifier-routed claim.

Model tier: T2, with T3 review for policy threshold freezing.

### M10 - Integration Demos And Evaluation Report

Goal: demonstrate the full system against agent memory and hallucination workflows.

Tasks:

- Add OpenClaw-style memory-write verification demo.
- Add Hermes-style tool integration demo.
- Add DCIR-A repair loop demo.
- Run benchmark-style briefs covering:
  - hardware/GARK-style evidence
  - research summary with citations
  - ops or business claims
- Add report generator summarising:
  - injected-fault precision and recall
  - per-class findings
  - iterations to acceptance
  - replay evidence
  - development and runtime cost notes

Definition of done:

- Evaluation report committed under `reports/`.
- Demos run from documented commands.
- Final release gate passes.

Model tier: T2, with T3 final review.

### Product Track - Verified Chat And Truth Output

Goal: turn the static verified-chat mock into a working user flow while preserving the deterministic kernel boundary.

Current UI state:

- `/app/chat` accepts a prompt or technical specification in the interface.
- model selector defaults to Gemini Flash and shows options for user-owned provider keys or local Ollama.
- `/app/truth-output` shows the intended cleaned truthful version after kernel verification.

Implementation plan:

- Add a non-kernel adapter boundary for model invocation. Model calls must live outside `src/truthkernel/`.
- Represent the prompt/specification, selected model, model settings, uploaded files, and retrieved references as canonical input artefacts.
- Add an adapter output format for raw model response and extracted claims.
- Pass those committed/canonical artefacts into the kernel for graph building, predicate evaluation, gate decision, repair contracts, and decision-bundle assembly.
- Persist raw prompt, raw model output, extracted claims, evidence references, cleaned output, and decision bundle in Supabase or an explicitly configured local store.
- Surface the cleaned truth output in `/app/truth-output`.
- Add support for user model selection:
  - Gemini Flash as default adapter
  - user-owned API keys for supported hosted providers
  - local model endpoint such as Ollama
- Add standard/reference pack selection so a user can ground a prompt against sources such as British Standards, uploaded technical files, or an organisation-specific rule pack.
- Ensure deterministic replay uses only the frozen adapter artefacts, not live model calls.

Definition of done:

- A prompt submitted through the UI produces a persisted raw model output, a kernel decision bundle, and a cleaned output.
- Replaying the saved artefacts produces byte-identical kernel results.
- Hosted model credentials are never exposed to the frontend.
- Kernel package remains free of network, LLM, environment, clock, random, and UUID behaviour.
- Mobile routes for `/app/chat` and `/app/truth-output` remain usable without body-level horizontal overflow.

Model tier: T3 for architecture and boundary design; T2 for implementation once contracts are fixed; T1 for route/page copy edits.

## First Coding Session Prompt

Historical prompt used to start M0:

```text
Read AGENTS.md, TRUTH-AI_SPEC.md, CODEX_HARNESS.md, and plan.md.
Model tier for this session: T1, with high-reasoning review if scaffold architecture becomes ambiguous.
Implement M0 only.
Do not add application logic.
Tests and gate targets must land with the scaffold.
When done, run make gate and summarise the diff against M0 Definition of Done.
```

## Next Session Prompt

Use this for the next implementation session if continuing in a fresh Codex chat:

```text
Read AGENTS.md, TRUTH-AI_SPEC.md, CODEX_HARNESS.md, and plan.md.
Repository: C:\Users\gedho\OneDrive\Documents\Truth Agent
GitHub target: Ged-glitch/Truth-AI
Latest frontend implementation head before plan update: d968951
Live site: https://www.truthai.tech

Important: local uncommitted M2/M3 backend milestone files exist. Do not overwrite, delete, or revert them.

Goal: choose the next coherent milestone.
If continuing backend: review M2 local diff, run relevant tests, commit M2 only, then proceed to M3 separately.
If continuing product UI/backend integration: design the verified-chat adapter boundary so hosted/local model calls remain outside src/truthkernel/ and kernel replay consumes only frozen artefacts.
Use the tiered model policy in plan.md.
```

## Open Decisions

- Whether taxonomy names in code should be strictly `TC-*`, with `GC-*` kept only as a historical harness alias.

## Resolved Scaffold Decisions

- Licence: MIT.
- `CLAUDE.md`: copied from `AGENTS.md` on this Windows host because symlink creation required Administrator privilege.
