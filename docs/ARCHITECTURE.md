# Utility Bill Decoder: Architecture and System Design

Status: draft v1 (before judging criteria review). Owner: Ayesha Mughal.

## 1. Goal and constraints

Turn a photo or scan of a K-Electric, LESCO or IESCO bill into:

- **Level 1**: one JSON object per bill (fixed schema, guide section 5), written to `level1.csv`.
- **Level 2**: plain-English answers to 12 questions per bill (120 rows), written to `level2.csv`.

Hard constraints from the participant guide:

| Constraint | Design consequence |
|---|---|
| Only 5 LLMs allowed, any other = disqualification | Model allow-list enforced in code; the run aborts before any call if `MODEL_NAME` is not on it. No silent fallback provider. |
| Gemini free tier: 15 req/min, 500 req/day | Client-side rate limiter, disk cache of every model response, 2 keys rotated on 429. |
| Single submission, no hand edits | The pipeline writes the CSVs itself. A packaging command validates and zips. |
| Numbers scored within ±1, text/dates exact | Deterministic post-processing in code. The LLM only reads the bill. |
| `null` is scored correct when a value is missing | The model never guesses: "if not printed or covered, null". Code never fills gaps with invented values. |
| Python 3.11+, pinned `requirements.txt` | Reuse the starter's `backend/` uv project. |

## 2. What the training bills tell us

| Bill | Layout facts that matter |
|---|---|
| KESC_0008 | Full itemised "Bill Calculation" table, two energy lines, two late-payment amounts (take highest), credit arrears `-0.53`. Ground truth available (guide 5.7). |
| KESC_0004 | Net metering: 4 meter registers (off peak, peak, import), `-1,442.74` negative quarterly adjustment, "Net Metering Benefit" printed **below** the charges section, all payable amounts `0`. |
| LESCO (Jul 26) | Phone photo, tilted. Net metering with 4 meter rows. **No itemised charges**, only summary lines. `54770CR` means negative. "NOT TO BE PAID" for the late amount. History has negative units. |
| LESCO (Aug 26) | Summary-only charges. Arrears printed as `39411 / 2` (odd format). Two late amounts `45088` / `45263` (take highest). |
| IESCO_0004 | Summary charges plus a **Subsidies** line (`3332`, record as negative), `Total FPA 267` in a side column, printed percentage split (84.76% / 15.24%). |

Takeaways:

1. **Three layout families, and the provider is known from the file name.** We give the model a layout guide for that provider. This is the biggest accuracy lever.
2. **LESCO and IESCO print only a combined tax figure.** Rule 5.3 says `taxes: []` and the figure goes in `total_taxes`. The model will get this wrong unless told for each provider.
3. **Net metering bills are the trap**: several readings and a units figure that is open to interpretation. Rule: take "units" as printed for the billed month, and the readings from the main import register.
4. **Level 2 questions use data outside the Level 1 schema**: usage history, payment history, rates, percentages, late-payment amounts. We must extract it.

## 3. Architecture

```
                 bills/*.png|jpg            csv/level1.csv, csv/level2.csv
                        |                               |
                        v                               v
+-----------------------------------------------------------------------+
| cli.py   run | eval | package                                         |
+-----------------------------------------------------------------------+
        |                    |                          |
        v                    v                          v
+----------------+   +-------------------+    +---------------------+
| pipeline.py    |   | answer.py (L2)    |    | csv_io.py           |
| per bill:      |   | facts + image +   |    | read templates,     |
|  image ->      |-->| 12 questions ->   |--->| keep order, write   |
|  extract ->    |   | answers with      |    | one-line JSON, UTF-8|
|  normalize ->  |   | calc expressions  |    +---------------------+
|  validate ->   |   |  -> calc.py       |
|  repair once   |   +-------------------+
+----------------+            |
   |      |      |            |
   v      v      v            v
imaging  normalize  validate   calc.py (safe arithmetic evaluator)
 .py      .py        .py
   \______________________________/
                  |
                  v
+-----------------------------------------------------------------------+
| llm.py  Gemini client: allow-list guard, rate limiter, key rotation,  |
|         retry with backoff, JSON schema output, disk cache             |
+-----------------------------------------------------------------------+
```

Package layout (`backend/bill_decoder/`, independent of the FastAPI app so the
frontend can call the same code later):

| Module | Responsibility | Uses the LLM? |
|---|---|---|
| `config.py` | Env vars, model allow-list, paths | no |
| `schema.py` | Pydantic models: `Level1Bill` (scored schema), `BillFacts` (Level 1 plus history, rates, notes) | no |
| `imaging.py` | Load, EXIF-rotate, cap long side ~2400 px, encode | no |
| `llm.py` | The only module that talks to the model | yes |
| `prompts.py` | System prompt, provider layout guides, Level 2 rules | no |
| `extract.py` | Image to raw `BillFacts` dict (1 call), repair call (only when validation fails) | yes |
| `normalize.py` | Numbers (`Rs. 19,964` to 19964, `38209CR` to -38209), dates, enum mapping, drop zero lines, provider from file name, highest late amount, strip PII keys | no |
| `validate.py` | Consistency checks, return a list of issues | no |
| `calc.py` | AST-based evaluator: numbers, + - * / ( ), `sum`, `avg`, `min`, `max`, `round`, `abs` | no |
| `answer.py` | Level 2: one call per bill for all 12 questions, evaluate calcs, render text | yes |
| `csv_io.py` | Template in, completed CSV out, never drop or reorder rows | no |
| `evaluate.py` | Score Level 1 against ground truth (exact text, numbers ±1) | no |
| `package.py` | Check outputs, build the submission ZIP, size check, secret scan | no |
| `cli.py` | `run`, `eval`, `package` commands | no |

