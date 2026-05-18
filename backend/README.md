# Tokn Backend

FastAPI service for prompt optimization.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY
```

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs for interactive API docs.

## Core endpoint

`POST /api/v1/optimize`

```json
{
  "prompt": "I was wondering if you could maybe help me write a really good email..."
}
```

Response includes `optimized_prompt`, `tokens_before`, `tokens_after`, `tokens_saved`, and `cost_saved_usd`.
