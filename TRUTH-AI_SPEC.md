# Truth‑AI: A Domain‑Agnostic Truth Kernel and Continuity Bridge for LLM Agents

**Version:** 0.1 (draft)  
**Date:** 12 June 2026  
**Language:** British English  
**Lineage:** Generalises the Gap‑Analysis Reasoning Kernel (GARK) from hardware assurance to conversational agents; incorporates lessons from Nexus Design and comparisons of Hermes and OpenClaw agents.

## 1 Purpose and vision

Large language models (LLMs) are powerful text‑generation and reasoning engines, yet they remain stochastic and prone to hallucinations.  Even advanced agent frameworks such as **OpenClaw** and **Hermes** persist raw model outputs and allow them to influence future sessions without verification【601453758788842†L130-L167】.  Research surveys highlight two major problems:

1. **Per‑response fabrication (P1).** LLMs frequently produce fluent but unsupported or contradicted content【214187853870647†L57-L73】.  Detection research spans uncertainty‑based hallucination scorers (e.g., semantic entropy【764606152140280†L299-L329】) and fact‑verification pipelines (claim extraction → retrieval → entailment), yet neither paradigm alone suffices【520097998750996†L61-L116】.
2. **Cross‑session truth decay (P2).** Agent memories store what the model *said* rather than what was *verified*.  Systems such as OpenClaw (Markdown files) and Hermes (FTS5 recall) lack an acceptance gate; thus hallucinations can accumulate across sessions, compounding misinformation.

Truth‑AI aims to invert this paradigm.  It introduces a **deterministic, post‑hoc verification layer** — the **Truth Kernel** — and a **Continuity Bridge (Truth Ledger)** that ensures only verified claims persist.  The project is domain‑agnostic: it does not attempt to train or fine‑tune models, but to build a measurement instrument that filters and labels outputs, providing **replayable judgement** and provenance.  In short, *Truth‑AI makes the system honest about what is known and unknown*.

## 2 Background and lineage

### 2.1 GARK (Gap‑Analysis Reasoning Kernel)

The GARK MSc proposal introduced a deterministic Python kernel for assessing hardware evidence packs.  It defined a **pre‑registered fault taxonomy**, processed typed evidence graphs, applied pure predicates to detect structural gaps and emitted a reproducible repair contract【589704447858179†L84-L99】.  Key design choices — pre‑committed predicates, lexicographic acceptance gates, SHA‑256 hashing, and byte‑equal replay — inspire Truth‑AI.  Truth‑AI generalises these principles from hardware to LLM‑generated content: evidence packs become conversation turns and retrieval contexts; fault classes become **Truth Classes**.

### 2.2 Agent frameworks

Open‑source agents demonstrate both the potential and pitfalls of LLM autonomy:

- **OpenClaw** provides a local gateway connecting over 50 messaging platforms and integrates with local files and tools【601453758788842†L130-L167】.  Its strengths are breadth and transparent Markdown memory, but it lacks verification on the memory write path【589704447858179†L83-L100】 and suffers from update instability【589704447858179†L83-L116】.
- **Hermes** offers a closed learning loop and agent‑curated memory【911270311578765†L552-L559】.  It automatically creates and refines skills, stores multi‑layer memory and spawns sub‑agents for parallel work【911270311578765†L552-L569】.  However, Hermes also persists unverified content and lacks a replayable acceptance gate.
- **Evaluation tools** such as **lm‑evaluation‑harness** provide benchmarks for LLMs【379076738730024†L373-L389】, while libraries like **UQLM** implement uncertainty‑quantification scorers (semantic entropy, entailment probability, etc.)【764606152140280†L299-L329】.  **Braintrust** integrates LLM‑as‑a‑judge scorers, semantic entropy and human review for pre‑deployment evaluation and runtime monitoring【520097998750996†L61-L90】.  These tools inform Truth‑AI’s verifier ensemble and evaluation plan.

## 3 Problem statement

Truth‑AI addresses two failure modes arising from the absence of a deterministic verification layer:

