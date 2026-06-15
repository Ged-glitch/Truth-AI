# Verified-chat adapter boundary

The verified-chat flow is split into two halves:

1. Live provider work happens here, outside `src/truthkernel/`.
2. The deterministic kernel only receives the frozen replay inputs.

The frozen replay payload is `FrozenReplayInputs`:

- `Pack`
- `RulePack`
- `DecisionBundle`

The adapter side persists the full `VerifiedChatRun`, which also holds:

- the canonical user prompt/specification
- provider selection and settings
- provider credentials by reference only
- the raw provider response
- the frozen extraction bundle that turns the raw response into a `Pack`
- the cleaned output shown in `/app/truth-output`

This boundary keeps Gemini, user-owned API keys and local model calls outside the
kernel package while giving replay a single frozen artefact to consume.
