"""Web API for the bill decoder: the same bill_decoder code the command line uses."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from bill_decoder import config as bill_config
from bill_decoder import extract, imaging
from bill_decoder.answer import answer_bill
from bill_decoder.llm import Client, Image
from bill_decoder.normalize import provider_from_bill_id

router = APIRouter(prefix="/api/bill", tags=["bill"])

_FILE_PREFIX = {"KE": "KESC", "LESCO": "LESCO", "IESCO": "IESCO"}
_BILLS: dict[str, tuple[Image, extract.Extraction]] = {}  # in memory, this session only
_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        try:
            _client = Client(bill_config.load())
        except bill_config.ConfigError as exc:
            raise HTTPException(500, str(exc)) from exc
    return _client


def _bill_id(filename: str, provider: str) -> str:
    """Use the file name when it already says the provider (KESC_0008.png), else prefix it."""
    stem = re.sub(r"[^A-Za-z0-9_\-]", "_", Path(filename or "bill").stem) or "bill"
    if provider_from_bill_id(stem):
        return stem
    if provider in _FILE_PREFIX:
        return f"{_FILE_PREFIX[provider]}_{stem}"
    raise HTTPException(400, "Choose the provider (KE, LESCO or IESCO): the file name does not say it.")


@router.post("")
async def decode(file: UploadFile = File(...), provider: str = Form("auto")):
    data = await file.read()
    if not data:
        raise HTTPException(400, "The file is empty.")
    bill_id = _bill_id(file.filename or "", provider.upper())
    try:
        image = imaging.load_bytes(data)
    except Exception as exc:  # Pillow raises several types for unreadable files
        raise HTTPException(400, "Could not read that image. Use a .png, .jpg or .webp bill photo.") from exc
    result = extract.extract_bill(_get_client(), bill_id, image)
    token = uuid.uuid4().hex[:12]
    _BILLS[token] = (image, result)
    return {
        "token": token,
        "bill_id": bill_id,
        "level1": result.level1,
        "checks": {"issues": result.issues, "repaired": result.repaired},
        "history": result.facts.get("usage_history", []),
        "messages": (result.facts.get("transcript") or {}).get("messages_in_english", []),
    }


class Question(BaseModel):
    token: str
    question: str


@router.post("/ask")
def ask(req: Question):
    if req.token not in _BILLS:
        raise HTTPException(404, "This bill is no longer loaded. Upload it again.")
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Type a question about the bill.")
    image, result = _BILLS[req.token]
    qid = "Q" + uuid.uuid5(uuid.NAMESPACE_URL, question.lower()).hex[:8]
    answers = answer_bill(_get_client(), result.bill_id, image, result.facts, [(qid, question)])
    return {"question": question, "answer": answers[qid]}
