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

"""
Module de chargement de la configuration ARK

Ce module est responsable de:
- Charger la configuration depuis le fichier ARK_Main_Config.yml à la racine du workspace
- Gérer les patterns d'inclusion/exclusion de fichiers
- Fournir des fonctions utilitaires pour accéder aux options de configuration
- Créer un fichier de configuration par défaut si nécessaire

Le fichier de configuration utilise le format YAML et permet de personnaliser:
- Les patterns de fichiers à inclure/exclure de la compilation
- Les gestionnaires d'environnement virtuel (Poetry, Pipenv, Conda, etc.)
- Les options de dépendances

Note: La configuration des plugins BCASL est gérée exclusivement par bcasl.yml
"""

import os
import fnmatch
from pathlib import Path, PurePosixPath
from typing import Any, Optional
import yaml


# =============================================================================
# PATTERNS D'EXCLUSION PAR DÉFAUT
# =============================================================================
# Ces patterns sont appliqués lors de la découverte des fichiers Python
# dans le workspace. Ils permettent d'exclure les fichiers non pertinents
# tels que les caches, les environnements virtuels, les fichiers compilés, etc.

DEFAULT_EXCLUSION_PATTERNS = [
    # Répertoires de cache Python
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.pyd",
    # Répertoires de gestion de version
    ".git/**",
    ".svn/**",
    ".hg/**",
    # Environnements virtuels (différentes conventions de nommage)
    "venv/**",
    ".venv/**",
    "env/**",
    ".env/**",
    # Modules Node.js (pour les projets hybrides)
    "node_modules/**",
    # Répertoires de build et distribution
    "build/**",
    "dist/**",
    # Métadonnées des packages Python
    "*.egg-info/**",
    # Répertoires de tests et linting
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".tox/**",
    # Packages système (rarement nécessaires pour la compilation)
    "site-packages/**",
]


# =============================================================================
# CONFIGURATION PAR DÉFAUT
# =============================================================================
# Cette configuration est utilisée comme base lorsque aucun fichier
# ARK_Main_Config.yml n'est trouvé dans le workspace. Elle peut être
# partiellement ou entièrement surchargée par la configuration utilisateur.

DEFAULT_CONFIG = {
    # -----------------------------------------------------------------------------
    # PATTERNS DE FICHIERS
    # -----------------------------------------------------------------------------
    "exclusion_patterns": DEFAULT_EXCLUSION_PATTERNS,
    "inclusion_patterns": ["**/*.py"],
    # -----------------------------------------------------------------------------
    # GESTION DES DÉPENDANCES
    # -----------------------------------------------------------------------------
    "dependencies": {
        # Ordre de priorité pour la détection des fichiers de dépendances
        "requirements_files": [
            "requirements.txt",
            "requirements-prod.txt",
            "requirements-dev.txt",
            "Pipfile",
            "Pipfile.lock",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "poetry.lock",
            "conda.yml",
            "environment.yml",
        ],
        # Génération automatique de requirements.txt depuis les imports du projet
        "auto_generate_from_imports": True,
    },
    # -----------------------------------------------------------------------------
    # GESTIONNAIRES D'ENVIRONNEMENT VIRTUEL
    # -----------------------------------------------------------------------------
    "environment_manager": {
        # Ordre de priorité pour la détection automatique du gestionnaire
        "priority": ["poetry", "pipenv", "conda", "pdm", "uv", "pip"],
        # Activer la détection automatique du gestionnaire
        "auto_detect": True,
        # Revenir à pip si aucun gestionnaire n'est détecté
        "fallback_to_pip": True,
    },
    # -----------------------------------------------------------------------------
    # BUILD / POINT D'ENTRÉE
    # -----------------------------------------------------------------------------
    "build": {
        # Chemin relatif du point d'entrée à compiler (ex: "app.py")
        "entrypoint": None,
    },
}


