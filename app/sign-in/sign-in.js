const SESSION_STORAGE_KEY = "truthai.supabase.session";
const state = {
  config: null,
  session: loadSession(),
};

const elements = {};

boot().catch((error) => {
  console.error(error);
  setStatus(error.message || String(error), "error");
});

async function boot() {
  bindElements();
  bindEvents();
  renderSession();

  const config = await loadConfig();
  state.config = config;

  if (config.ready) {
    setStatus("Supabase configuration loaded.", "success");
  } else {
    setStatus(
      "Set SUPABASE_URL and SUPABASE_ANON_KEY in .env.local or Vercel to enable login.",
      "error",
    );
  }

  await restoreSession();
}

function bindElements() {
  elements.form = document.getElementById("auth-form");
  elements.email = document.getElementById("email");
  elements.password = document.getElementById("password");
  elements.signup = document.getElementById("signup-button");
  elements.signout = document.getElementById("signout-button");
  elements.status = document.getElementById("status");
  elements.configBanner = document.getElementById("config-banner");
  elements.sessionUser = document.getElementById("session-user");
  elements.sessionToken = document.getElementById("session-token");
}

function bindEvents() {
  elements.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await runAction(performSignIn);
  });
  elements.signup.addEventListener("click", async () => {
    await runAction(performSignUp);
  });
  elements.signout.addEventListener("click", () => {
    clearSession();
    renderSession();
    setStatus("Signed out locally.", "success");
  });
}

async function loadConfig() {
  const response = await fetch("/api/public-config", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Could not load public config: HTTP ${response.status}`);
  }
  const payload = await response.json();
  const config = {
    ready: Boolean(payload.ready),
    supabaseUrl: String(payload.supabaseUrl || ""),
    supabaseAnonKey: String(payload.supabaseAnonKey || ""),
  };
  elements.configBanner.textContent = config.ready
    ? "Supabase is configured for this deployment."
    : "Supabase is not configured yet. Add the env vars first.";
  return config;
}

async function performSignIn() {
  const config = requireConfig();
  const email = elements.email.value.trim();
  const password = elements.password.value;
  if (!email || !password) {
    setStatus("Enter both email and password.", "error");
    return;
  }

  setStatus("Signing in...", "");
  const payload = await postAuth(
    config,
    "/auth/v1/token?grant_type=password",
    { email, password },
  );
  saveSession(payload);
  renderSession();
  setStatus("Signed in successfully.", "success");
  window.location.assign(resolveReturnPath());
}

async function performSignUp() {
  const config = requireConfig();
  const email = elements.email.value.trim();
  const password = elements.password.value;
  if (!email || !password) {
    setStatus("Enter both email and password before creating an account.", "error");
    return;
  }

  setStatus("Creating account...", "");
  const payload = await postAuth(
    config,
    "/auth/v1/signup",
    buildSignUpBody(email, password),
  );
  saveSession(payload);
  renderSession();
  if (state.session?.access_token) {
    setStatus("Account created and signed in.", "success");
    window.location.assign(resolveReturnPath());
    return;
  }
  setStatus(
    "Account created. Check your email to confirm the account, then sign in.",
    "success",
  );
}

async function runAction(action) {
  try {
    await action();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    setStatus(message, "error");
  }
}

async function restoreSession() {
  const session = state.session;
  if (!session || !session.access_token || !state.config?.ready) {
    renderSession();
    return;
  }

  try {
    const response = await fetch(`${state.config.supabaseUrl}/auth/v1/user`, {
      headers: authHeaders(state.config.supabaseAnonKey, session.access_token),
    });
    if (!response.ok) {
      clearSession();
      renderSession();
      return;
    }
    const user = await response.json();
    state.session = { ...session, user };
    persistSession();
    renderSession();
    setStatus("Session restored from local storage.", "success");
  } catch (error) {
    console.error(error);
    clearSession();
    renderSession();
  }
}

async function postAuth(config, path, body) {
  const response = await fetch(`${config.supabaseUrl}${path}`, {
    method: "POST",
    headers: authHeaders(config.supabaseAnonKey),
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(resolveAuthError(payload, response.status));
  }
  return payload;
}

function authHeaders(anonKey, token) {
  const headers = {
    apikey: anonKey,
    Authorization: `Bearer ${token || anonKey}`,
    "Content-Type": "application/json",
  };
  return headers;
}

function resolveAuthError(payload, status) {
  const message =
    payload?.msg ||
    payload?.message ||
    payload?.error_description ||
    payload?.error ||
    `HTTP ${status}`;
  return String(message);
}

function requireConfig() {
  if (!state.config?.ready) {
    throw new Error("Supabase is not configured yet.");
  }
  return state.config;
}

function saveSession(payload) {
  const sessionPayload = payload?.session || payload;
  const session = {
    access_token: sessionPayload?.access_token || null,
    refresh_token: sessionPayload?.refresh_token || null,
    expires_at: sessionPayload?.expires_at || null,
    user: payload?.user || sessionPayload?.user || null,
  };
  state.session = session;
  persistSession();
}

function persistSession() {
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(state.session));
}

function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    console.error(error);
    return null;
  }
}

function clearSession() {
  state.session = null;
  localStorage.removeItem(SESSION_STORAGE_KEY);
}

function renderSession() {
  const session = state.session;
  const user = session?.user?.email || session?.user?.id || "Not signed in";
  const token = session?.access_token ? `${session.access_token.slice(0, 18)}…` : "None";
  elements.sessionUser.textContent = user;
  elements.sessionToken.textContent = token;
}

function setStatus(message, tone) {
  elements.status.textContent = message;
  elements.status.dataset.tone = tone || "";
}

function resolveReturnPath() {
  const params = new URLSearchParams(window.location.search);
  const returnTo = params.get("return");
  if (typeof returnTo === "string" && returnTo.startsWith("/app/")) {
    return returnTo;
  }
  return "/app/overview";
}

function resolveEmailRedirectTo() {
  return `${window.location.origin}/app/sign-in?confirmed=1`;
}

function buildSignUpBody(email, password) {
  return {
    email,
    password,
    options: {
      emailRedirectTo: resolveEmailRedirectTo(),
    },
  };
}
