"""Helpers for loading and replaying verified-chat bundles."""

from __future__ import annotations

from pathlib import Path

from adapters.verified_chat.contracts import (
    FrozenReplayInputs,
    VerifiedChatRequest,
    VerifiedChatRun,
    verified_chat_run_path,
)


def load_verified_chat_run(path: Path) -> VerifiedChatRun:
    """Load a verified-chat bundle from canonical JSON."""
    return VerifiedChatRun.model_validate_json(path.read_text(encoding="utf-8"))


def load_verified_chat_run_at_root(root: Path, request: VerifiedChatRequest) -> VerifiedChatRun:
    """Load a verified-chat bundle from its hash-keyed root path."""
    return load_verified_chat_run(verified_chat_run_path(root, request))


def kernel_replay_inputs(run: VerifiedChatRun) -> FrozenReplayInputs:
    """Return the frozen artefacts that the kernel is allowed to see."""
    return run.replay_inputs
