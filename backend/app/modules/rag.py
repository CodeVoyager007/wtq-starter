"""Pattern 2: ask questions about documents (RAG).

Retrieval uses TF-IDF (no embedding API, so no extra rate limits and it works offline).
If you need smarter search on the day, swap search() for Gemini embeddings. Nothing else changes.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .. import llm
from ..schema import result

STATE: dict = {"chunks": [], "vec": None, "matrix": None}

PROMPT = """Answer the question using ONLY the context below. If the answer is not in the context, say you could not find it.
Mention the source numbers you used like [1] or [2].

Context:
{context}

Question: {question}"""


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + size])
        if start + size >= len(text):
            break
        start += size - overlap
    return chunks


def _rebuild() -> None:
    texts = [c["text"] for c in STATE["chunks"]]
    if not texts:
        STATE.update(vec=None, matrix=None)
        return
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vec.fit_transform(texts)
    except ValueError:  # tiny text where every word is a stop word
        vec = TfidfVectorizer()
        matrix = vec.fit_transform(texts)
    STATE.update(vec=vec, matrix=matrix)


def reset() -> None:
    STATE.update(chunks=[], vec=None, matrix=None)


def add_document(name: str, text: str) -> int:
    pieces = chunk_text(text)
    for p in pieces:
        STATE["chunks"].append({"source": name, "text": p})
    _rebuild()
    return len(pieces)


def search(query: str, k: int = 4) -> list[dict]:
    if not STATE["chunks"]:
        raise ValueError("No documents loaded. Upload a .txt, .md or .pdf file first (or click 'Load sample data').")
    q = STATE["vec"].transform([query])
    scores = cosine_similarity(q, STATE["matrix"]).ravel()
    order = scores.argsort()[::-1][:k]
    return [{**STATE["chunks"][i], "score": float(scores[i])} for i in order if scores[i] > 0] or [
        {**STATE["chunks"][i], "score": float(scores[i])} for i in order[:2]
    ]


def answer(question: str, k: int = 4) -> dict:
    hits = search(question, k)
    context = "\n\n".join(f"[{i + 1}] ({h['source']}) {h['text']}" for i, h in enumerate(hits))
    text = llm.generate(PROMPT.format(context=context, question=question), mock="[mock] Answer from the documents [1].")
    sources = [{"n": i + 1, "source": h["source"], "snippet": h["text"][:220], "score": round(h["score"], 3)} for i, h in enumerate(hits)]
    return result("text", title=question, text=text, sources=sources)
