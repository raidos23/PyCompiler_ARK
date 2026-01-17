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

from __future__ import annotations

import fnmatch
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


__all__ = [
    "BcPluginBase",
    "PluginMeta",
    "PreCompileContext",
    "ExecutionReport",
    "bc_register",
]

# Configuration logger par défaut (faible verbosité pour embarqué)
_logger = logging.getLogger("bcasl")
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter("[%(levelname)s] %(message)s")
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)

BCASL_PLUGIN_REGISTER_FUNC = "bcasl_register"


@dataclass(frozen=True)
class PluginMeta:
    """Métadonnées d'un plugin.

    id: identifiant unique (stable)
    name: nom
    version: chaîne de version
    description: courte description
    author: optionnel
    tags: liste de tags pour la priorité d'exécution (ex: ["lint", "format"])
    required_bcasl_version: version minimale requise de BCASL (ex: "2.0.0")
    required_core_version: version minimale requise du Core (ex: "1.0.0")
    required_plugins_sdk_version: version minimale requise du Plugins SDK (ex: "1.0.0")
    required_bc_plugin_context_version: version minimale requise de BcPluginContext (ex: "1.0.0")
    required_general_context_version: version minimale requise de GeneralContext (ex: "1.0.0")
    """

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    tags: tuple[str, ...] = ()
    required_bcasl_version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_plugins_sdk_version: str = "1.0.0"
    required_bc_plugin_context_version: str = "1.0.0"
    required_general_context_version: str = "1.0.0"

    def __post_init__(self) -> None:
        nid = (self.id or "").strip()
        if not nid:
            raise ValueError("PluginMeta invalide: 'id' requis")
        object.__setattr__(self, "id", nid)

        # Normaliser les tags: convertir en tuple de strings minuscules
        try:
            if isinstance(self.tags, str):
                # Si c'est une string, la splitter par virgule
                normalized = tuple(
                    t.strip().lower() for t in str(self.tags).split(",") if t.strip()
                )
            elif isinstance(self.tags, (list, tuple)):
                # Si c'est une liste/tuple, normaliser chaque élément
                normalized = tuple(
                    str(t).strip().lower() for t in self.tags if str(t).strip()
                )
            else:
                normalized = ()
            object.__setattr__(self, "tags", normalized)
        except Exception:
            object.__setattr__(self, "tags", ())