- **P1 — Per‑response fabrication.** LLMs emit unsupported or contradictory statements【307046287062984†L117-L140】.  Without verification, these hallucinations can be stored as fact and later retrieved.
- **P2 — Cross‑session truth decay.** Memories in current agents capture unverified outputs, causing hallucinations to persist and amplify across sessions.  There is no standard for superseding outdated or corrected information.

The root cause of both failures is the lack of a deterministic, reproducible gate between generation and persistence.  Truth‑AI introduces that gate.

## 4 Definitions

- **Claim:** An atomic, decontextualised, checkable proposition extracted from model output.  Each claim has a canonical subject–relation–object (SROM) triple and a claim type (`factual | prediction | opinion | instruction | calculation | citation`).
- **Evidence:** A piece of information (document segment, retrieval snippet, tool output) that may support or contradict a claim.  Evidence snapshots are frozen, hashed and stored.
- **Policy Pack:** A versioned configuration defining claim handling (e.g., which claim types are gate‑relevant), criticality rules (what constitutes a safety‑critical claim), evidence corpora and retrieval permissions, verifier weights and thresholds, and gate ceilings.
- **Truth Class (TC):** A pre‑registered predicate that identifies a particular failure mode (e.g., unsupported claim, stale evidence).  The TC taxonomy is committed before any detection code is written; precedence rules are fixed.
- **Decision bundle:** A tuple `(claim graph, evidence snapshots, ledger root, policy hash, kernel version)` that captures the entire context of a gate decision, allowing replay.

## 5 System overview

Truth‑AI introduces a post‑hoc, deterministic verification layer and a continuity bridge that sits between the LLM and persistence.  Figure 1 depicts the high‑level architecture.  The **Truth Kernel** receives raw model output and conversation context, extracts claims, verifies them against evidence and ledger, classifies findings and decides whether the output is accepted or rejected.  Accepted claims are written to the **Truth Ledger**, an append‑only, bitemporal, Merkle‑chained store that provides continuity and provenance.  Policy Packs define the rules for claim handling, criticality and gate thresholds.

![High‑Level Architecture: Agent with Truth Kernel]({{file:truth_kernel_architecture.png}})

### Main modules

1. **Gateway taps.** Thin adapters connect messaging platforms (Telegram, Discord, Slack, CLI, etc.) to the agent.  They **never transform content**; instead they wrap incoming and outgoing messages with capture metadata — model and provider identifiers, parameters, timestamps and a request hash — and then forward the payload unchanged.  Proxy taps can annotate, repair or block responses according to the policy, but when disabled they must be a faithful pass‑through.

2. **Claim Compiler.** Transforms raw model output and conversation context into a **typed claim graph**.  The pipeline comprises segmentation, **atomic claim extraction**, de‑contextualisation (resolving pronouns and ellipsis so each claim stands alone), **subject–relation–object–modifier (SROM) normalisation**, type assignment (`factual | prediction | opinion | instruction | calculation | citation`), criticality tagging, canonical JSON serialisation (RFC 8785) and SHA‑256 content addressing.  Two implementations are envisaged: (a) a deterministic, rule‑based baseline using spaCy patterns for high‑assurance domains; (b) an LLM‑based structured extractor using pinned open‑weight models with temperature 0 and JSON‑schema constraints.  Input hashes cache transcripts to guarantee replay.  By default, only factual, calculation and citation claims are gate‑relevant; opinions and predictions pass through labelled.

3. **Truth Kernel (deterministic core).** A **pure function** over `(claim_graph, ledger_view, policy)` with no network calls, file writes or clock reads.  It evaluates each claim against a pre‑registered taxonomy of Truth Classes (TC‑01…TC‑08) using set‑based predicates and fixed precedence rules, emitting **findings** and a per‑class count vector.  Output ordering is canonical (sort by class then claim id) to guarantee byte‑identical replay【589704447858179†L84-L99】.

