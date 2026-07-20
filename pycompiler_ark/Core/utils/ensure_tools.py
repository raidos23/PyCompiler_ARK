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

Indépendant de BCASL, Engine, BuildContext et Qt (sauf si un objet GUI est passé).
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
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pycompiler_ark.Ui import output

__all__ = ["ToolsCheckResult", "ensure_tools"]


@dataclass
class ToolsCheckResult:
    """Résultat de la vérification/installation des outils requis."""

    ok: bool
    missing_system: list[str] = field(default_factory=list)
    missing_python: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _tools_stage_message(stage: str, fr: str, en: str) -> tuple[str, str]:
    prefix = f"[tools:{stage}] "
    return prefix + fr, prefix + en


def ensure_tools(
    required_tools: dict,
    stop_signal: Callable[[], bool] | None = None,
    log_cb: Callable[[str], None] | None = None,
    timeout_s: int = 300,
    gui: Any | None = None,
) -> ToolsCheckResult:
    """Vérifie et installe les outils requis (système + Python).

    Args:
        required_tools: Dictionnaire ``{"python": [...], "system": [...]}``
        stop_signal:    Callable sans argument retournant True pour annuler
        log_cb:         Callable(str) pour émettre les messages de progression (utilisé si gui est absent)
        timeout_s:      Timeout global en secondes (non utilisé pour pip, garde-fou futur)
        gui:            Objet GUI ou Bridge optionnel pour le support complet de l'UI (VenvManager, SysDependencyManager, etc.)

    Returns:
        ToolsCheckResult avec ok=True si tout est disponible après installation.
    """

    missing_system: list[str] = []
    missing_python: list[str] = []
    errors: list[str] = []

    system_tools = [t for t in (required_tools.get("system") or []) if t]
    python_tools = [t for t in (required_tools.get("python") or []) if t]

    # ------------------------------------------------------------------ #
    # 1. Outils système                                                    #
    # ------------------------------------------------------------------ #
    if system_tools:
        if gui is not None:
            # GUI/Bridge system tools flow
            try:
                from ..Compiler.utils import check_internet_connection
                from pycompiler_ark.Core.SystemDepsManager import (
                    SysDependencyManager,
                    check_system_packages,
                )

                if hasattr(gui, "sys_deps_manager") and gui.sys_deps_manager:
                    sys_manager = gui.sys_deps_manager
                else:
                    sys_manager = SysDependencyManager(gui)

                for tool in system_tools:
                    if stop_signal and stop_signal():
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
                    output.info(
                        *_tools_stage_message(
                            "system",
                            "Vérification de la connexion Internet...",
                            "Checking Internet connection...",
                        ),
                    )

                    if not check_internet_connection(timeout=4.0):
                        err_fr = "Pas de connexion Internet. Impossible d'installer les outils systeme manquants."
                        err_en = "No Internet connection. Cannot install missing system tools."
                        output.error(
                            *_tools_stage_message("system", err_fr, err_en),
                        )
                        errors.append(f"[ensure_tools:system] {err_en}")
                        return ToolsCheckResult(
                            ok=False,
                            missing_system=missing_system,
                            missing_python=missing_python,
                            errors=errors,
                        )

                    output.info(
                        *_tools_stage_message(
                            "system",
                            f"Installation des outils systeme manquants: {missing_system}",
                            f"Installing missing system tools: {missing_system}",
                        ),
                    )

                    import platform

                    system = platform.system().lower()

                    system_install_ok = True
                    if system == "linux":
                        process = sys_manager.install_packages_linux(missing_system)
                        if process:
                            timeout_total = 600000  # 10 minutes
                            elapsed = 0
                            interval = 500  # 0.5s
                            while not process.waitForFinished(interval):
                                if stop_signal and stop_signal():
                                    from ..process_killer import (
                                        kill_process_tree,
                                    )

                                    try:
                                        kill_process_tree(process.processId())
                                    except Exception:
                                        pass
                                    errors.append(
                                        "Annulé par stop_signal pendant l'installation Linux"
                                    )
                                    return ToolsCheckResult(
                                        ok=False,
                                        missing_system=missing_system,
                                        missing_python=missing_python,
                                        errors=errors,
                                    )
                                elapsed += interval
                                if elapsed >= timeout_total:
                                    output.warn(
                                        *_tools_stage_message(
                                            "system",
                                            "Timeout lors de l'installation des outils systeme",
                                            "Timeout during system tools installation",
                                        ),
                                    )
                                    system_install_ok = False
                                    break

                            if system_install_ok:
                                if process.exitCode() == 0:
                                    output.success(
                                        *_tools_stage_message(
                                            "system",
                                            f"Outils systeme installes avec succes: {missing_system}",
                                            f"System tools installed successfully: {missing_system}",
                                        ),
                                    )
                                    missing_system = []
                                else:
                                    output.error(
                                        *_tools_stage_message(
                                            "system",
                                            f"Echec installation outils systeme: {missing_system} (code: {process.exitCode()})",
                                            f"System tools installation failed: {missing_system} (code: {process.exitCode()})",
                                        ),
                                    )
                                    system_install_ok = False
                        else:
                            # Fallback to headless
                            from pycompiler_ark.Core.SystemDepsManager import (
                                install_system_packages,
                            )

                            output.info(
                                *_tools_stage_message(
                                    "system",
                                    "Tentative d'installation systeme en mode headless...",
                                    "Attempting headless system installation...",
                                ),
                            )
                            if install_system_packages(missing_system):
                                output.success(
                                    *_tools_stage_message(
                                        "system",
                                        "Installation systeme headless reussie.",
                                        "Headless system installation successful.",
                                    ),
                                )
                                missing_system = []
                            else:
                                output.error(
                                    *_tools_stage_message(
                                        "system",
                                        "Echec de l'installation systeme headless.",
                                        "Headless system installation failed.",
                                    ),
                                )
                                system_install_ok = False

                    elif system == "windows":
                        winget_packages = []
                        for tool in missing_system:
                            winget_map = {
                                "build-essential": [
                                    {"id": "Microsoft.VisualStudio.2022.BuildTools"}
                                ],
                                "gcc": [
                                    {"id": "Microsoft.VisualStudio.2022.BuildTools"}
                                ],
                                "g++": [
                                    {"id": "Microsoft.VisualStudio.2022.BuildTools"}
                                ],
                                "python3-dev": [{"id": "Python.Python.3"}],
                                "libpython3-dev": [{"id": "Python.Python.3"}],
                                "patchelf": [],
                            }
                            if tool in winget_map:
                                winget_packages.extend(winget_map[tool])
                            else:
                                winget_packages.append({"id": tool})

                        if winget_packages:
                            process = sys_manager.install_packages_windows(
                                winget_packages
                            )
                            if process:
                                timeout_total = 600000  # 10 minutes
                                elapsed = 0
                                interval = 500  # 0.5s
                                while not process.waitForFinished(interval):
                                    if stop_signal and stop_signal():
                                        from ..process_killer import (
                                            kill_process_tree,
                                        )

                                        try:
                                            kill_process_tree(process.processId())
                                        except Exception:
                                            pass
                                        errors.append(
                                            "Annulé par stop_signal pendant l'installation Windows"
                                        )
                                        return ToolsCheckResult(
                                            ok=False,
                                            missing_system=missing_system,
                                            missing_python=missing_python,
                                            errors=errors,
                                        )
                                    elapsed += interval
                                    if elapsed >= timeout_total:
                                        output.warn(
                                            *_tools_stage_message(
                                                "system",
                                                "Timeout lors de l'installation Windows",
                                                "Timeout during Windows installation",
                                            ),
                                        )
                                        system_install_ok = False
                                        break

                                if system_install_ok:
                                    if process.exitCode() == 0:
                                        output.success(
                                            *_tools_stage_message(
                                                "system",
                                                f"Outils Windows installes: {missing_system}",
                                                f"Windows tools installed: {missing_system}",
                                            ),
                                        )
                                        missing_system = []
                                    else:
                                        output.error(
                                            *_tools_stage_message(
                                                "system",
                                                f"Echec installation Windows: {missing_system}",
                                                f"Windows installation failed: {missing_system}",
                                            ),
                                        )
                                        system_install_ok = False
                            else:
                                output.warn(
                                    *_tools_stage_message(
                                        "system",
                                        "winget non disponible, installation manuelle requise",
                                        "winget not available, manual installation required",
                                    ),
                                )
                                try:
                                    sys_manager.open_urls(
                                        [
                                            "https://learn.microsoft.com/en-us/windows/package-manager/winget/"
                                        ]
                                    )
                                except Exception:
                                    pass
                                system_install_ok = False
                        else:
                            output.warn(
                                *_tools_stage_message(
                                    "system",
                                    f"Aucun equivalent Windows pour: {missing_system}",
                                    f"No Windows equivalent for: {missing_system}",
                                ),
                            )
                            system_install_ok = False
                    else:
                        output.warn(
                            *_tools_stage_message(
                                "system",
                                "Plateforme non supportee pour l'installation automatique",
                                "Platform not supported for automatic installation",
                            ),
                        )
                        system_install_ok = False

                    if not system_install_ok:
                        errors.append(
                            f"Échec installation outils système: {missing_system}"
                        )

                else:
                    output.success(
                        *_tools_stage_message(
                            "system",
                            f"Tous les outils systeme sont deja installes: {system_tools}",
                            f"All system tools are already installed: {system_tools}",
                        ),
                    )

            except Exception as e:
                err_msg = f"Erreur lors de la verification/installation des outils systeme: {e}"
                output.warn(
                    *_tools_stage_message(
                        "system",
                        err_msg,
                        f"Error checking/installing system tools: {e}",
                    ),
                )
                errors.append(err_msg)

        else:
            # Original headless system tools check & installation flow
            try:
                from ..Compiler.utils import check_internet_connection
                from ..SystemDepsManager.headless import (
                    check_system_packages,
                    install_system_packages,
                )
            except ImportError as exc:
                err = f"[ensure_tools] Import headless impossible : {exc}"
                errors.append(err)
                output.error("error", err, err)
                return ToolsCheckResult(ok=False, errors=errors)

            for tool in system_tools:
                if stop_signal and stop_signal():
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
                output.info(
                    f"[ensure_tools:system] Outils manquants : {missing_system}",
                    f"[ensure_tools:system] Missing tools: {missing_system}",
                )
                output.info(
                    "[ensure_tools:system] Vérification de la connexion Internet…",
                    "[ensure_tools:system] Checking Internet connection...",
                )

                if not check_internet_connection(timeout=4.0):
                    err = "[ensure_tools:system] Pas de connexion Internet — installation impossible."
                    errors.append(err)
                    output.error("error", err, err)
                    return ToolsCheckResult(
                        ok=False,
                        missing_system=missing_system,
                        missing_python=missing_python,
                        errors=errors,
                    )

                output.info(
                    f"[ensure_tools:system] Installation de {missing_system}…",
                    f"[ensure_tools:system] Installing {missing_system}...",
                )
                if install_system_packages(missing_system):
                    output.success(
                        "[ensure_tools:system] Installation réussie.",
                        "[ensure_tools:system] Installation successful.",
                    )
                    missing_system = []
                else:
                    err = f"[ensure_tools:system] Échec installation : {missing_system}"
                    errors.append(err)
                    output.error("error", err, err)
            else:
                output.success(
                    f"[ensure_tools:system] Tous présents : {system_tools}",
                    f"[ensure_tools:system] All present: {system_tools}",
                )

    # ------------------------------------------------------------------ #
    # 2. Outils Python                                                     #
    # ------------------------------------------------------------------ #
    if python_tools:
        if gui is not None and hasattr(gui, "venv_manager") and gui.venv_manager:
            try:
                from ..Compiler.utils import check_internet_connection

                use_system = bool(getattr(gui, "use_system_python", False))

                if use_system:
                    for tool in python_tools:
                        if not gui.venv_manager.is_tool_installed_system(tool):
                            missing_python.append(tool)

                    if missing_python:
                        output.info(
                            *_tools_stage_message(
                                "python",
                                "Vérification de la connexion Internet...",
                                "Checking Internet connection...",
                            ),
                        )

                        if not check_internet_connection(timeout=4.0):
                            output.error(
                                *_tools_stage_message(
                                    "python",
                                    "Pas de connexion Internet. Impossible d'installer les outils Python manquants.",
                                    "No Internet connection. Cannot install missing Python tools.",
                                ),
                            )
                            errors.append(
                                "Pas de connexion Internet (outils Python système)"
                            )
                            return ToolsCheckResult(
                                ok=False,
                                missing_system=missing_system,
                                missing_python=missing_python,
                                errors=errors,
                            )

                        output.info(
                            *_tools_stage_message(
                                "python",
                                f"Installation des outils Python manquants: {missing_python}",
                                f"Installing missing Python tools: {missing_python}",
                            ),
                        )
                        gui.venv_manager.ensure_tools_installed_system(missing_python)

                        # Wait for Python tools to be installed on system
                        timeout_total = 600000  # 10 minutes
                        elapsed = 0
                        interval = 1000  # 1s
                        all_done = False
                        while elapsed < timeout_total:
                            if stop_signal and stop_signal():
                                errors.append(
                                    "Annulé par stop_signal pendant l'installation Python (système)"
                                )
                                return ToolsCheckResult(
                                    ok=False,
                                    missing_system=missing_system,
                                    missing_python=missing_python,
                                    errors=errors,
                                )

                            # Check if all are installed
                            all_done = True
                            for tool in missing_python:
                                if not gui.venv_manager.is_tool_installed_system(tool):
                                    all_done = False
                                    break
                            if all_done:
                                break

                            time.sleep(interval / 1000.0)
                            elapsed += interval

                        if not all_done:
                            output.warn(
                                *_tools_stage_message(
                                    "python",
                                    "Timeout ou echec de l'installation des outils Python (systeme)",
                                    "Timeout or failure installing system Python tools",
                                ),
                            )
                            errors.append(
                                "Timeout ou échec de l'installation des outils Python (système)"
                            )
                            missing_python = [
                                t
                                for t in missing_python
                                if not gui.venv_manager.is_tool_installed_system(t)
                            ]
                        else:
                            missing_python = []
                else:
                    venv_path = gui.venv_manager.resolve_project_venv()
                    if venv_path:
                        for tool in python_tools:
                            if not gui.venv_manager.is_tool_installed(venv_path, tool):
                                missing_python.append(tool)

                        if missing_python:
                            output.info(
                                *_tools_stage_message(
                                    "python",
                                    "Vérification de la connexion Internet...",
                                    "Checking Internet connection...",
                                ),
                            )

                            if not check_internet_connection(timeout=4.0):
                                output.error(
                                    *_tools_stage_message(
                                        "python",
                                        "Pas de connexion Internet. Impossible d'installer les outils Python manquants.",
                                        "No Internet connection. Cannot install missing Python tools.",
                                    ),
                                )
                                errors.append(
                                    "Pas de connexion Internet (outils Python venv)"
                                )
                                return ToolsCheckResult(
                                    ok=False,
                                    missing_system=missing_system,
                                    missing_python=missing_python,
                                    errors=errors,
                                )

                            output.info(
                                *_tools_stage_message(
                                    "python",
                                    f"Installation des outils Python manquants: {missing_python}",
                                    f"Installing missing Python tools: {missing_python}",
                                ),
                            )
                            gui.venv_manager.ensure_tools_installed(
                                venv_path, missing_python
                            )

                            # Wait for Python tools to be installed
                            timeout_total = 600000  # 10 minutes
                            elapsed = 0
                            interval = 1000  # 1s
                            all_done = False
                            while elapsed < timeout_total:
                                if stop_signal and stop_signal():
                                    errors.append(
                                        "Annulé par stop_signal pendant l'installation Python (venv)"
                                    )
                                    return ToolsCheckResult(
                                        ok=False,
                                        missing_system=missing_system,
                                        missing_python=missing_python,
                                        errors=errors,
                                    )

                                # Check if all are installed
                                all_done = True
                                for tool in missing_python:
                                    if not gui.venv_manager.is_tool_installed(
                                        venv_path, tool
                                    ):
                                        all_done = False
                                        break
                                if all_done:
                                    break

                                time.sleep(interval / 1000.0)
                                elapsed += interval

                            if not all_done:
                                output.warn(
                                    *_tools_stage_message(
                                        "python",
                                        "Timeout ou echec de l'installation des outils Python",
                                        "Timeout or failure installing Python tools",
                                    ),
                                )
                                errors.append(
                                    "Timeout ou échec de l'installation des outils Python (venv)"
                                )
                                missing_python = [
                                    t
                                    for t in missing_python
                                    if not gui.venv_manager.is_tool_installed(
                                        venv_path, t
                                    )
                                ]
                            else:
                                missing_python = []
            except Exception as e:
                err_msg = f"Erreur lors de la verification/installation des outils Python: {e}"
                output.warn(
                    *_tools_stage_message(
                        "python",
                        err_msg,
                        f"Error checking/installing Python tools: {e}",
                    ),
                )
                errors.append(err_msg)
        else:
            # Original headless Python tools check & installation flow
            for tool in python_tools:
                if stop_signal and stop_signal():
                    errors.append("Annulé par stop_signal (outils Python)")
                    return ToolsCheckResult(
                        ok=False,
                        missing_system=missing_system,
                        missing_python=missing_python,
                        errors=errors,
                    )
                spec_name = tool.replace("-", "_").split("[")[0]
                if importlib.util.find_spec(spec_name) is None:
                    missing_python.append(tool)

            if missing_python:
                output.info(
                    f"[ensure_tools:python] Paquets manquants : {missing_python}",
                    f"[ensure_tools:python] Missing packages: {missing_python}",
                )

                try:
                    from ..Compiler.utils import (
                        check_internet_connection,
                    )

                    output.info(
                        "[ensure_tools:python] Vérification de la connexion Internet…",
                        "[ensure_tools:python] Checking Internet connection...",
                    )
                    if not check_internet_connection(timeout=4.0):
                        err = "[ensure_tools:python] Pas de connexion Internet — installation impossible."
                        errors.append(err)
                        output.error("error", err, err)
                        return ToolsCheckResult(
                            ok=False,
                            missing_system=missing_system,
                            missing_python=missing_python,
                            errors=errors,
                        )
                except ImportError:
                    pass

                still_missing: list[str] = []
                for pkg in missing_python:
                    if stop_signal and stop_signal():
                        errors.append("Annulé par stop_signal (pip install)")
                        return ToolsCheckResult(
                            ok=False,
                            missing_system=missing_system,
                            missing_python=still_missing
                            + missing_python[len(still_missing) :],
                            errors=errors,
                        )
                    output.info(
                        f"[ensure_tools:python] pip install {pkg}…",
                        f"[ensure_tools:python] pip install {pkg}...",
                    )
                    try:
                        result = subprocess.run(
                            [sys.executable, "-m", "pip", "install", pkg],
                            capture_output=True,
                            text=True,
                            timeout=timeout_s,
                        )
                        if result.returncode == 0:
                            output.success(
                                f"[ensure_tools:python] {pkg} installé avec succès.",
                                f"[ensure_tools:python] {pkg} installed successfully.",
                            )
                        else:
                            err = f"[ensure_tools:python] Échec pip install {pkg} : {result.stderr.strip()}"
                            errors.append(err)
                            output.error("error", err, err)
                            still_missing.append(pkg)
                    except subprocess.TimeoutExpired:
                        err = f"[ensure_tools:python] Timeout pip install {pkg}"
                        errors.append(err)
                        output.error("error", err, err)
                        still_missing.append(pkg)
                    except Exception as exc:
                        err = f"[ensure_tools:python] Erreur pip install {pkg} : {exc}"
                        errors.append(err)
                        output.error("error", err, err)
                        still_missing.append(pkg)

                missing_python = still_missing
            else:
                output.success(
                    f"[ensure_tools:python] Tous présents : {python_tools}",
                    f"[ensure_tools:python] All present: {python_tools}",
                )

    ok = not missing_system and not missing_python and not errors
    return ToolsCheckResult(
        ok=ok,
        missing_system=missing_system,
        missing_python=missing_python,
        errors=errors,
    )