class BcPluginBase:
    """Classe de base minimale que doivent étendre les plugins BCASL.

    Un plugin doit fournir:
    - meta: PluginMeta (avec id unique)
    - requires: dépendances (liste d'ids d'autres plugins)
    - priority: entier pour l'ordonnancement (plus petit => plus tôt)
    - on_pre_compile(ctx): hook principal exécuté avant compilation

    Remarques:
    - Les opérations doivent être idempotentes et robustes (embarqués)
    - Éviter les dépendances externes; stdlib uniquement
    """

    meta: PluginMeta
    requires: tuple[str, ...]
    priority: int

    def __init__(
        self, meta: PluginMeta, requires: Iterable[str] = (), priority: int = 100
    ) -> None:
        if not meta or not meta.id:
            raise ValueError("PluginMeta invalide: 'id' requis")
        # Normaliser l'id pour éviter erreurs de casse/espaces accidentelles
        norm_id = meta.id.strip()
        if not norm_id:
            raise ValueError("PluginMeta invalide: 'id' vide")
        self.meta = meta
        self.requires = tuple(str(r).strip() for r in requires if str(r).strip())
        self.priority = int(priority)

    #  principal Hook
    def on_pre_compile(
        self, ctx: PreCompileContext
    ) -> None:  # pragma: no cover - à surcharger
        raise NotImplementedError

    def __repr__(self) -> str:
        """Return detailed plugin representation with compatibility requirements."""
        reqs = []
        if self.meta.required_bcasl_version != "1.0.0":
            reqs.append(f"bcasl>={self.meta.required_bcasl_version}")
        if self.meta.required_core_version != "1.0.0":
            reqs.append(f"core>={self.meta.required_core_version}")
        if self.meta.required_plugins_sdk_version != "1.0.0":
            reqs.append(f"sdk>={self.meta.required_plugins_sdk_version}")
        if self.meta.required_bc_plugin_context_version != "1.0.0":
            reqs.append(f"bc>={self.meta.required_bc_plugin_context_version}")
        if self.meta.required_general_context_version != "1.0.0":
            reqs.append(f"gc>={self.meta.required_general_context_version}")

        req_str = f" [{', '.join(reqs)}]" if reqs else ""
        return f"<Plugin {self.meta.id} v{self.meta.version} prio={self.priority}{req_str}>"

    def get_compatibility_info(self) -> dict[str, str]:
        """Get plugin compatibility information.

        Returns:
            Dictionary with required versions for BCASL and Core
        """
        return {
            "plugin_id": self.meta.id,
            "plugin_name": self.meta.name,
            "plugin_version": self.meta.version,
            "required_bcasl_version": self.meta.required_bcasl_version,
            "required_core_version": self.meta.required_core_version,
        }

    def is_compatible_with_bcasl(self, bcasl_version: str) -> bool:
        """Check if plugin is compatible with given BCASL version.

        Supports version formats:
        - "1.0.0" -> (1, 0, 0)
        - "1.0.0+" -> (1, 0, 0) [+ means "or higher"]
        - "1.0.0-beta" -> (1, 0, 0)
        - "1.0.0+build123" -> (1, 0, 0)

        Args:
            bcasl_version: BCASL version string to check against

        Returns:
            True if compatible, False otherwise
        """

        def parse_version(v: str) -> tuple:
            try:
                s = v.strip()
                if s.endswith("+"):
                    s = s[:-1].strip()
                s = s.split("+")[0].split("-")[0]
                parts = s.split(".")
                major = int(parts[0]) if len(parts) > 0 else 0
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int(parts[2]) if len(parts) > 2 else 0
                return (major, minor, patch)
            except Exception:
                return (0, 0, 0)

        current = parse_version(bcasl_version)
        required = parse_version(self.meta.required_bcasl_version)
        return current >= required

    def is_compatible_with_core(self, core_version: str) -> bool:
        """Check if plugin is compatible with given Core version.

        Supports version formats:
        - "1.0.0" -> (1, 0, 0)
        - "1.0.0+" -> (1, 0, 0) [+ means "or higher"]
        - "1.0.0-beta" -> (1, 0, 0)
        - "1.0.0+build123" -> (1, 0, 0)

        Args:
            core_version: Core version string to check against

        Returns:
            True if compatible, False otherwise
        """

        def parse_version(v: str) -> tuple:
            try:
                s = v.strip()
                if s.endswith("+"):
                    s = s[:-1].strip()
                s = s.split("+")[0].split("-")[0]
                parts = s.split(".")
                major = int(parts[0]) if len(parts) > 0 else 0
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int(parts[2]) if len(parts) > 2 else 0
                return (major, minor, patch)
            except Exception:
                return (0, 0, 0)

        current = parse_version(core_version)
        required = parse_version(self.meta.required_core_version)
        return current >= required

    def is_compatible_with_plugins_sdk(self, sdk_version: str) -> bool:
        """Check if plugin is compatible with given Plugins SDK version.

        Supports version formats:
        - "1.0.0" -> (1, 0, 0)
        - "1.0.0+" -> (1, 0, 0) [+ means "or higher"]
        - "1.0.0-beta" -> (1, 0, 0)
        - "1.0.0+build123" -> (1, 0, 0)

        Args:
            sdk_version: Plugins SDK version string to check against

        Returns:
            True if compatible, False otherwise
        """

        def parse_version(v: str) -> tuple:
            try:
                s = v.strip()
                if s.endswith("+"):
                    s = s[:-1].strip()
                s = s.split("+")[0].split("-")[0]
                parts = s.split(".")
                major = int(parts[0]) if len(parts) > 0 else 0
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int(parts[2]) if len(parts) > 2 else 0
                return (major, minor, patch)
            except Exception:
                return (0, 0, 0)

        current = parse_version(sdk_version)
        required = parse_version(self.meta.required_plugins_sdk_version)
        return current >= required

    def is_compatible_with_bc_plugin_context(self, context_version: str) -> bool:
        """Check if plugin is compatible with given BcPluginContext version.

        Supports version formats:
        - "1.0.0" -> (1, 0, 0)
        - "1.0.0+" -> (1, 0, 0) [+ means "or higher"]
        - "1.0.0-beta" -> (1, 0, 0)
        - "1.0.0+build123" -> (1, 0, 0)

        Args:
            context_version: BcPluginContext version string to check against

        Returns:
            True if compatible, False otherwise
        """

        def parse_version(v: str) -> tuple:
            try:
                s = v.strip()
                if s.endswith("+"):
                    s = s[:-1].strip()
                s = s.split("+")[0].split("-")[0]
                parts = s.split(".")
                major = int(parts[0]) if len(parts) > 0 else 0
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int(parts[2]) if len(parts) > 2 else 0
                return (major, minor, patch)
            except Exception:
                return (0, 0, 0)

        current = parse_version(context_version)
        required = parse_version(self.meta.required_bc_plugin_context_version)
        return current >= required

    def is_compatible_with_general_context(self, context_version: str) -> bool:
        """Check if plugin is compatible with given GeneralContext version.

        Supports version formats:
        - "1.0.0" -> (1, 0, 0)
        - "1.0.0+" -> (1, 0, 0) [+ means "or higher"]
        - "1.0.0-beta" -> (1, 0, 0)
        - "1.0.0+build123" -> (1, 0, 0)

        Args:
            context_version: GeneralContext version string to check against

        Returns:
            True if compatible, False otherwise
        """

        def parse_version(v: str) -> tuple:
            try:
                s = v.strip()
                if s.endswith("+"):
                    s = s[:-1].strip()
                s = s.split("+")[0].split("-")[0]
                parts = s.split(".")
                major = int(parts[0]) if len(parts) > 0 else 0
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int(parts[2]) if len(parts) > 2 else 0
                return (major, minor, patch)
            except Exception:
                return (0, 0, 0)

        current = parse_version(context_version)
        required = parse_version(self.meta.required_general_context_version)
        return current >= required

    def get_full_compatibility_info(self) -> dict[str, str]:
        """Get complete plugin compatibility information including all SDKs.

        Returns:
            Dictionary with all required versions
        """
        return {
            "plugin_id": self.meta.id,
            "plugin_name": self.meta.name,
            "plugin_version": self.meta.version,
            "required_bcasl_version": self.meta.required_bcasl_version,
            "required_core_version": self.meta.required_core_version,
            "required_plugins_sdk_version": self.meta.required_plugins_sdk_version,
            "required_bc_plugin_context_version": self.meta.required_bc_plugin_context_version,
            "required_general_context_version": self.meta.required_general_context_version,
        }

    def apply_i18n(self, gui, tr: dict[str, str]) -> None:
        raise NotImplementedError


