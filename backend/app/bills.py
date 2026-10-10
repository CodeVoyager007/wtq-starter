"""Web API for the bill decoder: the same bill_decoder code the command line uses.

Endpoints are plain `def`, so FastAPI runs them in its thread pool and a slow model
call never blocks other requests. Traffic is bounded three ways: upload size, a
per-IP rate limit, and a cap on decodes running at the same time.
"""
from __future__ import annotations

import re
import secrets
import threading
import time
from collections import OrderedDict, defaultdict, deque
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from bill_decoder import config as bill_config
from bill_decoder import extract, imaging
from bill_decoder.answer import answer_bill
from bill_decoder.llm import Client, Image
from bill_decoder.normalize import provider_from_bill_id

from . import config

router = APIRouter(prefix="/api/bill", tags=["bill"])

_FILE_PREFIX = {"KE": "KESC", "LESCO": "LESCO", "IESCO": "IESCO"}
_decode_slots = threading.BoundedSemaphore(config.MAX_CONCURRENT_DECODES)
_client: Client | None = None
_client_lock = threading.Lock()


class _BillStore:
    """Decoded bills for follow-up questions: in memory, bounded, oldest dropped first."""

    def __init__(self, limit: int):
        self.limit = limit
        self.items: OrderedDict[str, tuple[Image, extract.Extraction]] = OrderedDict()
        self.lock = threading.Lock()

    def add(self, image: Image, result: extract.Extraction) -> str:
        token = secrets.token_urlsafe(16)  # unguessable, so one user cannot read another's bill
        with self.lock:
            self.items[token] = (image, result)
            while len(self.items) > self.limit:
                self.items.popitem(last=False)
        return token

    def get(self, token: str) -> tuple[Image, extract.Extraction] | None:
        with self.lock:
            return self.items.get(token)


class _RateLimiter:
    """Sliding one-minute window per client IP."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            window = self.hits[key]
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= self.per_minute:
                return False
            window.append(now)
            return True


_bills = _BillStore(config.MAX_STORED_BILLS)
_limiter = _RateLimiter(config.DECODES_PER_IP_PER_MINUTE)


def _get_client() -> Client:
    global _client
    with _client_lock:
        if _client is None:
            _client = Client(bill_config.load())
    return _client


def _bill_id(filename: str, provider: str) -> str:
    """Use the file name when it already names the provider (KESC_0008.png), else prefix it."""
    stem = re.sub(r"[^A-Za-z0-9_\-]", "_", Path(filename or "bill").stem)[:60] or "bill"
    if provider_from_bill_id(stem):
        return stem
    if provider in _FILE_PREFIX:
        return f"{_FILE_PREFIX[provider]}_{stem}"
    raise HTTPException(400, "Choose the provider (KE, LESCO or IESCO): the file name does not say it.")


@router.post("")
def decode(request: Request, file: UploadFile = File(...), provider: str = Form("auto")):
    client_ip = request.client.host if request.client else "unknown"
    if not _limiter.allow(client_ip):
        raise HTTPException(429, "Too many bills from you in the last minute. Please wait a moment.")

    data = file.file.read(config.MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(400, "The file is empty.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"The image is larger than {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    bill_id = _bill_id(file.filename or "", provider.strip().upper())
    try:
        image = imaging.load_bytes(data)
    except imaging.ImageError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not _decode_slots.acquire(timeout=config.DECODE_WAIT_SECONDS):
        raise HTTPException(429, "The server is busy reading other bills. Please try again in a minute.")
    try:
        result = extract.extract_bill(_get_client(), bill_id, image)
    finally:
        _decode_slots.release()

    return {
        "token": _bills.add(image, result),
        "bill_id": bill_id,
        "level1": result.level1,
        "checks": {"issues": result.issues, "repaired": result.repaired},
        "history": result.facts.get("usage_history", []),
        "messages": (result.facts.get("transcript") or {}).get("messages_in_english", []),
    }


class Question(BaseModel):
    token: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=config.MAX_QUESTION_CHARS)


@router.post("/ask")
def ask(req: Question):
    stored = _bills.get(req.token)
    if stored is None:
        raise HTTPException(404, "This bill is no longer loaded. Upload it again.")
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Type a question about the bill.")
    image, result = stored
    answers = answer_bill(_get_client(), result.bill_id, image, result.facts, [("Q1", question)])
    return {"question": question, "answer": answers["Q1"]}