4. **Verifier Bank.** Performs **evidence snapshotting** and fact verification using pinned, versioned models.  Retrieval is hierarchical: the ledger is queried first, then configured corpora (e.g., internal knowledge bases), then — if permitted — the web.  All remote content is frozen to local snapshots so verification is replayable.  The ensemble comprises:

   - **Grounding/NLI tier:** small, deterministic natural‑language inference models (e.g., MiniCheck, HHEM‑2.1‑Open) that judge whether evidence entails, contradicts or is insufficient for a claim.
   - **Judge tier (optional):** larger open‑weight models (e.g., Patronus Lynx, Granite Guardian) used as a second opinion but never as the sole gate input【520097998750996†L61-L90】.
   - **Self‑consistency tier:** uncertainty scorers such as semantic entropy, entailment probability and SelfCheckGPT sampling from **UQLM**【764606152140280†L299-L329】.  These are Tier C (advisory) — they surface uncertainty but do not assert truth.

   Ensemble aggregation is a fixed, versioned function (e.g., weighted voting with abstention).  Thresholds are calibrated on public benchmarks (LLM‑AggreFact, HaluBench, FEVER‑AVeriTeC) and then frozen.

5. **Acceptance Gate.** Implements a **lexicographic decision procedure**.  First, it checks for **zero findings in critical classes** (as defined by the Policy Pack — by default unsupported critical claims, ledger contradictions and unqualified critical claims).  Second, it compares the remaining per‑class count vector against the previous iteration (for iterative refinement) or against policy ceilings (for single‑shot) using **Pareto ordering**.  Third, it applies fixed tie‑breakers (total findings, then graph hash order).  The gate is a pure function and cannot be prompt‑injected because it calls no models.

6. **Repair Contract & DCIR‑A (Deterministic Critic Iterative Refinement — Agnostic).** When the gate fails, the kernel emits a **Repair Contract** listing each finding with the claim id(s), class and required remedy type (`supply‑evidence | restate‑with‑source | retract | qualify | resolve‑contradiction`) and any conflicting ledger entries.  The contract is fed to the external generator (LLM) to revise the answer.  **DCIR‑A** runs an iterative loop with a cap on iterations; per‑iteration count vectors are logged so **convergence is measured, not assumed**【589704447858179†L84-L99】.

7. **Truth Ledger – The Continuity Bridge.** Accepted claims are appended to an **append‑only, bitemporal, Merkle‑chained store**.  Each ledger entry records when it was asserted (`t_asserted`) and the validity interval `[t_valid_from, t_valid_to)`; superseding entries are linked via `supersedes` edges so that corrections never overwrite history.  The ledger is the only writer (verified write); it is scoped per project or user and stored both as a queryable **SQLite + FTS5** database and as a **JSONL event log** suitable for Git.  A **Context Assembler** injects the top‑k relevant accepted claims (labelled with their hashes and confidence) into each new session and registers them as the contradiction baseline for TC‑07.

8. **Policy Packs.** Versioned YAML/JSON configurations define claim‑type handling, criticality rules, qualified source classes, evidence corpora and retrieval permissions, verifier weights and thresholds and gate ceilings.  Shipped packs might include `general-chat`, `research-notes`, `code-claims`, `hardware-evidence` (for GARK continuity) and `strict-critical`.  Every decision bundle records the policy hash, so each judgement is replayable.

## 6 Truth Class taxonomy (TC)

Truth‑AI commits its taxonomy **before any detection code is written**.  Precedence rules for overlapping classes are fixed and cannot be altered without a version bump.  The taxonomy generalises GARK’s fault classes and adds classes for knowledge continuity:

| Class | Name | Summary | Decidability | Default severity |
|---|---|---|---|---|
| **TC‑01** | **Unsupported claim** | Gate‑relevant claim has no resolvable evidence (ledger, corpus, snapshot or tool result). | Tier A (pure predicate) | Major |
| **TC‑02** | **Stale evidence** | Supporting evidence is superseded, expired or outside the claim’s validity interval. | Tier A | Major |
| **TC‑03** | **Unqualified critical claim** | A critical claim lacks a required qualified source (as defined in a Policy Pack). | Tier A | **Critical** |
| **TC‑04** | **Orphan claim** | Claim lacks traceability to the task/context graph (unanchored assertion). | Tier A | Minor |
| **TC‑05** | **Missing provenance** | Mandatory provenance metadata is absent (model id, source URI, retrieval time, hashes). | Tier A | Major |
| **TC‑06** | **Semantic support undecided** | Support relation cannot be decided structurally; routed to Verifier Bank and, if still unresolved, to human review. | Tier B→review | Review |
| **TC‑07** | **Ledger contradiction** | Claim conflicts with an accepted, non‑superseded ledger entry. | Tier A (given compiled graph) | Critical if target is critical, else Major |
| **TC‑08** | **Self‑contradiction** | Two claims in the same output conflict on canonical SROM. | Tier A | Major |

