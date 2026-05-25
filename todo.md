# compilation logic []
-dans les log du debut lon doit voir lelogue qui dit le env utliser pour la compile si cest le system ou un venv precis

- quand bczsl est desactiver dnas le ark.yml , la compialtion se lance rapidmetnt pas besoin de blbabla inutlie.

# fix engines []

## pyinstaller

[INFO] Starting engine compilation...
Etape 1/3 : Verification et installation des outils requis...
Etape 2/3 : Generation de la commande de compilation...
  -> [INFO] Engine-specific mapping (pyinstaller): /home/sam/PyCompiler_ARK/engines/pyinstaller/mapping.json
  -> [INFO] Generic builder used for engine 'pyinstaller'.
  -> [INFO] Auto-detection of sensitive modules (pyinstaller) enabled.
  -> [INFO] Detection source: requirements
  -> [INFO] Detected modules: Pillow, PySide6, PyYAML, bandit, black, click, colorama, jsonschema, mypy, pip-audit, prompt_toolkit, psutil, pyfiglet, pytest, 
pytest-asyncio, pytest-cov, pytest-qt, rich, ruff, safety, shiboken6, tomli
  -> [INFO] pyinstaller options added: --hidden-import yaml --collect-all PySide6 PIL
Etape 3/3 : Execution du processus de compilation...
  Commande : /home/sam/Bureau/just_an_app/.venv/bin/python -m PyInstaller --noconfirm --onedir --distpath dist/ --name just_an_app --hidden-import yaml --collect-all 
PySide6 PIL main.py
----------------------------------------
105 INFO: PyInstaller: 6.19.0, contrib hooks: 2026.4
106 INFO: Python: 3.13.9
110 INFO: Platform: Linux-6.16.8+kali-amd64-x86_64-with-glibc2.42
110 INFO: Python environment: /home/sam/Bureau/just_an_app/.venv
ERROR: Script file 'PIL' does not exist.
Engine: pyinstaller
Lock: /home/sam/Bureau/just_an_app/.ark/lock/ARK_2026_05_25_008.lock.yml
Error: Build failed

ici le probleme vient de la construction de la cmmade via auto mapppping qui a cassé.




[INFO] Workspace: /home/sam/Bureau/just_an_app
[INFO] Loading ark.yml...
[INFO] Validating configuration...
[INFO] Generating lock payload for engine 'pyinstaller'...
[INFO] Writing lock files...
[INFO] Running BCASL pre-compile checks...
[INFO] Plugin(s) chargé(s) depuis package Cleaner
2026-05-25 09:25:32,156 - bcasl - INFO - Plugin(s) chargé(s) depuis package Cleaner
[INFO] Plugin(s) chargé(s) depuis package OutputCleaner
2026-05-25 09:25:32,158 - bcasl - INFO - Plugin(s) chargé(s) depuis package OutputCleaner
[BCASL] BCASL: 2 package(s) chargé(s) depuis Plugins/
[BCASL] ⏫ Priorité 0 pour cleaner
[BCASL] ⏫ Priorité 1 pour outputcleaner
[INFO] --- Phase: Nettoyage ---
2026-05-25 09:25:32,160 - bcasl - INFO - --- Phase: Nettoyage ---
[BCASL] Phase: Nettoyage
[BCASL] Plugin: Cleaner
[INFO] Cleaning workspace: just_an_app (/home/sam/Bureau/just_an_app)
[INFO] Cleaner completed: 0 files and 35 dirs removed
[BCASL] Plugin: Output Cleaner
[INFO] OutputCleaner: Cleaning output directory: /home/sam/Bureau/just_an_app/dist
[INFO] OutputCleaner: Successfully cleaned /home/sam/Bureau/just_an_app/dist
[INFO] Plugins: 2/2 ok, temps total 3403.7 ms
2026-05-25 09:25:37,215 - bcasl - INFO - Plugins: 2/2 ok, temps total 3403.7 ms
[BCASL] BCASL - Rapport:
[BCASL]  - cleaner: OK (3369.3 ms)
[BCASL]  - outputcleaner: OK (34.4 ms)
[BCASL] Plugins: 2/2 ok, temps total 3403.7 ms
[SUCCESS] BCASL checks passed.
[INFO] Starting engine compilation...
Etape 1/3 : Verification et installation des outils requis...
Etape 2/3 : Generation de la commande de compilation...
  -> [INFO] Engine-specific mapping (pyinstaller): /home/sam/PyCompiler_ARK/engines/pyinstaller/mapping.json
  -> [INFO] Generic builder used for engine 'pyinstaller'.
  -> [INFO] Auto-detection of sensitive modules (pyinstaller) enabled.
  -> [INFO] Detection source: requirements
  -> [INFO] Detected modules: Pillow, PySide6, PyYAML, bandit, black, click, colorama, jsonschema, mypy, pip-audit, prompt_toolkit, psutil, pyfiglet, pytest, 