## 4. Level 1 flow (per bill)

1. **Provider** from the file name prefix (`KESC` to `KE`, `LESCO`, `IESCO`). Deterministic and never asked of the model.
2. **Image prep**: EXIF transpose, RGB, downscale only if the long side > 2400 px. No heavy OCR preprocessing; the model handles tilt and Urdu better than Tesseract.
3. **Extract** (1 call): system prompt with the rules from guide 5.2 to 5.4 plus the provider layout guide. `response_schema = BillFacts`, temperature 0. The model returns printed strings for amounts (for example `"54770CR"`), so sign and format handling stays in code.
4. **Normalize** (code): the rules above, then build the exact `Level1Bill` with every key present.
5. **Validate** (code), each check tolerant to ±1:
   - `current_reading - previous_reading == units_consumed` (skipped for net metering / multi-register)
   - `sum(charges) == total_charges` when both are present
   - `sum(taxes) == total_taxes` when taxes are itemised
   - `total_charges + total_taxes == current_bill` (KE)
   - `payable_after_due_date >= payable_within_due_date`
   - dates are valid and `issue_date <= due_date`
6. **Full transcription** (1 call, independent second reading): every section, label/value pair, table row, chart bar and notice (Urdu translated), with identifiers hidden. Used twice:
   - **cross-check**: every extracted amount must appear somewhere in the transcript, otherwise it is flagged as a likely misread;
   - **Level 2 context**: any question about anything printed on the bill can be answered, not only the fields we chose.
7. **Repair** (at most 1 extra call): only if a check fails, re-ask with the image, the previous JSON, the failed checks and the transcript as evidence. Keep the version with fewer failures. Never "fix" numbers in code: the guide says report as printed.
8. **Fail-safe**: if every call fails, write the all-`null` schema and log it. A cell is never empty.

Call budget: 10 test bills = 20 calls (extract + transcript), plus at most 10 repairs.

## 5. Level 2 flow (per bill)

1. Input: the bill image, the normalized `BillFacts` JSON, and the 12 questions.
2. One call. The model returns, for every question:
   ```json
   {"question_id": "Q1",
    "calcs": {"tax_share": "569.62 / 3430.24 * 100"},
    "answer": "Taxes total PKR 569.62 of PKR 3,430.24, about {tax_share:.1f}%."}
   ```
3. `calc.py` evaluates every expression (no `eval`, AST allow-list), then fills the placeholders. If an expression fails, we fall back to the model's own text without placeholders, so the answer is still never empty.
4. Prompt rules from guide 6.1: only use bill data, say clearly when a value is not on the bill, label estimates and show the method, state the interpretation when a question is ambiguous, English only, no identifiers.
5. After 12:30, when the real 12 questions are known, add deterministic helpers for any question that is purely arithmetic (for example averages over the usage history).

Call budget: 10 calls, so 1 full test run is about 30 to 40 calls (3 to 4 minutes at 12/min), well inside the free tier.

## 6. Reliability

| Risk | Mitigation |
|---|---|
| 429 / quota when the whole room runs at 12:30 | Token-bucket limiter (12 req/min), exponential backoff, rotate to backup key, cache means a rerun only redoes failures |
| Malformed JSON | Gemini structured output with schema, then a Pydantic parse, then one retry |
| Model returns a non-allowed enum | Mapped in `normalize.py` (`FCA` to `fpa`, `ED` to `electricity_duty`, unknown to `other` / `other_tax`) |
| Wrong model name in `.env` | Allow-list guard aborts at startup |
| CSV quoting bugs | Python `csv` module, `QUOTE_MINIMAL`, `json.dumps(..., ensure_ascii=False)` one line |
| PII leak | Schema has no PII fields; the prompt forbids them; a final scrub on known ID patterns in answers |
| Non-determinism | Temperature 0 plus cache keyed by `sha256(model, prompt, image, schema)` |

## 7. Configuration (`.env.example`)

```
MODEL_PROVIDER=google
MODEL_NAME=gemini-3.5-flash-lite
API_KEY=your-api-key-here
API_KEY_BACKUP=
REQUESTS_PER_MINUTE=12
CACHE_DIR=.cache
```

## 8. Commands

```
uv run python -m bill_decoder run     --bills <dir> --csv <dir> --out output/
uv run python -m bill_decoder eval    --pred output/level1.csv --truth data/truth.json
uv run python -m bill_decoder package --out output/ --zip submission.zip
```

## 9. Testing

- Unit tests (no API key): normalize, validate, calc, csv_io, package.
- Golden test: KESC_0008 normalized output matches guide 5.7 (needs one live call, or the cached response).
- Smoke: mock LLM mode runs the full pipeline end to end on the training folder.

## 10. Out of scope until the core scores

- Frontend changes (kept intact; later it can call `bill_decoder` through one FastAPI route for the demo).
- Local OCR (allowed, but adds install risk; reconsider only if the model misreads digits).
- Self-consistency voting (n=3) on extraction: only if the quota allows after the core works.
