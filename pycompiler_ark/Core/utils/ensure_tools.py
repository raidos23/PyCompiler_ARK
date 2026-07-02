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

"""
Utilitaire universel de vérification et d'installation d'outils.

Indépendant de BCASL, Engine, BuildContext et Qt.
Utilisable depuis n'importe quel module du projet via :

    from pycompiler_ark.Core.utils.ensure_tools import ensure_tools, ToolsCheckResult

    result = ensure_tools({"python": ["black"], "system": ["gcc"]})
    if not result.ok:
        print(result.errors)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

__all__ = ["ToolsCheckResult", "ensure_tools"]


@dataclass
class ToolsCheckResult:
    """Résultat de la vérification/installation des outils requis."""

    ok: bool
    missing_system: list[str] = field(default_factory=list)
    missing_python: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def ensure_tools(
    required_tools: dict,
    stop_signal: Callable[[], bool] | None = None,
    log_cb: Callable[[str], None] | None = None,
    timeout_s: int = 300,
) -> ToolsCheckResult:
    """Vérifie et installe les outils requis (système + Python).

    Utilitaire universel — aucune dépendance vers BCASL, Engine ou BuildContext.

    Args:
        required_tools: Dictionnaire ``{"python": [...], "system": [...]}``
        stop_signal:    Callable sans argument retournant True pour annuler
        log_cb:         Callable(str) pour émettre les messages de progression
        timeout_s:      Timeout global en secondes (non utilisé pour pip, garde-fou futur)

    Returns:
        ToolsCheckResult avec ok=True si tout est disponible après installation.
    """

    def _log(msg: str) -> None:
        if callable(log_cb):
            try:
                log_cb(msg)
            except Exception:
                pass

    def _stopped() -> bool:
        if callable(stop_signal):
            try:
                return bool(stop_signal())
            except Exception:
                pass
        return False

    missing_system: list[str] = []
    missing_python: list[str] = []
    errors: list[str] = []

    system_tools = [t for t in (required_tools.get("system") or []) if t]
    python_tools = [t for t in (required_tools.get("python") or []) if t]

    # ------------------------------------------------------------------ #
    # 1. Outils système                                                    #
    # ------------------------------------------------------------------ #
    if system_tools:
        try:
            from pycompiler_ark.Core.SystemDepsManager.headless import (
                check_system_packages,
                install_system_packages,
            )
            from pycompiler_ark.Core.Compiler.utils import check_internet_connection
        except ImportError as exc:
            err = f"[ensure_tools] Import headless impossible : {exc}"
            errors.append(err)
            _log(err)
            return ToolsCheckResult(ok=False, errors=errors)

        for tool in system_tools:
            if _stopped():
                errors.append("Annulé par stop_signal (outils système)")
                return ToolsCheckResult(
                    ok=False,
                    missing_system=missing_system,
                    missing_python=missing_python,
                    errors=errors,
                )
            if not check_system_packages([tool]):
                missing_system.append(tool)

        if missing_system:
            _log(f"[ensure_tools:system] Outils manquants : {missing_system}")
            _log("[ensure_tools:system] Vérification de la connexion Internet…")

            if not check_internet_connection(timeout=4.0):
                err = "[ensure_tools:system] Pas de connexion Internet — installation impossible."
                errors.append(err)
                _log(err)
                return ToolsCheckResult(
                    ok=False,
                    missing_system=missing_system,
                    missing_python=missing_python,
                    errors=errors,
                )

            if _stopped():
                errors.append("Annulé par stop_signal (avant install système)")
                return ToolsCheckResult(
                    ok=False,
                    missing_system=missing_system,
                    missing_python=missing_python,
                    errors=errors,
                )

            _log(f"[ensure_tools:system] Installation de {missing_system}…")
            if install_system_packages(missing_system):
                _log("[ensure_tools:system] Installation réussie.")
                missing_system = []
            else:
                err = f"[ensure_tools:system] Échec installation : {missing_system}"
                errors.append(err)
                _log(err)
        else:
            _log(f"[ensure_tools:system] Tous présents : {system_tools}")

    # ------------------------------------------------------------------ #
    # 2. Outils Python                                                     #
    # ------------------------------------------------------------------ #
    if python_tools:
        for tool in python_tools:
            if _stopped():
                errors.append("Annulé par stop_signal (outils Python)")
                return ToolsCheckResult(
                    ok=False,
                    missing_system=missing_system,
                    missing_python=missing_python,
                    errors=errors,
                )
            # find_spec accepte les noms avec tirets convertis en underscores
            spec_name = tool.replace("-", "_").split("[")[0]
            if importlib.util.find_spec(spec_name) is None:
                missing_python.append(tool)

        if missing_python:
            _log(f"[ensure_tools:python] Paquets manquants : {missing_python}")

            # Vérifier internet avant pip
            try:
                from pycompiler_ark.Core.Compiler.utils import check_internet_connection

                _log("[ensure_tools:python] Vérification de la connexion Internet…")
                if not check_internet_connection(timeout=4.0):
                    err = "[ensure_tools:python] Pas de connexion Internet — installation impossible."
                    errors.append(err)
                    _log(err)
                    return ToolsCheckResult(
                        ok=False,
                        missing_system=missing_system,
                        missing_python=missing_python,
                        errors=errors,
                    )
            except ImportError:
                pass  # Si l'import échoue on tente quand même pip

            still_missing: list[str] = []
            for pkg in missing_python:
                if _stopped():
                    errors.append("Annulé par stop_signal (pip install)")
                    return ToolsCheckResult(
                        ok=False,
                        missing_system=missing_system,
                        missing_python=still_missing,
                        errors=errors,
                    )
                _log(f"[ensure_tools:python] pip install {pkg}…")
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", pkg],
                        capture_output=True,
                        text=True,
                        timeout=timeout_s,
                    )
                    if result.returncode == 0:
                        _log(f"[ensure_tools:python] {pkg} installé avec succès.")
                    else:
                        err = f"[ensure_tools:python] Échec pip install {pkg} : {result.stderr.strip()}"
                        errors.append(err)
                        _log(err)
                        still_missing.append(pkg)
                except subprocess.TimeoutExpired:
                    err = f"[ensure_tools:python] Timeout pip install {pkg}"
                    errors.append(err)
                    _log(err)
                    still_missing.append(pkg)
                except Exception as exc:
                    err = f"[ensure_tools:python] Erreur pip install {pkg} : {exc}"
                    errors.append(err)
                    _log(err)
                    still_missing.append(pkg)

            missing_python = still_missing
        else:
            _log(f"[ensure_tools:python] Tous présents : {python_tools}")

    ok = not missing_system and not missing_python and not errors
    return ToolsCheckResult(
        ok=ok,
        missing_system=missing_system,
        missing_python=missing_python,
        errors=errors,
    )
