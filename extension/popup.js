import { TOKN_CONFIG } from "./config.js";

const STORAGE_KEYS = {
  enabled: "tokn_enabled",
  tokensToday: "tokn_tokens_saved_today",
  tokensDate: "tokn_tokens_saved_date",
  lastSite: "tokn_last_site",
};

const els = {
  toggle: document.getElementById("enabled-toggle"),
  tokensSaved: document.getElementById("tokens-saved"),
  detectedSite: document.getElementById("detected-site"),
  statusHint: document.getElementById("status-hint"),
  apiUrl: document.getElementById("api-url"),
};

init();

async function init() {
  const apiHost = TOKN_CONFIG.API_BASE_URL.replace(/^https?:\/\//, "");
  els.apiUrl.textContent = apiHost;

  const state = await sendMessage({ type: "TOKn_GET_STATE" });
  if (state?.ok) {
    els.toggle.checked = state.enabled;
    els.tokensSaved.textContent = formatNumber(state.tokensSavedToday || 0);
    updateSiteLabel(state.lastSite);
    updateHint(state.enabled);
  }

  els.toggle.addEventListener("change", async () => {
    const enabled = els.toggle.checked;
    await sendMessage({ type: "TOKn_SET_ENABLED", enabled });
    updateHint(enabled);
  });

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
  });

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
