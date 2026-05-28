import { TOKN_CONFIG, COMPRESSION_LEVELS, DEFAULT_LEVEL } from "./config.js";

const STORAGE_KEYS = {
  enabled: "tokn_enabled",
  tokensToday: "tokn_tokens_saved_today",
  tokensDate: "tokn_tokens_saved_date",
  lastSite: "tokn_last_site",
  apiKey: "tokn_api_key",
  level: "tokn_compression_level",
  devMode: "tokn_dev_mode",
};

const els = {
  toggle: document.getElementById("enabled-toggle"),
  devToggle: document.getElementById("dev-mode-toggle"),
  tokensSaved: document.getElementById("tokens-saved"),
  detectedSite: document.getElementById("detected-site"),
  statusHint: document.getElementById("status-hint"),
  devHint: document.getElementById("dev-hint"),
  apiUrl: document.getElementById("api-url"),
  apiKeyInput: document.getElementById("api-key-input"),
  apiKeySave: document.getElementById("api-key-save"),
  apiKeyHint: document.getElementById("api-key-hint"),
  shortcutKey: document.getElementById("shortcut-key"),
  levelSelector: document.getElementById("level-selector"),
  levelHint: document.getElementById("level-hint"),
};

init();

async function init() {
  // Show correct shortcut for platform
  const isMac = navigator.platform.includes("Mac");
  els.shortcutKey.textContent = isMac ? "⌘+Shift+T" : "Ctrl+Shift+T";

  const apiHost = TOKN_CONFIG.API_BASE_URL.replace(/^https?:\/\//, "");
  els.apiUrl.textContent = apiHost;

  // Load saved Dev Mode state
  chrome.storage.local.get([STORAGE_KEYS.devMode], (data) => {
    const isDev = data[STORAGE_KEYS.devMode] === true;
    els.devToggle.checked = isDev;
    updateApiUrlLabel(isDev);
  });

  // Dev mode toggle handler
  els.devToggle.addEventListener("change", () => {
    const isDev = els.devToggle.checked;
    chrome.storage.local.set({ [STORAGE_KEYS.devMode]: isDev }, () => {
      updateApiUrlLabel(isDev);
    });
  });

  // Load saved API key
  chrome.storage.local.get([STORAGE_KEYS.apiKey], (data) => {
    const key = data[STORAGE_KEYS.apiKey] || "";
    if (key) {
      els.apiKeyInput.value = key;
    }
  });

  const state = await sendMessage({ type: "TOKn_GET_STATE" });
  if (state?.ok) {
    els.toggle.checked = state.enabled;
    els.tokensSaved.textContent = formatNumber(state.tokensSavedToday || 0);
    updateSiteLabel(state.lastSite);
    updateHint(state.enabled);
    setActiveLevel(state.level || DEFAULT_LEVEL);
  }

  // Toggle handler
  els.toggle.addEventListener("change", async () => {
    const enabled = els.toggle.checked;
    await sendMessage({ type: "TOKn_SET_ENABLED", enabled });
    updateHint(enabled);
  });

  // Level selector handler
  els.levelSelector.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-level]");
    if (!btn) return;
    const level = btn.dataset.level;
    await sendMessage({ type: "TOKn_SET_LEVEL", level });
    setActiveLevel(level);
  });

  // API key save handler
  els.apiKeySave.addEventListener("click", async () => {
    const apiKey = els.apiKeyInput.value.trim();
    await sendMessage({ type: "TOKn_SET_API_KEY", apiKey });
    els.apiKeyHint.textContent = apiKey ? "✓ Key saved" : "✓ Cleared (dev mode)";
    setTimeout(() => {
      els.apiKeyHint.textContent = "Optional — required when backend auth is enabled";
    }, 2000);
  });

  // Live storage updates
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "local") return;
    if (changes[STORAGE_KEYS.tokensToday]) {
      els.tokensSaved.textContent = formatNumber(
        changes[STORAGE_KEYS.tokensToday].newValue || 0
      );
    }
    if (changes[STORAGE_KEYS.lastSite]) {
      updateSiteLabel(changes[STORAGE_KEYS.lastSite].newValue);
    }
    if (changes[STORAGE_KEYS.enabled]) {
      els.toggle.checked = changes[STORAGE_KEYS.enabled].newValue !== false;
      updateHint(els.toggle.checked);
    }
    if (changes[STORAGE_KEYS.level]) {
      setActiveLevel(changes[STORAGE_KEYS.level].newValue);
    }
    if (changes[STORAGE_KEYS.devMode]) {
      const isDev = changes[STORAGE_KEYS.devMode].newValue === true;
      els.devToggle.checked = isDev;
      updateApiUrlLabel(isDev);
    }
  });

  // Detect current tab site
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.url) {
      const site = siteFromUrl(tab.url);
      if (site) {
        updateSiteLabel({ id: site.id, name: site.name });
      }
    }
  } catch {
    /* popup may run without tab permission in some contexts */
  }
}

// ---------- Level selector ----------

function setActiveLevel(levelId) {
  const level = COMPRESSION_LEVELS[levelId] || COMPRESSION_LEVELS[DEFAULT_LEVEL];

  // Update button states
  els.levelSelector.querySelectorAll(".level-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.level === levelId);
  });

  // Update hint
  els.levelHint.textContent = level.hint;
}

// ---------- Helpers ----------

function siteFromUrl(url) {
  try {
    const host = new URL(url).hostname;
    if (/chat\.openai\.com$|chatgpt\.com$/.test(host)) return { id: "chatgpt", name: "ChatGPT" };
    if (/claude\.ai$/.test(host)) return { id: "claude", name: "Claude" };
    if (/gemini\.google\.com$/.test(host)) return { id: "gemini", name: "Gemini" };
    if (/perplexity\.ai$/.test(host)) return { id: "perplexity", name: "Perplexity" };
  } catch {
    return null;
  }
  return null;
}

function updateSiteLabel(lastSite) {
  if (!lastSite?.name) {
    els.detectedSite.textContent = "Not on a supported page";
    return;
  }
  els.detectedSite.textContent = lastSite.name;
}

function updateHint(enabled) {
  els.statusHint.textContent = enabled
    ? "Active on supported AI sites"
    : "Paused — enable to optimize prompts";
}

function formatNumber(n) {
  return new Intl.NumberFormat().format(Math.round(Number(n) || 0));
}

function sendMessage(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        resolve({ ok: false, error: chrome.runtime.lastError.message });
        return;
      }
      resolve(response);
    });
  });
}

function updateApiUrlLabel(isDev) {
  const host = isDev ? "localhost:8000" : TOKN_CONFIG.API_BASE_URL.replace(/^https?:\/\//, "");
  els.apiUrl.textContent = host;
}
