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
User preferences management for PyCompiler ARK.
Inclut la sauvegarde et le loadment des preferences.
La language selected par l'utilisateur (clé "language") est enregistrée et restaurée automatiquement.
"""

import json
import os

MAX_PARALLEL = 3
PREFS_BASENAME = "gui_prefs.json"


def _user_config_dir() -> str:
    """
    Return le folder de preferences global de l'utilisateur : ~/.pycompiler_ark
    """
    return os.path.expanduser("~/.pycompiler_ark")


def _prefs_path() -> str:
    cfgdir = _user_config_dir()
    try:
        os.makedirs(cfgdir, exist_ok=True)
    except Exception:
        pass
    return os.path.join(cfgdir, PREFS_BASENAME)


PREFS_FILE = _prefs_path()


def _atomic_write_json(path: str, data: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    # os.replace is atomic on POSIX/Windows
    os.replace(tmp, path)


def load_preferences(self):
    try:
        # Essaye d'abord le chemin config utilisateur (nouveau), puis les anciens chemins (migration)
        prefs_path = PREFS_FILE
        try:
            with open(prefs_path, encoding="utf-8") as f:
                prefs = json.load(f)
        except Exception:
            # Migration douce: tenter l'ancien chemin dans le projet <project_root>/.pref
            try:
                project_root = os.path.abspath(
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
                )
                old_pref_dir = os.path.join(project_root, ".pref")
                old_pref_path = os.path.join(old_pref_dir, PREFS_BASENAME)
                with open(old_pref_path, encoding="utf-8") as f:
                    prefs = json.load(f)
            except Exception:
                # Migration douce: tenter l'ancien chemin <project_root>/pref/
                try:
                    old_dir = os.path.abspath(
                        os.path.join(
                            os.path.dirname(os.path.abspath(__file__)),
                            os.pardir,
                            "pref",
                        )
                    )
                    old_path = os.path.join(old_dir, PREFS_BASENAME)
                    with open(old_path, encoding="utf-8") as f:
                        prefs = json.load(f)
                except Exception:
                    # Dernier recours: fichier à la racine du cwd
                    with open(PREFS_BASENAME, encoding="utf-8") as f:
                        prefs = json.load(f)

        self.language_pref = prefs.get("language_pref", prefs.get("language", "System"))
        # Compat: conserver self.language utilisé ailleurs
        self.language = self.language_pref
        # Thème UI
        self.theme = prefs.get("theme", "System")
    except Exception:
        # Préférence de langue par défaut
        self.language_pref = "System"
        self.language = "System"
        # Thème UI par défaut
        self.theme = "System"


def save_preferences(self):
    # Minimal persisted preferences: only language/theme; other UI states omitted by design.
    prefs = {
        "language_pref": getattr(
            self,
            "language_pref",
            getattr(self, "language", getattr(self, "current_language", "System")),
        ),
        "language": getattr(
            self,
            "language_pref",
            getattr(self, "language", getattr(self, "current_language", "System")),
        ),
        "theme": getattr(self, "theme", "System"),
    }
    try:
        # Écriture atomique dans le dossier de config utilisateur
        try:
            os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
        except Exception:
            pass
        _atomic_write_json(PREFS_FILE, prefs)
        # Écrit également un JSON d'information système détectée (diagnostic)
        try:
            export_system_preferences_json()
        except Exception:
            pass
    except Exception as e:
        try:
            from pycompiler_ark.Ui import output

            output.warn(
                (
                    f"Impossible de sauvegarder les préférences : {e}",
                    f"Unable to save preferences: {e}",
                ),
                gui=self,
            )
        except Exception:
            try:
                from pycompiler_ark.Ui import output

                output.warn(
                    f"Impossible de sauvegarder les préférences : {e}", gui=self
                )
            except Exception:
                pass


# --- System preference detection helpers ---


def detect_system_color_scheme() -> str:
    """
    Detect the system color scheme and return "dark" or "light".
    - Windows: registry AppsUseLightTheme (0 = dark, 1 = light)
    - macOS: defaults read -g AppleInterfaceStyle (Dark = dark)
    - Linux (GNOME/KDE): gsettings or kdeglobals, fallback to GTK_THEME
    Returns "light" on failure.
    """
    try:
        import os as _os
        import platform
        import subprocess

        sysname = platform.system()
        # Windows
        if sysname == "Windows":
            try:
                out = subprocess.run(
                    [
                        "reg",
                        "query",
                        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                        "/v",
                        "AppsUseLightTheme",
                    ],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and out.stdout:
                    val = out.stdout.lower()
                    if "0x0" in val or " 0x0\n" in val:
                        return "dark"
                    return "light"
            except Exception:
                pass
            return "light"
        # macOS
        if sysname == "Darwin":
            try:
                out = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and "dark" in out.stdout.strip().lower():
                    return "dark"
            except Exception:
                pass
            return "light"
        # Linux (GNOME/KDE)
        if sysname == "Linux":
            # GNOME 42+: color-scheme
            try:
                out = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and "prefer-dark" in out.stdout:
                    return "dark"
            except Exception:
                pass
            # GNOME: gtk-theme contains "dark"
            try:
                out = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and "dark" in out.stdout.lower():
                    return "dark"
            except Exception:
                pass
            # KDE: kdeglobals
            try:
                kdeglobals = _os.path.expanduser("~/.config/kdeglobals")
                if _os.path.isfile(kdeglobals):
                    with open(kdeglobals, encoding="utf-8", errors="ignore") as f:
                        txt = f.read().lower()
                    if "colorscheme" in txt and "dark" in txt:
                        return "dark"
            except Exception:
                pass
            # Env GTK_THEME
            try:
                gtk_theme = _os.environ.get("GTK_THEME", "").lower()
                if gtk_theme and "dark" in gtk_theme:
                    return "dark"
            except Exception:
                pass
            return "light"
        # Other systems
        return "light"
    except Exception:
        return "light"


def detect_system_language() -> tuple[str, str]:
    """
    Detect the system language and return a pair (code, display_name),
    where code is like 'fr' or 'en', and display_name is 'Français' or 'English'.
    Defaults to ('en', 'English') on failure.
    """
    try:
        import locale

        loc = (locale.getlocale()[0] or "").lower()
        if loc.startswith(("fr", "fr_")):
            return ("fr", "Français")
        return ("en", "English")
    except Exception:
        return ("en", "English")


def preferences_system_info() -> dict:
    """
    Return a dict summarizing system-related preference defaults and paths.
    Keys:
     - config_dir: user configuration directory used by the app
     - prefs_file: absolute path to the JSON preferences file
     - system_language_code: e.g., 'fr' or 'en'
     - system_language_name: human-readable name
     - system_theme: 'dark' or 'light'
    """
    try:
        code, name = detect_system_language()
    except Exception:
        code, name = ("en", "English")
    try:
        theme = detect_system_color_scheme()
    except Exception:
        theme = "light"
    return {
        "config_dir": _user_config_dir(),
        "prefs_file": PREFS_FILE,
        "system_language_code": code,
        "system_language_name": name,
        "system_theme": theme,
    }


def export_system_preferences_json(path: str | None = None) -> str:
    """
    Write JSON file containing system information tied to preferences
    (language système détectée, theme clair/sombre, paths de config).
    Si path n'est pas fourni, écrit dans le folder de config utilisateur
    sous le nom 'system_infos.json'. Return le path final écrit.
    """
    data = preferences_system_info()
    if not path:
        path = os.path.join(_user_config_dir(), "system_infos.json")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass
    _atomic_write_json(path, data)
    return path