Claims may trigger multiple classes; precedence rules determine gate outcomes.

### 6.1 Formal model and decision bundles

Truth‑AI models a candidate output as a finite, typed, labelled graph `G = (V, E, τ, α)`.  The vertices `V` represent **claims** and **evidence snapshots**; edges `E ⊆ V × L × V` carry labelled links such as `supports`, `cites`, `derives`, `anchors`, `contradicts` and `supersedes`.  A typing function `τ` assigns each vertex and edge a kind (claim type, evidence type, link relation), while an attribute function `α` attaches metadata — criticality tags, validity intervals, provenance fields and hashes.  The **ledger** is a monotone sequence `Λ` of accepted graphs; a *ledger view* `Λₜ` filters superseded entries and validity intervals at time `t`.  Each Truth Class predicate operates over `(G, Λₜ, P)` for a given **Policy Pack** `P`.

When the kernel and gate decide on an output, they assemble a **decision bundle** — a self‑contained record comprising the claim graph hash, evidence snapshot hashes, ledger root, policy hash, taxonomy hash, compiler identifier, verifier identifiers and weights, findings, verdicts and the final decision.  The decision bundle, together with the repository, is sufficient to replay the gate decision exactly.  All hashes use SHA‑256; JSON is serialised via RFC 8785 to guarantee canonicalisation.  Decision bundles are stored alongside the ledger to audit past judgements and support reproducibility.

## 7 Determinism, replay and provenance

Truth‑AI treats generation as stochastic and measurement as deterministic.  Each component declares a **determinism tier**:

* **Tier A — deterministic:** pure functions with no network, file writes or clock reads (e.g., the Truth Kernel, Acceptance Gate, canonical serialisation).  Given the same inputs, they produce byte‑identical outputs; this property is enforced with replay tests.
* **Tier B — replayable:** components that call models or retrieval but fix all nondeterminism by pinning model weights, setting temperature to 0 and caching transcripts (e.g., LLM‑based claim extraction or the Verifier Bank).  Replays from cache are byte‑equal; cold re‑runs may vary slightly, and this variance is recorded and reported【764606152140280†L299-L329】.
* **Tier C — advisory:** components that rely on sampling or large models for uncertainty estimation (e.g., semantic entropy, SelfCheckGPT scoring).  These provide guidance but never decide gates by themselves【764606152140280†L299-L329】.

Every gate decision emits a **decision bundle** containing hashes of the claim graph, evidence snapshots, ledger root, policy and taxonomy, compiler and verifier versions, and the findings and verdicts.  Together with the repository, this bundle allows any reviewer to replay the decision exactly.  Byte‑equal replay across 30 runs is a release requirement; the repository is the experiment, with JSONL logs, policy hashes and kernel versions committed.

## 8 Security and threat model

- **LLM output is untrusted input.**  The kernel, ledger and user should assume that model output may be malicious or incorrect.  The acceptance gate prevents unverified content from persisting.  Tool commands executed on the user’s machine must be gated and require user approval.
- **Supply‑chain risk.**  Models, verifiers and retrieval connectors are pinned to specific versions; updates require explicit review.  Evidence snapshots are captured locally to prevent retrieval drift.
- **Injection attacks.**  Since the Truth Kernel and gate do not call models, they cannot be prompt‑injected.  Extractors and verifiers run with pinned prompts and schema constraints.

## 9 Technology selection

Truth‑AI is implemented in **Python 3.12+** with `uv` for package management.  Python offers the richest ecosystem for verification and retrieval: **spaCy** for rule‑based extraction, **Pydantic v2** for schema validation, **NetworkX** for graph predicates, open‑weight models such as **HHEM‑2.1‑Open** and **MiniCheck** for fact verification, **sentence‑transformers** for embeddings, **UQLM** for uncertainty scorers【764606152140280†L299-L329】, and **vLLM/Ollama** for efficient model serving.  The existing GARK code (Pydantic models, Typer CLI, graph predicates) can be reused.  Hermes Agent is Python; OpenClaw is TypeScript but can be integrated via a thin proxy.  A TypeScript client SDK can be built later for browser‑side integrations.

