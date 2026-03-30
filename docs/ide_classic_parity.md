# IDE-Like vs Classic GUI Parity

This matrix tracks the functional parity between the classic GUI and the IDE-like GUI.
It focuses on shared user-facing behaviors and the remaining IDE-specific deltas.

| Capability | Classic GUI | IDE-like GUI | Status | Notes |
|---|---|---|---|---|
| Shared core signal wiring | Yes | Yes | Done | IDE-like now reuses `UiConnection._connect_signals()`. |
| Workspace / venv / files actions | Yes | Yes | Done | Routed through the same shared handlers. |
| Compilation / cancel actions | Yes | Yes | Done | Uses the common signal connector. |
| Dependencies analysis action | Yes | Yes | Done | Shared button plus IDE activity button. |
| App icon button wiring | Yes | No | Intentional | No dedicated icon button in `ui_ide_design2.ui`. |
| Nuitka icon button wiring | Yes | No | Intentional | No dedicated Nuitka icon button in `ui_ide_design2.ui`. |
| Entrypoint selector | Yes | Yes | Done | `setup_entrypoint_selector()` is called during IDE init. |
| Theme and language dialogs | Yes | Yes | Done | IDE keeps dedicated affordances on top of shared wiring. |
| More-actions (`...`) menu | No | Yes | Done | IDE-only affordance, now translated and refreshed with language changes. |
| IDE-specific tooltip parity | N/A | Yes | Done | `activity_btn_deps` and `toolButton_more` tooltips are refreshed. |
| Status line | No | Yes | Intentional | IDE-specific enhancement, not a parity gap. |

## Notes

- The goal is behavioral parity, not a pixel-identical UI.
- IDE-only affordances remain acceptable as long as the classic feature set stays available.
- Future parity work should prefer shared wiring/helpers over duplicating signal logic in each UI variant.
