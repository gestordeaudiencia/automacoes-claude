from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from .config import get_settings
from .platforms import NormalizedEvent

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def acquire():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def fetch(query: str, *args) -> list[asyncpg.Record]:
    async with acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args) -> asyncpg.Record | None:
    async with acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute(query: str, *args) -> str:
    async with acquire() as conn:
        return await conn.execute(query, *args)


async def insert_evento(ev: NormalizedEvent) -> int:
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO eventos_pagamento (
                platform, raw_event_type, event_kind, user_number, email,
                customer_name, product_name, product_id, charge_amount,
                pix_code, pix_expiration, boleto_url, boleto_barcode, boleto_expiry,
                access_url, rejection_reason, payment_method, raw_payload
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18
            ) RETURNING id
            """,
            ev.platform,
            ev.raw_event_type,
            ev.event_kind,
            ev.customer.user_number or None,
            ev.customer.email or None,
            ev.customer.name or None,
            ev.product.name or None,
            ev.product.id or None,
            ev.product.value_cents,
            ev.payment.pix_code or None,
            ev.payment.pix_expiration or None,
            ev.payment.boleto_url or None,
            ev.payment.boleto_barcode or None,
            ev.payment.boleto_expiry or None,
            ev.payment.access_url or None,
            ev.payment.rejection_reason or None,
            ev.payment.method or None,
            ev.raw_payload,
        )
        return row["id"]


async def upsert_contato(
    user_number: str,
    *,
    email: str | None = None,
    nome: str | None = None,
    produto_interesse: str | None = None,
    link_oferta: str | None = None,
    platform_origem: str | None = None,
) -> None:
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO contatos_agente (user_number, email, nome, produto_interesse, link_oferta, platform_origem)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_number) DO UPDATE SET
                email = COALESCE(EXCLUDED.email, contatos_agente.email),
                nome = COALESCE(EXCLUDED.nome, contatos_agente.nome),
                produto_interesse = COALESCE(EXCLUDED.produto_interesse, contatos_agente.produto_interesse),
                link_oferta = COALESCE(EXCLUDED.link_oferta, contatos_agente.link_oferta),
                platform_origem = COALESCE(EXCLUDED.platform_origem, contatos_agente.platform_origem)
            """,
            user_number, email, nome, produto_interesse, link_oferta, platform_origem,
        )


async def insert_followup(
    user_number: str,
    tipo: str,
    produto: str | None,
    message: str,
    status: str = "completed",
    etapa_atual: int = 1,
) -> None:
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO follow_up (user_number, tipo, produto, status, etapa_atual, message)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_number, tipo, produto, status, etapa_atual, message,
        )
