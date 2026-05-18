# Tokn — Prompt Optimizer

> **Grammarly for AI prompts.** Compress, clarify, and quantify token savings in real time — right inside ChatGPT, Claude, Gemini, and Perplexity.

![Chrome Extension](https://img.shields.io/badge/Manifest-V3-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## How It Works

```
User types prompt → Extension detects input (800ms debounce) → 
  → Service Worker → FastAPI backend → Claude optimizes → 
  → Floating panel shows optimized prompt + token/cost savings
```

1. **Content script** auto-detects the AI platform's text input
2. **Service worker** proxies the prompt to the FastAPI backend (no API keys in the extension)
3. **Backend** uses Anthropic's Claude to compress/clarify the prompt
4. **Floating panel** appears beside the input with the optimized prompt, tokens saved, and cost saved
5. **One-click replace** swaps the user's prompt with the optimized version

---

## Monorepo Layout

```
Tokn/
├── backend/              # FastAPI API server
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Config, dependencies
│   │   ├── schemas/      # Pydantic models
│   │   ├── services/     # Tokenizer, optimizer, cost calculator
│   │   └── main.py       # App entry point
│   ├── tests/            # Pytest suite (6/6 passing)
│   ├── requirements.txt
│   └── .env.example
├── extension/            # Chrome Extension (MV3)
│   ├── manifest.json     # Permissions, host matching, icons
│   ├── background.js     # Service worker — API proxy
│   ├── content.js        # Input detection, debounce, floating panel
│   ├── content.css       # Panel styling (dark card, green badges)
│   ├── popup.html/js/css # Extension popup UI
│   ├── config.js         # Centralized config (API URL, selectors)
│   └── icons/            # 16/48/128px extension icons
└── frontend/             # React web app (planned)
```

---

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure your Anthropic API key
cp .env.example .env
# Edit .env → set ANTHROPIC_API_KEY=sk-ant-...

uvicorn app.main:app --reload --port 8000
```

Verify: `http://localhost:8000/docs` — Swagger UI should load.

### 2. Chrome Extension

1. Open `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select the `extension/` folder
4. Navigate to any supported AI site and start typing

### 3. Test the API (no browser needed)

```bash
curl -s -X POST http://localhost:8000/api/v1/optimize/ \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Please could you kindly help me write a good email"}' | python3 -m json.tool
```

---

## Supported Platforms

| Platform    | URL                          | Input Selector                      |
|-------------|------------------------------|-------------------------------------|
| ChatGPT     | `chat.openai.com`, `chatgpt.com` | `div[contenteditable="true"]`   |
| Claude      | `claude.ai`                  | `div[contenteditable="true"]`       |
| Gemini      | `gemini.google.com`          | `rich-textarea`                     |
| Perplexity  | `perplexity.ai`              | `textarea`                          |

---

## API Endpoints

| Method | Endpoint              | Description                      |
|--------|-----------------------|----------------------------------|
| GET    | `/api/v1/health`      | Health check                     |
| POST   | `/api/v1/optimize/`   | Optimize a prompt                |

### POST `/api/v1/optimize/`

**Request:**
```json
{
  "prompt": "Please could you kindly help me write a good email to my boss"
}
```

**Response:**
```json
{
  "original_prompt": "Please could you kindly help me write a good email to my boss",
  "optimized_prompt": "Write a professional email to my boss",
  "original_tokens": 15,
  "optimized_tokens": 8,
  "tokens_saved": 7,
  "cost_saved_usd": 0.000021
}
```

---

## Extension Architecture

### Message Flow

```
content.js  ──TOKn_OPTIMIZE──▸  background.js  ──fetch──▸  FastAPI /optimize/
             ◂──response.data──               ◂──JSON────
```

### Key Design Decisions

- **No API keys in extension code** — all AI calls go through the FastAPI backend
- **800ms debounce** — prevents API spam while user is actively typing
- **Daily token counter** — stored in `chrome.storage.local`, auto-resets each day
- **MutationObserver** — watches for dynamic DOM changes (SPAs re-render inputs)
- **Request ID tracking** — prevents stale responses from overwriting newer ones

### Storage Keys

| Key                       | Type    | Description                    |
|---------------------------|---------|--------------------------------|
| `tokn_enabled`            | boolean | Extension on/off toggle        |
| `tokn_tokens_saved_today` | number  | Running total for current day  |
| `tokn_tokens_saved_date`  | string  | ISO date for daily reset check |
| `tokn_last_site`          | object  | Last detected AI platform info |

---

## Development Notes

### DOM Selectors Are Fragile

AI platforms frequently update their DOM structure. If the floating panel doesn't appear:

1. Open DevTools on the AI site
2. Inspect the text input element
3. Update the selector in `content.js` (SITES object) and `config.js`

### Production Deployment

Before deploying:

1. Update `API_BASE_URL` in `extension/config.js` to your production API URL
2. Add rate limiting to `/api/v1/optimize/`
3. Add authentication (JWT planned)
4. Build the React frontend for the marketing site

---

## Roadmap

- [x] FastAPI backend with Claude optimization
- [x] Chrome Extension (MV3) with floating panel
- [x] Real-time token & cost savings
- [x] Daily savings tracker
- [ ] React web app / marketing site
- [ ] JWT authentication
- [ ] PostgreSQL usage history
- [ ] Rate limiting on `/optimize`
- [ ] Chrome Web Store listing
- [ ] Firefox / Safari extensions

---

## License

MIT
