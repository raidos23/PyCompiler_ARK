# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen
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

import heapq
import importlib.util
import math
import multiprocessing as mp
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

from .Base import (
    BCASL_PLUGIN_REGISTER_FUNC,
    BcPluginBase,
    ExecutionItem,
    ExecutionReport,
    PluginMeta,
    PreCompileContext,
    _logger,
    _PluginRecord,
)

_ACTIVE_WORKER_PIDS: set[int] = set()
_ACTIVE_WORKER_LOCK = threading.Lock()


def _register_worker_pid(pid: int) -> None:
    try:
        with _ACTIVE_WORKER_LOCK:
            _ACTIVE_WORKER_PIDS.add(int(pid))
    except Exception:
        pass


def _unregister_worker_pid(pid: int) -> None:
    try:
        with _ACTIVE_WORKER_LOCK:
            _ACTIVE_WORKER_PIDS.discard(int(pid))
    except Exception:
        pass


def _kill_pid_tree(pid: int) -> None:
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(int(pid)), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return
    except Exception:
        pass
    try:
        import psutil  # type: ignore

        p = psutil.Process(int(pid))
        children = p.children(recursive=True)
        for ch in reversed(children):
            try:
                ch.kill()
            except Exception:
                pass
        try:
            p.kill()
        except Exception:
            pass
        return
    except Exception:
        pass
    try:
        os.kill(int(pid), signal.SIGKILL)
    except Exception:
        pass


def kill_active_workers() -> int:
    """Kill all currently tracked BCASL sandbox worker processes."""
    try:
        with _ACTIVE_WORKER_LOCK:
            pids = list(_ACTIVE_WORKER_PIDS)
            _ACTIVE_WORKER_PIDS.clear()
    except Exception:
        pids = []
    for pid in pids:
        _kill_pid_tree(pid)
    return len(pids)


def _normalize_tags(tags: Any) -> list[str]:
    """Normalise les tags en liste de strings minuscules."""
    if not tags:
        return []
    if isinstance(tags, str):
        parts = [t.strip() for t in tags.split(",")]
    elif isinstance(tags, (list, tuple, set)):
        parts = list(tags)
    else:
        return []
    return [str(t).strip().lower() for t in parts if str(t).strip()]


def _tag_priority_from_tags(tags: Any) -> int:
    """Calcule la priorité basée sur les tags."""
    try:
        from .tagging import DEFAULT_TAG_PRIORITY, TAG_PRIORITY_MAP

        norm = _normalize_tags(tags)
        if not norm:
            return DEFAULT_TAG_PRIORITY
        scores = [
            TAG_PRIORITY_MAP.get(t, DEFAULT_TAG_PRIORITY) for t in norm if t is not None
        ]
        return min(scores) if scores else DEFAULT_TAG_PRIORITY
    except Exception:
        # Fallback conservateur
        try:
            from .tagging import DEFAULT_TAG_PRIORITY

            return DEFAULT_TAG_PRIORITY
        except Exception:
            return 100


def _add_report_item(
    report: ExecutionReport,
    *,
    plugin_id: str,
    name: str,
    success: bool,
    duration_ms: float,
    error: str = "",
) -> None:
    report.add(
        ExecutionItem(
            plugin_id=plugin_id,
            name=name,
            success=success,
            duration_ms=duration_ms,
            error=error if not success else "",
        )
    )


def _record_worker_result(
    report: ExecutionReport,
    *,
    plugin_id: str,
    name: str,
    start_t: float,
    q,
) -> bool:
    try:
        res = q.get_nowait()
    except Exception:
        res = {
            "ok": False,
            "error": "aucun résultat renvoyé (crash du processus enfant ?)",
            "duration_ms": (time.perf_counter() - start_t) * 1000.0,
        }
    duration_ms = float(
        res.get("duration_ms", (time.perf_counter() - start_t) * 1000.0)
    )
    ok = bool(res.get("ok"))
    if ok:
        _add_report_item(
            report,
            plugin_id=plugin_id,
            name=name,
            success=True,
            duration_ms=duration_ms,
        )
    else:
        _add_report_item(
            report,
            plugin_id=plugin_id,
            name=name,
            success=False,
            duration_ms=duration_ms,
            error=str(res.get("error", "")),
        )
    return ok