def _deep_merge_dict(base: dict, override: dict) -> dict:
    """
    Fusionne récursivement deux dictionnaires.

    Cette fonction permet de combiner une configuration de base avec des
    valeurs personnalisées. Les dictionnaires imbriqués sont fusionnés
    plutôt que remplacés, permettant une configuration modulaire.

    Args:
        base: Dictionnaire de configuration de base
        override: Dictionnaire contenant les valeurs à surcharger

    Returns:
        Un nouveau dictionnaire avec les valeurs fusionnées
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Fusion récursive pour les dictionnaires imbriqués
            result[key] = _deep_merge_dict(result[key], value)
        else:
            # Remplacement simple pour les autres types
            result[key] = value
    return result


def load_ark_config(workspace_dir: str) -> dict[str, Any]:
    """
    Charge la configuration ARK depuis un fichier YAML.

    Cette fonction recherche un fichier de configuration dans le workspace
    selon un ordre de priorité prédéfini et fusionne la configuration
    utilisateur avec les valeurs par défaut.

    Fichiers recherchés (ordre de priorité):
    1. ARK_Main_Config.yaml
    2. ARK_Main_Config.yml
    3. .ARK_Main_Config.yaml
    4. .ARK_Main_Config.yml

    Args:
        workspace_dir: Chemin absolu vers le répertoire du workspace

    Returns:
        Dictionnaire complet de configuration, incluant les valeurs par défaut
        et les personnalisations utilisateur
    """
    import copy

    # Commencer avec une copie complète de la configuration par défaut
    config = copy.deepcopy(DEFAULT_CONFIG)

    # Validation du paramètre d'entrée
    if not workspace_dir:
        # Normaliser la section build
        build_opts = config.get("build", {})
        if not isinstance(build_opts, dict):
            build_opts = {}
        entrypoint = build_opts.get("entrypoint")
        if isinstance(entrypoint, str):
            entrypoint = entrypoint.strip() or None
        else:
            entrypoint = None
        build_opts["entrypoint"] = entrypoint
        config["build"] = build_opts
        return config

    workspace_path = Path(workspace_dir)

    # Liste des candidats fichiers de configuration par ordre de priorité
    config_candidates = [
        workspace_path / "ARK_Main_Config.yaml",
        workspace_path / "ARK_Main_Config.yml",
        workspace_path / ".ARK_Main_Config.yaml",
        workspace_path / ".ARK_Main_Config.yml",
    ]

    # Rechercher le premier fichier de configuration existant
    config_file = None
    for candidate in config_candidates:
        if candidate.exists() and candidate.is_file():
            config_file = candidate
            break

    # Aucun fichier de configuration trouvé
    if not config_file:
        return config

    try:
        # Lecture et parsing du fichier YAML
        with open(config_file, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}

        # Validation du format (doit être un dictionnaire)
        if not isinstance(user_config, dict):
            return config

        # Fusion de la configuration utilisateur avec les valeurs par défaut
        config = _deep_merge_dict(config, user_config)

        # -----------------------------------------------------------------------------
        # VALIDATION ET NORMALISATION DES PATTERNS D'EXCLUSION
        # -----------------------------------------------------------------------------
        # Les patterns utilisateur sont ajoutés à la liste par défaut
        if "exclusion_patterns" in config:
            if isinstance(config["exclusion_patterns"], list):
                # Conversion en chaînes et过滤 des valeurs nulles
                user_patterns = [str(p) for p in config["exclusion_patterns"] if p]
                # Fusion avec les patterns par défaut (évite les doublons)
                config["exclusion_patterns"] = list(
                    set(DEFAULT_EXCLUSION_PATTERNS + user_patterns)
                )

        # -----------------------------------------------------------------------------
        # VALIDATION DES PATTERNS D'INCLUSION
        # -----------------------------------------------------------------------------
        if "inclusion_patterns" in config:
            if isinstance(config["inclusion_patterns"], list):
                config["inclusion_patterns"] = [
                    str(p) for p in config["inclusion_patterns"] if p
                ]

        return config

    except Exception as e:
        print(
            f"Attention: Échec du chargement de la config ARK depuis {config_file}: {e}"
        )
        return config


def get_dependency_options(config: dict[str, Any]) -> dict[str, Any]:
    """
    Récupère les options de gestion des dépendances.

    Returns:
        Dictionnaire des options de dépendances
    """
    return config.get("dependencies", {})


def get_environment_manager_options(config: dict[str, Any]) -> dict[str, Any]:
    """
    Récupère les options du gestionnaire d'environnement virtuel.

    Returns:
        Dictionnaire des options du gestionnaire d'environnement
    """
    return config.get("environment_manager", {})


def get_build_options(config: dict[str, Any]) -> dict[str, Any]:
    """
    Récupère les options de build.

    Returns:
        Dictionnaire des options de build
    """
    return config.get("build", {})


def get_entrypoint(config: dict[str, Any]) -> Optional[str]:
    """
    Récupère le point d'entrée configuré.

    Returns:
        Chemin relatif du point d'entrée ou None
    """
    build_opts = get_build_options(config)
    if not isinstance(build_opts, dict):
        return None
    entry = build_opts.get("entrypoint")
    return entry if isinstance(entry, str) and entry.strip() else None


def save_ark_config(workspace_dir: str, config: dict[str, Any]) -> bool:
    """
    Sauvegarde la configuration ARK dans ARK_Main_Config.yml.

    Args:
        workspace_dir: Chemin du workspace
        config: Configuration complète à enregistrer

    Returns:
        True si succès, False sinon
    """
    if not workspace_dir or not isinstance(config, dict):
        return False
    try:
        workspace_path = Path(workspace_dir)
        config_file = workspace_path / "ARK_Main_Config.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                config,
                f,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )
        return True
    except Exception:
        return False


def set_entrypoint(workspace_dir: str, entrypoint: Optional[str]) -> bool:
    """
    Met à jour le point d'entrée dans ARK_Main_Config.yml.

    Args:
        workspace_dir: Chemin du workspace
        entrypoint: Chemin relatif du point d'entrée (ou None pour effacer)

    Returns:
        True si succès, False sinon
    """
    if not workspace_dir:
        return False
    cfg = load_ark_config(workspace_dir)
    build_opts = cfg.get("build", {})
    if not isinstance(build_opts, dict):
        build_opts = {}
    if isinstance(entrypoint, str):
        entrypoint = entrypoint.strip() or None
    else:
        entrypoint = None
    build_opts["entrypoint"] = entrypoint
    cfg["build"] = build_opts
    return save_ark_config(workspace_dir, cfg)


def _normalize_exclusion_pattern(pattern: str) -> str:
    """
    Normalise un pattern d'exclusion pour un matching fiable cross-plateforme.

    - Convertit les séparateurs Windows en "/"
    - Retire le préfixe "./"
    - Si le pattern se termine par "/", on l'étend à "/**"
    """
    p = str(pattern).strip()
    if not p:
        return ""
    p = p.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    if p.endswith("/"):
        p = p.rstrip("/") + "/**"
    return p


def should_exclude_file(
    file_path: str, workspace_dir: str, exclusion_patterns: Optional[list[str]]
) -> bool:
    """
    Détermine si un fichier doit être exclu de la compilation.

    Cette fonction compare le chemin du fichier avec les patterns
    d'exclusion définis dans la configuration. Elle normalise les
    séparateurs puis combine Path.match() et fnmatch pour supporter
    les patterns glob avec "**" de façon cross-plateforme.

    Args:
        file_path: Chemin absolu du fichier à vérifier
        workspace_dir: Chemin absolu du workspace
        exclusion_patterns: Liste des patterns d'exclusion

    Returns:
        True si le fichier doit être exclu, False sinon
    """
    try:
        if not file_path or not workspace_dir:
            return False

        file_path_obj = Path(file_path)
        workspace_path_obj = Path(workspace_dir)

        # Résolution pour éviter les surprises (symlinks, chemins relatifs)
        try:
            file_abs = file_path_obj.resolve()
            workspace_abs = workspace_path_obj.resolve()
        except Exception:
            file_abs = file_path_obj
            workspace_abs = workspace_path_obj

        # Calcul du chemin relatif par rapport au workspace
        try:
            relative_path = file_abs.relative_to(workspace_abs)
        except ValueError:
            # Le fichier est hors du workspace
            return True

        # Normalisation vers POSIX pour matcher les patterns avec "/"
        rel_posix = PurePosixPath(relative_path.as_posix())
        abs_posix = PurePosixPath(file_abs.as_posix())
        rel_str = rel_posix.as_posix()
        abs_str = abs_posix.as_posix()
        file_name = file_abs.name

        patterns = exclusion_patterns or []

        # Vérification des patterns d'exclusion
        for pattern in patterns:
            pat = _normalize_exclusion_pattern(pattern)
            if not pat:
                continue

            # Patterns avec "**" : matcher via fnmatch pour supporter les répertoires
            if "**" in pat:
                if fnmatch.fnmatch(rel_str, pat):
                    return True
                if fnmatch.fnmatch(abs_str, pat):
                    return True
            else:
                # Comparaison avec le chemin relatif complet
                if rel_posix.match(pat):
                    return True

                # Autoriser les patterns absolus si fournis par l'utilisateur
                if abs_posix.match(pat):
                    return True

            # Comparaison avec juste le nom du fichier (pour patterns comme "*.pyc")
            if "/" not in pat and PurePosixPath(file_name).match(pat):
                return True

        return False

    except Exception:
        # En cas d'erreur, safer de ne pas exclure le fichier
        return False


def create_default_ark_config(workspace_dir: str) -> bool:
    """
    Crée un fichier ARK_Main_Config.yml avec la configuration par défaut.

    Cette fonction génère un fichier de configuration complet avec
    toutes les options disponibles et leurs valeurs par défaut.
    Elle ne remplace pas un fichier existant.

    Args:
        workspace_dir: Chemin du répertoire du workspace

    Returns:
        True si le fichier a été créé avec succès, False s'il existe déjà
        ou si une erreur s'est produite
    """
    if not workspace_dir:
        return False

    workspace_path = Path(workspace_dir)
    config_file = workspace_path / "ARK_Main_Config.yml"

    # Ne pas écraser un fichier existant
    if config_file.exists():
        return False

    try:
        # Contenu du fichier de configuration par défaut
        default_content = """# ════════════════════════════════════════════════════════════════
