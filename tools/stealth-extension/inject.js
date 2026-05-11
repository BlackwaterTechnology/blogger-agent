// Runs in the isolated content-script world at document_start.
// It can't directly patch `navigator` / `window.chrome` of the page —
// those live in MAIN world. So we inject a <script> element whose body
// runs in MAIN world *immediately*, before any page script parses.
//
// Why not declare `world: "MAIN"` in manifest? In Chrome 147 it loads
// successfully but inject.js silently fails to defineProperty on the
// page's navigator (cross-world reference). The <script>-tag dance is
// the classic puppeteer-extra-stealth approach and works reliably.

(function () {
  const code = `
    (function () {
      try { window.__blogger_stealth_loaded = Date.now(); } catch (e) {}

      try {
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      } catch (e) {}

      try {
        if (typeof window.chrome === 'object' && !window.chrome.runtime) {
          window.chrome.runtime = {
            id: undefined,
            OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
            OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
            PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
            PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
            RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' },
            connect: function () { return { onMessage: { addListener: function () {}, removeListener: function () {} }, onDisconnect: { addListener: function () {}, removeListener: function () {} }, postMessage: function () {}, disconnect: function () {} }; },
            sendMessage: function () {},
            getURL: function (p) { return p; },
            getManifest: function () { return {}; }
          };
        }
      } catch (e) {}

      try {
        const desired = ['zh-CN', 'zh', 'en-US', 'en'];
        if (!navigator.languages || navigator.languages[0] !== 'zh-CN') {
          Object.defineProperty(navigator, 'languages', { get: () => desired });
          Object.defineProperty(navigator, 'language', { get: () => 'zh-CN' });
        }
      } catch (e) {}
    })();
  `;

  try {
    const s = document.createElement('script');
    s.textContent = code;
    // Use documentElement (the <html> root) — it exists at document_start
    // even before <head> / <body>. Inserting here guarantees we run before
    // any inline script the page parses.
    (document.documentElement || document.head || document.body).appendChild(s);
    s.remove();
  } catch (e) {
    // best effort
  }
})();