def _record_timeout(
    report: ExecutionReport,
    *,
    plugin_id: str,
    name: str,
    start_t: float,
    timeout_s: float,
) -> bool:
    duration_ms = (time.perf_counter() - start_t) * 1000.0
    _add_report_item(
        report,
        plugin_id=plugin_id,
        name=name,
        success=False,
        duration_ms=duration_ms,
        error=f"timeout après {timeout_s:.1f}s",
    )
    _logger.error("Plugin %s timeout après %.1fs", plugin_id, timeout_s)
    return False


def _record_dependency_blocked(
    report: ExecutionReport,
    *,
    plugin_id: str,
    name: str,
    failed_dep: str,
) -> None:
    _add_report_item(
        report,
        plugin_id=plugin_id,
        name=name,
        success=False,
        duration_ms=0.0,
        error=f"dépendance échouée: {failed_dep}",
    )


def _cleanup_queue(q) -> None:
    try:
        if q is not None:
            try:
                q.close()
            except Exception:
                pass
            try:
                q.cancel_join_thread()
            except Exception:
                pass
    except Exception:
        pass


def _stop_process(proc, join_s: float = 1.0) -> None:
    if proc is None:
        return
    try:
        if not proc.is_alive():
            return
    except Exception:
        return
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.join(join_s)
    except Exception:
        pass
    try:
        if proc.is_alive():
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.join(max(0.2, join_s))
            except Exception:
                pass
    except Exception:
        pass


def _resolve_reliability_options(config: dict[str, Any]) -> tuple[bool, bool]:
    try:
        opts = dict(config or {}).get("options", {}) if isinstance(config, dict) else {}
    except Exception:
        opts = {}
    skip_dependents = bool(opts.get("skip_dependents_on_failure", True))
    fail_fast = bool(opts.get("fail_fast", False))
    return skip_dependents, fail_fast


def _resolve_exec_options(
    config: dict[str, Any], default_sandbox: bool
) -> tuple[bool, int]:
    try:
        opts = dict(config or {}).get("options", {}) if isinstance(config, dict) else {}
    except Exception:
        opts = {}
    sandbox = bool(opts.get("sandbox", default_sandbox))
    parallelism = int(opts.get("plugin_parallelism", 0))
    return sandbox, parallelism


def _build_dependency_graph(
    active_items: dict[str, _PluginRecord],
) -> tuple[dict[str, int], dict[str, list[str]]]:
    indeg: dict[str, int] = {pid: 0 for pid in active_items}
    children: dict[str, list[str]] = {pid: [] for pid in active_items}
    for pid, rec in active_items.items():
        for dep in rec.requires:
            if dep not in active_items:
                _logger.warning(
                    "Dépendance manquante pour %s: '%s' (ignorée)", pid, dep
                )
                continue
            indeg[pid] += 1
            children[dep].append(pid)
    return indeg, children


def _build_ready_queue(
    active_items: dict[str, _PluginRecord], indeg: dict[str, int]
) -> list[tuple[int, int, str]]:
    ready: list[tuple[int, int, str]] = []
    for pid, rec in active_items.items():
        if indeg.get(pid, 0) == 0:
            heapq.heappush(ready, (rec.priority, rec.insert_idx, pid))
    return ready


def _compute_sequential_order(
    ready: list[tuple[int, int, str]],
    children: dict[str, list[str]],
    indeg: dict[str, int],
    active_items: dict[str, _PluginRecord],
) -> list[str]:
    order: list[str] = []
    tmp_ready = list(ready)
    heapq.heapify(tmp_ready)
    while tmp_ready:
        _, _, pid = heapq.heappop(tmp_ready)
        order.append(pid)
        for ch in children[pid]:
            indeg[ch] -= 1
            if indeg[ch] == 0:
                rch = active_items[ch]
                heapq.heappush(tmp_ready, (rch.priority, rch.insert_idx, ch))
    return order


