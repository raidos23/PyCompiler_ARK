from __future__ import annotations
from typing import Any

# Language code aliases for normalization
_LANG_ALIASES: dict[str, str] = {
    "en-us": "en",
    "en_gb": "en",
    "en-uk": "en",
    "fr-fr": "fr",
    "fr_ca": "fr",
    "fr-ca": "fr",
    "pt-br": "pt-BR",
    "pt_br": "pt-BR",
    "zh": "zh-CN",
    "zh_cn": "zh-CN",
    "zh-cn": "zh-CN",
}
_GLOBAL_TR: dict[str, Any] = {}
_GLOBAL_LANG: str = "en"

WORKSPACE_CONFIG_DIRNAME = ".ark"
