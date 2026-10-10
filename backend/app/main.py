"""FastAPI app for the web interface. The bill logic itself lives in bill_decoder."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bill_decoder import config as bill_config
from bill_decoder.llm import LLMError

from . import bills, config

app = FastAPI(title="Utility Bill Decoder API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.FRONTEND_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(bills.router)


@app.exception_handler(LLMError)
async def llm_error(_, exc: LLMError):
    detail = "The AI model is not responding right now. Try again in a minute."
    return JSONResponse(status_code=502, content={"detail": detail})


@app.exception_handler(bill_config.ConfigError)
async def config_error(_, exc: bill_config.ConfigError):
    return JSONResponse(status_code=500, content={"detail": f"Server is not configured: {exc}"})


@app.get("/health")
def health():
    settings = bill_config.load()
    return {"status": "ok", "model": settings.model, "api_keys": len(settings.api_keys)}