pytest-asyncio, pytest-cov, pytest-qt, rich, ruff, safety, shiboken6, tomli
  -> [INFO] pyinstaller options added: --collect-all PySide6 PIL --hidden-import yaml
Etape 3/3 : Execution du processus de compilation...
  Commande : /home/sam/Bureau/just_an_app/.venv/bin/python -m PyInstaller --noconfirm --onedir --distpath dist/ --name just_an_app --collect-all PySide6 PIL 
--hidden-import yaml main.py
----------------------------------------
usage: pyinstaller [-h] [-v] [-D] [-F] [--specpath DIR] [-n NAME]
                   [--contents-directory CONTENTS_DIRECTORY]
                   [--add-data SOURCE:DEST] [--add-binary SOURCE:DEST]
                   [-p DIR] [--hidden-import MODULENAME]
                   [--collect-submodules MODULENAME]
                   [--collect-data MODULENAME] [--collect-binaries MODULENAME]
                   [--collect-all MODULENAME] [--copy-metadata PACKAGENAME]
                   [--recursive-copy-metadata PACKAGENAME]
                   [--additional-hooks-dir HOOKSPATH]
                   [--runtime-hook RUNTIME_HOOKS] [--exclude-module EXCLUDES]
                   [--splash IMAGE_FILE]
                   [-d {all,imports,bootloader,noarchive}] [--optimize LEVEL]
                   [--python-option PYTHON_OPTION] [-s] [--noupx]
                   [--upx-exclude FILE] [-c] [-w]
                   [--hide-console {minimize-late,hide-late,minimize-early,hide-early}]
                   [-i <FILE.ico or FILE.exe,ID or FILE.icns or Image or "NONE">]
                   [--disable-windowed-traceback] [--version-file FILE]
                   [--manifest <FILE or XML>] [-m <FILE or XML>] [-r RESOURCE]
                   [--uac-admin] [--uac-uiaccess] [--argv-emulation]
                   [--osx-bundle-identifier BUNDLE_IDENTIFIER]
                   [--target-architecture ARCH] [--codesign-identity IDENTITY]
                   [--osx-entitlements-file FILENAME] [--runtime-tmpdir PATH]
                   [--bootloader-ignore-signals] [--distpath DIR]
                   [--workpath WORKPATH] [-y] [--upx-dir UPX_DIR] [--clean]
                   [--log-level LEVEL]
                   scriptname [scriptname ...]
pyinstaller: error: unrecognized arguments: main.py
Engine: pyinstaller
Lock: /home/sam/Bureau/just_an_app/.ark/lock/ARK_2026_05_25_002.lock.yml
Error: Build failed
                                                           
ic le mme problmem de mapping  cassr al chaine car normalemnt au lieu de  --collect-all PySide6 PIL  ça doit etre --collect-all PySide6  --collect-all PIL 