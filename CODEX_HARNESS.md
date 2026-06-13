# Truth‑AI — Codex Harness (development plan for agentic coding)

**Companion to:** `TRUTH-AI_SPEC.md` (read it first; it is the source of truth for semantics)
**Audience:** OpenAI Codex, Claude Code, or any CLI coding agent — and you, supervising.
**Convention:** the repo carries an `AGENTS.md` (provided) which Codex reads natively; symlink `CLAUDE.md → AGENTS.md` so Claude Code picks up the same rules.

---

## 0. How to drive this plan

1. **One milestone per agent session.** Paste the milestone block verbatim as the task. Do not let a session span milestones — context drift is how determinism rules get forgotten.
2. **The harness is the product discipline.** Every milestone lands tests and fixtures *before or with* features. An agent that writes the feature first has the order wrong; reject the diff.
3. **Every session must end green:** `make gate` passes locally and in CI. No green, no merge.
4. **Frozen things stay frozen.** Once M1 lands, schema changes require a version bump + migration note + golden‑file regeneration in a dedicated PR. Agents must never edit schemas as a side effect.
5. **You review the diff, not the vibes.** The kickoff prompt template (§5) tells the agent to summarise its diff against the milestone's Definition of Done before finishing.

---

## 1. Repository layout (target)

```
Truth-AI/
├── AGENTS.md                  # agent operating rules (Codex-native; CLAUDE.md symlinks here)
├── TRUTH-AI_SPEC.md           # the spec — committed, hashed
├── CODEX_HARNESS.md           # this file
├── Makefile                   # gate, test, replay, fixtures, serve
├── pyproject.toml             # uv-managed; pinned; py3.12+
├── src/truthkernel/
│   ├── schemas/               # Pydantic models + exported JSON Schema (frozen after M1)
│   ├── canonical.py           # canonical JSON + SHA-256 helpers
│   ├── graph.py               # typed graph builder (GC-00 lives at the door)
│   ├── predicates/            # gc01.py … gc06.py + precedence.py
│   ├── gate.py                # fault vector, lexicographic gate, tie-breakers
│   ├── contract.py            # repair-contract emitter
│   ├── ledger/                # event log, blob store, promotion, snapshots
│   ├── cli.py                 # Typer app: verify / ledger / replay / fixtures
│   └── mcp_server.py          # FastMCP surface (M8)
├── adapters/                  # OUTSIDE the kernel: claim-extraction, grounding cache,
│   │                          # provenance fetcher, openclaw/, hermes/
├── rulepacks/
│   ├── strict-default/        # shipped default (versioned, hashed)
│   └── hardware-demo/         # GARK-flavoured demo pack
├── fixtures/
│   ├── single/                # one injected fault each, with manifest.json
│   ├── mixed/                 # multi-fault packs, with manifests
│   └── golden/                # byte-exact expected bundles
└── tests/                     # unit, property (Hypothesis), replay, mutation-style
```

---

## 2. The gate

```make
gate: lint type test replay freeze-check

lint:         uv run ruff check . && uv run ruff format --check .
type:         uv run mypy --strict src/
test:         uv run pytest -q
replay:       uv run truth replay fixtures/golden --runs 30 --byte-equal
freeze-check: uv run python tools/schema_freeze_check.py   # schemas hash-match recorded freeze
```

CI runs `make gate` on Linux and macOS. The replay target is non‑negotiable from M2 onward.

---

## 3. Milestones

### M0 — Scaffold
**Goal:** a repo an agent can't easily wreck.
**Tasks:** `uv init` (py3.12), pyproject with pinned ruff/mypy/pytest/hypothesis/pydantic/typer/networkx; Makefile with `gate` (replay stubbed as no‑op until M2); GitHub Actions (or GitLab CI — author uses both) running `make gate` on push; pre‑commit (ruff, end‑of‑file, no‑binary); `AGENTS.md` + `CLAUDE.md` symlink; MIT or Apache‑2.0 licence decision recorded.
**DoD:** fresh clone → `uv sync && make gate` green in <2 min. CI green.
**Agent guard‑rail:** no application code in this milestone. Scaffold only.