# Fichier de Configuration Principal ARK
# ════════════════════════════════════════════════════════════════════════

# Ce fichier permet de personnaliser le comportement de PyCompiler ARK
# pour ce workspace spécifique. Reportez-vous à la documentation pour
# plus de détails sur les options disponibles.

# -----------------------------------------------------------------------------
# PATTERNS DE FICHIERS
# -----------------------------------------------------------------------------
# Patterns pour exclure certains fichiers/répertoires de la compilation
exclusion_patterns:
  - "**/__pycache__/**"
  - "**/*.pyc"
  - "**/*.pyo"
  - "**/*.pyd"
  - ".git/**"
  - ".svn/**"
  - "venv/**"
  - ".venv/**"
  - "env/**"
  - "build/**"
  - "dist/**"
  - "*.egg-info/**"
  - ".pytest_cache/**"
  - ".mypy_cache/**"
  - "node_modules/**"

# Patterns pour inclure certains fichiers (par défaut: tous les .py)
inclusion_patterns:
  - "**/*.py"



# -----------------------------------------------------------------------------
# GESTION DES DÉPENDANCES
# -----------------------------------------------------------------------------
dependencies:
  # Générer automatiquement requirements.txt depuis les imports du projet
  auto_generate_from_imports: true

# -----------------------------------------------------------------------------
# GESTIONNAIRE D'ENVIRONNEMENT VIRTUEL
# -----------------------------------------------------------------------------
# Priorité de détection des gestionnaires d'environnement
environment_manager:
  priority:
    - "poetry"
    - "pipenv"
    - "conda"
    - "pdm"
    - "uv"
    - "pip"
  auto_detect: true
  fallback_to_pip: true

# -----------------------------------------------------------------------------
# BUILD / POINT D'ENTRÉE
# -----------------------------------------------------------------------------
build:
  # Chemin relatif du point d'entrée à compiler (ex: "app.py")
  entrypoint: null
"""

        with open(config_file, "w", encoding="utf-8") as f:
            f.write(default_content)

        return True

    except Exception as e:
        print(f"Attention: Échec de la création de ARK_Main_Config.yml: {e}")
        return False
