(async () => {
  try {
    const source = location.pathname === "/" || location.pathname.startsWith("/app")
      ? "/frontend/Truth-Kernel-Studio.dc.html"
      : "/frontend/Truth-AI.dc.html";
    const response = await fetch(source, {
      cache: "no-store"
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const html = (await response.text()).replace(
      '<script src="./support.js"></script>',
      '<script src="/frontend/support.js"></script>'
    );
    document.open();
    document.write(html);
    document.close();
  } catch (error) {
    document.body.innerHTML = '<main style="font-family:system-ui,sans-serif;padding:32px;"><h1>Truth-AI</h1><p>The console could not be loaded.</p><p><a href="/frontend/Truth-AI.dc.html">Open the frontend directly</a></p></main>';
    console.error(error);
  }
})();
