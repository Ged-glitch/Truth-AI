const SESSION_STORAGE_KEY = "truthai.supabase.session";

boot();

function boot() {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderAuthControls, { once: true });
  } else {
    renderAuthControls();
  }
  window.addEventListener("storage", handleSessionStorageChange);
}

function renderAuthControls() {
  const controls = document.querySelector("[data-auth-controls]");
  if (!controls) {
    return;
  }
  if (!controls.dataset.authDefaultHtml) {
    controls.dataset.authDefaultHtml = controls.innerHTML;
  }
  controls.style.flexWrap = "wrap";
  controls.style.justifyContent = "flex-end";

  const session = readSession();
  if (!session) {
    controls.innerHTML = controls.dataset.authDefaultHtml;
    return;
  }

  const user = session.user?.email || session.user?.id || "Signed in";
  const returnTo = `${location.pathname}${location.search}${location.hash}`;
  controls.innerHTML = "";

  const badge = document.createElement("span");
  badge.style.cssText =
    "display:inline-flex;align-items:center;gap:8px;max-width:min(38vw,220px);font-size:13px;font-weight:600;color:#0f172a;padding:9px 12px;border:1px solid #d4dde8;border-radius:9px;background:#fff;white-space:nowrap;overflow:hidden;";
  const dot = document.createElement("span");
  dot.style.cssText =
    "width:8px;height:8px;border-radius:50%;background:#059669;box-shadow:0 0 0 3px rgba(5,150,105,0.16);";
  badge.appendChild(dot);

  const label = document.createElement("span");
  label.style.cssText = "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;";
  label.textContent = user;
  badge.appendChild(label);

  const signOut = document.createElement("button");
  signOut.type = "button";
  signOut.textContent = "Sign out";
  signOut.style.cssText =
    "font:inherit;font-size:14px;font-weight:600;color:#0f172a;padding:9px 14px;border:1px solid #d4dde8;border-radius:9px;background:#fff;cursor:pointer;white-space:nowrap;flex-shrink:0;";
  signOut.addEventListener("click", () => {
    clearSession();
    location.assign(`/app/sign-in?return=${encodeURIComponent(returnTo)}`);
  });

  controls.appendChild(badge);
  controls.appendChild(signOut);
}

function handleSessionStorageChange(event) {
  if (event.key && event.key !== SESSION_STORAGE_KEY) {
    return;
  }
  renderAuthControls();
}

function readSession() {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const session = JSON.parse(raw);
    return session && typeof session.access_token === "string" ? session : null;
  } catch (error) {
    console.error(error);
    return null;
  }
}

function clearSession() {
  try {
    localStorage.removeItem(SESSION_STORAGE_KEY);
  } catch (error) {
    console.error(error);
  }
}
