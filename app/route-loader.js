(async () => {
  try {
    const pathname = location.pathname.replace(/\/$/, "") || "/";
    if (pathname.startsWith("/app") && pathname !== "/app/sign-in") {
      const session = readSession();
      if (!session) {
        const signInUrl = new URL("/app/sign-in", location.origin);
        const returnTo = `${location.pathname}${location.search}${location.hash}`;
        signInUrl.searchParams.set("return", returnTo);
        location.replace(signInUrl.toString());
        return;
      }
    }
    const source = pathname === "/"
      ? "/frontend/Truth-Kernel-Studio.dc.html"
      : "/frontend/Truth-AI-App.dc.html";
    const response = await fetch(source, {
      cache: "no-store"
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const html = (await response.text()).replace(
      '<script src="./support.js"></script>',
      '<script src="/frontend/support.js"></script><script src="/app/auth-client.js"></script><script src="/app/verified-chat-client.js"></script><script src="/app/standards-library.js?v=standards-ingest-1"></script>'
    );
    document.open();
    document.write(html);
    document.close();
  } catch (error) {
    document.body.innerHTML = '<main style="font-family:system-ui,sans-serif;padding:32px;"><h1>Truth-AI</h1><p>The console could not be loaded.</p><p><a href="/">Return to the site</a></p></main>';
    console.error(error);
  }
})();

function readSession() {
  try {
    const raw = localStorage.getItem("truthai.supabase.session");
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
