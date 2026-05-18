# Tokn Chrome Extension (MV3)

Real-time prompt optimization on ChatGPT, Claude, Gemini, and Perplexity.

## Load unpacked

1. Start the backend: `cd ../backend && uvicorn app.main:app --reload --port 8000`
2. Open `chrome://extensions` → enable **Developer mode**
3. **Load unpacked** → select this `extension/` folder
4. Open a supported AI site and type in the prompt box (wait ~800ms after you stop typing)

## Configure API URL

Edit `config.js` → `API_BASE_URL` for production (e.g. `https://api.tokn.app`).

No API keys belong in the extension — all AI calls go through FastAPI.

## Files

| File | Role |
|------|------|
| `manifest.json` | MV3 permissions and content script registration |
| `background.js` | Service worker → `POST /api/v1/optimize/` |
| `content.js` | Site detection, debounce, floating panel |
| `popup.html` / `popup.js` | Toggle + daily token savings |
| `content.css` | Panel styles (dark card, green badge) |
| `config.js` | Backend URL only |