For provider‑agnostic model calls, **LiteLLM** (Python) wraps multiple API providers (OpenAI, Anthropic, Gemma, Ollama) under one interface, enabling the Verifier Bank and the DCIR‑A loop to call external models without bespoke clients.  **FastAPI + Uvicorn** provides a lightweight proxy server exposing OpenAI‑compatible endpoints and MCP tools.  Structured claim extraction uses **Instructor** or **Outlines** to enforce JSON‑schema‑constrained decoding from LLMs, with caching keyed by input hash.

### Key libraries and frameworks

| Concern | Choice | Why |
|---|---|---|
| Schemas / validation | **Pydantic v2** | GARK continuity; JSON‑schema export for extractors |
| CLI | **Typer** | simple, testable commands; reuse of GARK CLI |
| Graph predicates | **NetworkX** | proven library; reuses GARK fault predicates |
| Canonical JSON + hashing | **rfc8785** implementation + `hashlib` | ensures byte‑equal serialisation and content addressing |
| Provider‑agnostic LLM calls | **LiteLLM** | one client for OpenAI/Anthropic/Gemini/Ollama/vLLM |
| Structured extraction | **Instructor** or **Outlines** | JSON‑schema‑bound extraction using pinned models |
| Retrieval / RAG | **LlamaIndex / LangChain** | flexible document loaders, vector stores and retrievers |
| Fact‑verification models | **MiniCheck**, **HHEM‑2.1‑Open**, **Lynx** | open‑weight NLI models for grounded claim checking |
| Judge tier (optional) | **Lynx‑8B/70B**, **Granite Guardian** via **vLLM** | second‑opinion LLM‑judges; never sole gate input |
| Uncertainty quantification | **UQLM** | semantic entropy, entailment probability, min‑token probability【764606152140280†L299-L329】 |
| Observability / evaluation | **lm‑evaluation‑harness**, **Braintrust** | standard benchmarks【379076738730024†L373-L389】 and integrated LLM‑as‑a‑judge evaluation【520097998750996†L61-L90】 |
| Storage | **SQLite + FTS5 + sqlite‑vec**, JSONL event log | local, tamper‑evident, bitemporal ledger; Git‑friendly logs |
| API / Proxy | **FastAPI + Uvicorn** | implements OpenAI‑compatible proxy and MCP server |
| Testing | **pytest + hypothesis + mutmut** | property tests; mutation testing ensures kernel predicates are robust |
| Lint / types | **ruff + mypy (strict on kernel)** | enforces kernel purity and style consistency |

## 10 Relationship to the state of the art

Truth‑AI addresses gaps in current systems.  Agent frameworks (OpenClaw, Hermes) provide gateways, tools, loops and memory but no verification or replayable judgement【589704447858179†L83-L100】.  Guardrails (NeMo Guardrails, Granite Guardian) enforce policies and sometimes check hallucinations, but they rely on LLM judgements and do not persist truth【520097998750996†L61-L90】.  Hallucination detection techniques (semantic entropy, SelfCheckGPT, internal probes) are model‑centric and cannot provide evidence or memory【764606152140280†L299-L329】; fact‑verification systems (FActScore, SAFE, MiniCheck) operate at the claim level but lack a gate, ledger or repair loop.  Deterministic verification tools exist for specialised tasks (natural‑logic QA) but are domain‑specific.  Memory systems (Letta/MemGPT, Zep/Graphiti) store unverified content and have no tamper evidence.  Truth‑AI’s novelty lies in **combining** a deterministic kernel with a calibrated verifier ensemble, a lexicographic acceptance gate, a repair contract loop and a verified‑write continuity ledger.

