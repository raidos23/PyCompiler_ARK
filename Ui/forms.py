from __future__ import annotations

from pathlib import Path

FORMS_DIR = Path(__file__).resolve().parent / "Forms"


def ui_form_path(filename: str) -> str:
    """Return the absolute path of a Qt Designer form stored in `Ui/Forms/`."""
    return str((FORMS_DIR / filename).resolve())
