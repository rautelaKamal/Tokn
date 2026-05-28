# Tokn — Prompt Optimizer

> **Grammarly for AI prompts.** Compress, clarify, and quantify token savings in real time — right inside ChatGPT, Claude, Gemini, and Perplexity.

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Deployed-black?logo=vercel)](https://tokn-nine.vercel.app)
![Chrome Extension](https://img.shields.io/badge/Manifest-V3-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal)
![Groq](https://img.shields.io/badge/Groq-Llama_3.1_8B_Instant-orange)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## How It Works

```
User types prompt → Extension detects input (1500ms typing-pause debounce)
  → Read selected compression level (Safe, Balanced, Aggressive)
  
  IF Safe (JS only, offline):
    → Runs compressor.js (lossless filler stripping) 
    → Instantly updates UI & saves tokens locally (no API call)

  IF Balanced / Aggressive (JS + API):
    → Runs compressor.js (lossless pre-cleaning)
    → Sends cleaned prompt + level to FastAPI backend
    → FastAPI uses Groq Llama 3.1 8B Instant (with temperature tuned for level)
    → Returns semantic/structural optimization
    
  → Floating panel shows optimized prompt + token/cost savings
  → One-click "Use this prompt" swaps input text
```

1. **Content script** auto-detects the AI platform's text input and intelligently hides the panel during typing to prevent flashing.
2. **Compressor** executes client-side lossless filler removal, saving tokens and network bandwidth before backend delivery.
3. **Service worker** manages state, coordinates level routing, and handles backend API proxying.
4. **Backend** uses Groq (Llama 3.1 8B Instant) to semantically structure, condense, and rewrite the prompt.
5. **Floating panel** displays the optimized prompt, tokens saved, and cost saved.
6. **Popup UI** allows switching compression levels, configuring API keys, tracking daily savings, and toggling **Local Dev Mode**.

---

## 3-Tier Compression Levels

| Level | Engine | Expected Savings | Description & Techniques |
| :--- | :--- | :--- | :--- |
| **🟢 Safe** | JS Only (Offline) | ~15% - 30% | Lossless filler stripping, phrase compaction, comparison shortcuts. Zero API cost. |
| **🟡 Balanced** | JS + Groq API | ~40% - 55% | Pre-cleaned via JS, then optimized by Llama 3.1 8B (temp=0.2). Smart semantic simplification. |
| **🔴 Aggressive** | JS + Groq API | ~55% - 80% | Pre-cleaned via JS, then compressed by Llama 3.1 8B (temp=0.1). High-density rephrasing, colon-stacking. |

---

## 🔬 Context Preservation & Performance Audit

A programmatic audit comparing verbose original prompts against Tokn's optimized prompts was conducted to verify context preservation. The audit evaluated named technologies, formatting parameters, explicit constraints, and numeric values.

### Audit Summary:
- **Average Token Savings**: **62.3%**
- **Average Response Latency**: **0.40 seconds** (Vercel Mumbai Edge ➔ Groq Llama 3.1)
- **Functional Context Retained**: **100%** (All technical constraints, output formats, and named frameworks preserved).

### Examples:
- **Software Architecture Prompt**: Compressed from **205 tokens** to **70 tokens (65.9% savings)**.
  - *Original*: Polite intro + requests for highly scalable multi-tenant Node/PostgreSQL/Redis/Kafka/K8s SaaS platform for 100k concurrent users, JWT+OAuth auth, RBAC, DB sharding, CI/CD, observability, DR, markdown tables, and cost <$10k/mo.
  - *Optimized*: `Design multi-tenant SaaS PM platform (100k concurrent, Node/PostgreSQL/Redis/Kafka/K8s): JWT+OAuth auth, RBAC, rate limiting, DB sharding, CI/CD, observability, DR. Output: architecture, sequence diagrams, microservices tables (markdown), AWS cost <$10k/mo.`
  - *Audit Score*: **9/10 (PASS)**
- **FastAPI Code Generation**: Compressed from **127 tokens** to **27 tokens (78.7% savings)**.
  - *Original*: Polite greeting + request to write a FastAPI REST API for user registration and login, password hashing with bcrypt, JWT tokens, JSON responses, type hints, and code comments.
  - *Optimized*: `FastAPI REST API: user registration, login, secure password hashing (bcrypt/passlib), JWT auth, JSON responses, type hints.`
  - *Audit Score*: **8/10 (PASS)**

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
│   ├── vercel.json       # Vercel Serverless routing & India bom1 edge config
│   ├── tests/            # Pytest suite (6/6 passing)
│   ├── Dockerfile        # Container setup for Render / cloud deployment
│   ├── requirements.txt
│   └── .env.example
├── extension/            # Chrome Extension (MV3)
│   ├── manifest.json     # Permissions, host matching, icons
│   ├── background.js     # Service worker — handles routing, state, API requests
│   ├── compressor.js     # Shared client-side lossless compression engine
│   ├── content.js        # Input detection, 1.5s typing pause debounce, floating panel
│   ├── content.css       # Panel styling (dark card, green badges)
│   ├── popup.html/js/css # Extension popup UI with level selector and Local Dev Toggle
│   ├── config.js         # Centralized config (Vercel production URL)
│   └── icons/            # 16/48/128px extension icons
└── frontend/             # Marketing & Landing Page
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
4. **Instant Offline Testing**: Click the Tokn browser popup and toggle **Local Dev Mode** on. It will immediately route all extension API traffic to your local `http://localhost:8000` server.

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

---

## Extension Architecture

### Message Flow

```
content.js  ──TOKn_OPTIMIZE──▸  background.js  ──fetch──▸  FastAPI /optimize/
             ◂──response.data──               ◂──JSON────
```

### Key Design Decisions

- **No API keys in extension code** — all Groq API interactions are handled on the server.
- **1.5-second typing pause debounce** — prevents excessive API requests during active writing, hiding the panel completely while you type.
- **Local Dev Mode Toggle** — lets you instantly switch extension traffic to `localhost:8000` with one click for easy offline debugging.
- **Hybrid Optimization Pipeline** — client-side JS pre-cleans prompts for API calls, maximizing token efficiency and reducing prompt payloads.
- **Offline Safe Mode** — allows zero-latency, local-only compression without consuming API key quotas.
- **Daily savings tracker** — saved in `chrome.storage.local` with automatic daily reset.
- **MutationObserver** — handles dynamic UI updates across single-page applications.

---

## Deployment

The backend is configured for automated deployments to **Vercel** via git push triggers:
- **Production URL**: `https://tokn-nine.vercel.app`
- **Function Region**: Mumbai, India (`bom1`) for ultra-low latency.
- **Environment config**: Requires `GROQ_API_KEY` and `GROQ_MODEL=llama-3.1-8b-instant`.

### ⚡ 1-Click Vercel Deploy:

Deploy your own private, fast prompt optimizer backend to Vercel in seconds:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FrautelaKamal%2FTokn&root-directory=backend&env=GROQ_API_KEY,GROQ_MODEL,ENVIRONMENT,CORS_ORIGINS)

---

## License

MIT
