(() => {
  const DEFAULT_API_ROUTE = "/api/verified-chat";
  const storageKeyPrefix = "truthAiVerifiedChatLatest";
  const settingsKeyPrefix = "truthAiVerifiedChatSettings";

  function routeKey() {
    const parts = window.location.pathname.split("/").filter(Boolean);
    return parts[0] === "app" ? parts[1] || "overview" : "overview";
  }

  function isAssistantRoute() {
    const route = routeKey();
    return route === "chat" || route === "assistant";
  }

  function endpointRoot() {
    const settings = loadSettings();
    return settings.endpointUrl || defaultEndpoint();
  }

  function sessionScope() {
    const session = readSession();
    const scope =
      session?.user?.email ||
      session?.user?.id ||
      session?.access_token?.slice(0, 12) ||
      "anonymous";
    return String(scope).replace(/[^A-Za-z0-9_.-]/g, "_");
  }

  function scopedStorageKey() {
    return `${storageKeyPrefix}:${sessionScope()}`;
  }

  function scopedSettingsKey() {
    return `${settingsKeyPrefix}:${sessionScope()}`;
  }

  function readSession() {
    try {
      const raw = window.localStorage.getItem("truthai.supabase.session");
      if (!raw) return null;
      const session = JSON.parse(raw);
      return session && typeof session.access_token === "string" ? session : null;
    } catch {
      return null;
    }
  }

  function authHeaders() {
    const session = readSession();
    if (!session?.access_token) {
      return {};
    }
    return { Authorization: `Bearer ${session.access_token}` };
  }

  function defaultEndpoint() {
    const hostname = window.location && window.location.hostname ? String(window.location.hostname) : "";
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return "http://127.0.0.1:8010";
    }
    return DEFAULT_API_ROUTE;
  }

  function findText(selector, needle) {
    return Array.from(document.querySelectorAll(selector)).find((element) =>
      element.textContent.includes(needle)
    );
  }

  function installChatComposer() {
    if (!isAssistantRoute() || document.querySelector("[data-verified-chat-form]")) return;
    const placeholder = findText("span", "Ask anything");
    if (!placeholder || !placeholder.parentElement) return;
    const shell = placeholder.parentElement;
    shell.setAttribute("data-verified-chat-form", "");
    shell.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:12px;">
        <label style="display:flex;flex-direction:column;gap:6px;font-size:11px;font-family:'IBM Plex Mono',monospace;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">
          Provider
          <select data-verified-chat-provider style="height:38px;border:1px solid #d6e0ee;border-radius:9px;background:#fff;padding:0 10px;font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:13px;color:#0f172a;">
            <option value="local">Local</option>
            <option value="gemini">Gemini</option>
            <option value="user-owned">Custom endpoint</option>
          </select>
        </label>
        <label style="display:flex;flex-direction:column;gap:6px;font-size:11px;font-family:'IBM Plex Mono',monospace;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">
          Model
          <input data-verified-chat-model type="text" placeholder="truth-ai-local-adapter" style="height:38px;border:1px solid #d6e0ee;border-radius:9px;background:#fff;padding:0 10px;font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:13px;color:#0f172a;" />
        </label>
        <label style="display:flex;flex-direction:column;gap:6px;font-size:11px;font-family:'IBM Plex Mono',monospace;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">
          API key
          <input data-verified-chat-key type="password" placeholder="Optional" style="height:38px;border:1px solid #d6e0ee;border-radius:9px;background:#fff;padding:0 10px;font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:13px;color:#0f172a;" />
        </label>
        <label style="display:flex;flex-direction:column;gap:6px;font-size:11px;font-family:'IBM Plex Mono',monospace;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">
          Endpoint
          <input data-verified-chat-endpoint type="url" placeholder="http://127.0.0.1:8010" style="height:38px;border:1px solid #d6e0ee;border-radius:9px;background:#fff;padding:0 10px;font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:13px;color:#0f172a;" />
        </label>
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;flex-wrap:wrap;">
        <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:#475569;">
          <input data-verified-chat-remember type="checkbox" />
          Remember settings on this device
        </label>
        <button type="button" data-verified-chat-save title="Save settings" style="height:38px;border:1px solid #d6e0ee;border-radius:9px;background:#fff;color:#0f172a;padding:0 14px;font-size:13px;font-weight:600;cursor:pointer;">Save</button>
      </div>
      <textarea data-verified-chat-input rows="3" placeholder="Ask anything - responses are verified before they are shown..." style="flex:1;min-height:72px;resize:vertical;background:transparent;border:0;outline:0;font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:14px;line-height:1.45;color:#0f172a;padding:4px 2px;"></textarea>
      <button type="button" data-verified-chat-submit title="Run through Truth AI" style="width:42px;height:42px;border-radius:10px;border:none;background:#2563eb;color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;box-shadow:0 1px 2px rgba(37,99,235,0.4);">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
      </button>
    `;
    const panel = document.createElement("div");
    panel.setAttribute("data-verified-chat-status", "");
    panel.style.cssText =
      "margin-top:10px;border:1px solid #e0e7f0;border-radius:11px;background:#f8fafd;padding:12px 14px;font-size:13px;line-height:1.5;color:#64748b;";
    panel.textContent = "Adapter ready at " + endpointRoot();
    shell.parentElement.appendChild(panel);
    hydrateSettings(shell);
  }

  let delegatedSubmitInstalled = false;

  function installDelegatedSubmit() {
    if (delegatedSubmitInstalled) return;
    delegatedSubmitInstalled = true;
    document.addEventListener("click", (event) => {
      const submit = event.target.closest("[data-verified-chat-submit]");
      if (!submit) return;
      const shell = submit.closest("[data-verified-chat-form]");
      const panel = document.querySelector("[data-verified-chat-status]");
      if (shell && panel) return submitPrompt(shell, panel);
      return;
    });
    document.addEventListener("click", (event) => {
      const save = event.target.closest("[data-verified-chat-save]");
      if (!save) return;
      const shell = save.closest("[data-verified-chat-form]");
      if (shell) persistSettings(readSettings(shell));
    });
  }

  async function submitPrompt(shell, panel) {
    const input = shell.querySelector("[data-verified-chat-input]");
    const submit = shell.querySelector("[data-verified-chat-submit]");
    const prompt = input.value.trim();
    if (!prompt) {
      panel.textContent = "Enter a prompt before running the adapter.";
      return;
    }
    submit.disabled = true;
    submit.style.opacity = "0.65";
    panel.textContent = "Calling adapter and freezing replay artefacts...";
    try {
      const settings = readSettings(shell);
      const response = await fetch(runUrl(settings.endpointUrl || defaultEndpoint()), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          prompt_text: prompt,
          provider: settings.provider,
          model_id: settings.modelId || "truth-ai-local-adapter",
          credential_value: settings.apiKey || undefined,
          endpoint_url: settings.endpointUrl || undefined,
          settings: { temperature: "0", top_p: "1", max_output_tokens: 1024 },
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "adapter request failed");
      window.localStorage.setItem(scopedStorageKey(), JSON.stringify(payload));
      panel.innerHTML = resultMarkup(payload);
    } catch (error) {
      panel.textContent = "Adapter unavailable: " + error.message;
    } finally {
      submit.disabled = false;
      submit.style.opacity = "1";
    }
  }

  function hydrateSettings(shell) {
    const settings = loadSettings();
    const provider = shell.querySelector("[data-verified-chat-provider]");
    const model = shell.querySelector("[data-verified-chat-model]");
    const key = shell.querySelector("[data-verified-chat-key]");
    const endpointInput = shell.querySelector("[data-verified-chat-endpoint]");
    const remember = shell.querySelector("[data-verified-chat-remember]");
    if (provider) provider.value = settings.provider;
    if (model) model.value = settings.modelId;
    if (key) key.value = settings.apiKey;
    if (endpointInput) endpointInput.value = settings.endpointUrl;
    if (remember) remember.checked = settings.remember;
  }

  function readSettings(shell) {
    const provider = shell.querySelector("[data-verified-chat-provider]");
    const model = shell.querySelector("[data-verified-chat-model]");
    const key = shell.querySelector("[data-verified-chat-key]");
    const endpointInput = shell.querySelector("[data-verified-chat-endpoint]");
    const remember = shell.querySelector("[data-verified-chat-remember]");
    return {
      provider: provider ? provider.value : "local",
      modelId: model ? model.value.trim() : "truth-ai-local-adapter",
      apiKey: key ? key.value.trim() : "",
      endpointUrl: endpointInput ? endpointInput.value.trim() : "",
      remember: Boolean(remember && remember.checked),
    };
  }

  function loadSettings() {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(scopedSettingsKey()) || "null");
      if (!parsed || typeof parsed !== "object") throw new Error("missing settings");
      return {
        provider: parsed.provider || "local",
        modelId: parsed.modelId || "truth-ai-local-adapter",
        apiKey: parsed.apiKey || "",
        endpointUrl: parsed.endpointUrl || defaultEndpoint(),
        remember: Boolean(parsed.remember),
      };
    } catch {
      return {
        provider: "local",
        modelId: "truth-ai-local-adapter",
        apiKey: "",
        endpointUrl: defaultEndpoint(),
        remember: false,
      };
    }
  }

  function persistSettings(settings) {
    if (!settings.remember) {
      window.localStorage.removeItem(scopedSettingsKey());
      return;
    }
    window.localStorage.setItem(
      scopedSettingsKey(),
      JSON.stringify({
        provider: settings.provider,
        modelId: settings.modelId,
        apiKey: settings.apiKey,
        endpointUrl: settings.endpointUrl,
        remember: settings.remember,
      }),
    );
    const panel = document.querySelector("[data-verified-chat-status]");
    if (panel) panel.textContent = "Settings saved for " + settings.provider + " at " + endpointRoot();
  }

  function installOutputPanel() {
    if (routeKey() !== "truth-output" || document.querySelector("[data-live-output-panel]")) {
      return;
    }
    const screen = document.querySelector("[data-verified-output-screen]");
    const frame = screen ? screen.querySelector(".ta-frame") : null;
    if (!frame) return;
    const panel = document.createElement("div");
    panel.setAttribute("data-live-output-panel", "");
    panel.style.cssText =
      "border-bottom:1px solid #e6ecf4;background:#f8fafd;padding:18px 22px;color:#0f172a;";
    panel.textContent = "Loading latest verified output...";
    frame.prepend(panel);
    loadLatest(panel);
  }

  async function loadLatest(panel) {
    try {
      const response = await fetch(latestUrl(endpointRoot()), {
        cache: "no-store",
        headers: { ...authHeaders() },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "latest output unavailable");
      window.localStorage.setItem(scopedStorageKey(), JSON.stringify(payload));
      panel.innerHTML = resultMarkup(payload);
    } catch {
      const cached = window.localStorage.getItem(scopedStorageKey());
      panel.innerHTML = cached
        ? resultMarkup(JSON.parse(cached))
        : "<strong>No verified output yet.</strong> Run a prompt from the Assistant screen.";
    }
  }

  function resultMarkup(payload) {
    const output = escapeHtml(payload.cleaned_output || "");
    const decision = escapeHtml(payload.decision || "review");
    const runHash = escapeHtml((payload.run_hash || "").slice(0, 16));
    return `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;">
        <strong style="font-size:14px;color:#0f172a;">Truth AI output</strong>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#047857;background:#ecfdf5;border:1px solid #c7ead7;border-radius:7px;padding:4px 9px;">${decision} · ${runHash}</span>
      </div>
      <div style="margin-top:10px;white-space:pre-wrap;font-size:14px;line-height:1.6;color:#334155;">${output}</div>
      <a href="/app/truth-output/" style="display:inline-flex;margin-top:10px;font-size:12px;font-weight:600;color:#2563eb;">Open verification result</a>
    `;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function runUrl(base) {
    const trimmed = base.replace(/\/$/, "");
    return trimmed.startsWith("/")
      ? `${trimmed}/run`
      : `${trimmed}/verified-chat/run`;
  }

  function latestUrl(base) {
    const trimmed = base.replace(/\/$/, "");
    return trimmed.startsWith("/")
      ? `${trimmed}/latest`
      : `${trimmed}/verified-chat/latest`;
  }

  let tries = 0;
  const timer = setInterval(() => {
    tries += 1;
    installDelegatedSubmit();
    installChatComposer();
    installOutputPanel();
    if (tries > 80) clearInterval(timer);
  }, 75);
  document.addEventListener("DOMContentLoaded", () => {
    installDelegatedSubmit();
    installChatComposer();
    installOutputPanel();
  });
})();
