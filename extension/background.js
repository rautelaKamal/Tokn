/**
 * Tokn service worker — proxies optimize requests to FastAPI.
 * Routes compression by level: Safe (JS only), Balanced/Aggressive (JS + API).
 * No API keys; all AI calls happen on the backend.
 */
import { TOKN_CONFIG, COMPRESSION_LEVELS, DEFAULT_LEVEL } from "./config.js";
import { clientCompress, estimateTokens } from "./compressor.js";

const STORAGE_KEYS = {
  enabled: "tokn_enabled",
  tokensToday: "tokn_tokens_saved_today",
  tokensDate: "tokn_tokens_saved_date",
  lastSite: "tokn_last_site",
  apiKey: "tokn_api_key",
  level: "tokn_compression_level",
  devMode: "tokn_dev_mode",
};

// ---------- Install ----------

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(
    [STORAGE_KEYS.enabled, STORAGE_KEYS.tokensToday, STORAGE_KEYS.tokensDate, STORAGE_KEYS.level],
    (data) => {
      const updates = {};
      if (data[STORAGE_KEYS.enabled] === undefined) {
        updates[STORAGE_KEYS.enabled] = true;
      }
      if (data[STORAGE_KEYS.tokensToday] === undefined) {
        updates[STORAGE_KEYS.tokensToday] = 0;
      }
      if (!data[STORAGE_KEYS.tokensDate]) {
        updates[STORAGE_KEYS.tokensDate] = todayKey();
      }
      if (!data[STORAGE_KEYS.level]) {
        updates[STORAGE_KEYS.level] = DEFAULT_LEVEL;
      }
      if (Object.keys(updates).length > 0) {
        chrome.storage.local.set(updates);
      }
    }
  );
});

// ---------- Message router ----------

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "TOKn_OPTIMIZE") {
    handleOptimize(message)
      .then(sendResponse)
      .catch((err) => {
        sendResponse({
          ok: false,
          error: err?.message || "Optimization failed",
        });
      });
    return true;
  }

  if (message?.type === "TOKn_GET_STATE") {
    getExtensionState().then(sendResponse);
    return true;
  }

  if (message?.type === "TOKn_SET_ENABLED") {
    chrome.storage.local.set({ [STORAGE_KEYS.enabled]: Boolean(message.enabled) }, () => {
      sendResponse({ ok: true, enabled: Boolean(message.enabled) });
    });
    return true;
  }

  if (message?.type === "TOKn_SET_LEVEL") {
    const level = COMPRESSION_LEVELS[message.level] ? message.level : DEFAULT_LEVEL;
    chrome.storage.local.set({ [STORAGE_KEYS.level]: level }, () => {
      sendResponse({ ok: true, level });
    });
    return true;
  }

  if (message?.type === "TOKn_SET_API_KEY") {
    chrome.storage.local.set({ [STORAGE_KEYS.apiKey]: message.apiKey || "" }, () => {
      sendResponse({ ok: true });
    });
    return true;
  }

  if (message?.type === "TOKn_SITE_DETECTED") {
    chrome.storage.local.set(
      {
        [STORAGE_KEYS.lastSite]: {
          id: message.siteId,
          name: message.siteName,
          url: message.url,
          at: Date.now(),
        },
      },
      () => sendResponse({ ok: true })
    );
    return true;
  }

  return false;
});

// ---------- Optimize handler ----------

