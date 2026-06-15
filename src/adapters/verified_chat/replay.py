"""Helpers for loading and replaying verified-chat bundles."""

from __future__ import annotations

from pathlib import Path

from adapters.verified_chat.contracts import FrozenReplayInputs, VerifiedChatRun


def load_verified_chat_run(path: Path) -> VerifiedChatRun:
    """Load a verified-chat bundle from canonical JSON."""
    return VerifiedChatRun.model_validate_json(path.read_text(encoding="utf-8"))


def kernel_replay_inputs(run: VerifiedChatRun) -> FrozenReplayInputs:
    """Return the frozen artefacts that the kernel is allowed to see."""
    return run.replay_inputs