def _run_plugin_sequential(
    report: ExecutionReport,
    rec: _PluginRecord,
    ctx: PreCompileContext,
    project_root: Path,
    timeout_s: float,
    eff_sandbox: bool,
    stop_requested=None,
) -> bool:
    plg = rec.plugin
    start = time.perf_counter()
    if eff_sandbox and getattr(rec, "module_path", None):
        _ctx = mp.get_context("spawn")
        q = _ctx.Queue()
        p = _ctx.Process(
            target=_plugin_worker,
            args=(
                str(rec.module_path),
                plg.meta.id,
                str(project_root),
                ctx.config,
                q,
            ),
        )
        p.start()
        _register_worker_pid(p.pid)
        cancelled = False
        timed_out = False
        try:
            while p.is_alive():
                if callable(stop_requested):
                    try:
                        if bool(stop_requested()):
                            cancelled = True
                            _stop_process(p, join_s=0.5)
                            break
                    except Exception:
                        pass
                if timeout_s and timeout_s > 0:
                    if (time.perf_counter() - start) >= timeout_s:
                        timed_out = True
                        _stop_process(p, join_s=1.0)
                        break
                try:
                    p.join(0.05)
                except Exception:
                    break

            if cancelled:
                _add_report_item(
                    report,
                    plugin_id=plg.meta.id,
                    name=plg.meta.name,
                    success=False,
                    duration_ms=(time.perf_counter() - start) * 1000.0,
                    error="annulé par l'utilisateur",
                )
                return False
            if timed_out or p.is_alive():
                _record_timeout(
                    report,
                    plugin_id=plg.meta.id,
                    name=plg.meta.name,
                    start_t=start,
                    timeout_s=timeout_s,
                )
                return False
            ok = _record_worker_result(
                report,
                plugin_id=plg.meta.id,
                name=plg.meta.name,
                start_t=start,
                q=q,
            )
            return ok
        finally:
            _unregister_worker_pid(p.pid)
            _cleanup_queue(q)
    else:
        try:
            plg.on_pre_compile(ctx)
            duration_ms = (time.perf_counter() - start) * 1000.0
            _add_report_item(
                report,
                plugin_id=plg.meta.id,
                name=plg.meta.name,
                success=True,
                duration_ms=duration_ms,
            )
            return True
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            _add_report_item(
                report,
                plugin_id=plg.meta.id,
                name=plg.meta.name,
                success=False,
                duration_ms=duration_ms,
                error=str(exc),
            )
            return False


def _configure_worker_env(config: dict[str, Any]) -> None:
    try:
        _opts = (
            dict(config or {}).get("options", {}) if isinstance(config, dict) else {}
        )
        _env_nonint = os.environ.get("PYCOMPILER_NONINTERACTIVE_PLUGINS")
        _env_offscreen = os.environ.get("PYCOMPILER_OFFSCREEN_PLUGINS")
        _noninteractive = (
            (str(_env_nonint).strip().lower() in ("1", "true", "yes"))
            if (_env_nonint is not None)
            else bool(_opts.get("noninteractive_plugins", False))
        )
        _offscreen = (
            (str(_env_offscreen).strip().lower() in ("1", "true", "yes"))
            if (_env_offscreen is not None)
            else bool(_opts.get("offscreen_plugins", False))
        )
        try:
            import platform as _plat

            _is_windows = _plat.system().lower().startswith("win")
        except Exception:
            _is_windows = False
        if not _is_windows and (
            not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY")
        ):
            _noninteractive = True
        if _noninteractive:
            os.environ["PYCOMPILER_NONINTERACTIVE"] = "1"
        if _offscreen and "QT_QPA_PLATFORM" not in os.environ:
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
    except Exception:
        pass


def _maybe_init_qt_app(config: dict[str, Any]) -> None:
    try:
        _opts2 = (
            dict(config or {}).get("options", {}) if isinstance(config, dict) else {}
        )
        _env_allow = os.environ.get("PYCOMPILER_SANDBOX_DIALOGS")
        _allow_dialogs = (
            (str(_env_allow).strip().lower() in ("1", "true", "yes"))
            if (_env_allow is not None)
            else bool(_opts2.get("allow_sandbox_dialogs", True))
        )
        if _allow_dialogs and (
            str(os.environ.get("PYCOMPILER_NONINTERACTIVE", "")).strip().lower()
            not in ("1", "true", "yes")
        ):
            os.environ.setdefault("QT_WAYLAND_DISABLE_FRACTIONAL_SCALE", "1")
            try:
                from PySide6.QtWidgets import QApplication as _QApp  # type: ignore
            except Exception:
                try:
                    from PyQt5.QtWidgets import QApplication as _QApp  # type: ignore
                except Exception:
                    _QApp = None  # type: ignore
            if _QApp is not None:
                try:
                    if _QApp.instance() is None:
                        _sandbox_qapp = _QApp([])  # noqa: F841
                except Exception:
                    pass
    except Exception:
        pass


