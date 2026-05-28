/**
 * Tokn content script — detects AI inputs, debounces prompts, shows floating panel.
 *
 * ⚠️  SITES is duplicated from config.js because content scripts cannot use
 *     ES module imports. If you update selectors in config.js, mirror the
 *     change here.
 */
(function () {
  "use strict";

  const DEBOUNCE_MS = 1500;
  const MIN_PROMPT_LENGTH = 20;
  const PANEL_ID = "tokn-optimizer-panel";

  const SITES = {
    chatgpt: {
      id: "chatgpt",
      name: "ChatGPT",
      test: () => /chat\.openai\.com$|chatgpt\.com$/.test(location.hostname),
      // ProseMirror-based editor — class names change, but contenteditable is stable
      inputSelectors: [
        'div.ProseMirror[contenteditable="true"]',
        '#prompt-textarea',
        'div[contenteditable="true"]',
      ],
      inputType: "contenteditable",
    },
    claude: {
      id: "claude",
      name: "Claude",
      test: () => /claude\.ai$/.test(location.hostname),
      // Claude also uses ProseMirror; data-testid may be present
      inputSelectors: [
        'div[contenteditable="true"].ProseMirror',
        'div[contenteditable="true"][data-testid]',
        'div[contenteditable="true"][placeholder]',
        'div[contenteditable="true"]',
      ],
      inputType: "contenteditable",
    },
    gemini: {
      id: "gemini",
      name: "Gemini",
      test: () => /gemini\.google\.com$/.test(location.hostname),
      inputSelectors: [
        "rich-textarea",
        'div[contenteditable="true"]',
      ],
      inputType: "rich-textarea",
    },
    perplexity: {
      id: "perplexity",
      name: "Perplexity",
      test: () => /perplexity\.ai$/.test(location.hostname),
      inputSelectors: [
        'textarea[placeholder]',
        "textarea",
      ],
      inputType: "textarea",
    },
  };

  const LEVEL_EMOJIS = { safe: "🟢", balanced: "🟡", aggressive: "🔴" };
  const LEVEL_LABELS = {
    safe: "Safe mode — no API call",
    balanced: "Balanced — JS + API",
    aggressive: "Aggressive — full semantic",
  };

  const state = {
    site: null,
    inputEl: null,
    panel: null,
    enabled: true,
    level: "balanced",
    debounceTimer: null,
    lastSentPrompt: "",
    lastRequestId: 0,
    dismissed: false,
    boundInput: null,
  };

  // ---------- Init ----------

  init();

  function init() {
    const site = detectSite();
    if (!site) return;

    state.site = site;
    notifySiteDetected(site);

    chrome.storage.local.get(["tokn_enabled", "tokn_compression_level"], (data) => {
      state.enabled = data.tokn_enabled !== false;
      state.level = data.tokn_compression_level || "balanced";
      if (!state.enabled) return;
      startWatching();
    });

    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== "local") return;
      if (changes.tokn_compression_level) {
        state.level = changes.tokn_compression_level.newValue || "balanced";
      }
      if (!changes.tokn_enabled) return;
      state.enabled = changes.tokn_enabled.newValue !== false;
      if (!state.enabled) {
        hidePanel();
        clearDebounce();
      } else {
        startWatching();
      }
    });

    // Keyboard shortcut: Ctrl+Shift+T (or Cmd+Shift+T on Mac) to manually trigger
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "T") {
        e.preventDefault();
        if (!state.enabled || !state.inputEl) return;
        const text = getPromptText(state.inputEl).trim();
        if (text.length >= MIN_PROMPT_LENGTH) {
          state.dismissed = false;
          requestOptimization(text, state.inputEl);
        }
      }
    });
  }

  function detectSite() {
    return Object.values(SITES).find((s) => s.test()) || null;
  }

  function notifySiteDetected(site) {
    safeSendMessage({
      type: "TOKn_SITE_DETECTED",
      siteId: site.id,
      siteName: site.name,
      url: location.href,
    });
  }

  // ---------- Watching ----------

  function startWatching() {
    bindToBestInput();
    const observer = new MutationObserver(() => {
      if (!state.enabled) return;
      if (!state.inputEl || !document.contains(state.inputEl)) {
        bindToBestInput();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    window.addEventListener(
      "resize",
      () => state.panel && positionPanel(state.inputEl),
      { passive: true }
    );
    window.addEventListener(
      "scroll",
      () => state.panel && positionPanel(state.inputEl),
      true
    );
  }

  function bindToBestInput() {
    const el = findBestInput();
    if (!el || el === state.boundInput) return;

    unbindInput(state.boundInput);
    state.boundInput = el;
    state.inputEl = el;
    state.dismissed = false;

    const onInput = () => handleInputChange(el);
    el.addEventListener("input", onInput);
    el.addEventListener("keyup", onInput);
    el.addEventListener("focus", onInput);
    el._toknHandlers = { onInput };

    if (getPromptText(el).length >= MIN_PROMPT_LENGTH) {
      handleInputChange(el);
    }
  }

  function unbindInput(el) {
    if (!el?._toknHandlers) return;
    const { onInput } = el._toknHandlers;
    el.removeEventListener("input", onInput);
    el.removeEventListener("keyup", onInput);
    el.removeEventListener("focus", onInput);
    delete el._toknHandlers;
  }

  function findBestInput() {
    if (!state.site) return null;

    // Try each selector from most-specific to least-specific
    const selectors = state.site.inputSelectors || [state.site.inputSelector];
    let nodes = [];
    for (const sel of selectors) {
      nodes = Array.from(document.querySelectorAll(sel)).filter(isVisible);
      if (nodes.length) break;
    }
    if (!nodes.length) return null;

    const active = document.activeElement;
    if (active && nodes.includes(active)) return active;

    const focused = nodes.find((n) => n === active || n.contains(active));
    if (focused) return focused;

    return nodes.sort((a, b) => scoreInput(b) - scoreInput(a))[0];
  }

  function scoreInput(el) {
    const rect = el.getBoundingClientRect();
    const area = Math.max(0, rect.width) * Math.max(0, rect.height);
    const textLen = getPromptText(el).length;
    const bottomBonus = rect.bottom * 0.01;
    return area + textLen * 50 + bottomBonus;
  }

  function isVisible(el) {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 20 && rect.height > 10 && rect.bottom > 0 && rect.top < window.innerHeight;
  }

  // ---------- Text read/write ----------

  function getEditableTarget(el) {
    if (!el) return null;
    if (state.site.inputType === "rich-textarea") {
      return (
        el.querySelector?.('[contenteditable="true"]') ||
        el.shadowRoot?.querySelector?.('[contenteditable="true"]') ||
        el
      );
    }
    return el;
  }

  function getPromptText(el) {
    const target = getEditableTarget(el);
    if (!target) return "";

    if (state.site.inputType === "textarea") {
      return target.value || "";
    }
    return (target.innerText || target.textContent || "").trim();
  }

  function setPromptText(el, text) {
    const target = getEditableTarget(el);
    if (!target) return;

    if (state.site.inputType === "textarea") {
      // For standard textareas (Perplexity)
      const nativeSetter = Object.getOwnPropertyDescriptor(
        HTMLTextAreaElement.prototype, "value"
      )?.set;
      if (nativeSetter) {
        nativeSetter.call(target, text);
      } else {
        target.value = text;
      }
      target.dispatchEvent(new Event("input", { bubbles: true }));
      target.dispatchEvent(new Event("change", { bubbles: true }));
      return;
    }

    // For contenteditable (ChatGPT, Claude) — use execCommand for React compat
    target.focus();

    // Select all existing text
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(target);
    selection.removeAllRanges();
    selection.addRange(range);

    // Insert replacement text — this fires React-compatible input events
    if (document.execCommand("insertText", false, text)) {
      // execCommand worked — React/ProseMirror will pick up the change
    } else {
      // Fallback: simulate clipboard paste (works with ProseMirror editors)
      try {
        const clipData = new DataTransfer();
        clipData.setData("text/plain", text);
        const pasteEvent = new ClipboardEvent("paste", {
          bubbles: true,
          cancelable: true,
          clipboardData: clipData,
        });
        target.dispatchEvent(pasteEvent);
      } catch {
        // Last resort: direct DOM manipulation
        target.innerText = text;
        target.dispatchEvent(new InputEvent("input", {
          bubbles: true,
          inputType: "insertText",
          data: text,
        }));
      }
    }
  }

  // ---------- Input handler ----------

  function handleInputChange(el) {
    if (!state.enabled) return;

    const text = getPromptText(el).trim();

    if (state.dismissed && text !== state.lastSentPrompt) {
      state.dismissed = false;
    }
    if (state.dismissed) return;
    clearDebounce();

    if (text.length < MIN_PROMPT_LENGTH) {
      hidePanel();
      return;
    }

    // Hide the panel immediately while actively typing to stay completely out of the way
    hidePanel();

    state.debounceTimer = window.setTimeout(() => {
      requestOptimization(text, el);
    }, DEBOUNCE_MS);
  }

  function clearDebounce() {
    if (state.debounceTimer) {
      clearTimeout(state.debounceTimer);
      state.debounceTimer = null;
    }
  }

  // ---------- API communication ----------

  /**
   * Send message to background with automatic retry.
   * Chrome kills idle service workers — if the first attempt fails
   * with a disconnected port error, we retry after a short delay.
   */
  function safeSendMessage(msg, callback, retries = 2) {
    chrome.runtime.sendMessage(msg, (response) => {
      if (chrome.runtime.lastError) {
        if (retries > 0) {
          setTimeout(() => safeSendMessage(msg, callback, retries - 1), 500);
          return;
        }
        if (callback) callback(undefined);
        return;
      }
      if (callback) callback(response);
    });
  }

  function requestOptimization(prompt, inputEl) {
    if (prompt === state.lastSentPrompt) return;

    const requestId = ++state.lastRequestId;
    state.lastSentPrompt = prompt;

    showPanelLoading();

    safeSendMessage(
      {
        type: "TOKn_OPTIMIZE",
        prompt,
        siteId: state.site.id,
        siteName: state.site.name,
      },
      (response) => {
        if (requestId !== state.lastRequestId) return;

        if (!response) {
          showPanelError("Extension connection lost — try refreshing the page");
          return;
        }

        if (!response.ok) {
          showPanelError(response.error || "Could not optimize prompt");
          state.lastSentPrompt = "";
          return;
        }

        showPanelResult(response.data, inputEl);
      }
    );
  }

  // ---------- Panel UI ----------

  function buildPanelMarkup() {
    const root = document.createElement("div");
    root.innerHTML = `
      <div class="tokn-panel__header">
        <div class="tokn-panel__brand">
          <span class="tokn-panel__logo">T</span>
          <span>Tokn</span>
        </div>
        <span class="tokn-panel__badge" data-tokn-badge>-</span>
        <button type="button" class="tokn-panel__close" data-tokn-dismiss aria-label="Dismiss">&times;</button>
      </div>
      <div class="tokn-panel__body">
        <div class="tokn-panel__label"><span data-tokn-mode-label>Optimized prompt</span></div>
        <p class="tokn-panel__text" data-tokn-text></p>
      </div>
      <div class="tokn-panel__meta">
        <span><strong data-tokn-tokens>0</strong> tokens saved</span>
        <span>$<strong data-tokn-cost>0.00</strong> saved</span>
      </div>
      <div class="tokn-panel__footer">
        <button type="button" class="tokn-panel__btn tokn-panel__btn--primary" data-tokn-apply>
          Use this prompt
        </button>
        <button type="button" class="tokn-panel__btn tokn-panel__btn--ghost" data-tokn-dismiss-btn>
          Dismiss
        </button>
      </div>
      <div class="tokn-panel__status" data-tokn-status hidden></div>
      <div class="tokn-panel__shortcut">
        <kbd>${navigator.platform.includes("Mac") ? "⌘" : "Ctrl"}+Shift+T</kbd> to optimize
      </div>
    `;
    return root.innerHTML.trim();
  }

  function ensurePanel() {
    if (state.panel) return state.panel;

    const panel = document.createElement("div");
    panel.id = PANEL_ID;
    panel.className = "tokn-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Tokn prompt optimizer");
    panel.innerHTML = buildPanelMarkup();

    document.body.appendChild(panel);

    panel.querySelector("[data-tokn-dismiss]").addEventListener("click", dismissPanel);
    panel.querySelector("[data-tokn-dismiss-btn]").addEventListener("click", dismissPanel);

    state.panel = panel;
    return panel;
  }

  function dismissPanel() {
    state.dismissed = true;
    hidePanel();
    clearDebounce();
  }

  function hidePanel() {
    const panel = state.panel;
    if (!panel) return;
    panel.classList.remove("tokn-panel--visible");
    panel.classList.add("tokn-panel--hidden");
  }

  function showPanel() {
    const panel = ensurePanel();
    panel.classList.remove("tokn-panel--hidden");
    requestAnimationFrame(() => {
      panel.classList.add("tokn-panel--visible");
      positionPanel(state.inputEl);
    });
  }

  function positionPanel(inputEl) {
    const panel = state.panel;
    if (!panel || !inputEl) return;

    const rect = inputEl.getBoundingClientRect();
    const panelWidth = panel.offsetWidth || 380;
    const panelHeight = panel.offsetHeight || 220;
    const margin = 12;

    let left = rect.right - panelWidth;
    let top = rect.bottom + margin;

    if (left + panelWidth > window.innerWidth - margin) {
      left = window.innerWidth - panelWidth - margin;
    }
    if (left < margin) left = margin;

    if (top + panelHeight > window.innerHeight - margin) {
      top = rect.top - panelHeight - margin;
    }
    if (top < margin) top = margin;

    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
  }

  function showPanelLoading() {
    const panel = ensurePanel();
    showPanel();
    panel.querySelector("[data-tokn-badge]").textContent = "Optimizing...";
    panel.querySelector("[data-tokn-text]").textContent = "";
    const status = panel.querySelector("[data-tokn-status]");
    status.hidden = false;
    status.className = "tokn-panel__status";
    status.innerHTML =
      '<span class="tokn-panel__loading"></span>Analyzing your prompt...';
    panel.querySelector("[data-tokn-tokens]").textContent = "-";
    panel.querySelector("[data-tokn-cost]").textContent = "-";
    positionPanel(state.inputEl);
  }

  function showPanelError(message) {
    const panel = ensurePanel();
    showPanel();
    panel.querySelector("[data-tokn-badge]").textContent = "Error";
    panel.querySelector("[data-tokn-text]").textContent = "";
    const status = panel.querySelector("[data-tokn-status]");
    status.hidden = false;
    status.className = "tokn-panel__status tokn-panel__status--error";
    status.textContent = message;
    positionPanel(state.inputEl);
  }

  function showPanelResult(data, inputEl) {
    const panel = ensurePanel();
    showPanel();

    const tokensSaved = data.tokens_saved ?? 0;
    const costSaved = data.cost_saved_usd ?? 0;
    const optimized = data.optimized_prompt || "";

    const emoji = LEVEL_EMOJIS[data.level || state.level] || "🟡";
    panel.querySelector("[data-tokn-badge]").textContent =
      tokensSaved > 0 ? `${emoji} -${formatNumber(tokensSaved)} tokens` : `${emoji} Optimized`;

    const modeLabel = panel.querySelector("[data-tokn-mode-label]");
    if (modeLabel) modeLabel.textContent = LEVEL_LABELS[data.level || state.level] || "Optimized prompt";

    panel.querySelector("[data-tokn-text]").textContent = optimized;
    panel.querySelector("[data-tokn-tokens]").textContent = formatNumber(tokensSaved);
    panel.querySelector("[data-tokn-cost]").textContent = formatCost(costSaved);

    const status = panel.querySelector("[data-tokn-status]");
    status.hidden = true;
    status.textContent = "";

    const applyBtn = panel.querySelector("[data-tokn-apply]");
    const newApply = applyBtn.cloneNode(true);
    applyBtn.replaceWith(newApply);
    newApply.addEventListener("click", () => {
      setPromptText(inputEl, optimized);
      state.lastSentPrompt = optimized.trim();
      state.dismissed = true;
      hidePanel();
    });

    positionPanel(inputEl);
  }

  // ---------- Helpers ----------

  function formatNumber(n) {
    return new Intl.NumberFormat().format(Math.round(n));
  }

  function formatCost(usd) {
    if (usd >= 0.01) return usd.toFixed(2);
    if (usd >= 0.0001) return usd.toFixed(4);
    return usd.toFixed(6);
  }
})();
