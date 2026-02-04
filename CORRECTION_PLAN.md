# Plan de Correction - RuntimeError QListWidget

## Problème Identifié
L'erreur `RuntimeError: Internal C++ object (PySide6.QtWidgets.QListWidget) already deleted.` se produit car:
- L'attribut `plugins_list` existe toujours dans l'objet Python
- Mais l'objet C++ sous-jacent a été détruit
- `hasattr()` retourne `True` car l'attribut existe, même si l'objet interne est invalide

## Solution
Créer une méthode utilitaire robuste pour vérifier la validité des widgets Qt avant utilisation.

## Fichiers à Modifier
1. `/home/sam/PyCompiler_ARK/OnlyMod/BcaslOnlyMod/gui.py`

## Modifications Détaillées

### 1. Ajouter une méthode utilitaire `_is_valid()` après `_center_window()`

```python
def _is_valid(self, widget) -> bool:
    """Vérifie si un widget Qt est toujours valide.
    
    Contrairement à hasattr(), cette méthode vérifie si l'objet C++
    sous-jacent n'a pas été détruit.
    
    Args:
        widget: Le widget Qt à vérifier
        
    Returns:
        True si le widget est valide, False sinon
    """
    if widget is None:
        return False
    try:
        # Vérification par la présence de l'objet Qt
        # isValid() n'existe pas pour QListWidget, on utilise une vérification indirecte
        # La tentative d'accès au widget lui-même détecte si l'objet C++ est détruit
        widget.objectName()
        return True
    except RuntimeError:
        return False
```

### 2. Modifier `_discover_plugins()` pour utiliser la nouvelle méthode

Lignes ~640-645: Remplacer la vérification actuelle par une vérification robuste.

### 3. Modifier `_on_global_toggle()` pour vérifier la validité

Lignes ~716-730: Ajouter des vérifications avant d'accéder à `plugins_list`.

### 4. Modifier `_move_plugin_up()` et `_move_plugin_down()`

Ajouter des vérifications au début de ces méthodes.

### 5. Modifier `_get_plugin_order()` et `_get_enabled_plugins()`

Ajouter des vérifications de validité.

### 6. Modifier `_run_plugins()`

Ajouter des vérifications avant de désactiver le widget.

### 7. Modifier `_on_execution_finished()` et `_on_execution_error()`

Ajouter des vérifications avant d'activer/désactiver le widget.

## Critères de Succès
- L'application se lance sans erreur
- La liste des plugins s'affiche correctement
- Les interactions avec la liste (déplacer, activer/désactiver) fonctionnent sans erreur

