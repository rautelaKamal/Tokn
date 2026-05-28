# Tokn — Prompt Optimizer

> **Grammarly for AI prompts.** Compress, clarify, and quantify token savings in real time — right inside ChatGPT, Claude, Gemini, and Perplexity.

![Chrome Extension](https://img.shields.io/badge/Manifest-V3-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## How It Works

```
User types prompt → Extension detects input (800ms debounce)
  → Read selected compression level (Safe, Balanced, Aggressive)
  
  IF Safe (JS only, offline):
    → Runs compressor.js (lossless filler stripping) 
    → Instantly updates UI & saves tokens locally (no API call)

  IF Balanced / Aggressive (JS + API):
    → Runs compressor.js (lossless pre-cleaning)
    → Sends cleaned prompt + level to FastAPI backend
    → FastAPI uses Groq Llama 3.3 70B (with temperature tuned for level)
    → Returns semantic/structural optimization
    
  → Floating panel shows optimized prompt + token/cost savings
  → One-click "Use this prompt" swaps input text
```

1. **Content script** auto-detects the AI platform's text input.
2. **Compressor** executes client-side lossless filler removal, saving tokens and network bandwidth before backend delivery.
3. **Service worker** manages state, coordinates level routing, and handles backend API proxying.
4. **Backend** uses Groq (Llama 3.3 70B) to semantically structure, condense, and rewrite the prompt.
5. **Floating panel** displays the optimized prompt, tokens saved, and cost saved.
6. **Popup UI** allows switching compression levels, configuring API keys, and tracking daily savings.

---

## 3-Tier Compression Levels

| Level | Engine | Expected Savings | Description & Techniques |
| :--- | :--- | :--- | :--- |
| **🟢 Safe** | JS Only (Offline) | ~15% - 30% | Lossless filler stripping, phrase compaction, comparison shortcuts. Zero API cost. |
| **🟡 Balanced** | JS + Groq API | ~40% - 55% | Pre-cleaned via JS, then optimized by Llama 3.3 70B (temp=0.2). Smart semantic simplification. |
| **🔴 Aggressive** | JS + Groq API | ~55% - 70% | Pre-cleaned via JS, then compressed by Llama 3.3 70B (temp=0.1). High-density rephrasing, colon-stacking. |

---

## Monorepo Layout

```
Tokn/
├── backend/              # FastAPI API server
│   ├── app/
│   │   ├── api/          # Route handlers (/health, /optimize)
│   │   ├── core/         # Config, dependencies (Groq SDK settings)
│   │   ├── schemas/      # Pydantic models (OptimizeRequest, OptimizeResponse)
│   │   ├── services/     # Tokenizer, optimizer, cost calculator
│   │   └── main.py       # App entry point
│   ├── tests/            # Pytest suite (6/6 passing)
│   ├── Dockerfile        # Container setup for Render / cloud deployment
│   ├── requirements.txt
│   └── .env.example
├── extension/            # Chrome Extension (MV3)
│   ├── manifest.json     # Permissions, host matching, icons
│   ├── background.js     # Service worker — handles routing, state, API requests
│   ├── compressor.js     # Shared client-side lossless compression engine
│   ├── content.js        # Input detection, debounce, floating panel controller
│   ├── content.css       # Panel styling (dark card, green badges)
│   ├── popup.html/js/css # Extension popup UI with level selector (segmented control)
│   ├── config.js         # Centralized config (production Render URL, selectors)
│   └── icons/            # 16/48/128px extension icons
└── frontend/             # Marketing & Landing Page (deployed)
```

---

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure your Groq API key
cp .env.example .env
# Edit .env → set GROQ_API_KEY=gsk_... (get free key at https://console.groq.com)
```

Start the local server:
```bash
uvicorn app.main:app --reload --port 8000
```
Verify: `http://localhost:8000/docs` — Swagger UI should load.

### 2. Chrome Extension

1. Open `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle).
3. Click **Load unpacked** → select the `extension/` folder.
4. Open the extension popup in your browser toolbar to verify connection status or change compression levels.
5. Navigate to any supported AI site (e.g., ChatGPT) and start typing to see the optimizer panel in action.

### 3. Test the API (no browser needed)

```bash
curl -s -X POST http://localhost:8000/api/v1/optimize/ \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Please could you kindly help me write a good email", "level":"balanced"}' | python3 -m json.tool
```

---

## Supported Platforms

| Platform    | URL                          | Input Selector                      |
|-------------|------------------------------|-------------------------------------|
| ChatGPT     | `chat.openai.com`, `chatgpt.com` | `div[contenteditable="true"]`, `#prompt-textarea` |
| Claude      | `claude.ai`                  | `div[contenteditable="true"]`       |
| Gemini      | `gemini.google.com`          | `rich-textarea`, `div[contenteditable="true"]` |
| Perplexity  | `perplexity.ai`              | `textarea[placeholder]`, `textarea`  |

---

## API Endpoints

| Method | Endpoint              | Description                      |
|--------|-----------------------|----------------------------------|
| GET    | `/api/v1/health`      | Health check                     |
| POST   | `/api/v1/optimize/`   | Optimize a prompt using specified level |

### POST `/api/v1/optimize/`

**Request:**
```json
{
  "prompt": "I was wondering if you could write a REST API in Python using FastAPI that handles user authentication and returns JSON responses",
  "level": "balanced"
}
```

**Response:**
```json
{
  "original_prompt": "I was wondering if you could write a REST API in Python using FastAPI that handles user authentication and returns JSON responses",
  "optimized_prompt": "FastAPI REST API: user auth, JSON responses.",
  "tokens_before": {
    "tokens": 25,
    "estimated_cost_usd": 0.0
  },
  "tokens_after": {
    "tokens": 9,
    "estimated_cost_usd": 0.0
  },
  "tokens_saved": 16,
  "cost_saved_usd": 0.0,
  "compression_ratio": 0.64,
  "model_used": "llama-3.3-70b-versatile",
  "encoding_used": "cl100k_base"
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

- **No API keys in extension code** — all Groq API interactions are handled on the server.
- **800ms debounce** — prevents excessive API requests during active typing.
- **Hybrid Optimization Pipeline** — client-side JS pre-cleans prompts for API calls, maximizing token efficiency and reducing prompt payloads.
- **Offline Safe Mode** — allows zero-latency, local-only compression without consuming API key quotas.
- **Daily savings tracker** — saved in `chrome.storage.local` with automatic daily reset.
- **MutationObserver** — handles dynamic UI updates across single-page applications.

### Storage Keys

| Key                       | Type    | Description                    |
|---------------------------|---------|--------------------------------|
| `tokn_enabled`            | boolean | Global extension state (on/off) |
| `tokn_tokens_saved_today` | number  | Running token savings total for the current day |
| `tokn_tokens_saved_date`  | string  | ISO date string for tracking daily resets |
| `tokn_last_site`          | object  | Details of the last active supported AI platform |
| `tokn_compression_level`  | string  | Active compression mode (`safe`, `balanced`, `aggressive`) |
| `tokn_api_key`            | string  | Optional client authorization key (if backend auth is enabled) |

---

## Deployment

The backend is configured for automated deployments to **Render** via git push triggers:
- **Production URL**: `https://tokn-pbie.onrender.com`
- **Environment config**: Requires `GROQ_API_KEY` and `GROQ_MODEL=llama-3.3-70b-versatile` (free tier offers 14,400 requests per day).

---

## License

MIT
