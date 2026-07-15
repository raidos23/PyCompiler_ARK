import asyncio
from ...i18n import available_languages, get_translations, i18n_synchro, translate
from ... import output


def show_language_dialog(self):
    from PySide6.QtWidgets import QInputDialog

    langs = asyncio.run(available_languages())
    # Build options list with 'System' at top
    options = ["System"] + [str(x.get("name", x.get("code", ""))) for x in langs]
    # Determine current index
    current_pref = getattr(self, "language", "System")
    if current_pref == "System":
        start_index = 0
    else:
        codes = [str(x.get("code", "")) for x in langs]
        start_index = 1 + codes.index(current_pref) if current_pref in codes else 0
    title = translate(self.id, "choose_language_title", getattr(self, "windowTitle", lambda: "")())
    label = translate(
        self.id,
        "choose_language_label",
        getattr(getattr(self, "select_lang", None), "text", lambda: "")(),
    )
    choice, ok = QInputDialog.getItem(self, title, label, options, start_index, False)
    if ok and choice:
        lang_pref = (
            "System"
            if choice == "System"
            else next(
                (
                    str(x.get("code", "en"))
                    for x in langs
                    if str(x.get("name", "")) == choice
                ),
                "en",
            )
        )
        tr = asyncio.run(get_translations(lang_pref))
        i18n_synchro(self, lang_pref, tr)
    else:
        output.info(("Sélection de la langue annulée.", "Language selection cancelled."), gui=self)
