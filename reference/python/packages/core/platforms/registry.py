"""Registro de adapters disponíveis. Permite adicionar plataforma em runtime."""
from typing import Any

from .base import PlatformAdapter
from .generic import GenericAdapter
from .hotmart import HotmartAdapter
from .kiwify import KiwifyAdapter
from .lastlink import LastlinkAdapter
from .shopify import ShopifyAdapter

_ADAPTERS: dict[str, PlatformAdapter] = {
    "kiwify": KiwifyAdapter(),
    "hotmart": HotmartAdapter(),
    "shopify": ShopifyAdapter(),
    "lastlink": LastlinkAdapter(),
}


def get_adapter(platform: str) -> PlatformAdapter:
    p = (platform or "").lower().strip()
    if p not in _ADAPTERS:
        raise KeyError(
            f"Platform '{platform}' não registrada. Disponíveis: {sorted(_ADAPTERS)}"
        )
    return _ADAPTERS[p]


def register_adapter(adapter: PlatformAdapter) -> None:
    """Adiciona um adapter custom (ex: GenericAdapter com config) em runtime."""
    _ADAPTERS[adapter.name.lower()] = adapter


def register_generic_from_config(config: dict[str, Any]) -> None:
    """Atalho: cria + registra GenericAdapter a partir de config dict."""
    register_adapter(GenericAdapter(config))


def list_platforms() -> list[str]:
    return sorted(_ADAPTERS)
