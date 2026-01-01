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
Example: Engine with UI Binding

Démontre comment utiliser le système de binding UI pour gérer la configuration.
"""

from engines_loader import CompilerEngine, UIBindingManager


class ExampleEngineWithUI(CompilerEngine):
    """Engine avec gestion UI automatique de la configuration."""

    id = "example_ui"
    name = "Example with UI"
    version = "1.0.0"

    config_schema = {
        "enabled": True,
        "optimization_level": 2,
        "strip_binaries": False,
        "output_dir": "dist",
        "timeout_seconds": 300,
    }

    def __init__(self):
        super().__init__()
        self.ui_manager: UIBindingManager | None = None

    def create_tab(self, gui):
        """Crée l'onglet avec widgets liés à la configuration."""
        try:
            from PySide6.QtWidgets import (
                QWidget,
                QVBoxLayout,
                QHBoxLayout,
                QLabel,
                QLineEdit,
                QCheckBox,
                QSpinBox,
                QComboBox,
            )
        except Exception:
            return None

        # Créer le widget principal
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Créer le gestionnaire de binding
        self.ui_manager = self.create_ui_binding_manager()

        # === Optimization Level ===
        opt_row = QHBoxLayout()
        opt_label = QLabel("Optimization Level:")
        opt_spin = QSpinBox()
        opt_spin.setMinimum(0)
        opt_spin.setMaximum(3)
        opt_row.addWidget(opt_label)
        opt_row.addWidget(opt_spin)
        opt_row.addStretch()
        layout.addLayout(opt_row)

        # Lier le spinbox à la config
        self.ui_manager.bind("optimization_level", opt_spin, "spinbox")

        # === Strip Binaries ===
        strip_cb = QCheckBox("Strip Binaries")
        layout.addWidget(strip_cb)

        # Lier la checkbox à la config
        self.ui_manager.bind("strip_binaries", strip_cb, "checkbox")

        # === Output Directory ===
        out_row = QHBoxLayout()
        out_label = QLabel("Output Directory:")
        out_edit = QLineEdit()
        out_edit.setPlaceholderText("dist")
        out_row.addWidget(out_label)
        out_row.addWidget(out_edit)
        layout.addLayout(out_row)

        # Lier le lineedit à la config
        self.ui_manager.bind("output_dir", out_edit, "lineedit")

        # === Timeout ===
        timeout_row = QHBoxLayout()
        timeout_label = QLabel("Timeout (seconds):")
        timeout_spin = QSpinBox()
        timeout_spin.setMinimum(1)
        timeout_spin.setMaximum(3600)
        timeout_row.addWidget(timeout_label)
        timeout_row.addWidget(timeout_spin)
        timeout_row.addStretch()
        layout.addLayout(timeout_row)

        # Lier le spinbox à la config
        self.ui_manager.bind("timeout_seconds", timeout_spin, "spinbox")

        # Ajouter du stretch pour remplir l'espace
        layout.addStretch()

        # Charger la configuration sauvegardée dans les widgets
        self.load_ui_from_config(self.ui_manager)

        return tab, gui.tr("Example UI", "Example UI")

    def build_command(self, gui, file: str) -> list[str]:
        """Utilise la configuration pour construire la commande."""
        if not self.ui_manager:
            config = self.load_config()
        else:
            config = self.ui_manager.save_to_config()

        cmd = ["example-compiler"]

        opt_level = config.get("optimization_level", 2)
        if opt_level > 0:
            cmd.append(f"-O{opt_level}")

        if config.get("strip_binaries"):
            cmd.append("--strip")

        cmd.append(file)
        return cmd


# Exemple d'utilisation directe (sans GUI)
def example_direct_usage():
    """Utilisation directe sans GUI."""
    engine = ExampleEngineWithUI()

    # Charger la config
    config = engine.load_config()
    print(f"Loaded config: {config}")

    # Modifier et sauvegarder
    config["optimization_level"] = 3
    config["strip_binaries"] = True
    engine.save_config(config)

    print(f"Saved config: {config}")


# Exemple avec binding manager (sans GUI)
def example_binding_manager():
    """Utilisation du binding manager sans widgets réels."""
    from engines_loader import UIBindingManager

    manager = UIBindingManager("example_ui")

    # Créer des objets mock pour tester
    class MockLineEdit:
        def __init__(self, value=""):
            self.value = value

        def text(self):
            return self.value

        def setText(self, value):
            self.value = value

        def textChanged(self):
            pass

    class MockSpinBox:
        def __init__(self, value=0):
            self.value = value

        def value(self):
            return self.value

        def setValue(self, value):
            self.value = value

        def valueChanged(self):
            pass

    # Lier les widgets mock
    output_edit = MockLineEdit("dist")
    timeout_spin = MockSpinBox(300)

    manager.bind("output_dir", output_edit, "lineedit")
    manager.bind("timeout_seconds", timeout_spin, "spinbox")

    # Charger la config
    config = {
        "output_dir": "build",
        "timeout_seconds": 600,
    }
    manager.load_from_config(config)

    print(f"Output dir: {output_edit.text()}")
    print(f"Timeout: {timeout_spin.value()}")

    # Sauvegarder
    saved = manager.save_to_config()
    print(f"Saved: {saved}")


if __name__ == "__main__":
    print("Example 1: Direct usage")
    example_direct_usage()

    print("\nExample 2: Binding manager")
    example_binding_manager()
