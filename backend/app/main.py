import io
import json
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bill_decoder.llm import LLMError as BillLLMError

from . import bills, config, custom, llm, store
from .modules import rag
from .modules.profiler import profile_dataframe, schema_text

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"

app = FastAPI(title="WTQ Starter API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.FRONTEND_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Vercel preview + production URLs
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(bills.router)


@app.exception_handler(BillLLMError)
async def bill_llm_error_handler(_, exc: BillLLMError):
    return JSONResponse(status_code=502, content={"detail": f"The AI model call failed: {exc}"})


@app.exception_handler(ValueError)
async def value_error_handler(_, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(llm.LLMError)
async def llm_error_handler(_, exc: llm.LLMError):
    return JSONResponse(status_code=502, content={"detail": f"The AI model call failed: {exc}"})


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mock_mode": config.mock_mode(),
        "gemini_keys": len(config.GEMINI_KEYS),
        "model": config.GEMINI_MODEL,
    }


def _read_table(name: str, raw: bytes) -> pd.DataFrame:
    lower = name.lower()
    if lower.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(raw))
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(raw), encoding="latin-1")
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(raw))
    data = json.loads(raw.decode("utf-8"))
    return pd.json_normalize(data if isinstance(data, list) else data.get("data", [data]))


def _read_document(name: str, raw: bytes) -> str:
    if name.lower().endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return raw.decode("utf-8", errors="ignore")


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    name = file.filename or "upload"
    raw = await file.read()
    lower = name.lower()
    if lower.endswith((".csv", ".xlsx", ".xls", ".json")):
        df = _read_table(name, raw)
        dataset_id = store.add_dataset(name, df)
        return {"kind": "dataset", "dataset_id": dataset_id, "name": name, "profile": profile_dataframe(df)}
    if lower.endswith((".txt", ".md", ".pdf")):
        text = _read_document(name, raw)
        chunks = rag.add_document(name, text)
        if chunks == 0:
            raise ValueError("Could not read any text from that file.")
        return {"kind": "document", "name": name, "chunks": chunks}
    raise HTTPException(400, "Unsupported file type. Use .csv .xlsx .json .txt .md or .pdf")


@app.post("/api/sample")
def load_sample():
    """Loads the bundled demo table + demo document so you can test the whole app with no files."""
    df = pd.read_csv(SAMPLE_DIR / "support_tickets.csv")
    dataset_id = store.add_dataset("support_tickets.csv", df)
    rag.reset()
    rag.add_document("faq.txt", (SAMPLE_DIR / "faq.txt").read_text(encoding="utf-8"))
    return {
        "kind": "dataset",
        "dataset_id": dataset_id,
        "name": "support_tickets.csv",
        "profile": profile_dataframe(df),
        "also_loaded_document": "faq.txt",
    }


class RunRequest(BaseModel):
    mode: str = "analyze"
    input: str = ""
    dataset_id: str | None = None
    options: dict = {}


@app.post("/api/run")
def run(req: RunRequest):
    return custom.run(req.model_dump())


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    dataset_id: str | None = None


@app.post("/api/chat")
def chat(req: ChatRequest):
    context = ""
    if req.dataset_id and req.dataset_id in store.DATASETS:
        context = "The user is working with this table:\n" + schema_text(store.get_df(req.dataset_id)) + "\n\n"
    history = "\n".join(f"{m.role}: {m.content}" for m in req.history[-8:])
    prompt = f"{context}Conversation so far:\n{history}\n\nuser: {req.message}\nassistant:"
    reply = llm.generate(
        prompt,
        system="You are a friendly, concise assistant inside a data and AI app. Keep answers short and clear.",
        temperature=0.4,
        mock="[mock] This is a mock reply. Add your Gemini key in backend/.env to get real answers.",
    )
    return {"reply": reply}