### M1 — Schemas v0.1 + canonical serialisation (then freeze)
**Goal:** the data contract everything else obeys.
**Tasks:** Pydantic v2 models for Claim, Evidence, Entity, Link, Pack, RulePack, Finding, RepairContract, DecisionBundle exactly per spec §3/§5; export JSON Schema to `schemas/json/`; `canonical.py` implementing RFC 8785‑style canonical JSON (UTF‑8, sorted keys, fixed separators, decimals as strings — binary floats forbidden in hashed payloads) + `sha256_of(obj)`; golden files: three hand‑written packs serialised, hashed, committed; `tools/schema_freeze_check.py` records and verifies schema hashes.
**DoD:** round‑trip property test (parse→serialise→parse identical) under Hypothesis; golden hashes stable across 30 runs; freeze file committed.
**Agent guard‑rail:** any field not in spec §3 needs a `# SPEC-DEVIATION:` comment and a question to the supervisor — do not invent fields silently.

### M2 — Typed graph builder + GC‑00
**Goal:** packs become graphs deterministically.
**Tasks:** `graph.py` builds G=(V,E,τ,α) from a validated pack; GC‑00 rejects pre‑graph with a Finding; node/edge ordering normalised (sorted by content hash) so construction is input‑order‑independent.
**DoD:** Hypothesis test — shuffle pack element order ⇒ identical canonical graph dump and hash; malformed‑pack fixtures yield GC‑00 and nothing else; `make replay` now live and green.

### M3 — Predicates GC‑01..GC‑05 + precedence
**Goal:** the heart of the kernel, GARK‑style.
**Tasks:** one module per predicate over (G, R); typed‑value comparator module (decimal exact/tolerance, dates/intervals UTC, enums, pint unit quantities incl. dimensional mismatch); GC‑08 intra‑pack self‑contradiction built on it; precedence resolver per spec §5; `rulepacks/strict-default` v0.1 (typed obligations, validity windows, reachability, gate‑relevant claim kinds) — versioned and hashed; fixture pairs (positive fires / negative silent) per predicate, single‑fault fixtures with `manifest.json` declaring expected findings.
**DoD:** every predicate's positive/negative pair passes; precedence regression tests for crafted overlap cases; mutation‑style check — for each predicate, a deliberately broken copy fails its fixture (script in `tests/mutation/`).
**Agent guard‑rail:** predicates are pure functions of (G, R). Any import of `datetime.now`, `random`, `uuid`, `os.environ` or network libs inside `predicates/` is an automatic reject (enforced by a lint rule added this milestone).

### M4 — Fault vector, gate, repair contract
**Goal:** verdicts and the loop's outbound half.
**Tasks:** `gate.py` per spec §6 (criticality tiers from rule pack; lexicographic; Pareto; fixed tie‑breakers); `contract.py` emits RepairContract with per‑finding required action and admissible evidence types; DecisionBundle assembly with input hashes and kernel version; envelope (signed timestamp) kept outside the hashed payload.
**DoD:** golden bundles for three fixtures, byte‑exact across 30 runs; gate truth‑table tests (critical>0 ⇒ reject, etc.); contract round‑trips through schemas.

### M5 — Continuity Ledger + GC‑06
**Goal:** the bridge.
**Tasks:** `ledger/`: JSONL event log + SQLite index + sha256‑named blob store; hash chain (each bundle embeds prev hash); fact promotion on gate pass with bi‑temporal fields; invalidation/supersession events (never deletion); snapshot pinning by head hash; context assembler (top‑k fact selection for session bootstrap — ranking may be fuzzy, admission never is); GC‑06 evaluated against the pinned snapshot, reusing the M3 comparator module.
**DoD:** ledger replay from genesis reproduces head hash; contradiction fixtures (number, date, enum, unit, dimensional) each raise GC‑06 pointing at the exact conflicting fact; invalidation closes intervals correctly under property tests.
**Agent guard‑rail:** the ledger package may write only under a path passed in explicitly; no implicit home‑directory state.

### M6 — Replay harness, hardened
**Goal:** determinism as a CI fact, not a hope.
**Tasks:** `truth replay` runs N verifications, byte‑compares bundles; CI matrix Linux+macOS; environment pinning checks (TZ=UTC, LC_ALL=C.UTF‑8 set by the tool, PYTHONHASHSEED irrelevant by construction — add a test proving hash‑seed independence).
**DoD:** N=30 green in CI on both OSes; a deliberately introduced `dict`‑order dependency (test‑only) is caught by the harness.

### M7 — CLI
**Goal:** usable by a human in a terminal.
**Tasks:** Typer commands — `truth verify PACK --rulepack RP --ledger PATH`, `truth ledger facts|show|snapshot`, `truth replay`, `truth fixtures make` (fault injector for authoring fixtures); `--json` everywhere; exit codes: 0 accept, 1 reject, 2 error.
**DoD:** CLI smoke tests via `subprocess`; README quickstart verified by a test that runs its commands.

