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

Use the hash-keyed helpers when writing to disk:

- `verified_chat_request_path(root, request)`
- `verified_chat_response_path(root, request)`
- `verified_chat_extracted_pack_path(root, request)`
- `verified_chat_cleaned_output_path(root, request)`
- `verified_chat_run_path(root, request)`
- `save_verified_chat_request(request, path)`
- `save_verified_chat_response(response, path)`
- `save_verified_chat_extracted_pack(bundle, path)`
- `save_verified_chat_cleaned_output(cleaned_output, path)`
- `save_verified_chat_run_at_root(root, run)`
- `load_verified_chat_request(path)`
- `load_verified_chat_response(path)`
- `load_verified_chat_extracted_pack(path)`
- `load_verified_chat_cleaned_output(path)`
- `load_verified_chat_run_at_root(root, request)`

Use the runner when compiling and persisting a verified-chat session:

- `build_verified_chat_run(...)`
- `persist_verified_chat_run(root, run)`
- `build_and_persist_verified_chat_run(...)`
- `load_verified_chat_run_bundle(root, request)`

This boundary keeps Gemini, user-owned API keys and local model calls outside the
kernel package while giving replay a single frozen artefact to consume.
