# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""Services — logique métier extraite des fichiers mixtes. Aucune dépendance Qt."""

from .ConfigEditorService import (
    read_text,
    write_text,
    safe_parse_yaml,
    safe_parse_json,
    render_unified_diff,
    render_colored_diff,
    validate_payload,
    format_text,
    make_default_content,
)

__all__ = [
    "read_text",
    "write_text",
    "safe_parse_yaml",
    "safe_parse_json",
    "render_unified_diff",
    "render_colored_diff",
    "validate_payload",
    "format_text",
    "make_default_content",
]
