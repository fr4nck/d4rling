# LOGIC-L1 — reproduire les observations, sans lancer Logic

Shell : **Bash sous Debian WSL2**, 5700X. Nécessite le stage privé du lot et le jeu d'audit Logic du 4 novembre déjà autorisé, avec ses copies légitimes. Il n'y a aucune extraction, installation, modification de binaire Apple ni exécution de Logic ou de framework Apple original.

Depuis le worktree privé contenant ce dossier, bloc complet :

```bash
set -Eeuo pipefail
stage="$HOME/d4wrling-work/validation/security-s4-logic-l1-20261114"
test -d "$stage/src/.git" || test -f "$stage/src/.git"
cd -- "$stage/src"
audit="$(python3 - "$stage" <<'PY'
import json, sys
from pathlib import Path
stage = Path(sys.argv[1])
paths = json.loads((stage / 'private/logic-input-sha256.json').read_text())
first = Path(next(iter(paths)))
for parent in first.parents:
    if (parent / 'binary-analysis.json').is_file():
        print(parent)
        break
else:
    raise SystemExit('BLOCKED: existing private audit not found')
PY
)"
test -f "$stage/l1-frozen-inputs.json"
test -f "$audit/binary-analysis.json"
python3 tests/regressions/logic-l1-loading/analyze-current.py --stage "$stage" --audit "$audit"
python3 tests/regressions/logic-l1-loading/reproduce.py --stage "$stage" --rebuild --run
```

Le chemin d'audit est résolu depuis le manifeste privé du stage ; aucun chemin personnel n'est inscrit dans cette recette. Le lecteur et les 73 fichiers sont contrôlés par SHA ; aucune récupération ni recherche de logiciel ne se produit. Si le stage ou le jeu privé est absent, la recette est BLOCKED et n'invente pas de substitut.

Le rejeu reconstruit quatre exécutables à partir des trois sources originales (FreeType en deux architectures), uniquement dans un nouveau sous-répertoire du stage. Il conserve les anciennes sorties, sélectionne ces nouveaux binaires dans une copie locale du runner délégué et vérifie les cinq observations :

- Carbon absent du préfixe S4 : RC 20 ;
- fermeture Carbon préparée : RC 134, FreeType ELF32 non résolu ;
- wrapper FreeType i386 : RC 134, même erreur ;
- wrapper FreeType x86_64 : RC 0 ;
- lookup des noms importés sur huit fournisseurs S4 : 689 examinés, 9 absents, RC 0 d'inventaire terminé.

**Les erreurs attendues restent des échecs du banc actuel**, pas des PASS applicatifs. Si FreeType ELF32 ou un autre défaut a été corrigé depuis, le résultat attendu doit être requalifié ; ne jamais forcer artificiellement son retour. Le script n'invoque pas de logique de démarrage Apple et ne prouve aucune négociation TLS, interface Cocoa, audio ou MIDI.

Les commandes et journaux exacts restent privés ; les nouvelles sorties reçoivent leur propre empreinte. Les préfixes sont neufs, privés et bornés par timeout ; aucune source de framework partagée n'est modifiée. `logic-system-imports.h` est généré en privé à partir de l'inventaire et n'est pas redistribué.

[Rapport et matrice](../../../docs/audits/logic-studio-8/2026-11-14-logic-l1.md).
