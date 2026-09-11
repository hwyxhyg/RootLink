# RootLink Backend

Standalone FastAPI service for the Chinese and English RootLink LangGraph agents.

## Local start

1. Use Python 3.11 or 3.12.
2. Copy `.env.example` to `.env` and fill in the required values.
3. Install dependencies with `python -m pip install -r requirements.txt`.
4. Start from this directory:

```bash
uvicorn src.api.chat_sse:app --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/health`.

See `DEPLOY.md` for the production setup.
