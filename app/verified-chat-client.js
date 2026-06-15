(() => {
  const DEFAULT_ENDPOINT = "http://127.0.0.1:8010";
  const storageKey = "truthAiVerifiedChatLatest";

  function routeKey() {
    const parts = window.location.pathname.split("/").filter(Boolean);
    return parts[0] === "app" ? parts[1] || "overview" : "overview";
  }

  function endpoint() {
    return window.localStorage.getItem("truthAiAdapterEndpoint") || DEFAULT_ENDPOINT;
  }

  function findText(selector, needle) {
    return Array.from(document.querySelectorAll(selector)).find((element) =>
      element.textContent.includes(needle)
    );
  }

  function installChatComposer() {
    if (routeKey() !== "chat" || document.querySelector("[data-verified-chat-form]")) return;
    const placeholder = findText("span", "Ask anything");
    if (!placeholder || !placeholder.parentElement) return;
    const shell = placeholder.parentElement;
    shell.setAttribute("data-verified-chat-form", "");
    shell.innerHTML = `
      <textarea data-verified-chat-input rows="3" placeholder="Ask anything - responses are verified before they are shown..." style="flex:1;min-height:72px;resize:vertical;background:transparent;border:0;outline:0;font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:14px;line-height:1.45;color:#0f172a;padding:4px 2px;"></textarea>
      <button type="button" data-verified-chat-submit title="Run through Truth AI" style="width:42px;height:42px;border-radius:10px;border:none;background:#2563eb;color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;box-shadow:0 1px 2px rgba(37,99,235,0.4);">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
      </button>
    `;
    const panel = document.createElement("div");
    panel.setAttribute("data-verified-chat-status", "");
    panel.style.cssText =
      "margin-top:10px;border:1px solid #e0e7f0;border-radius:11px;background:#f8fafd;padding:12px 14px;font-size:13px;line-height:1.5;color:#64748b;";
    panel.textContent = "Adapter ready at " + endpoint();
    shell.parentElement.appendChild(panel);
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
      if (shell && panel) submitPrompt(shell, panel);
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
      const response = await fetch(endpoint() + "/verified-chat/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt_text: prompt,
          provider: "local",
          model_id: "truth-ai-local-adapter",
          settings: { temperature: "0", top_p: "1", max_output_tokens: 1024 },
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "adapter request failed");
      window.localStorage.setItem(storageKey, JSON.stringify(payload));
      panel.innerHTML = resultMarkup(payload);
    } catch (error) {
      panel.textContent = "Adapter unavailable: " + error.message;
    } finally {
      submit.disabled = false;
      submit.style.opacity = "1";
    }
  }

  function installOutputPanel() {
    if (routeKey() !== "truth-output" || document.querySelector("[data-live-output-panel]")) {
      return;
    }
    const marker = findText("span", "05 · Verification Result");
    const screen = marker ? marker.closest("[data-screen-label]") : null;
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
      const response = await fetch(endpoint() + "/verified-chat/latest", { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "latest output unavailable");
      window.localStorage.setItem(storageKey, JSON.stringify(payload));
      panel.innerHTML = resultMarkup(payload);
    } catch {
      const cached = window.localStorage.getItem(storageKey);
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
