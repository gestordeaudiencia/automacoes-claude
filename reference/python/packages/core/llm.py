from .config import get_settings


async def gerar_mensagem(system: str, user: str, max_tokens: int = 400) -> str:
    """Gera uma mensagem usando o provider configurado. Retorna texto puro."""
    settings = get_settings()
    if settings.llm_provider == "openai":
        return await _openai_call(system, user, max_tokens, settings)
    return await _anthropic_call(system, user, max_tokens, settings)


async def _openai_call(system: str, user: str, max_tokens: int, settings) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.8,
    )
    return (resp.choices[0].message.content or "").strip()


async def _anthropic_call(system: str, user: str, max_tokens: int, settings) -> str:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=settings.anthropic_model,
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=max_tokens,
    )
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()
