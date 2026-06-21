"""Supabase-backed verified-chat archive helpers."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from adapters.verified_chat.contracts import VerifiedChatRun
from truthkernel.canonical import canonical_text
from truthkernel.schemas import Decision
from truthkernel.schemas.models import StrictBaseModel

_HTTP_TIMEOUT_SECONDS = 30


class SupabaseVerifiedChatStoreError(RuntimeError):
    """Raised when a Supabase archive call fails."""


@dataclass(frozen=True, slots=True)
class SupabaseVerifiedChatStoreConfig:
    """Runtime configuration for the Supabase archive."""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    table_name: str = "verified_chat_runs"

    @property
    def ready(self) -> bool:
        """Return whether the archive has enough configuration to operate."""
        return bool(self.supabase_url and self.supabase_anon_key and self.table_name)


class VerifiedChatArchiveRecord(StrictBaseModel):
    """Latest verified-chat payload stored in Supabase."""

    request_hash: str
    run_hash: str
    decision: Decision
    cleaned_output: str
    run_json: str


RequestJson = Callable[[str, str, Mapping[str, str], object | None], object]


class SupabaseVerifiedChatStore:
    """Persist verified-chat runs in Supabase using the public project config."""

    def __init__(
        self,
        config: SupabaseVerifiedChatStoreConfig,
        request_json: RequestJson | None = None,
    ) -> None:
        self.config = config
        self._request_json = request_json or _request_json

    def save(self, run: VerifiedChatRun, authorization_token: str | None) -> None:
        """Mirror a frozen verified-chat run into Supabase."""
        if not self.config.ready or not authorization_token:
            return
        row = {
            "request_hash": run.request_hash,
            "run_hash": run.run_hash,
            "decision": run.replay_inputs.decision_bundle.decision.value,
            "cleaned_output": run.cleaned_output,
            "created_at": datetime.now(UTC).isoformat(),
            "run_json": canonical_text(run),
        }
        self._request_json(
            self._table_url({"on_conflict": "run_hash"}),
            "POST",
            self._headers(authorization_token, prefer="resolution=merge-duplicates,return=minimal"),
            [row],
        )

    def latest_record(self, authorization_token: str | None) -> VerifiedChatArchiveRecord | None:
        """Load the latest frozen verified-chat run from Supabase."""
        if not self.config.ready or not authorization_token:
            return None
        payload = self._request_json(
            self._table_url(
                {
                    "select": "request_hash,run_hash,decision,cleaned_output,run_json",
                    "order": "created_at.desc",
                    "limit": "1",
                }
            ),
            "GET",
            self._headers(authorization_token),
            None,
        )
        if isinstance(payload, list):
            if not payload:
                return None
            return VerifiedChatArchiveRecord.model_validate(payload[0])
        if isinstance(payload, dict) and payload:
            return VerifiedChatArchiveRecord.model_validate(payload)
        return None

    def _headers(self, authorization_token: str, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "apikey": self.config.supabase_anon_key,
            "Authorization": authorization_token,
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _table_url(self, query: Mapping[str, str] | None = None) -> str:
        base = (
            f"{self.config.supabase_url.rstrip('/')}/rest/v1/"
            f"{quote(self.config.table_name, safe='')}"
        )
        if not query:
            return base
        return f"{base}?{urlencode(dict(query))}"


def _request_json(
    url: str,
    method: str,
    headers: Mapping[str, str],
    body: object | None,
) -> object:
    data = (
        None if body is None else json.dumps(body, allow_nan=False, sort_keys=True).encode("utf-8")
    )
    request = Request(url, data=data, headers=dict(headers), method=method)
    try:
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except URLError as exc:  # pragma: no cover - surfaced to callers
        raise SupabaseVerifiedChatStoreError(f"Supabase request failed: {exc}") from exc

    if not raw:
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, (dict, list)):
        raise SupabaseVerifiedChatStoreError("Supabase returned a non-JSON object payload")
    return payload
