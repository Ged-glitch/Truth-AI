(() => {
  const LIBRARY_URL = "/standards/library/sample-standard-library.json";
  const EVALUATORS_URL = "/standards/evaluators/sample-evaluator-library.json";
  const IMPORTS_KEY = "truthAiStandardImports";

  function routeKey() {
    const parts = window.location.pathname.split("/").filter(Boolean);
    return parts[0] === "app" ? parts[1] || "overview" : "overview";
  }

  function installStandardsLibrary() {
    if (routeKey() !== "rulepacks" || document.querySelector("[data-standards-library]")) {
      return;
    }

    const placeholder = document.querySelector("[data-route-placeholder]");
    if (!placeholder) return;
    placeholder.style.display = "";
    placeholder.innerHTML = layoutMarkup();
    loadLibrary();
    loadEvaluators();
    renderImports();
  }

  async function loadLibrary() {
    const host = document.querySelector("[data-standards-sources]");
    if (!host) return;
    try {
      const response = await fetch(LIBRARY_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const library = await response.json();
      host.innerHTML = library.sources.map(sourceCard).join("");
      const count = document.querySelector("[data-standards-count]");
      if (count) count.textContent = `${library.sources.length} sources`;
    } catch (error) {
      host.innerHTML = `<div style="padding:18px;color:#b91c1c;background:#fef2f2;border:1px solid #fecaca;border-radius:10px;">Standards library unavailable: ${escapeHtml(error.message)}</div>`;
    }
  }

  async function loadEvaluators() {
    const enginesHost = document.querySelector("[data-evaluator-engines]");
    const benchmarksHost = document.querySelector("[data-evaluator-benchmarks]");
    if (!enginesHost || !benchmarksHost) return;
    try {
      const response = await fetch(EVALUATORS_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const library = await response.json();
      enginesHost.innerHTML = library.engines.map(evaluatorCard).join("");
      benchmarksHost.innerHTML = library.benchmarks.map(benchmarkCard).join("");
    } catch (error) {
      enginesHost.innerHTML = `<div style="padding:14px;color:#b91c1c;background:#fef2f2;border:1px solid #fecaca;border-radius:10px;">Evaluator library unavailable: ${escapeHtml(error.message)}</div>`;
      benchmarksHost.innerHTML = "";
    }
  }

  function layoutMarkup() {
    return `
      <div data-standards-library>
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#64748b;background:#fff;border:1px solid #dde5ef;border-radius:7px;padding:4px 10px;">Standards library</span>
          <span style="height:1px;flex:1;background:#dde5ef;"></span>
          <span data-standards-count style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#94a3b8;">loading</span>
        </div>
        <div class="ta-frame" style="border:1px solid #dde5ef;border-radius:16px;overflow:hidden;box-shadow:0 1px 2px rgba(15,23,42,0.05),0 30px 60px -34px rgba(15,23,42,0.32);background:#fff;">
          <div style="padding:22px 24px;background:#f8fafd;border-bottom:1px solid #e6ecf4;display:grid;grid-template-columns:1.2fr 0.8fr;gap:20px;align-items:start;">
            <div>
              <h3 style="margin:0;font-size:18px;font-weight:700;color:#0f172a;">Load standards as governed evidence</h3>
              <p style="margin:8px 0 0;font-size:13.5px;line-height:1.55;color:#64748b;">Public sources can be loaded from official URLs. Paid standards stay as links or user uploads until the licence is confirmed.</p>
            </div>
            <div style="background:#fff;border:1px solid #e6ecf4;border-radius:12px;padding:14px;">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#94a3b8;">Import source</div>
              <div style="display:grid;gap:8px;margin-top:10px;">
                <input data-standard-title placeholder="Standard title" style="height:36px;border:1px solid #d6e0ee;border-radius:8px;padding:0 10px;font-size:13px;color:#0f172a;" />
                <input data-standard-publisher placeholder="Publisher, e.g. BSI" style="height:36px;border:1px solid #d6e0ee;border-radius:8px;padding:0 10px;font-size:13px;color:#0f172a;" />
                <input data-standard-url placeholder="Official URL or shop link" style="height:36px;border:1px solid #d6e0ee;border-radius:8px;padding:0 10px;font-size:13px;color:#0f172a;" />
                <select data-standard-access style="height:36px;border:1px solid #d6e0ee;border-radius:8px;padding:0 10px;font-size:13px;color:#0f172a;background:#fff;">
                  <option value="paid">Paid/licensed</option>
                  <option value="public">Public</option>
                  <option value="user-upload">User upload</option>
                  <option value="institutional">Institutional</option>
                </select>
                <button data-standard-add type="button" style="height:38px;border:none;border-radius:9px;background:#2563eb;color:#fff;font-size:13px;font-weight:700;cursor:pointer;">Add source</button>
              </div>
            </div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 0.8fr;gap:0;">
            <div style="padding:22px 24px;border-right:1px solid #e6ecf4;">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#94a3b8;">Official source catalogue</div>
              <div data-standards-sources style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:12px;"></div>
            </div>
            <div style="padding:22px 24px;background:#fbfdff;">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#94a3b8;">Registered imports</div>
              <div data-standard-imports style="display:grid;gap:10px;margin-top:12px;"></div>
            </div>
          </div>
          <div style="border-top:1px solid #e6ecf4;background:#f8fafd;padding:22px 24px;">
            <div style="display:flex;align-items:start;justify-content:space-between;gap:18px;">
              <div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#94a3b8;">Advisory context evaluators</div>
                <h3 style="margin:7px 0 0;font-size:16px;font-weight:700;color:#0f172a;">Score context quality after standards evidence is retrieved</h3>
              </div>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:7px;padding:4px 9px;text-transform:uppercase;">Advisory only</span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 0.8fr;gap:16px;margin-top:16px;">
              <div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#94a3b8;">Runtime engines</div>
                <div data-evaluator-engines style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:10px;"></div>
              </div>
              <div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#94a3b8;">Benchmark packs</div>
                <div data-evaluator-benchmarks style="display:grid;gap:10px;margin-top:10px;"></div>
              </div>
            </div>
          </div>
        </div>
      </div>`;
  }

  function sourceCard(source) {
    const access = String(source.access || "public");
    const badge = access === "public" ? ["#047857", "#ecfdf5", "#c7ead7"] : ["#92400e", "#fffbeb", "#fde68a"];
    const clauseCount = Array.isArray(source.clauses) ? source.clauses.length : 0;
    const ingestState =
      clauseCount > 0
        ? `${clauseCount} sample clause${clauseCount === 1 ? "" : "s"} - evidence pack ready`
        : access === "public"
          ? "Link registered - authorised text needed"
          : "Upload required before ingestion";
    return `
      <a href="${escapeHtml(source.source_url)}" target="_blank" rel="noopener" style="display:block;border:1px solid #e6ecf4;border-radius:12px;padding:14px;background:#fff;color:inherit;text-decoration:none;">
        <div style="display:flex;justify-content:space-between;gap:10px;align-items:start;">
          <div>
            <div style="font-size:14px;font-weight:700;color:#0f172a;">${escapeHtml(source.title)}</div>
            <div style="margin-top:3px;font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:#94a3b8;">${escapeHtml(source.publisher)} · ${escapeHtml(source.domain)}</div>
          </div>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:${badge[0]};background:${badge[1]};border:1px solid ${badge[2]};border-radius:7px;padding:3px 7px;text-transform:uppercase;">${escapeHtml(access)}</span>
        </div>
        <p style="margin:10px 0 0;font-size:12.5px;line-height:1.45;color:#64748b;">${escapeHtml(source.retrieval_policy)}</p>
        <div style="margin-top:10px;font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:#2563eb;background:#eef4ff;border:1px solid #dbe7ff;border-radius:7px;padding:5px 8px;">${escapeHtml(ingestState)}</div>
      </a>`;
  }

  function evaluatorCard(engine) {
    const metrics = (engine.metrics || [])
      .map((metric) => `<span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#475569;background:#f8fafd;border:1px solid #eef2f7;border-radius:6px;padding:3px 7px;">${escapeHtml(metric.label)}</span>`)
      .join("");
    return `
      <a href="${escapeHtml(engine.source_url)}" target="_blank" rel="noopener" style="display:block;border:1px solid #e6ecf4;border-radius:12px;padding:14px;background:#fff;color:inherit;text-decoration:none;">
        <div style="display:flex;justify-content:space-between;gap:10px;align-items:start;">
          <div>
            <div style="font-size:14px;font-weight:700;color:#0f172a;">${escapeHtml(engine.name)}</div>
            <div style="margin-top:3px;font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:#94a3b8;">${escapeHtml(engine.package_name)} - ${escapeHtml(engine.access)}</div>
          </div>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:7px;padding:3px 7px;">non-det</span>
        </div>
        <p style="margin:10px 0 0;font-size:12.5px;line-height:1.45;color:#64748b;">${escapeHtml(engine.role)}</p>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;">${metrics}</div>
      </a>`;
  }

  function benchmarkCard(dataset) {
    return `
      <a href="${escapeHtml(dataset.source_url)}" target="_blank" rel="noopener" style="display:block;border:1px solid #e6ecf4;border-radius:11px;background:#fff;padding:13px;color:inherit;text-decoration:none;">
        <div style="display:flex;justify-content:space-between;gap:10px;">
          <strong style="font-size:13.5px;color:#0f172a;">${escapeHtml(dataset.name)}</strong>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#64748b;text-transform:uppercase;">benchmark</span>
        </div>
        <p style="margin:8px 0 0;font-size:12px;line-height:1.45;color:#64748b;">${escapeHtml(dataset.use_case)}</p>
      </a>`;
  }

  function renderImports() {
    const host = document.querySelector("[data-standard-imports]");
    if (!host) return;
    const imports = loadImports();
    if (imports.length === 0) {
      host.innerHTML = `<div style="padding:14px;border:1px dashed #cbd5e1;border-radius:10px;color:#64748b;font-size:13px;line-height:1.45;">No user standards registered yet.</div>`;
      return;
    }
    host.innerHTML = imports.map(importCard).join("");
  }

  function importCard(item) {
    return `
      <div style="border:1px solid #e6ecf4;border-radius:11px;background:#fff;padding:13px;">
        <div style="display:flex;justify-content:space-between;gap:10px;">
          <strong style="font-size:13.5px;color:#0f172a;">${escapeHtml(item.title)}</strong>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#64748b;text-transform:uppercase;">${escapeHtml(item.access)}</span>
        </div>
        <div style="margin-top:5px;font-size:12px;color:#64748b;">${escapeHtml(item.publisher)}</div>
        <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener" style="display:block;margin-top:8px;font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:#2563eb;word-break:break-all;">${escapeHtml(item.url)}</a>
      </div>`;
  }

  function loadImports() {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(IMPORTS_KEY) || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function saveImports(imports) {
    window.localStorage.setItem(IMPORTS_KEY, JSON.stringify(imports));
  }

  function addImport() {
    const title = value("[data-standard-title]");
    const publisher = value("[data-standard-publisher]");
    const url = value("[data-standard-url]");
    const access = value("[data-standard-access]") || "paid";
    if (!title || !publisher || !url) return;
    const imports = loadImports();
    imports.unshift({ access, publisher, title, url });
    saveImports(imports.slice(0, 20));
    renderImports();
  }

  function value(selector) {
    const element = document.querySelector(selector);
    return element && "value" in element ? element.value.trim() : "";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  let delegated = false;
  function installDelegation() {
    if (delegated) return;
    delegated = true;
    document.addEventListener("click", (event) => {
      if (event.target.closest("[data-standard-add]")) addImport();
    });
  }

  let tries = 0;
  const timer = setInterval(() => {
    tries += 1;
    installDelegation();
    installStandardsLibrary();
    if (tries > 80) clearInterval(timer);
  }, 75);

  document.addEventListener("DOMContentLoaded", () => {
    installDelegation();
    installStandardsLibrary();
  });
})();