def _enforce_sdk_progress() -> None:
    try:
        os.environ["PYCOMPILER_ENFORCE_SDK_PROGRESS"] = "1"
    except Exception:
        pass
    try:
        from PySide6 import QtWidgets as _QtW2  # type: ignore

        class _NoDirectProgressDialog:  # type: ignore
            def __init__(self, *args, **kwargs) -> None:
                raise RuntimeError(
                    "Plugins must use Plugins_SDK.progress(...) instead of PySide6.QProgressDialog"
                )

        try:
            _QtW2.QProgressDialog = _NoDirectProgressDialog  # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:
        try:
            from PyQt5 import QtWidgets as _QtW2  # type: ignore

            class _NoDirectProgressDialog:  # type: ignore
                def __init__(self, *args, **kwargs) -> None:
                    raise RuntimeError(
                        "Plugins must use Plugins_SDK.progress(...) instead of PyQt.QProgressDialog"
                    )

            try:
                _QtW2.QProgressDialog = _NoDirectProgressDialog  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception:
            pass


def _apply_resource_limits(config: dict[str, Any]) -> None:
    try:
        _opts3 = (
            dict(config or {}).get("options", {}) if isinstance(config, dict) else {}
        )
        _limits = _opts3.get("plugin_limits", {}) if isinstance(_opts3, dict) else {}
        _mem_mb = int(_limits.get("mem_mb", 0))
        _cpu_s = int(_limits.get("cpu_time_s", 0))
        _nofile = int(_limits.get("nofile", 0))
        _fsize_mb = int(_limits.get("fsize_mb", 0))
        try:
            import resource as _res  # POSIX only

            def _set(limit, soft, hard):
                try:
                    _res.setrlimit(limit, (soft, hard))
                except Exception:
                    pass

            if _mem_mb > 0:
                _set(_res.RLIMIT_AS, _mem_mb * 1024 * 1024, _mem_mb * 1024 * 1024)
            if _cpu_s > 0:
                _set(_res.RLIMIT_CPU, _cpu_s, _cpu_s)
            if _nofile > 0:
                _set(_res.RLIMIT_NOFILE, _nofile, _nofile)
            if _fsize_mb > 0:
                _set(
                    _res.RLIMIT_FSIZE,
                    _fsize_mb * 1024 * 1024,
                    _fsize_mb * 1024 * 1024,
                )
        except Exception:
            pass
    except Exception:
        pass


def _load_plugin_instance(
    module_path: str, plugin_id: str, project_root: str, config: dict[str, Any]
):
    import importlib.util as _ilu
    import sys as _sys
    from pathlib import Path as _Path

    spec = _ilu.spec_from_file_location(
        "bcasl_sandbox_module",
        module_path,
        submodule_search_locations=[str(_Path(module_path).parent)],
    )
    if spec is None or spec.loader is None:
        raise ImportError("spec invalide")
    module = _ilu.module_from_spec(spec)
    _sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    plg = getattr(module, "PLUGIN", None)
    if plg is None or getattr(getattr(plg, "meta", None), "id", None) != plugin_id:
        try:
            mgr = BCASL(_Path(project_root), config=config, sandbox=False)
            if hasattr(module, "bcasl_register") and callable(
                getattr(module, "bcasl_register")
            ):
                module.bcasl_register(mgr)
            rec = getattr(mgr, "_registry", {}).get(plugin_id)
            if rec is None:
                for attr_name in dir(module):
                    try:
                        attr = getattr(module, attr_name, None)
                        if attr is None:
                            continue
                        if not isinstance(attr, type):
                            continue
                        if not getattr(attr, "__bcasl_plugin__", False):
                            continue
                        plugin_instance = getattr(attr, "_bcasl_instance_", None)
                        if plugin_instance is None:
                            try:
                                plugin_instance = attr()
                            except Exception:
                                continue
                        if getattr(plugin_instance.meta, "id", None) == plugin_id:
                            plg = plugin_instance
                            break
                    except Exception:
                        continue
            else:
                plg = rec.plugin
            if plg is None:
                raise RuntimeError(f"Plugin '{plugin_id}' introuvable dans le module")
        except Exception as ex:
            raise RuntimeError(f"Impossible d'instancier le plugin: {ex}")
    return plg


