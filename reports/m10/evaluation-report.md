# Truth-AI M10 evaluation report

## Demos

### OpenClaw memory-write verification
Hardware/GARK-style memory write admitted only after deterministic verification.

- Iterations to acceptance: 1
- Final decision: accept
- Accepted on attempt: 1
- Per-class findings:
  - TC-01: 0
  - TC-02: 0
  - TC-03: 0
  - TC-04: 0
  - TC-05: 0
  - TC-06: 0
  - TC-07: 0
  - TC-08: 0
- Attempts:
  - memory-write: accept (findings=0, critical=0)
    - graph hash: a2d4b3586fb5cf4fd0493d3a8d34c8d952d1279a27f3243865cd7b84f63758e3
    - decision bundle: f6fe694ca2c9fa79ec94ce5ea0a06df5d53d4fe2d11b5cbd6710c2a0e5353e9f

### Hermes tool integration
Research-summary tool output is repaired until the memory write satisfies policy.

- Iterations to acceptance: 2
- Final decision: accept
- Accepted on attempt: 2
- Per-class findings:
  - TC-01: 0
  - TC-02: 0
  - TC-03: 1
  - TC-04: 0
  - TC-05: 0
  - TC-06: 0
  - TC-07: 0
  - TC-08: 0
- Attempts:
  - tool-write-1: reject (findings=1, critical=1)
    - graph hash: 82de9f0f9c9ca7a2ff7f9d39da70134996a6e92be68ace1a546115362abc4b97
    - decision bundle: 88ac2a68404253393a76e3116a88ed4db3a3d1ec284be78ab130552484e4ade8
    - repair contract: dfe89203ddd18233a1d0685bcc48860e1960e5dfac38434f989df1d1f7d7e606
  - tool-write-2: accept (findings=0, critical=0)
    - graph hash: 14a0f903463a624ee1efc9daf9a95253d8c6e33cfa5797f167d985367a73e03a
    - decision bundle: 5856aff94dd1dc3cffee51c22f14d53f26ee7fad651d45c7f2392f15798e0e9e

### DCIR-A repair loop
Ops/business claims move from raw output to an accepted kernel-gated answer.

- Iterations to acceptance: 3
- Final decision: accept
- Accepted on attempt: 3
- Per-class findings:
  - TC-01: 1
  - TC-02: 0
  - TC-03: 0
  - TC-04: 0
  - TC-05: 1
  - TC-06: 0
  - TC-07: 0
  - TC-08: 0
- Attempts:
  - dcir-1: reject (findings=1, critical=0)
    - graph hash: 92d62d3e54c337d5f7c66bd0adec02c7bb085457cda64323fce14440df3b667f
    - decision bundle: 11cdc58e6552cbb61795e7cc405263eabb0faffdc563539ac2e5ca0a1072d1fb
    - repair contract: 358ace1ef9a7d4bc30bfbdc9aac336d2fd6cbbc2c3b5eee6941db12d30e340b0
  - dcir-2: reject (findings=1, critical=0)
    - graph hash: 0a317ae8459a5fcfb1fce8bd336f582a41703f33ec5be4a9d6d006694dc6578b
    - decision bundle: 4de0c6364f9590f83ba50d20d5b14746a99b303bafa2e7349c4c72903187247d
    - repair contract: a606ae48f975153e605630fb94aee25b8447306fb889b4057e13d2cb26b1f7c6
  - dcir-3: accept (findings=0, critical=0)
    - graph hash: ed3a1db769e118b06692916cf45cc47483b2b8807930aa0e4d12cb6546224d55
    - decision bundle: 8aff3ffd552e41cb481d459540b67b5f62f32789cfb5f65eadd274eb892a8c07

## Injected Fault Suite

- Precision: 1
- Recall: 1
- True positives: 4
- False positives: 0
- False negatives: 0
- Per-class findings:
  - TC-01: 1
  - TC-02: 0
  - TC-03: 1
  - TC-04: 1
  - TC-05: 1
  - TC-06: 0
  - TC-07: 0
  - TC-08: 0

## Fault Cases

- tc01-unsupported
  - expected: TC-01
  - observed: TC-01
  - decision: reject
- tc03-unqualified-critical
  - expected: TC-03
  - observed: TC-03
  - decision: reject
- tc04-orphan
  - expected: TC-04
  - observed: TC-04
  - decision: reject
- tc05-missing-provenance
  - expected: TC-05
  - observed: TC-05
  - decision: reject
- healthy-control
  - expected: none
  - observed: none
  - decision: accept

## Replay Evidence

- `uv run truth replay fixtures/golden --runs 30 --byte-equal`: passed

## Cost Notes

- Milestone executed locally with deterministic kernel and committed fixtures.
- No external model calls were required to produce the report artefacts.
- Report generation replays committed golden fixtures and evaluates static demo packs.
- Runtime cost is bounded by local graph construction, predicate evaluation and replay.
