from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from pathlib import Path

from adapters.verified_chat import (
    ProviderKind,
    VerifiedChatRunRequest,
    VerifiedChatService,
    VerifiedChatServiceConfig,
    create_verified_chat_http_server,
)
from truthkernel.schemas import Decision

_RULEPACK_PATH = (
    Path(__file__).resolve().parents[1] / "rulepacks" / "strict-default" / "rulepack.json"
)


def test_verified_chat_service_runs_model_adapter_and_persists_outputs(tmp_path: Path) -> None:
    service = VerifiedChatService(
        VerifiedChatServiceConfig(store_root=tmp_path, rulepack_path=_RULEPACK_PATH)
    )

    response = service.run(
        VerifiedChatRunRequest(
            prompt_text="Explain why frozen replay artefacts matter.",
            provider=ProviderKind.LOCAL,
            model_id="truth-ai-local-adapter",
            credential_ref="local-secret",
            credential_value="do-not-persist",
        )
    )

    assert response.decision is Decision.ACCEPT
    assert "frozen" in response.cleaned_output
    assert response.artefacts["run"].endswith(f"{response.request_hash}.json")
    assert Path(response.artefacts["request"]).exists()
    assert Path(response.artefacts["response"]).exists()
    assert Path(response.artefacts["extracted_pack"]).exists()
    assert Path(response.artefacts["cleaned_output"]).exists()
    assert service.latest().run_hash == response.run_hash

    request_payload = Path(response.artefacts["request"]).read_text(encoding="utf-8")
    run_payload = Path(response.artefacts["run"]).read_text(encoding="utf-8")
    assert "do-not-persist" not in request_payload
    assert "do-not-persist" not in run_payload
    assert "local-secret" in request_payload


def test_verified_chat_http_server_accepts_prompt_and_returns_latest(tmp_path: Path) -> None:
    server = create_verified_chat_http_server(
        VerifiedChatServiceConfig(
            store_root=tmp_path,
            rulepack_path=_RULEPACK_PATH,
            host="127.0.0.1",
            port=0,
        )
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        payload = json.dumps(
            {
                "prompt_text": "Summarise deterministic verification.",
                "provider": "local",
                "model_id": "truth-ai-local-adapter",
            }
        )
        connection = HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "POST",
            "/verified-chat/run",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["decision"] == "accept"
        assert body["cleaned_output"].startswith("Truth AI received the prompt")

        connection.request("GET", "/verified-chat/latest")
        latest_response = connection.getresponse()
        latest_body = json.loads(latest_response.read().decode("utf-8"))
        assert latest_response.status == 200
        assert latest_body["run_hash"] == body["run_hash"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
