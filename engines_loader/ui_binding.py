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
Engine UI Binding System
Permet aux engines de lier leurs widgets UI à la configuration persistante.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, List
from abc import ABC, abstractmethod


class UIBinding(ABC):
    """Binding abstrait entre un widget et une clé de configuration."""

    def __init__(self, key: str, widget: Any):
        """
        Args:
            key: Clé de configuration (ex: "optimization_level")
            widget: Widget PySide6 à lier
        """
        self.key = key
        self.widget = widget

    @abstractmethod
    def get_value(self) -> Any:
        """Récupère la valeur du widget."""
        pass

    @abstractmethod
    def set_value(self, value: Any) -> None:
        """Définit la valeur du widget."""
        pass

    @abstractmethod
    def connect_changed(self, callback: Callable[[Any], None]) -> None:
        """Connecte un callback au changement du widget."""
        pass


class LineEditBinding(UIBinding):
    """Binding pour QLineEdit."""

    def get_value(self) -> str:
        try:
            return self.widget.text().strip()
        except Exception:
            return ""

    def set_value(self, value: Any) -> None:
        try:
            self.widget.setText(str(value) if value is not None else "")
        except Exception:
            pass

    def connect_changed(self, callback: Callable[[Any], None]) -> None:
        try:
            self.widget.textChanged.connect(lambda: callback(self.get_value()))
        except Exception:
            pass


class CheckBoxBinding(UIBinding):
    """Binding pour QCheckBox."""

    def get_value(self) -> bool:
        try:
            return self.widget.isChecked()
        except Exception:
            return False

    def set_value(self, value: Any) -> None:
        try:
            self.widget.setChecked(bool(value))
        except Exception:
            pass

    def connect_changed(self, callback: Callable[[Any], None]) -> None:
        try:
            self.widget.stateChanged.connect(lambda: callback(self.get_value()))
        except Exception:
            pass


class ComboBoxBinding(UIBinding):
    """Binding pour QComboBox."""

    def get_value(self) -> str:
        try:
            return self.widget.currentText()
        except Exception:
            return ""

    def set_value(self, value: Any) -> None:
        try:
            idx = self.widget.findText(str(value))
            if idx >= 0:
                self.widget.setCurrentIndex(idx)
        except Exception:
            pass

    def connect_changed(self, callback: Callable[[Any], None]) -> None:
        try:
            self.widget.currentTextChanged.connect(lambda: callback(self.get_value()))
        except Exception:
            pass


class SpinBoxBinding(UIBinding):
    """Binding pour QSpinBox."""

    def get_value(self) -> int:
        try:
            return self.widget.value()
        except Exception:
            return 0

    def set_value(self, value: Any) -> None:
        try:
            self.widget.setValue(int(value) if value is not None else 0)
        except Exception:
            pass

    def connect_changed(self, callback: Callable[[Any], None]) -> None:
        try:
            self.widget.valueChanged.connect(lambda: callback(self.get_value()))
        except Exception:
            pass


class DoubleSpinBoxBinding(UIBinding):
    """Binding pour QDoubleSpinBox."""

    def get_value(self) -> float:
        try:
            return self.widget.value()
        except Exception:
            return 0.0

    def set_value(self, value: Any) -> None:
        try:
            self.widget.setValue(float(value) if value is not None else 0.0)
        except Exception:
            pass

    def connect_changed(self, callback: Callable[[Any], None]) -> None:
        try:
            self.widget.valueChanged.connect(lambda: callback(self.get_value()))
        except Exception:
            pass


class SliderBinding(UIBinding):
    """Binding pour QSlider."""

    def get_value(self) -> int:
        try:
            return self.widget.value()
        except Exception:
            return 0

    def set_value(self, value: Any) -> None:
        try:
            self.widget.setValue(int(value) if value is not None else 0)
        except Exception:
            pass

    def connect_changed(self, callback: Callable[[Any], None]) -> None:
        try:
            self.widget.valueChanged.connect(lambda: callback(self.get_value()))
        except Exception:
            pass


class UIBindingManager:
    """Gestionnaire de bindings UI pour un engine."""

    def __init__(self, engine_id: str):
        """
        Args:
            engine_id: Identifiant de l'engine
        """
        self.engine_id = engine_id
        self.bindings: Dict[str, UIBinding] = {}
        self._auto_save_enabled = True
        self._on_change_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def bind(self, key: str, widget: Any, binding_type: Optional[str] = None) -> UIBinding:
        """
        Lie un widget à une clé de configuration.

        Args:
            key: Clé de configuration
            widget: Widget PySide6
            binding_type: Type de binding ("lineedit", "checkbox", "combobox", "spinbox", "doublespinbox", "slider")
                         Si None, détecte automatiquement

        Returns:
            L'objet UIBinding créé
        """
        if binding_type is None:
            binding_type = self._detect_widget_type(widget)

        binding_class = self._get_binding_class(binding_type)
        binding = binding_class(key, widget)

        # Connecter le callback de changement
        binding.connect_changed(lambda value: self._on_widget_changed(key, value))

        self.bindings[key] = binding
        return binding

    def _detect_widget_type(self, widget: Any) -> str:
        """Détecte automatiquement le type de widget."""
        widget_class_name = widget.__class__.__name__

        type_map = {
            "QLineEdit": "lineedit",
            "QCheckBox": "checkbox",
            "QComboBox": "combobox",
            "QSpinBox": "spinbox",
            "QDoubleSpinBox": "doublespinbox",
            "QSlider": "slider",
        }

        return type_map.get(widget_class_name, "lineedit")

    def _get_binding_class(self, binding_type: str) -> type[UIBinding]:
        """Retourne la classe de binding appropriée."""
        type_map = {
            "lineedit": LineEditBinding,
            "checkbox": CheckBoxBinding,
            "combobox": ComboBoxBinding,
            "spinbox": SpinBoxBinding,
            "doublespinbox": DoubleSpinBoxBinding,
            "slider": SliderBinding,
        }
        return type_map.get(binding_type, LineEditBinding)

    def load_from_config(self, config: Dict[str, Any]) -> None:
        """Charge les valeurs des widgets depuis la configuration."""
        self._auto_save_enabled = False
        try:
            for key, binding in self.bindings.items():
                if key in config:
                    binding.set_value(config[key])
        finally:
            self._auto_save_enabled = True

    def save_to_config(self) -> Dict[str, Any]:
        """Sauvegarde les valeurs des widgets dans un dictionnaire."""
        config = {}
        for key, binding in self.bindings.items():
            try:
                config[key] = binding.get_value()
            except Exception:
                pass
        return config

    def _on_widget_changed(self, key: str, value: Any) -> None:
        """Appelé quand un widget change."""
        if not self._auto_save_enabled:
            return

        config = self.save_to_config()

        if self._on_change_callback:
            try:
                self._on_change_callback(config)
            except Exception:
                pass

    def on_config_changed(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Enregistre un callback appelé quand la configuration change.

        Args:
            callback: Fonction(config: Dict) appelée à chaque changement
        """
        self._on_change_callback = callback

    def get_bindings(self) -> Dict[str, UIBinding]:
        """Retourne tous les bindings."""
        return self.bindings.copy()

    def unbind(self, key: str) -> bool:
        """Supprime un binding."""
        if key in self.bindings:
            del self.bindings[key]
            return True
        return False

    def clear_bindings(self) -> None:
        """Supprime tous les bindings."""
        self.bindings.clear()
