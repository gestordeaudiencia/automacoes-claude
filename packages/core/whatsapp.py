"""WhatsApp driver pluggable. Adiciona um novo provider implementando _send_<driver>."""
import httpx
from loguru import logger

from .config import get_settings


async def send_message(phone: str, message: str) -> dict:
    """phone: número limpo (sem @s.whatsapp.net). Retorna resposta do provider."""
    settings = get_settings()
    phone_clean = phone.replace("@s.whatsapp.net", "")
    driver = settings.whatsapp_driver

    if driver == "avisaapi":
        return await _send_avisaapi(phone_clean, message, settings)
    if driver == "evolution":
        return await _send_evolution(phone_clean, message, settings)
    if driver == "zapi":
        return await _send_zapi(phone_clean, message, settings)
    raise ValueError(f"WhatsApp driver desconhecido: {driver}")


async def _send_avisaapi(phone: str, message: str, settings) -> dict:
    headers = {"Authorization": f"Bearer {settings.whatsapp_api_token}"}
    body = {"number": phone, "message": message}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(settings.whatsapp_api_url, headers=headers, json=body)
        r.raise_for_status()
        logger.info(f"AvisaAPI → {phone}: {r.status_code}")
        return r.json()


async def _send_evolution(phone: str, message: str, settings) -> dict:
    # Evolution API: POST {url}/message/sendText/{instance}
    headers = {"apikey": settings.whatsapp_api_token}
    body = {"number": phone, "text": message}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(settings.whatsapp_api_url, headers=headers, json=body)
        r.raise_for_status()
        logger.info(f"Evolution → {phone}: {r.status_code}")
        return r.json()


async def _send_zapi(phone: str, message: str, settings) -> dict:
    # Z-API: POST {url} com Client-Token header
    headers = {"Client-Token": settings.whatsapp_api_token}
    body = {"phone": phone, "message": message}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(settings.whatsapp_api_url, headers=headers, json=body)
        r.raise_for_status()
        logger.info(f"Z-API → {phone}: {r.status_code}")
        return r.json()