## 11 Evaluation plan

 - **Track 1 — Kernel validation.**  Synthetic claim‑graph fixtures with known injected faults (similar to GARK fixtures) are used to measure precision and recall of each Truth Class predicate.  The evaluation harness ensures byte‑equal replay across runs.
 - **Track 1b — Verifier Bank calibration.**  The ensemble of verifiers is calibrated on public fact‑verification benchmarks such as **LLM‑AggreFact**, **HaluBench**, **FEVER‑AVeriTeC** and **RAGTruth**.  Balanced accuracy, calibration curves and abstention rates are measured per verifier and for the ensemble; thresholds are then frozen into Policy Packs【764606152140280†L299-L329】【379076738730024†L373-L389】.
 - **Track 2 — Pipeline measurement.**  Truth‑AI is run in front of stochastic LLM pipelines (e.g., OpenClaw or Hermes) on task suites such as FEVER, TruthfulQA and summarisation datasets.  The instrument measures error profiles per model and per tool chain, counts of each Truth Class per 100 claims, DCIR‑A iterations to acceptance and runtime variance.  Braintrust integration allows continuous evaluation across pre‑deployment and production【520097998750996†L61-L90】.

## 12 Roadmap (abridged)

1. **M0 — Bootstrap.**  Initialise repository; establish `make gate` targets; set up schemas and test harness.
2. **M1 — Taxonomy pre‑registration and schemas.**  Commit TC taxonomy with hash; implement Pydantic models for claims, evidence, ledger entries.
3. **M2 — Truth Ledger.**  Implement append‑only bitemporal ledger; Merkle‑chain event log; context assembler; integrate SQLite view.
4. **M3 — Truth Kernel predicates.**  Implement pure predicates for TC‑01…TC‑05 and TC‑07, TC‑08; deterministic ordering; outputs.
5. **M4 — Claim Compiler.**  Implement deterministic extractor and LLM‑based extractor behind a common interface; calibrate on extraction benchmarks.
6. **M5 — Verifier Bank.**  Integrate retrieval snapshotter; implement ensemble of verifiers (MiniCheck, HHEM, UQLM); calibrate thresholds.
7. **M6 — Acceptance loop and repair contracts.**  Implement lexicographic gate; generate repair contracts; implement DCIR‑A loop.
8. **M7 — Gateway taps.**  Add adapters for messaging platforms (Telegram, Slack, Hermes Gateway); integrate with existing agent frameworks via a thin proxy.
9. **M8 — Continuity Bridge runtime.**  Finalise ledger‑interaction flows; implement context assembler queries; integrate with agent session start.
10. **M9 — Evaluation harness and Track 2.**  Build test suites; run pipeline evaluations; integrate Braintrust for regressions.
11. **M10 — Hardening and release.**  Conduct threat‑model review; ensure fail‑open and fail‑closed policies are respected; lint documentation.

## 13 Non‑goals and exclusions

- Truth‑AI does not train or fine‑tune LLMs; it assumes model outputs are untrusted input.
- It does not moderate content or enforce safety policies (e.g., hate speech detection); these can be added via separate policies or tool wrappers.
- It does not attempt to detect deception or opinion falsity; opinions are tagged but never “verified”.
- It does not judge human users; it focuses on machine outputs.

## 14 Risks and mitigations

- **Extractor quality ceiling.**  Claim extraction quality heavily influences downstream verification.  A dedicated extractor calibration phase (M4) and rule‑based fallback mitigate this risk.
- **Verification bias.**  LLM judges may introduce bias.  The Verifier Bank uses multiple small models and weights them conservatively.  TC‑06 catches undecided cases and routes them for human review.
- **Complexity creep.**  The roadmap locks scope, with cut‑offs for backlog items and versioned milestones.  Additional features (e.g., TypeScript SDK, frozen‑context comparator) are explicitly deferred.

## 15 Conclusion

Truth‑AI proposes a domain‑agnostic, deterministic verification layer and continuity bridge for LLM agents.  By combining a pre‑registered Truth Class taxonomy with a calibrated verifier ensemble and a lexicographic acceptance gate, it filters hallucinations and ensures that only verified claims persist.  The append‑only Truth Ledger provides a bitemporal, tamper‑evident record of accepted knowledge, while repair contracts allow iterative refinement.  Inspired by the GARK project【589704447858179†L84-L99】 and informed by research on hallucination detection【764606152140280†L299-L329】, fact verification and multi‑agent memory, Truth‑AI offers a practical path to harnessing LLM power without sacrificing truth and continuity.
## 16 Implementation acceptance criteria for v0.1

