/**
 * Tokn extension config — no API keys here.
 * Backend URL is the only remote dependency exposed to the extension.
 */
export const TOKN_CONFIG = {
  API_BASE_URL: "http://localhost:8000",
  OPTIMIZE_PATH: "/api/v1/optimize/",
  DEBOUNCE_MS: 800,
  MIN_PROMPT_LENGTH: 20,
};

/**
 * Supported AI sites — canonical source of truth.
 * ⚠️  content.js duplicates this list because content scripts cannot use
 *     ES module imports. If you update selectors here, mirror the change
 *     in the SITES object inside content.js.
 */
export const SITES = {
  chatgpt: {
    id: "chatgpt",
    name: "ChatGPT",
    hostPattern: /chat\.openai\.com$|chatgpt\.com$/,
    matchUrls: ["https://chat.openai.com/*", "https://chatgpt.com/*"],
    inputSelector: 'div[contenteditable="true"]',
    inputType: "contenteditable",
  },
  claude: {
    id: "claude",
    name: "Claude",
    hostPattern: /claude\.ai$/,
    matchUrls: ["https://claude.ai/*"],
    inputSelector: 'div[contenteditable="true"]',
    inputType: "contenteditable",
  },
  gemini: {
    id: "gemini",
    name: "Gemini",
    hostPattern: /gemini\.google\.com$/,
    matchUrls: ["https://gemini.google.com/*"],
    inputSelector: "rich-textarea",
    inputType: "rich-textarea",
  },
  perplexity: {
    id: "perplexity",
    name: "Perplexity",
    hostPattern: /perplexity\.ai$/,
    matchUrls: [
      "https://www.perplexity.ai/*",
      "https://perplexity.ai/*",
    ],
    inputSelector: "textarea",
    inputType: "textarea",
  },
};
