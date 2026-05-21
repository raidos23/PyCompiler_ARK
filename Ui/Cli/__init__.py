"""Spec-first CLI implementation for ARK."""

from .app import build_cli, has_click
from .entrypoint import main

__all__ = ["build_cli", "has_click", "main"]