These criteria are carried forward from the earlier v0.1.3 draft and are binding for the first implementation series. They convert the evaluation plan into concrete release checks.

1. Every TC predicate implemented in v0.1 fires on its positive fixture and remains silent on its negative fixture.
2. Byte-equal replay across N = 30 runs passes in CI on every commit, with at least one Linux/macOS cross-check before release.
3. Ledger replay from genesis reproduces the head hash exactly.
4. The injected-fault fixture suite reports per-class precision and recall for approximately 60 single-fault fixtures and at least 12 mixed-fault fixtures.
5. A raw-agent versus kernel-gated pipeline demo runs on three briefs and reports per-class fault profiles plus DCIR-A convergence. These results are descriptive only; no open-world accuracy claim is made.
6. The MCP server passes a scripted session from at least two distinct clients.
7. Advisory grounding adapters are calibrated once on public benchmarks, including LLM-AggreFact, RAGTruth, AVeriTeC and HaluBench-style classes. Balanced accuracy and abstention rates are reported, and thresholds are frozen into a hashed Policy Pack before pipeline measurement.

## 17 Runtime model-tier policy

Every model call in Truth-AI is external to the deterministic kernel. Tiering is therefore a Policy Pack concern, not a kernel concern. Like other policy material, tier routing is versioned, hashed and recorded in decision or adapter outputs where it affects a run.

| Tier | Capability band | Used for |
|---|---|---|
| **T0** | No model: the kernel itself | Schema checks, Truth Class predicates, acceptance gate, ledger, comparators. Zero tokens per check. |
| **T1** | Small/local models, task specialists, low-cost API models | Constrained claim extraction, first-pass grounding verdicts, uncertainty scoring, human-readable summaries and routine conversational turns. |
| **T2** | Mid-tier reasoning models or 30-70B open-weight models | Default pack generation on familiar briefs, early repair iterations and multi-document synthesis. |
| **T3** | Frontier reasoning models | Novel domains, dense multi-constraint packs, stalled repairs, rule-pack authoring assistance and adversarial review. |

Routing rules:

1. **Default down.** Start at the lowest tier whose preconditions hold.
2. **Escalate on evidence.** Escalation is triggered by measured kernel outcomes: Pareto non-improvement of the fault vector across a configured number of repair iterations, high extraction failure rates, or advisory unsupported verdicts on critical claims.
3. **De-escalate by ledger statistics.** If a brief class achieves stable first-pass acceptance at a tier over a defined window, pin it one tier lower and revisit on regression.
4. **Cache by content.** Adapter outputs are keyed by input hash, model id and settings hash; identical work does not re-run.
5. **Respect budget caps.** Per-pack and per-loop token ceilings sit beside the DCIR-A iteration cap. On breach, stop, emit findings and flag the budget condition.
6. **Record tier and policy version.** Cost per accepted pack and escalation rates must be queryable from run logs and included in the M10 evaluation report.

## 18 Open-source landscape and positioning

Truth-AI should build on existing systems where they are useful while keeping its own contribution narrow and testable.

| Project family | Relationship to Truth-AI |
|---|---|
| OpenClaw | Primary gateway integration target; its plain-text memory pattern is exactly what the Truth Ledger hardens. |
| Hermes Agent | Second integration target; its memory loop is a useful demonstration of admission gating. |
| Graphiti / Zep | Close prior art for bitemporal memory structure; differs because Truth-AI gates admission deterministically. |
| Letta / MemGPT, Mem0, Cognee | Useful comparators for agent memory, but not deterministic verified-write ledgers. |
| Guardrails AI, NeMo Guardrails, LLM Guard, LlamaFirewall, Llama Guard | Complementary content and safety rails; Truth-AI focuses on claims, evidence, replay and persistence. |
| MiniCheck, VeriScore, FActScore, SAFE, HHEM-style models | Candidate advisory grounding and fact-verification components outside the kernel. |
| UQLM and semantic-entropy methods | Advisory uncertainty signals only; never sole gate inputs. |
| lm-evaluation-harness | Generator selection and benchmark reporting, not kernel verification. |
| in-toto, Sigstore, transparency logs, W3C PROV | Useful provenance and attestation patterns for hash chains and metadata naming. |

