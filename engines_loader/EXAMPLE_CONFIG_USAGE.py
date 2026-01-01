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
Example: Engine Configuration Usage

Demonstrates how to use the persistent configuration system for engines.
"""

from engines_loader import CompilerEngine, get_config_manager


class ExampleEngine(CompilerEngine):
    """Example engine with persistent configuration."""

    id = "example"
    name = "Example Engine"
    version = "1.0.0"

    # Define the default configuration schema
    config_schema = {
        "enabled": True,
        "output_dir": "dist",
        "optimization_level": 2,
        "strip_binaries": False,
        "include_modules": [],
        "exclude_modules": [],
        "timeout_seconds": 300,
    }

    def __init__(self):
        super().__init__()
        # Load configuration at initialization
        self.config = self.load_config()

    def build_command(self, gui, file: str) -> list[str]:
        """Build command using saved configuration."""
        cmd = ["example-compiler"]

        # Use configuration values
        if self.config.get("optimization_level"):
            cmd.append(f"-O{self.config['optimization_level']}")

        if self.config.get("strip_binaries"):
            cmd.append("--strip")

        cmd.append(file)
        return cmd

    def on_success(self, gui, file: str) -> None:
        """Update configuration after successful build."""
        # Example: track last successful build
        self.config["last_build"] = file
        self.save_config(self.config)


# Usage examples:

def example_load_config():
    """Load engine configuration."""
    engine = ExampleEngine()
    config = engine.load_config()
    print(f"Loaded config: {config}")


def example_save_config():
    """Save engine configuration."""
    engine = ExampleEngine()
    engine.config["optimization_level"] = 3
    engine.config["strip_binaries"] = True
    success = engine.save_config(engine.config)
    print(f"Config saved: {success}")


def example_check_config():
    """Check if engine has saved configuration."""
    engine = ExampleEngine()
    has_config = engine.has_config()
    print(f"Has saved config: {has_config}")


def example_get_config_path():
    """Get the path to engine configuration file."""
    engine = ExampleEngine()
    path = engine.get_config_path()
    print(f"Config path: {path}")


def example_delete_config():
    """Delete engine configuration."""
    engine = ExampleEngine()
    success = engine.delete_config()
    print(f"Config deleted: {success}")


def example_list_all_engines():
    """List all engines with saved configurations."""
    manager = get_config_manager()
    engines = manager.list_engines()
    print(f"Engines with config: {engines}")


def example_custom_config_dir():
    """Use custom configuration directory."""
    manager = get_config_manager(config_dir="/custom/path/.pycompiler")
    config = manager.load("example", {"key": "default_value"})
    print(f"Config from custom dir: {config}")


if __name__ == "__main__":
    print("Engine Configuration Examples")
    print("=" * 50)

    print("\n1. Load configuration:")
    example_load_config()

    print("\n2. Save configuration:")
    example_save_config()

    print("\n3. Check if configuration exists:")
    example_check_config()

    print("\n4. Get configuration path:")
    example_get_config_path()

    print("\n5. List all engines with configurations:")
    example_list_all_engines()