### M8 — MCP server + HTTP sidecar
**Goal:** agnostic integration surface.
**Tasks:** FastMCP server exposing `verify_pack`, `get_repair_contract`, `query_facts`, `get_snapshot`; identical functionality over a minimal HTTP sidecar (FastAPI or stdlib) for non‑MCP callers; auth = bearer token, loopback‑only default (copy OpenClaw's refuse‑non‑loopback‑without‑token posture).
**DoD:** scripted MCP session test; HTTP contract tests; server holds no state beyond the ledger path it was given.

### M9 — Advisory adapters (outside the kernel)
**Goal:** stochastic helpers, quarantined and committed.
**Tasks:** `adapters/grounding/`: wraps a MiniCheck‑class checker (via Ollama or HF), writes verdict files into the committed corpus keyed by (claim hash, evidence hash, model id, settings hash); `adapters/uncertainty/` (optional): UQLM‑style scorers (semantic entropy, entailment/token probability) writing graded confidence files keyed the same way; `adapters/extract/`: free‑text → pack converter using structured output (Outlines/Instructor), output always written to disk before verification; `adapters/provenance/`: fetch‑and‑hash tool populating the corpus (retrieval order: ledger → committed corpora → web only where the rule pack permits); calibration runs: score grounding adapters on public benchmarks (LLM‑AggreFact, RAGTruth, AVeriTeC, HaluBench classes), record balanced accuracy and abstention, freeze thresholds into the rule pack and hash them.
**DoD:** kernel consumes a cached grounding verdict as evidence for a GC‑07‑flagged claim without any kernel code change; replay remains byte‑equal because adapter outputs are static files; a test proves the kernel package has zero imports from `adapters/`.

### M10 — Integration demos + evaluation report
**Goal:** the show‑and‑tell that proves the thesis.
**Tasks:** OpenClaw skill routing memory writes + outbound answers through `verify_pack` (reject ⇒ agent receives the repair contract); Hermes Agent tool doing the same; DCIR demo: raw pipeline vs kernel‑gated pipeline on three briefs, per‑class fault profiles + iterations‑to‑acceptance; generator selection: benchmark candidate models with lm‑evaluation‑harness on TruthfulQA/FEVER‑class tasks and record the chosen model + settings hash in the report; evaluation report generator (`truth report`) producing the spec §15 acceptance‑criteria evidence, including injected‑fault precision/recall.
**DoD:** spec §15 items 1–6 all demonstrably met; report committed under `reports/`.

---

## 4. Fixture strategy

- **Single‑fault fixtures** (~60): minimal pack + one injected defect + `manifest.json` listing exactly the expected findings (class, location). The fault injector (`truth fixtures make`) mutates a clean pack so fixtures stay regenerable.
- **Mixed‑fault fixtures** (≥12): combinations chosen to exercise precedence and GC‑06 masking rules.
- **Golden bundles:** byte‑exact expected outputs for replay; regenerating them is a deliberate, reviewed act (`make golden-regen` prints a red warning and diffs).
- **Briefs** (M10): three domain briefs — one hardware (GARK‑flavoured), one research‑summary‑with‑citations, one ops/business — to demonstrate agnosticism.

---

## 5. Kickoff prompt template (paste per milestone)

```
Read AGENTS.md, TRUTH-AI_SPEC.md, and CODEX_HARNESS.md milestone <Mx> only.
Model tier for this session: <T1|T2|T3> per CODEX_HARNESS §7.
Implement milestone <Mx> exactly. Tests and fixtures land before or with features.
Hard rules: no network, clock, randomness, UUIDs or env-dependence in src/truthkernel/;
decimals as strings in hashed payloads; sorted iteration everywhere; schemas are frozen
(version-bump PRs only). When done: run `make gate`, paste its output, and summarise
your diff against the milestone's Definition of Done, flagging any deviation with
SPEC-DEVIATION. Ask before inventing anything the spec does not define.
```

---

## 6. Determinism checklist (re‑read every session)

1. IDs are content hashes; `uuid` is banned in the kernel.
2. No `datetime.now()`, `random`, `os.urandom`, locale or env reads in any hashed‑output path; envelope timestamps only.
3. Iterate sorted; never rely on set/dict order even where CPython preserves it.
4. Canonical JSON only for anything hashed; decimals as strings; no NaN/Inf.
5. TZ=UTC and C.UTF‑8 enforced by the tool, not assumed from the shell.
6. Dependencies pinned by `uv.lock`; a CI job fails if the lockfile drifts from pyproject.
7. Stochastic anything (models, fetches) lives in `adapters/`, writes files, and those files are inputs — determinism by commitment.
8. New predicate ⇒ positive fixture, negative fixture, mutation check, precedence case. No exceptions.

---

## 7. Model tier plan (token economy for development)

Same logic as the runtime policy in spec §10.1, applied to the coding agents building the repo. The gate is what makes cheap‑first safe here too: a low‑tier model cannot merge bad code, because `make gate` and the fixtures reject it deterministically.

| Tier | Use for | Milestones |
|---|---|---|
| **T3 — frontier** (Opus‑class / GPT‑5‑class) | Correctness‑critical, cross‑cutting invariants; anything touching hashing, canonical serialisation or the ledger; debugging byte‑equality failures — the nastiest bug class in this repo | M1, M3, M4, M5 |
| **T2 — mid** (Sonnet‑class / 30–70B open weights) | Well‑specified construction with strong tests already defined | M2, M6, M7, M8, M9, M10 |
| **T1 — small** (Haiku‑class / local 7–8B) | Mechanical volume: scaffold, generating the ~60 single‑fault fixtures from templates, docstrings, README polish, lint fixes, commit messages | M0 + chores in any milestone |

**Session‑level economy:**

1. **Plan and review high, execute low.** Plan the milestone and review the final diff at the highest tier in play; switch down for grunt work mid‑session (most CLI agents support a `/model`‑style switch).
2. **One milestone per session is also the token rule.** Long sessions re‑read the same context repeatedly. Start fresh, point at file paths, and never paste the spec into the prompt — agents read `TRUTH-AI_SPEC.md` from disk themselves.
3. **Let `make gate` do the reasoning.** Run the suite and paste failures; never ask a frontier model to simulate the test run in its head.
4. **Escalate like the runtime.** If a T2 session fails the same milestone twice, hand the failing diff and gate output to T3 rather than retrying at T2 — two failed cheap attempts cost more than one expensive success.
5. **Track it.** Note model and approximate token spend per milestone in each PR description; the M10 report should state development cost alongside runtime cost per accepted pack.

---

## 8. Running this plan with Codex

Codex reads `AGENTS.md` natively, so the rules file already binds it; the points below tune the rest. (Claude Code picks the same rules up via the `CLAUDE.md` symlink — this section is Codex‑specific, the plan is not.)

**Why this repo is Codex‑shaped by construction.** `make gate` needs no network — kernel purity is a spec requirement — so the entire verify loop runs inside Codex's sandbox without escalations. The only step that touches the network is dependency installation.

**Environment setup (Codex cloud environments).** Put this in the environment's setup script, which runs while the network is available; everything after it is offline:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --frozen
```

**Recommended repo profile** (in `~/.codex/config.toml`; launch with `codex --profile truth-ai`):

```toml
[profiles.truth-ai]
model = "gpt-5.3-codex"            # or the current frontier codex model
model_reasoning_effort = "medium"  # T2 default; raise for T3 milestones
approval_policy = "on-request"
sandbox_mode = "workspace-write"
web_search = "disabled"            # the plan needs no browsing; zero injection surface
```

**Tier mapping (binds §7 to Codex settings).**

| Plan tier | Codex setting |
|---|---|
| **T3** | frontier codex model, `model_reasoning_effort = "high"` (reserve `xhigh`, where the model offers it, for byte‑equality bug hunts) |
| **T2** | same model, effort `medium` |
| **T1** | effort `low`/`minimal` — or fully local via `--oss` with `oss_provider = "ollama"` for fixture batches, docstrings and lint fixes |

Switch mid‑session with `/model` or the reasoning‑effort shortcuts rather than restarting, but still keep one milestone per session.

**Non‑interactive chores.** `codex exec` suits scripted T1 work and CI:

```bash
codex exec --profile truth-ai "Regenerate the GC-02 single-fault fixtures from templates per CODEX_HARNESS §4, run make gate, and show the diff."
```

A second profile with `sandbox_mode = "read-only"` is right for pre‑merge `codex review` passes — the reviewer agent should not be able to write at all.

**Dogfooding via MCP (after M8).** Register the kernel's MCP server in Codex's config so the agent can call `verify_pack` on its own outputs — Truth‑AI gating its own builder is the first integration demo, and the cheapest.

**Hard line.** Never run this repo with `--yolo`/full‑access bypass. Approval‑on‑request plus workspace‑write covers every milestone; the only escalation a session should ever request is the initial `uv sync`.
