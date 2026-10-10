# Project Name

> One clear sentence: what it does and who it helps.

Built at **Women Tech Quest 2026** (Build with AI stream) by Ayesha Mughal.

**Live demo:** _paste Vercel link_  ·  **Video / screenshots:** _add after the demo_

## The problem

_Two or three simple sentences. Who has this problem? Why does it matter?_

## What we built

_Three bullets. What can a user do in the app?_

- _Upload data or paste text_
- _Ask a question / run the analysis_
- _Get an answer with a table, a chart and proof (code or sources)_

## How it works

```
Browser (Next.js)  ->  FastAPI backend  ->  Gemini + pandas / scikit-learn  ->  answer
```

1. The user adds a file or text in the **Workspace** page.
2. The backend looks at the data first (columns, types, missing values).
3. Gemini reasons over a short summary, the backend runs the steps and checks the result.
4. The UI shows the answer, a table or chart, and the code or sources that were used.

Built-in modes (each is one small file in `backend/app/modules/`):

| Mode | What it does | File |
|---|---|---|
| Analyze data | Plain English question -> pandas code -> answer | `csv_analyst.py` |
| Ask documents | Search text/PDF files and answer with sources (RAG) | `rag.py` |
| Extract / Classify | Messy text -> structured fields or labels | `extraction.py` |
| Predict | Quick scikit-learn baseline with honest metrics | `ml_stub.py` |
| Custom | Your own logic for the challenge | `custom.py` -> `solve_challenge()` |

## Tech stack

Next.js 16, Tailwind CSS 4, FastAPI, Python 3.11, pandas, scikit-learn, Google Gemini (`google-genai`).

## Run it on your laptop (Windows PowerShell)

Install once: [Node.js 20+](https://nodejs.org) and uv (`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`).

**Terminal 1: backend**

```powershell
cd backend
uv sync
copy .env.example .env      # then open .env and paste your GEMINI_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```

**Terminal 2: frontend**

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Open http://localhost:3000, go to **Workspace**, and click **Load sample data**.

No key yet? Set `LLM_MOCK=1` in `backend/.env` and the whole app runs with fake AI answers. Good for testing the screens.

**Check everything works (before the event):**

```powershell
cd backend
uv run pytest -q
```

## Environment variables

| Where | Name | Meaning |
|---|---|---|
| backend/.env | `GEMINI_API_KEY` | Your main Gemini key |
| backend/.env | `GEMINI_API_KEY_BACKUP` | Second key, used automatically if the first hits a limit |
| backend/.env | `GEMINI_MODEL` | Model name (default `gemini-2.5-flash`). Check it still exists in Google AI Studio |
| backend/.env | `FALLBACK_*` | Optional Groq/OpenRouter backup (see `.env.example`) |
| backend/.env | `FRONTEND_ORIGINS` | Allowed frontend URLs (`*.vercel.app` is already allowed) |
| frontend/.env.local | `NEXT_PUBLIC_API_URL` | Backend URL (`http://localhost:8000` locally) |

Never commit `.env` files. They are in `.gitignore`.

## Deploy (only if you have 30+ minutes left)

**Backend on Render:** New > Blueprint > pick this repo (it reads `render.yaml`). Add `GEMINI_API_KEY` and `GEMINI_API_KEY_BACKUP` in the dashboard. Free plans sleep, so open `<your-backend>/health` about 5 minutes before you demo.

**Frontend on Vercel:** Import the repo, set **Root Directory** to `frontend`, add `NEXT_PUBLIC_API_URL` = your Render URL, deploy.

If you add a Python package, refresh the deploy list: `cd backend; uv export --no-hashes --no-dev --no-emit-project > requirements.txt`.

## Project structure

```
backend/
  app/main.py            API routes (upload, run, chat, sample)
  app/custom.py          EVENT DAY: the one file to edit for the challenge
  app/llm.py             Gemini calls, retries, backup key, fallback provider
  app/modules/           the 4 AI patterns + data profiler
  sample_data/           demo table + demo FAQ document
  scripts/profile_data.py   profile any file from the terminal
  tests/test_smoke.py    proves all modes work
frontend/
  lib/config.ts          EVENT DAY: names, text, steps (edit this first)
  app/globals.css        theme colors and fonts (one block)
  app/                   Home, Workspace (/app), How it works
  components/            Workspace, ResultView, ChatBox, charts, tables
```

## Limitations and next steps

_Be honest, judges like it. Example: answers depend on data quality; large files are trimmed; no user accounts yet._

## Team

Ayesha Mughal