async function handleOptimize({ prompt, siteId, siteName }) {
  const data = await storageGet([
    STORAGE_KEYS.enabled,
    STORAGE_KEYS.apiKey,
    STORAGE_KEYS.level,
    STORAGE_KEYS.devMode,
  ]);

  if (data[STORAGE_KEYS.enabled] === false) {
    return { ok: false, error: "Tokn is turned off" };
  }

  const trimmed = (prompt || "").trim();
  if (trimmed.length < 1) {
    return { ok: false, error: "Prompt is empty" };
  }

  const level = data[STORAGE_KEYS.level] || DEFAULT_LEVEL;
  const levelConfig = COMPRESSION_LEVELS[level] || COMPRESSION_LEVELS[DEFAULT_LEVEL];

  if (siteId) {
    await storageSet({
      [STORAGE_KEYS.lastSite]: {
        id: siteId,
        name: siteName || siteId,
        at: Date.now(),
      },
    });
  }

  // ---- Step 1: Always run client-side compression first ----
  const jsResult = clientCompress(trimmed);

  // ---- Step 2: If Safe mode, return JS result directly ----
  if (!levelConfig.usesApi) {
    const tokensSaved = jsResult.tokensBefore - jsResult.tokensAfter;
    if (tokensSaved > 0) {
      const newTotal = await addTokensSavedToday(tokensSaved);
      updateBadge(newTotal);
    }
    return {
      ok: true,
      data: {
        original_prompt: trimmed,
        optimized_prompt: jsResult.compressed,
        tokens_before: { tokens: jsResult.tokensBefore, estimated_cost_usd: 0 },
        tokens_after: { tokens: jsResult.tokensAfter, estimated_cost_usd: 0 },
        tokens_saved: tokensSaved,
        cost_saved_usd: 0,
        compression_ratio: jsResult.tokensBefore > 0
          ? (jsResult.tokensBefore - jsResult.tokensAfter) / jsResult.tokensBefore
          : 0,
        model_used: "client-side (no API)",
        encoding_used: "estimate",
        level,
        changes: jsResult.changes,
      },
    };
  }

  // ---- Step 3: Balanced/Aggressive — send JS-cleaned text to API ----
  const headers = { "Content-Type": "application/json" };
  const apiKey = data[STORAGE_KEYS.apiKey];
  if (apiKey) {
    headers["X-Tokn-Key"] = apiKey;
  }

  const isDev = data[STORAGE_KEYS.devMode] === true;
  const baseUrl = isDev ? "http://127.0.0.1:8000" : TOKN_CONFIG.API_BASE_URL;
  const url = `${baseUrl}${TOKN_CONFIG.OPTIMIZE_PATH}`;
  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      prompt: jsResult.compressed, // always send pre-cleaned text
      level,                        // backend adjusts behavior
    }),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const errBody = await response.json();
      detail = errBody.detail || errBody.message || detail;
      if (Array.isArray(detail)) {
        detail = detail.map((d) => d.msg || JSON.stringify(d)).join(", ");
      }
    } catch {
      /* ignore parse errors */
    }
    return { ok: false, error: String(detail) };
  }

  const result = await response.json();

  // Recalculate savings from original (pre-JS) prompt
  result.tokens_saved = jsResult.tokensBefore - (result.tokens_after?.tokens || 0);
  result.tokens_before = { tokens: jsResult.tokensBefore, estimated_cost_usd: 0 };
  result.original_prompt = trimmed;
  result.level = level;
  result.changes = jsResult.changes;

  const tokensSaved = Number(result.tokens_saved) || 0;
  if (tokensSaved > 0) {
    const newTotal = await addTokensSavedToday(tokensSaved);
    updateBadge(newTotal);
  }

  return { ok: true, data: result };
}

// ---------- State ----------

async function getExtensionState() {
  const data = await storageGet([
    STORAGE_KEYS.enabled,
    STORAGE_KEYS.tokensToday,
    STORAGE_KEYS.tokensDate,
    STORAGE_KEYS.lastSite,
    STORAGE_KEYS.level,
  ]);

  const { tokensToday } = await ensureTodayBucket(
    data[STORAGE_KEYS.tokensToday],
    data[STORAGE_KEYS.tokensDate]
  );

  updateBadge(tokensToday);

  return {
    ok: true,
    enabled: data[STORAGE_KEYS.enabled] !== false,
    tokensSavedToday: tokensToday,
    lastSite: data[STORAGE_KEYS.lastSite] || null,
    level: data[STORAGE_KEYS.level] || DEFAULT_LEVEL,
  };
}

// ---------- Token counter ----------

async function addTokensSavedToday(delta) {
  const data = await storageGet([
    STORAGE_KEYS.tokensToday,
    STORAGE_KEYS.tokensDate,
  ]);
  const { tokensToday, dateKey } = await ensureTodayBucket(
    data[STORAGE_KEYS.tokensToday],
    data[STORAGE_KEYS.tokensDate]
  );
  const next = tokensToday + delta;
  await storageSet({
    [STORAGE_KEYS.tokensToday]: next,
    [STORAGE_KEYS.tokensDate]: dateKey,
  });
  return next;
}

async function ensureTodayBucket(storedTokens, storedDate) {
  const dateKey = todayKey();
  if (storedDate !== dateKey) {
    await storageSet({
      [STORAGE_KEYS.tokensToday]: 0,
      [STORAGE_KEYS.tokensDate]: dateKey,
    });
    return { tokensToday: 0, dateKey };
  }
  return {
    tokensToday: Number(storedTokens) || 0,
    dateKey,
  };
}

// ---------- Badge ----------

function updateBadge(tokensSaved) {
  const text = tokensSaved > 0 ? formatBadgeNumber(tokensSaved) : "";
  chrome.action.setBadgeText({ text }).catch(() => {});
  chrome.action.setBadgeBackgroundColor({ color: "#22c55e" }).catch(() => {});
}

function formatBadgeNumber(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

// ---------- Helpers ----------

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function storageGet(keys) {
  return new Promise((resolve) => {
    chrome.storage.local.get(keys, resolve);
  });
}

function storageSet(obj) {
  return new Promise((resolve) => {
    chrome.storage.local.set(obj, resolve);
  });
}
