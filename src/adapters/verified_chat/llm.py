"""Live model adapters for verified chat.

These adapters deliberately live outside ``truthkernel``. They may call user
owned or hosted models, but they only return frozen ``ModelResponse`` artefacts
for the deterministic pipeline to consume.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Protocol
from urllib.error import URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from adapters.verified_chat.contracts import ModelResponse, ProviderKind, VerifiedChatRequest
from truthkernel.canonical import sha256_of

_HTTP_TIMEOUT_SECONDS = 60


class LLMAdapterError(RuntimeError):
    """Raised when a live model adapter cannot produce a response."""


class LLMAdapter(Protocol):
    """Adapter protocol for live text generation outside the kernel."""

    def generate(
        self,
        request: VerifiedChatRequest,
        *,
        credential_value: str | None = None,
    ) -> ModelResponse:
        """Generate a raw model response for a verified-chat request."""


class DeterministicStubLLMAdapter:
    """Offline development adapter used when no live local endpoint is configured."""

    def generate(
        self,
        request: VerifiedChatRequest,
        *,
        credential_value: str | None = None,
    ) -> ModelResponse:
        del credential_value
        raw_text = (
            "Truth AI received the prompt and froze this adapter response for "
            f"verification: {request.prompt_text.strip()}"
        )
        return model_response_for_text(request, raw_text)


class UserOwnedHTTPAdapter:
    """Call a user-owned model endpoint using common JSON response shapes."""

    def generate(
        self,
        request: VerifiedChatRequest,
        *,
        credential_value: str | None = None,
    ) -> ModelResponse:
        endpoint_url = request.selection.endpoint_url
        if endpoint_url is None:
            return DeterministicStubLLMAdapter().generate(request)

        body = {
            "model": request.selection.model_id,
            "prompt": request.prompt_text,
            "stream": False,
            "options": _settings_payload(request),
        }
        headers = {"Content-Type": "application/json"}
        if credential_value:
            headers["Authorization"] = f"Bearer {credential_value}"

        payload = _post_json(endpoint_url, body, headers)
        raw_text = _extract_text_payload(payload)
        return model_response_for_text(request, raw_text)


class GeminiHTTPAdapter:
    """Call Gemini's generateContent API outside the deterministic kernel."""

    def generate(
        self,
        request: VerifiedChatRequest,
        *,
        credential_value: str | None = None,
    ) -> ModelResponse:
        if not credential_value:
            raise LLMAdapterError("Gemini requests require a credential value")
        model_id = quote(request.selection.model_id, safe="")
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_id}:generateContent?key={quote(credential_value, safe='')}"
        )
        body = {
            "contents": [{"parts": [{"text": request.prompt_text}]}],
            "generationConfig": _settings_payload(request),
        }
        payload = _post_json(endpoint, body, {"Content-Type": "application/json"})
        raw_text = _extract_gemini_text(payload)
        return model_response_for_text(request, raw_text)


def adapter_for_provider(provider: ProviderKind) -> LLMAdapter:
    """Return the adapter implementation for a provider kind."""
    if provider is ProviderKind.GEMINI:
        return GeminiHTTPAdapter()
    if provider in {ProviderKind.LOCAL, ProviderKind.USER_OWNED}:
        return UserOwnedHTTPAdapter()
    raise LLMAdapterError(f"unsupported provider: {provider.value}")


def model_response_for_text(request: VerifiedChatRequest, raw_text: str) -> ModelResponse:
    """Build the frozen model response metadata for raw model text."""
    return ModelResponse(
        request_hash=request.request_hash,
        raw_text=raw_text,
        response_hash=sha256_of(
            {
                "content_type": "text/plain",
                "raw_text": raw_text,
                "request_hash": request.request_hash,
            }
        ),
        content_type="text/plain",
    )


def _settings_payload(request: VerifiedChatRequest) -> dict[str, int | float]:
    settings = request.selection.settings
    payload: dict[str, int | float] = {"temperature": _decimal_to_number(settings.temperature)}
    if settings.top_p is not None:
        payload["topP"] = _decimal_to_number(settings.top_p)
    if settings.max_output_tokens is not None:
        payload["maxOutputTokens"] = settings.max_output_tokens
        payload["num_predict"] = settings.max_output_tokens
    return payload


def _decimal_to_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _post_json(
    url: str,
    body: Mapping[str, object],
    headers: Mapping[str, str],
) -> Mapping[str, Any]:
    data = json.dumps(body, allow_nan=False, sort_keys=True).encode("utf-8")
    request = Request(url, data=data, headers=dict(headers), method="POST")
    try:
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            response_body = response.read().decode("utf-8")
    except URLError as exc:
        raise LLMAdapterError(f"model endpoint request failed: {exc}") from exc
    payload = json.loads(response_body) if response_body else {}
    if not isinstance(payload, dict):
        raise LLMAdapterError("model endpoint returned a non-object JSON payload")
    return payload


def _extract_text_payload(payload: Mapping[str, Any]) -> str:
    response = payload.get("response")
    if isinstance(response, str):
        return response
    text = payload.get("text")
    if isinstance(text, str):
        return text
    output = payload.get("output")
    if isinstance(output, str):
        return output
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return str(message["content"])
            if isinstance(first_choice.get("text"), str):
                return str(first_choice["text"])
    raise LLMAdapterError("model endpoint response did not contain text")


def _extract_gemini_text(payload: Mapping[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise LLMAdapterError("Gemini response did not contain candidates")
    first_candidate = candidates[0]
    if not isinstance(first_candidate, dict):
        raise LLMAdapterError("Gemini candidate was not an object")
    content = first_candidate.get("content")
    if not isinstance(content, dict):
        raise LLMAdapterError("Gemini candidate did not contain content")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise LLMAdapterError("Gemini content did not contain parts")
    texts = tuple(
        part["text"]
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )
    if not texts:
        raise LLMAdapterError("Gemini response did not contain text parts")
    return "\n".join(texts)


def normalise_endpoint(base_url: str, default_path: str) -> str:
    """Return a full model endpoint URL for a base URL and default path."""
    if base_url.endswith(default_path):
        return base_url
    return urljoin(base_url.rstrip("/") + "/", default_path.lstrip("/"))
