from __future__ import annotations

import os

FORMS_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Forms"))


def ui_form_path(filename: str) -> str:
    """Return the absolute path of a Qt Designer form stored in `Ui/Forms/`."""
    return os.path.abspath(os.path.join(FORMS_DIR, filename))
