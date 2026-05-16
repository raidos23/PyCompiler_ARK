Voici la SPEC UX BCASL — interface graphique pour la gestion du pipeline. 

--- 

SPEC UX BCASL — Interface utilisateur (Qt/PySide6) 

--- 

1. Philosophie 

L'UI BCASL est un éditeur visuel du pipeline qui respecte les contraintes du système. 

· Lecture seule : la catégorie d'un plugin ne peut pas être changée
· Ordre modifiable : à l'intérieur d'une section (même catégorie)
· Guidage : plages de priorité recommandées
· Sauvegarde : tout est écrit dans bcasl.yml 

--- 

2. Vue principale 

```
┌─────────────────────────────────────────────────────────────────────┐
│ BCASL Pipeline                                              [Save] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ▼ Validation (10-19)                                               │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │ ☑ syntax_checker               priority [12]  [↑] [↓] (drag)│  │
│   │ ☑ type_checker                 priority [15]  [↑] [↓]       │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│ ▼ Transformation (20-39)                                           │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │ ☑ minifier                     priority [25]  [↑] [↓]       │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│ ▼ Obfuscation (40-59)                                              │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │ ☐ pyobfus                      priority [45]  [↑] [↓]       │  │
│   │ ⚠️ ☑ byteshift                  priority [22]  [↑] [↓]       │  │
│   │       ↑ hors plage (40-59)                                   │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│ ▼ Preparation (60-79)                                              │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │ ☐ signer                       priority [70]  [↑] [↓]       │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                        [Cancel]  [Save to bcasl.yml]│
└─────────────────────────────────────────────────────────────────────┘
``` 

--- 

3. Composants UI 

3.1 Section (catégorie) 

Élément Rôle
▼ Validation (10-19) Titre de section (collapsible)
Plage de priorité Indique les bornes recommandées
Background Léger (gris très clair) 

3.2 Ligne plugin 

Élément Rôle
☑ Checkbox enabled
Nom plugin.name
priority [22] Label + champ de saisie (spinbox)
[↑] [↓] Boutons pour réorganiser
(drag) Poignée pour drag & drop
⚠️ Warning si priorité hors plage 

--- 

4. Interactions 

4.1 Réorganisation (même section) 

Action Résultat
Cliquer [↑] Échange avec plugin au-dessus (même section)
Cliquer [↓] Échange avec plugin en-dessous
Drag & drop Déplace dans la même section 

→ Si drop dans une autre section, opération annulée + message d'erreur. 

4.2 Modification priorité 

Action Résultat
Changer spinbox Met à jour la priorité
Si hors plage Affiche ⚠️ + tooltip explicatif
Sauvegarde Écrit la priorité (même hors plage) 

4.3 Activation/désactivation 

Action Résultat
Clic checkbox Met à jour enabled
Sauvegarde Écrit enabled: true/false 

--- 

5. Messages utilisateur 

5.1 Drag & drop interdit 

```python
show_warning(
    title="Cannot move plugin",
    text=f"'{plugin_name}' belongs to category '{category}'.\n"
         "Category is defined by the plugin vendor and cannot be changed."
)
``` 

5.2 Priorité hors plage (tooltip) 

```
⚠️ Priority 22 is outside recommended range for 'obfuscation' (40-59).
Execution order may be unexpected.
Use 'Expert mode' to disable warnings.
``` 

5.3 Priorité hors plage (warning visuel) 

· Fond de ligne : #FFF3CD (jaune pâle)
· Icône ⚠️ devant le nom
· Bordure orange sur le spinbox 

--- 

6. Mode expert 

6.1 Activation 

```yaml
# .ark/pref.json
{
  "bcasl_ux": {
    "expert_mode": true
  }
}
``` 

Ou checkbox en bas de l'UI : 

```
[✓] Expert mode (allow any priority)
``` 

6.2 Effet 

Sans expert Avec expert
Slider priorité borné (40-59) Slider libre (0-99)
Spinbox priorité borné Spinbox libre
Warning visuel présent Warning désactivé
Message bloquant sur drag & drop Toujours bloquant (catégorie) 

--- 

7. Sauvegarde 

7.1 Bouton Save to bcasl.yml 

· Sauvegarde l'état actuel dans bcasl.yml (dans le workspace)
· Format YAML exact (priorités, enabled, config) 

7.2 Format généré 

```yaml
plugins:
  - name: syntax_checker
    enabled: true
    priority: 12
    config: {} 

  - name: type_checker
    enabled: true
    priority: 15
    config: {} 

  - name: minifier
    enabled: true
    priority: 25
    config: {}
``` 

ce format doit etre ainsi obligatoire le bcasl true ou flase est gerer par le ark.yml , le bcasl.yml gere uniquement les cfg des plugins et leur ordre.

--- 

8. Raccourcis clavier 

Raccourci Action
Ctrl+S Sauvegarder
Ctrl+Z Annuler (undo local)
Ctrl+Y Rétablir (redo)
↑ ↓ Navigation entre plugins
Space Toggle enabled 

--- 

9. Contraintes techniques 

Contrainte Implémentation
Ordre interne = priority Le tri UI est basé sur priority (pas un ordre séparé)
Drag & drop interdit entre sections Vérification source_category == target_category
Sauvegarde YAML Utiliser ruamel.yaml pour préserver les commentaires ? (optionnel) 

--- 

10. Règles UX 

ID Règle
UX1 Les sections sont définies par category (lu depuis plugin).
UX2 Réorganisation possible uniquement à l'intérieur d'une section.
UX3 Drag & drop inter-sections → erreur.
UX4 Priorité hors plage → warning (sauf mode expert).
UX5 bcasl.yml est le seul fichier source de vérité. 

--- 

Fin de la SPEC UX BCASL 