(async () => {
  try {
    const response = await fetch("/frontend/Truth-AI.dc.html", {
      cache: "no-store"
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const html = await response.text();
    document.open();
    document.write(html);
    document.close();
  } catch (error) {
    document.body.innerHTML = '<main style="font-family:system-ui,sans-serif;padding:32px;"><h1>Truth-AI</h1><p>The console could not be loaded.</p><p><a href="/frontend/Truth-AI.dc">Open the frontend directly</a></p></main>';
    console.error(error);
  }
})();
