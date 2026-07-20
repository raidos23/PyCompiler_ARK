# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