@dataclass
class PreCompileContext:
    """Contexte passé aux plugins.

    Fournit utilitaires peu coûteux pour la découverte des fichiers et la config.
    Donne accès complet au workspace sélectionné et à ses métadonnées.
    """

    project_root: Path
    config: dict[str, Any] = field(default_factory=dict)
    workspace_metadata: dict[str, Any] = field(default_factory=dict)
    _iter_cache: dict[tuple[tuple[str, ...], tuple[str, ...]], list[Path]] = field(
        default_factory=dict, repr=False, compare=False
    )

    def _load_bcasl_config(self) -> dict[str, Any]:
        """Charge la configuration depuis bcasl.yml."""
        try:
            import yaml

            bcasl_file = self.project_root / "bcasl.yml"
            if bcasl_file.exists():
                with open(bcasl_file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        except Exception:
            pass
        return self.config

    def get_workspace_root(self) -> Path:
        """Retourne le chemin racine du workspace sélectionné depuis bcasl.yml."""
        return self.project_root

    def get_workspace_name(self) -> str:
        """Retourne le nom du workspace (nom du dossier) depuis bcasl.yml."""
        return self.project_root.name

    def get_workspace_config(self) -> dict[str, Any]:
        """Retourne la configuration complète du workspace depuis bcasl.yml."""
        cfg = self._load_bcasl_config()
        return dict(cfg) if cfg else {}

    def get_workspace_metadata(self) -> dict[str, Any]:
        """Retourne les métadonnées du workspace depuis bcasl.yml (fichiers requis, patterns, etc.)."""
        cfg = self._load_bcasl_config()
        return {
            "workspace_name": self.project_root.name,
            "workspace_path": str(self.project_root),
            "file_patterns": cfg.get("file_patterns", []),
            "exclude_patterns": cfg.get("exclude_patterns", []),
            "required_files": cfg.get("required_files", []),
        }

    def get_file_patterns(self) -> tuple[str, ...]:
        """Retourne les patterns d'inclusion des fichiers depuis bcasl.yml."""
        cfg = self._load_bcasl_config()
        patterns = cfg.get("file_patterns", []) if isinstance(cfg, dict) else []
        return tuple(patterns) if patterns else ("**/*.py",)

    def get_exclude_patterns(self) -> tuple[str, ...]:
        """Retourne les patterns d'exclusion des fichiers depuis bcasl.yml."""
        cfg = self._load_bcasl_config()
        patterns = cfg.get("exclude_patterns", []) if isinstance(cfg, dict) else []
        return tuple(patterns) if patterns else ()

    def get_required_files(self) -> tuple[str, ...]:
        """Retourne la liste des fichiers requis du workspace depuis bcasl.yml."""
        cfg = self._load_bcasl_config()
        files = cfg.get("required_files", []) if isinstance(cfg, dict) else []
        return tuple(files) if files else ()

    def has_required_file(self, filename: str) -> bool:
        """Vérifie si un fichier requis existe dans le workspace (basé sur bcasl.yml)."""
        try:
            required = self.get_required_files()
            return filename in required and (self.project_root / filename).is_file()
        except Exception:
            return False

    def get_workspace_files(self, pattern: str = "**/*") -> list[Path]:
        """Retourne tous les fichiers du workspace correspondant au pattern (patterns depuis bcasl.yml)."""
        try:
            return list(self.project_root.glob(pattern))
        except Exception:
            return []

    def is_workspace_valid(self) -> bool:
        """Vérifie si le workspace est valide (existe et est accessible, configuré dans bcasl.yml)."""
        try:
            bcasl_file = self.project_root / "bcasl.yml"
            return (
                self.project_root.exists()
                and self.project_root.is_dir()
                and bcasl_file.exists()
            )
        except Exception:
            return False

    def iter_files(
        self, include: Iterable[str], exclude: Iterable[str] = ()
    ) -> Iterable[Path]:
        """Itère sur les fichiers du projet en appliquant des motifs glob d'inclusion/exclusion.

        - include: motifs type glob (ex: "**/*.py", "src/**/*.c")
        - exclude: motifs à exclure (ex: "venv/**", "**/__pycache__/**")
        Optimisé: évite la création de grosses listes; yield au fil de l'eau.
        """
        root = self.project_root
        inc = tuple(include) if include else ("**/*",)
        exc = tuple(exclude) if exclude else tuple()

        # Déterminer si le cache est activé
        try:
            opt = (
                dict(self.config or {}).get("options", {})
                if isinstance(self.config, dict)
                else {}
            )
            enable_cache = bool(opt.get("iter_files_cache", True))
        except Exception:
            enable_cache = True

        # Créer une clé de cache cohérente (patterns normalisés et triés)
        cache_key = None
        if enable_cache:
            try:
                cache_key = (tuple(sorted(inc)), tuple(sorted(exc)))
                cached = self._iter_cache.get(cache_key)
                if cached is not None:
                    for p in cached:
                        yield p
                    return
            except Exception:
                enable_cache = False

        # Fonction pour vérifier si un chemin doit être exclu
        def is_excluded(p: Path) -> bool:
            s = p.as_posix()
            for pat in exc:
                if fnmatch.fnmatch(s, pat):
                    return True
            return False

        # Collecter les fichiers avec déduplication (utiliser un set pour éviter les doublons)
        seen: set[Path] = set()
        collected: list[Path] = []

        for pat in inc:
            try:
                for path in root.glob(pat):
                    if path.is_file() and not is_excluded(path):
                        # Utiliser le chemin résolu pour la déduplication
                        resolved = path.resolve()
                        if resolved not in seen:
                            seen.add(resolved)
                            collected.append(path)
                            yield path
            except (OSError, ValueError):
                # Ignorer les patterns invalides ou les erreurs d'accès
                continue

        # Mettre en cache le résultat si activé
        if enable_cache and cache_key is not None:
            try:
                self._iter_cache[cache_key] = collected
            except Exception:
                pass


@dataclass
class ExecutionItem:
    plugin_id: str
    name: str
    success: bool
    duration_ms: float
    error: str = ""


@dataclass
class ExecutionReport:
    """Rapport d'exécution agrégé après run_pre_compile."""

    items: list[ExecutionItem] = field(default_factory=list)

    def add(self, item: ExecutionItem) -> None:
        self.items.append(item)

    @property
    def ok(self) -> bool:
        return all(i.success for i in self.items)

    def summary(self) -> str:
        total = len(self.items)
        ok = sum(1 for i in self.items if i.success)
        ko = total - ok
        dur = sum(i.duration_ms for i in self.items)
        return f"Plugins: {ok}/{total} ok, {ko} échec(s), temps total {dur:.1f} ms"

    def __iter__(self):
        return iter(self.items)


class _PluginRecord:
    __slots__ = (
        "plugin",
        "active",
        "requires",
        "priority",
        "order",
        "insert_idx",
        "module_path",
        "module_name",
    )

    def __init__(self, plugin: BcPluginBase, insert_idx: int) -> None:
        self.plugin = plugin
        self.active = True
        self.requires = tuple(plugin.requires)
        self.priority = plugin.priority
        self.order = 0  # calculé
        self.insert_idx = insert_idx
        self.module_path: Optional[Path] = None
        self.module_name: Optional[str] = None


def register_plugin(cls: Any) -> Any:
    """Marque une classe comme plugin BCASL (legacy).

    Args:
        cls: Classe à marquer

    Returns:
        La classe inchangée, avec l'attribut __bcasl_plugin__ = True
    """
    setattr(cls, "__bcasl_plugin__", True)
    return cls


def bc_register(
    cls: Optional[type] = None,
    *,
    manager: Any = None,
    auto_instantiate: bool = True,
    priority: Optional[int] = None,
) -> Any:
    """Décorateur pour enregistrer un plugin BCASL.

    Peut être utilisé de plusieurs façons:

    1. En tant que décorateur simple (le plugin sera automatiquement instancié
       et enregistré lorsque le module est importé par BCASL):

       @bc_register
       class MyPlugin(BcPluginBase):
           meta = PluginMeta(
               id="my_plugin",
               name="My Plugin",
               version="1.0.0",
           )

           def on_pre_compile(self, ctx: PreCompileContext) -> None:
               ...

    2. Avec un manager explicite (pour enregistrement immédiat):

       @bc_register(manager=my_manager)
       class MyPlugin(BcPluginBase):
           meta = PluginMeta(
               id="my_plugin",
               name="My Plugin",
               version="1.0.0",
           )
           ...

    3. Avec des options de configuration:

       @bc_register(priority=10)
       class MyPlugin(BcPluginBase):
           meta = PluginMeta(
               id="my_plugin",
               name="My Plugin",
               version="1.0.0",
           )
           ...

    Args:
        cls: Classe de plugin (rempli automatiquement par Python lors de l'utilisation
             du décorateur sans parenthèses).
        manager: Instance optionnelle de BCASL pour enregistrement immédiat.
        auto_instantiate: Si True (défaut), le plugin est instancié automatiquement.
        priority: Priorité optionnelle du plugin (écrase celle définie dans le meta).

    Returns:
        La classe de plugin (avec instance créée si auto_instantiate=True)

    Raises:
        TypeError: Si la classe décorée n'hérite pas de BcPluginBase
        ValueError: Si le plugin n'a pas de métadonnées valides

    Example:
        # Utilisation simple
        from bcasl import BcPluginBase, PluginMeta, bc_register
        from bcasl.Base import PreCompileContext

        @bc_register
        class MyLinter(BcPluginBase):
            meta = PluginMeta(
                id="my_linter",
                name="My Linter",
                version="1.0.0",
                tags=["lint"],
            )

            def on_pre_compile(self, ctx: PreCompileContext) -> None:
                # Votre logique de linting ici
                pass

        # Utilisation avec options
        @bc_register(priority=5)
        class EarlyPlugin(BcPluginBase):
            meta = PluginMeta(
                id="early_plugin",
                name="Early Plugin",
                version="1.0.0",
                tags=["prepare"],
            )

            def on_pre_compile(self, ctx: PreCompileContext) -> None:
                pass
    """
    def decorator_inner(cls_to_decorate: type) -> Any:
        # Vérifier que c'est bien une classe
        if not isinstance(cls_to_decorate, type):
            raise TypeError(
                f"bc_register doit être appliqué à une classe, pas à {type(cls_to_decorate)}"
            )

        # Vérifier l'héritage BcPluginBase (support des deux versions)
        is_valid = False
        try:
            # Vérifier BcPluginBase de bcasl
            if issubclass(cls_to_decorate, BcPluginBase):
                is_valid = True
        except TypeError:
            pass

        # Vérifier si le module Plugins_SDK est disponible
        try:
            from Plugins_SDK.BcPluginContext import BcPluginBase as BcPluginBaseSDK
            if issubclass(cls_to_decorate, BcPluginBaseSDK):
                is_valid = True
        except (ImportError, TypeError):
            pass

        if not is_valid:
            raise TypeError(
                f"La classe décorée avec @bc_register doit hériter de BcPluginBase. "
                f"Classe reçue: {cls_to_decorate.__name__}"
            )

        # Marquer la classe comme plugin BCASL
        setattr(cls_to_decorate, "__bcasl_plugin__", True)

        # Récupérer les métadonnées depuis l'attribut de classe
        meta = getattr(cls_to_decorate, "meta", None)
        if meta is None:
            # Essayer d'instancier pour récupérer le meta depuis l'instance
            # (utile pour les plugins old-style qui passent META à super().__init__)
            try:
                if cls_to_decorate.__init__ is not BcPluginBase.__init__:
                    # Custom __init__ - try to instantiate
                    temp_instance = cls_to_decorate()
                    if hasattr(temp_instance, 'meta'):
                        meta = temp_instance.meta
            except Exception:
                pass
        
        if meta is None:
            raise ValueError(
                f"La classe plugin '{cls_to_decorate.__name__}' doit avoir un attribut 'meta' "
                f"contenant un PluginMeta valide."
            )

        # Valider les métadonnées
        if not hasattr(meta, "id") or not meta.id:
            raise ValueError(
                f"Le PluginMeta du plugin '{cls_to_decorate.__name__}' doit avoir un 'id' défini."
            )

        # Fonction helper pour instancier le plugin
        def _create_plugin_instance() -> "BcPluginBase":
            """Crée une instance du plugin en gérant différents styles d'initialisation."""
            # Stratégie 1: Si la classe a son propre __init__ (comme les plugins existants),
            # essayer d'instancier directement
            init_method = getattr(cls_to_decorate, "__init__", None)
            # Obtenir le __init__ original de BcPluginBase
            base_init = getattr(BcPluginBase, "__init__", None)
            
            # Si la classe n'a pas redéfini __init__ ou si son __init__ est le même que BcPluginBase
            if init_method is base_init or cls_to_decorate.__init__ is BcPluginBase.__init__:
                # Pas de __init__ personnalisé, utiliser meta de l'attribut de classe
                cls_meta = getattr(cls_to_decorate, "meta", None)
                if cls_meta is not None:
                    return cls_to_decorate(meta=cls_meta)
                # fallback: passer meta directement
                return cls_to_decorate(meta)
            else:
                # __init__ personnalisé (probablement comme Cleaner), instancier directement
                try:
                    return cls_to_decorate()
                except TypeError:
                    # Si ça échoue, essayer avec meta
                    cls_meta = getattr(cls_to_decorate, "meta", None)
                    if cls_meta is not None:
                        return cls_to_decorate(meta=cls_meta)
                    return cls_to_decorate(meta)

        # Créer l'instance si demandé
        plugin_instance = None
        if auto_instantiate:
            try:
                plugin_instance = _create_plugin_instance()
                setattr(cls_to_decorate, "_bcasl_instance_", plugin_instance)
            except Exception as e:
                raise ValueError(
                    f"Impossible d'instancier le plugin '{cls_to_decorate.__name__}': {e}"
                ) from e

        # Si un manager est fourni, enregistrer immédiatement
        if manager is not None:
            if plugin_instance is None:
                try:
                    plugin_instance = _create_plugin_instance()
                except Exception as e:
                    raise ValueError(
                        f"Impossible d'instancier le plugin '{cls_to_decorate.__name__}': {e}"
                    ) from e

            # Appliquer la priorité personnalisée si fournie
            if priority is not None and plugin_instance is not None:
                plugin_instance.priority = priority

            # Ajouter au manager
            try:
                manager.add_plugin(plugin_instance)
                _logger.debug("Plugin '%s' enregistré avec @bc_register", meta.id)
            except Exception as e:
                raise RuntimeError(
                    f"Échec de l'enregistrement du plugin '{meta.id}': {e}"
                ) from e

        return cls_to_decorate

    # Gestion des deux syntaxes du décorateur:
    # - @bc_register sans parenthèses: cls est la classe, manager/priority sont None
    # - @bc_register() ou @bc_register(manager=x): cls est None, retourne decorator_inner
    
    if cls is not None and isinstance(cls, type):
        # @bc_register sans parenthèses - cls est la classe à décorée
        return decorator_inner(cls)
    
    # @bc_register() ou @bc_register(manager=x, priority=x) - retourner le décorateur
    # Les paramètres manager et priority ont été capturés dans la closure
    return decorator_inner
