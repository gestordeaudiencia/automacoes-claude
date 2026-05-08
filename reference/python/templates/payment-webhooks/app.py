"""
Payment Webhooks — multi-plataforma
===================================
FastAPI endpoint genérico que recebe webhooks de QUALQUER plataforma registrada
(Kiwify, Hotmart, Shopify, ...) e dispara recovery em background.

URL: POST /webhook/{platform}

    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request  # noqa: E402
from loguru import logger  # noqa: E402

from core import db  # noqa: E402
from core.config import get_settings  # noqa: E402
from core.platforms import get_adapter, list_platforms  # noqa: E402

from processor import processar_evento  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.get_pool()
    logger.info(f"Pool Postgres inicializado. Plataformas: {list_platforms()}")
    yield
    await db.close_pool()


app = FastAPI(title="Payment Webhooks (multi-plataforma)", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ok": True, "platforms": list_platforms()}


def _secret_for(platform: str) -> str:
    return os.getenv(f"{platform.upper()}_WEBHOOK_SECRET", "")


@app.post("/webhook/{platform}")
async def webhook(platform: str, request: Request, background: BackgroundTasks):
    try:
        adapter = get_adapter(platform)
    except KeyError:
        raise HTTPException(404, f"Plataforma '{platform}' não registrada")

    raw = await request.body()
    try:
        body = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        raise HTTPException(400, "JSON inválido")

    headers_lc = {k.lower(): v for k, v in request.headers.items()}
    query = dict(request.query_params)

    secret = _secret_for(platform)
    if not adapter.validate_signature(raw, headers_lc, query, secret):
        logger.warning(f"[{platform}] signature inválida, rejeitando.")
        raise HTTPException(401, "Signature inválida")

    if platform == "shopify":
        body["_topic"] = headers_lc.get("x-shopify-topic", "")

    ev = adapter.normalize(body)

    try:
        await db.insert_evento(ev)
    except Exception as e:
        logger.error(f"Falha insert evento: {e}")

    if ev.customer.user_number:
        try:
            await db.upsert_contato(
                ev.customer.user_number,
                email=ev.customer.email or None,
                nome=ev.customer.name or None,
                platform_origem=ev.platform,
            )
        except Exception as e:
            logger.error(f"Falha upsert contato: {e}")

    background.add_task(processar_evento, ev)

    return {
        "ok": True,
        "platform": ev.platform,
        "event_kind": ev.event_kind,
        "raw_event_type": ev.raw_event_type,
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.app_port)
