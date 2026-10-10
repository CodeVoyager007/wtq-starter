# Utility Bill Decoder

Reads a photo or scan of a K-Electric, LESCO or IESCO electricity bill, extracts its billing
details as JSON (Level 1) and answers customer questions about it in plain English (Level 2).

Built at **Women Tech Quest 2026** (Build with AI track) by Ayesha Mughal.

## Quick start (Windows PowerShell)

Requirements: **Python 3.11** (managed by [uv](https://docs.astral.sh/uv/)) and a Gemini API key from
[Google AI Studio](https://aistudio.google.com).

```powershell
# 1. Install uv once (skip if `uv --version` works)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Configure the model and key
copy .env.example backend\.env      # then open backend\.env and set API_KEY

# 3. Install dependencies (exact versions from uv.lock)
cd backend
uv sync

# 4. Run on a folder of bills and the two CSV templates
uv run python -m bill_decoder run --bills <bills-folder> --csv <csv-folder> --out output
```

`<bills-folder>` holds the bill images (`KESC_0002.png`, `LESCO_0008.jpg`, ...).
`<csv-folder>` holds the templates `level1.csv` and `level2.csv`.
The completed files are written to `backend/output/level1.csv` and `backend/output/level2.csv`,
with a per-bill log of checks in `backend/output/run_report.json`.

On macOS/Linux the commands are the same, with `cp .env.example backend/.env`.
Without uv: `pip install -r backend/requirements.txt`, then run the same command with `python`
instead of `uv run python`, from the `backend` folder.

### Other commands

```powershell
# Score level1.csv against reference JSON files (text exact, numbers within ±1)
uv run python -m bill_decoder eval --pred output/level1.csv --truth data/train/truth

# Check the outputs against the templates (headers, row order, no empty cells, valid JSON)
uv run python -m bill_decoder check --out output --csv <csv-folder>

# Check, then build the submission ZIP (refuses if anything looks like an API key)
uv run python -m bill_decoder package --out output --csv <csv-folder> --zip submission.zip --include-cache

# Tests (no API key needed) and lint
uv run pytest -q
uvx ruff check .
```

### Web interface (optional, for the demo)

```powershell
# terminal 1, in backend/
uv run uvicorn app.main:app --port 8000
# terminal 2, in frontend/ (Node.js 20+)
npm install
npm run dev
```

Open http://localhost:3000/app, upload a bill, see the extracted details and checks, and ask questions.
The web API uses the same `bill_decoder` code as the command line. It bounds traffic: 10 MB uploads,
5 decodes per minute per client, 3 decodes in parallel (the free model tier allows about 15 requests/min),
a bounded in-memory store behind unguessable tokens, and 500-character questions.

Training example: `uv run python -m bill_decoder run --bills data/train/bills --csv data/train/csv --out output`
(the training templates were built with the `templates` command from `data/train/questions.txt`).

## How it works

```
bill image ─┬─> extraction call ──> normalize (code) ──┐
            │                                           ├─> checks (code) ──> repair call if any fail ──> level1.csv
            └─> full transcription call ───────────────┘                                                    │
                                                                                                             v
                     questions + checked facts + transcript + image ──> answer call ──> calculations (code) ──> level2.csv
```

1. **Provider from the file name.** `KESC_*` → `KE`, `LESCO_*`, `IESCO_*`. Deterministic, never asked of the model.
2. **Extraction** (1 model call per bill). The prompt carries the guide's rules plus a layout guide for that
   provider (where each value sits on a KE, LESCO or IESCO bill). The model copies values as printed strings.
3. **Normalization in code**: `Rs. 19,964` → `19964`, `54770CR` → `-54770`, `21st Apr 2026` → `2026-04-21`,
   types mapped to the allowed lists, blank and zero lines dropped, subsidies negative, the highest
   late-payment amount, combined tax figure → `taxes: []` + `total_taxes`, every field present (null if unreadable).
4. **Full transcription** (1 call): an independent second reading of everything printed (all sections,
   tables, chart bars, notices translated from Urdu), with personal identifiers hidden.
5. **Checks in code**: readings vs units, charge lines vs `total_charges`, tax lines vs `total_taxes`,
   charges + taxes vs `current_bill`, late amount ≥ on-time amount, date order, and a **cross-check**
   that every extracted amount, date, month and tariff also appears in the independent transcription.
6. **Repair** (at most 1 call): if a check fails, the model re-reads the bill with the failed checks and the
   transcript as evidence. The reading with fewer failed checks is kept.
   If a printed sum still does not add up, code corrects **one** value only when two independent sources agree:
   solving the sum gives a number that the transcript shows printed on the bill (`validate.reconcile`).
7. **Level 2** (1 call per bill for all questions): the model gets the checked facts, the transcript and the
   image. It writes the reasoning and **calculation expressions**; a safe evaluator in Python
   (`calc.py`, no `eval`) computes every number. A failed calculation is retried once with the error, then
   answered directly; no answer cell is ever left empty.

### Reliability and reproducibility

- **Same answers on a rerun**: temperature 0, fixed seed, `top_k=1`, and every model response is cached in
  `backend/.cache/` keyed by a hash of model, prompt, image and schema. A rerun reuses the cache and gives
  identical CSVs. Delete `backend/.cache` to force fresh model calls.
- **Rate limits**: client-side limiter (`REQUESTS_PER_MINUTE`), exponential backoff, and automatic switch to
  `API_KEY_BACKUP` on HTTP 429.
- **Failure handling**: a bill whose image is missing or whose calls all fail still gets a valid row
  (all fields `null`), and the failure is listed in `run_report.json` and at the end of the run.
- **Model guard**: the code refuses to start unless `MODEL_NAME` is one of the competition's allowed models.

### Calls and cost

Per bill: extraction + transcription + (repair, only if a check fails) + 1 answer call.
For 10 test bills that is about 30 to 40 calls, inside the Gemini free tier (15 requests/min, 500/day).

## Configuration

All settings are environment variables in `backend/.env` (template: `.env.example`).

| Variable | Meaning | Value used |
|---|---|---|
| `MODEL_PROVIDER` | Model provider | `google` |
| `MODEL_NAME` | Model ID | `gemini-3.5-flash-lite` |
| `API_KEY` | Gemini API key | placeholder in `.env.example` |
| `API_KEY_BACKUP` | Optional second key (different Google account) | empty |
| `REQUESTS_PER_MINUTE` | Client-side rate limit | `12` |
| `CACHE_DIR` | Cache folder, relative to `backend/` | `.cache` |
| `LLM_MOCK` | `1` = no model calls (tests only) | unset |
| `FRONTEND_ORIGINS` | Web API: allowed browser origins | `http://localhost:3000` |
| `MAX_UPLOAD_MB`, `DECODES_PER_IP_PER_MINUTE`, `MAX_CONCURRENT_DECODES` | Web API traffic limits | `10`, `5`, `3` |

## Project structure

```
backend/
  bill_decoder/          the solution (command line: python -m bill_decoder)
    __main__.py          commands: run, eval, check, package, templates
    pipeline.py          batch run: templates in, completed CSVs out
    extract.py           Level 1 flow: extract, transcribe, check, repair
    answer.py            Level 2 flow: answers with code-computed numbers
    prompts.py           all prompt text, including the per-provider layout guides
    normalize.py         numbers, dates, types, provider (no model calls)
    validate.py          consistency checks and transcript cross-check
    calc.py              safe arithmetic evaluator for answers
    llm.py               the only module that calls the model: guard, limiter, retries, cache
    imaging.py           image loading (EXIF rotation, size cap)
    schema.py            Level 1 field list and the JSON schemas sent to the model
    csv_io.py, package.py, evaluate.py, config.py
  data/train/            training bills, templates, sample questions, reference answers
  data/stress/           tilted and low-resolution copies of the training bills (robustness test)
  tests/                 unit, end-to-end and edge-case tests (mock model, no key needed)
  app/                   FastAPI web API (bills.py) used by the web interface
frontend/                Next.js web interface
docs/ARCHITECTURE.md     design notes
```

## AI usage

| Category | Used |
|---|---|
| Models called by the code | **Gemini 3.5 Flash-Lite** (`gemini-3.5-flash-lite`) via the Google AI Studio API (`google-genai` SDK). Used for bill extraction, full transcription, repair re-reads and Level 2 answers. |
| Other AI APIs or services | none |
| OCR or document-extraction services | none (no local OCR either) |
| AI tools used to write the code | Claude Code (Anthropic's Claude), used as a pair programmer for design, code and tests |

Where the model is used, and where it is not: the model reads the bill and writes explanations. Everything
with a fixed rule is code: the provider, number and date formats, type mapping, consistency checks and all
arithmetic in answers.

## Results on the training data

| Set | Level 1 fields correct |
|---|---|
| 5 training bills | 90 / 90 |
| Same bills tilted 7° and JPEG-compressed | 88 / 90 |
| Same bills at half resolution and blurred (two below 400 px wide) | 53 / 90 |

Reference answers: `KESC_0008` is the official example (guide 5.7); the other four were read by hand
(`backend/data/train/truth/README.md` lists the judgment calls).

## Limitations

- Values hidden under grey boxes or too blurry to read are returned as `null`, as the guide requires.
- Net metering bills with several meter registers: `previous_reading` and `current_reading` are `null`,
  because the bill has no single reading pair. `units_consumed` is used when one total is printed.
- The layout guides cover KE, LESCO and IESCO; another provider's bill would be read with the generic rules only.
- Level 2 answers use only what is printed on the bill; questions that need outside tariff data are answered
  with what the bill shows and a note on what it does not show.

## Team

Ayesha Mughal