## 19 Reference list carried forward from v0.1.3 draft

The earlier draft included the following reference list. These references should be verified and normalised before publication, but they are retained here so the implementation and report work can track provenance.

- Atil, B. et al. (2025) 'Non-determinism of nominally deterministic LLM inference settings', *Proceedings of Eval4NLP*.
- Bishop, P. and Bloomfield, R. (1998) 'A methodology for safety case development', in *Industrial Perspectives of Safety-Critical Systems*. London: Springer.
- CVS Health (no date) *UQLM: uncertainty quantification for language models* [Software]. Available at: https://github.com/cvs-health/uqlm.
- EleutherAI (no date) *lm-evaluation-harness* [Software]. Available at: https://github.com/EleutherAI/lm-evaluation-harness.
- Farquhar, S., Kossen, J., Kuhn, L. and Gal, Y. (2024) 'Detecting hallucinations in large language models using semantic entropy', *Nature*, 630, pp. 625-630. https://doi.org/10.1038/s41586-024-07421-0.
- Gotel, O.C.Z. and Finkelstein, A.C.W. (1994) 'An analysis of the requirements traceability problem', *Proceedings of the First International Conference on Requirements Engineering (ICRE)*. IEEE, pp. 94-101.
- Hevner, A.R., March, S.T., Park, J. and Ram, S. (2004) 'Design science in information systems research', *MIS Quarterly*, 28(1), pp. 75-105.
- Ji, Z. et al. (2023) 'Survey of hallucination in natural language generation', *ACM Computing Surveys*, 55(12), pp. 1-38.
- Lewis, P. et al. (2020) 'Retrieval-augmented generation for knowledge-intensive NLP tasks', *Advances in Neural Information Processing Systems 33*.
- Marks, S. and Tegmark, M. (2024) 'The geometry of truth: emergent linear structure in large language model representations of true/false datasets', *Conference on Language Modeling*. arXiv:2310.06824.
- Meta AI (2025) *LlamaFirewall: an open source guardrail system for building secure AI agents*. arXiv:2505.03574.
- Min, S. et al. (2023) 'FActScore: fine-grained atomic evaluation of factual precision in long form text generation', *Proceedings of EMNLP 2023*. arXiv:2305.14251.
- Nous Research (2026) *hermes-agent* [Software]. Available at: https://github.com/NousResearch/hermes-agent.
- OpenClaw (2026) *Gateway architecture*. Available at: https://docs.openclaw.ai/concepts/architecture.
- Patronus AI (2024) 'Lynx: an open source hallucination evaluation model'. arXiv:2407.08488.
- Rasmussen, P. et al. (2025) *Zep: a temporal knowledge graph architecture for agent memory*. arXiv:2501.13956.
- Rebedea, T. et al. (2023) 'NeMo Guardrails: a toolkit for controllable and safe LLM applications with programmable rails', *Proceedings of EMNLP 2023: System Demonstrations*. arXiv:2310.10501.
- Song, Y., Kim, Y. and Iyyer, M. (2024) 'VeriScore: evaluating the factuality of verifiable claims in long-form text generation', *Proceedings of EMNLP 2024*. arXiv:2406.19276.
- Tang, L., Laban, P. and Durrett, G. (2024) 'MiniCheck: efficient fact-checking of LLMs on grounding documents', *Proceedings of EMNLP 2024*. arXiv:2404.10774.
- van Bekkum, M. et al. (2021) 'Modular design patterns for hybrid learning and reasoning systems', *Applied Intelligence*, 51, pp. 6528-6546.
- Vectara (no date) *HHEM-2.1-Open: hallucination evaluation model* [Software]. Available at: https://huggingface.co/vectara/hallucination_evaluation_model.
- Zheng, L. et al. (2023) 'Judging LLM-as-a-judge with MT-Bench and Chatbot Arena', *Advances in Neural Information Processing Systems 36*.
