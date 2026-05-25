# Business logic

- [] ameliorer encore plus le system de killing de process Core/process_killer.py

- [] ameliorer la detection d'internet pour plus de certitude et renforcer son utilisaion.


# refactor []
- [] dans Core le globals.py doit normaleent appartenir a la Ui/Gui/  , 
- [] Core/SyDependencyManager.py , il faut que tout le ui soit deplacer ver le dialog dedier dans Ui/Gui/Dialogs/SysDependencyUI.py . donc le Core/SyDependencyManager.py ne doit plus contenir d'appelle de Pyside6. il faut qu'il contienne puremnt de la business logic. 
- [] Core/Venv_Manager/ ne doit pls du tout contenir de la logique UI soit pyside6 du tout même pas de callback ou fallback.... tout le ui doit etre transmis vers Ui/Gui/Dialogs/VenvDialog.py .
