"""Hash-keyed storage helpers for verified-chat artefacts."""

from __future__ import annotations

from pathlib import Path

from adapters.extract import ExtractedPackBundle
from adapters.verified_chat.contracts import (
    ModelResponse,
    VerifiedChatRequest,
    VerifiedChatRun,
    verified_chat_run_path,
)
from truthkernel.canonical import canonical_text


def verified_chat_request_path(root: Path, request: VerifiedChatRequest) -> Path:
    """Return the canonical file path for a verified-chat request."""
    return root / f"{request.request_hash}.request.json"


def verified_chat_response_path(root: Path, request: VerifiedChatRequest) -> Path:
    """Return the canonical file path for a verified-chat raw response."""
    return root / f"{request.request_hash}.response.json"


def verified_chat_extracted_pack_path(root: Path, request: VerifiedChatRequest) -> Path:
    """Return the canonical file path for a verified-chat extraction bundle."""
    return root / f"{request.request_hash}.extracted-pack.json"


def verified_chat_cleaned_output_path(root: Path, request: VerifiedChatRequest) -> Path:
    """Return the canonical file path for a verified-chat cleaned output."""
    return root / f"{request.request_hash}.cleaned.txt"


def save_verified_chat_request(request: VerifiedChatRequest, path: Path) -> None:
    """Write a canonical verified-chat request to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(request) + "\n", encoding="utf-8")


def load_verified_chat_request(path: Path) -> VerifiedChatRequest:
    """Load a canonical verified-chat request from disk."""
    return VerifiedChatRequest.model_validate_json(path.read_text(encoding="utf-8"))


def save_verified_chat_response(response: ModelResponse, path: Path) -> None:
    """Write a canonical verified-chat raw response to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(response) + "\n", encoding="utf-8")


def load_verified_chat_response(path: Path) -> ModelResponse:
    """Load a canonical verified-chat raw response from disk."""
    return ModelResponse.model_validate_json(path.read_text(encoding="utf-8"))


def save_verified_chat_extracted_pack(bundle: ExtractedPackBundle, path: Path) -> None:
    """Write a canonical verified-chat extracted pack to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(bundle) + "\n", encoding="utf-8")


def load_verified_chat_extracted_pack(path: Path) -> ExtractedPackBundle:
    """Load a canonical verified-chat extracted pack from disk."""
    return ExtractedPackBundle.model_validate_json(path.read_text(encoding="utf-8"))


def save_verified_chat_cleaned_output(cleaned_output: str, path: Path) -> None:
    """Write the cleaned assistant output to disk without reformatting it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cleaned_output, encoding="utf-8")


def load_verified_chat_cleaned_output(path: Path) -> str:
    """Load the cleaned assistant output exactly as stored."""
    return path.read_text(encoding="utf-8")


def save_verified_chat_run_at_root(root: Path, run: VerifiedChatRun) -> Path:
    """Write a canonical verified-chat bundle to its hash-keyed path."""
    path = verified_chat_run_path(root, run.request)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(run) + "\n", encoding="utf-8")
    return path


def load_verified_chat_run_at_root(root: Path, request: VerifiedChatRequest) -> VerifiedChatRun:
    """Load a verified-chat bundle from its hash-keyed root path."""
    return VerifiedChatRun.model_validate_json(
        verified_chat_run_path(root, request).read_text(encoding="utf-8")
    )