# phase_score -> (display_name, min_priority, max_priority)
PHASES: dict[int, tuple[str, int, int]] = {
    0: ("Nettoyage", 0, 9),
    10: ("Validation", 10, 19),
    20: ("Préparation", 20, 29),
    30: ("Conformité", 30, 39),
    40: ("Linting", 40, 49),
    50: ("Obfuscation", 50, 59),
    100: ("Défaut", 60, 199),
}


class BCASL:
    """Gestionnaire main des plugins et de leur exécution avant compilation."""

    def __init__(
        self,
        project_root: Path,
        config: Optional[dict[str, Any]] = None,
        *,
        sandbox: bool = True,
        plugin_timeout_s: float = 3.0,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.config = dict(config or {})
        self._registry: dict[str, _PluginRecord] = {}
        self._insert_counter = 0
        # Sandbox settings
        self.sandbox = bool(sandbox)
        # Timeout settings
        try:
            timeout = float(plugin_timeout_s)
            if not math.isfinite(timeout) or timeout < 0:
                timeout = 0.0
        except Exception:
            timeout = 0.0
        self.plugin_timeout_s = timeout

    # Plugins publique
    def add_plugin(self, plugin: BcPluginBase) -> None:
        if not isinstance(plugin, BcPluginBase):
            raise TypeError("Le plugin doit être une instance de BcPluginBase")
        pid = plugin.meta.id
        if pid in self._registry:
            raise ValueError(f"Plugin id déjà enregistré: {pid}")
        rec = _PluginRecord(plugin, self._insert_counter)
        self._registry[pid] = rec
        self._insert_counter += 1
        _logger.debug("Plugin ajouté: %s", plugin)

    def remove_plugin(self, plugin_id: str) -> bool:
        return self._registry.pop(plugin_id, None) is not None

    def list_plugins(
        self, include_inactive: bool = True
    ) -> list[tuple[str, PluginMeta, bool, int]]:
        out = []
        for pid, rec in self._registry.items():
            if include_inactive or rec.active:
                out.append((pid, rec.plugin.meta, rec.active, rec.priority))
        out.sort(key=lambda x: (x[3], x[0]))
        return out

    def enable_plugin(self, plugin_id: str) -> bool:
        rec = self._registry.get(plugin_id)
        if not rec:
            return False
        rec.active = True
        return True

    def disable_plugin(self, plugin_id: str) -> bool:
        rec = self._registry.get(plugin_id)
        if not rec:
            return False
        rec.active = False
        return True

    def set_priority(self, plugin_id: str, priority: int) -> bool:
        rec = self._registry.get(plugin_id)
        if not rec:
            return False
        rec.priority = int(priority)
        rec.plugin.priority = int(priority)
        return True

    # Chargement automatique
    def load_plugins_from_directory(
        self, directory: Path
    ) -> tuple[int, list[tuple[str, str]]]:
        """Load automatiquement tous les plugins depuis un folder.

        Return (nombre_plugins_enregistrés, liste_erreurs[(module, message)]).
        """
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            _logger.warning("Dossier plugins introuvable: %s", directory)
            return 0, [(str(directory), "non trouvé ou non répertoire")]

        count = 0
        errors: list[tuple[str, str]] = []
        # Parcourt uniquement les packages Python (dossiers contenant __init__.py)
        try:
            pkg_dirs = sorted(
                [p for p in directory.iterdir() if p.is_dir()], key=lambda p: p.name
            )
        except Exception:
            pkg_dirs = []
        for pkg_dir in pkg_dirs:
            if pkg_dir.name.startswith("__"):
                continue
            init_file = pkg_dir / "__init__.py"
            if not init_file.exists():
                continue
            mod_name = f"bcasl_Plugins_{pkg_dir.name}"
            try:
                spec = importlib.util.spec_from_file_location(
                    mod_name, str(init_file), submodule_search_locations=[str(pkg_dir)]
                )
                if spec is None or spec.loader is None:
                    raise ImportError("spec invalide")
                module = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = module
                spec.loader.exec_module(module)  # type: ignore[attr-defined]

                # Recherche et appel de la fonction d'enregistrement si présente
                reg = getattr(module, BCASL_PLUGIN_REGISTER_FUNC, None)
                is_decorator_plugin = False
                new_ids: list[str] = []

                if callable(reg):
                    # Ancien style: fonction bcasl_register(manager)
                    before_ids = set(self._registry.keys())
                    reg(self)  # le package appelle self.add_plugin(...)
                    new_ids = [k for k in self._registry.keys() if k not in before_ids]
                else:
                    # Nouveau style: chercher les classes marquées avec @bc_register
                    # Ces classes ont l'attribut __bcasl_plugin__ = True
                    # et peuvent avoir _bcasl_instance_ pour l'instance
                    for attr_name in dir(module):
                        try:
                            attr = getattr(module, attr_name, None)
                            if attr is None:
                                continue
                            # Vérifier si c'est une classe marquée comme plugin
                            if not getattr(attr, "__bcasl_plugin__", False):
                                continue
                            if not isinstance(attr, type):
                                continue
                            # C'est une classe de plugin décorée avec @bc_register
                            plugin_instance = getattr(attr, "_bcasl_instance_", None)
                            if plugin_instance is None:
                                try:
                                    plugin_instance = attr()
                                except Exception as e:
                                    _logger.warning(
                                        "Impossible d'instancier le plugin %s: %s",
                                        attr_name,
                                        e,
                                    )
                                    continue
                            # Enregistrer le plugin
                            pid = plugin_instance.meta.id
                            if pid not in self._registry:
                                self.add_plugin(plugin_instance)
                                new_ids.append(pid)
                                is_decorator_plugin = True
                        except Exception:
                            continue

                for pid in new_ids:
                    rec = self._registry.get(pid)
                    if rec is not None:
                        rec.module_path = init_file
                        rec.module_name = mod_name
                # Validation de signature supprimée (simplification)
                added = len(new_ids)
                if added <= 0:
                    if not is_decorator_plugin:
                        _logger.debug(
                            "Package %s: aucun plugin trouvé (ni %s, ni décorateur @bc_register), ignoré",
                            pkg_dir.name,
                            BCASL_PLUGIN_REGISTER_FUNC,
                        )
                    else:
                        _logger.warning(
                            "Aucun plugin enregistré par package %s", pkg_dir.name
                        )
                else:
                    count += added
                    _logger.info("Plugin(s) chargé(s) depuis package %s", pkg_dir.name)
            except Exception as exc:  # isolation
                msg = f"échec chargement: {exc}"
                errors.append((pkg_dir.name, msg))
                _logger.error("%s: %s", pkg_dir.name, msg)
        return count, errors

    def run_pre_compile(
        self,
        ctx: Optional[PreCompileContext] = None,
        stop_requested: Optional[callable] = None,
        log_cb: Optional[callable] = None,
    ) -> ExecutionReport:
        """Execute le hook 'on_pre_compile' de tous les plugins actifs.

        Logic:
        1. Groupes par phase (tags -> phase score)
        2. Vérifie si la phase est activée (via self.config["phases"])
        3. Exécution séquentielle par phase
        """
        if ctx is None:
            ctx = PreCompileContext(root=self.project_root, config=self.config)
        else:
            ctx.root = Path(ctx.root).resolve()
            ctx.config = dict(self.config) | dict(ctx.config or {})

        report = ExecutionReport()
        eff_sandbox, _ = _resolve_exec_options(self.config, self.sandbox)
        skip_dependents_on_failure, fail_fast = _resolve_reliability_options(
            self.config
        )

        # 1. Identifier les plugins actifs
        active_items = {pid: rec for pid, rec in self._registry.items() if rec.active}
        if not active_items:
            if log_cb:
                try:
                    log_cb("Aucun plugin BCASL actif")
                except Exception:
                    pass
            _logger.info("Aucun plugin Bcasl actif")
            return report

        # 2. Groupe par phase
        phase_groups: dict[int, list[str]] = {}
        for pid, rec in active_items.items():
            tags = getattr(rec.plugin.meta, "tags", ())
            score = _tag_priority_from_tags(tags)
            phase_groups.setdefault(score, []).append(pid)

        # 3. Charger l'état d'activation des phases
        phases_cfg = self.config.get("phases", {})
        if not isinstance(phases_cfg, dict):
            phases_cfg = {}

        # 4. Exécuter phases une par une
        for score in sorted(PHASES.keys()):
            pname, _, _ = PHASES[score]
            if not phases_cfg.get(pname, True):
                _logger.info("Phase '%s' désactivée par configuration", pname)
                continue

            p_ids = phase_groups.get(score, [])
            if not p_ids:
                continue

            _logger.info("--- Phase: %s ---", pname)
            if log_cb:
                try:
                    log_cb(f"Phase: {pname}")
                except Exception:
                    pass

            # Sous-ensemble d'items pour cette phase
            p_items = {pid: active_items[pid] for pid in p_ids}
            indeg, children = _build_dependency_graph(p_items)
            ready = _build_ready_queue(p_items, indeg)

            # Exécution strictement séquentielle
            order = _compute_sequential_order(ready, children, indeg, p_items)
            failed_seq: set[str] = set()
            for pid in order:
                rec = p_items[pid]
                if log_cb:
                    try:
                        log_cb(f"Plugin: {rec.plugin.meta.name}")
                    except Exception:
                        pass

                if skip_dependents_on_failure:
                    failed_dep = next(
                        (d for d in rec.requires if d in failed_seq), None
                    )
                    if failed_dep:
                        _record_dependency_blocked(
                            report,
                            plugin_id=pid,
                            name=rec.plugin.meta.name,
                            failed_dep=str(failed_dep),
                        )
                        failed_seq.add(pid)
                        continue

                ok = _run_plugin_sequential(
                    report,
                    rec,
                    ctx,
                    ctx.root,
                    self.plugin_timeout_s,
                    eff_sandbox,
                    stop_requested,
                )
                if not ok:
                    failed_seq.add(pid)
                    if fail_fast:
                        return report

        _logger.info(report.summary())
        return report


def _plugin_worker(
    module_path: str, plugin_id: str, project_root: str, config: dict[str, Any], q
) -> None:
    """Load un module de plugin depuis son path et execute on_pre_compile dans un process isolé."""
    import logging as _logging
    import os as _os
    import sys as _sys
    import time as _time
    import traceback as _tb
    from pathlib import Path as _Path

    # Handle quiet mode for sandbox processes
    _quiet = _os.environ.get("PYCOMPILER_QUIET") == "1"
    _fnull = None
    _old_stdout = None
    _old_stderr = None
    
    if _quiet:
        _fnull = open(_os.devnull, "w")
        _old_stdout = _sys.stdout
        _old_stderr = _sys.stderr
        _sys.stdout = _fnull
        _sys.stderr = _fnull
        _logging.getLogger("bcasl").setLevel(_logging.ERROR)

    try:
        _configure_worker_env(config)
        _maybe_init_qt_app(config)
        _enforce_sdk_progress()
        _apply_resource_limits(config)
        try:
            from bcasl import PreCompileContext as _PCC

            plg = _load_plugin_instance(module_path, plugin_id, project_root, config)
            ctx = _PCC(root=_Path(project_root), config=dict(config or {}))
            t0 = _time.perf_counter()
            plg.on_pre_compile(ctx)
            dur = (_time.perf_counter() - t0) * 1000.0
            q.put({"ok": True, "error": "", "duration_ms": dur})
        except Exception:
            q.put({"ok": False, "error": _tb.format_exc(), "duration_ms": 0.0})
    finally:
        if _quiet:
            _sys.stdout = _old_stdout
            _sys.stderr = _old_stderr
            if _fnull:
                _fnull.close()
