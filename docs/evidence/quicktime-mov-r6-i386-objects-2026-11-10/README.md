# D4rling — QT-MOV-02 / R6-CROSS-01 : vrais objets Mach-O i386, sans SDK

**10 novembre 2026 — preuve de compilation croisée uniquement.** Sources de production QuickTime R6 inchangées. La qualification porte sur les deux modules C privés `qt_mov_pcm.c` et `qt_mov_probe.c` ; elle ne porte **pas** sur la dylib QuickTime ni sur l'exécution sous Darling.

## Motivation et documentation primaire

Clang produit du code pour une cible distincte de l'hôte avec `-target`, mais les en-têtes et bibliothèques de la cible ne sont pas fournis automatiquement ; voir [Clang — Cross-compilation](https://clang.llvm.org/docs/CrossCompilation.html). Les champs de l'objet sont inspectés avec `llvm-objdump --macho --private-headers` et un parseur dédié à `MH_OBJECT` ; voir [LLVM — llvm-objdump](https://llvm.org/docs/CommandGuide/llvm-objdump.html). Le format et les symboles observés sont le résultat d'une **compilation véritable** à partir des fichiers C R6, non des octets Mach-O artificiels.

**Prérequis de qualification explicitement limité :** Clang 17 déjà installé avec cible `i386-apple-darwin9`, Python 3 et `llvm-objdump`. Sans SDK cible, une déclaration `string.h` *test-only* définit les prototypes standard de `memcmp`, `memcpy` et `memset` ; `stdint.h`, `stddef.h` et `limits.h` viennent du répertoire de ressources de Clang. La compilation en `-ffreestanding -nostdinc` ne comporte **aucune liaison**. Ce shim n'est pas intégré au dépôt de production et ne garantit pas l'ABI de libSystem.

## Entrées et commande

Sources Git originales contrôlées via `git hash-object` :

| Source | Git blob requis |
| --- | --- |
| `src/frameworks/QuickTime/src/qt_mov_pcm.c` | `cdb35c2f882caaf1954e79baf97191cdd5816eb9` |
| `src/frameworks/QuickTime/src/qt_mov_pcm.h` | `42aa7d3322a83045822567c941be31d0ba6fe952` |
| `src/frameworks/QuickTime/src/qt_mov_probe.c` | `6d1fcd89a7396a120da7b4d456bd708a9bcfdecd` |
| `src/frameworks/QuickTime/src/qt_mov_probe.h` | `d04d0a72edc554b9281ee7c1a60120c230c8940e` |

Le [lanceur reproductible](run_i386_objects.sh) s'exécute sous **Bash Linux ou WSL2** depuis n'importe quel répertoire :

```bash
bash docs/evidence/quicktime-mov-r6-i386-objects-2026-11-10/run_i386_objects.sh
```

Son chemin est résolu à partir du fichier de script ; pour un appel depuis ailleurs que le dépôt, fournir le chemin absolu du script. Le prévol vérifie `master`, l'URL du dépôt canonique, les empreintes des quatre sources et les outils ; aucun `git fetch`, clone, installation, checkout, sous-module ou volume Windows n'est touché. Les écritures sont limitées à un dossier temporaire dédié sous `TMPDIR` (défaut `/tmp`), supprimé par le script après vérification ; il n'écrit ni dans les sources ni dans l'index Git. L'absence d'un prérequis stoppe immédiatement la recette. Le [vérificateur structurel](verify_i386_macho_objects.py) est en lecture seule.

## Qualification réellement exécutée — hôte isolé Linux x86_64

Sources R6 montées dans le dossier de qualification isolé, empreintes Git **identiques** aux quatre blobs ci-dessus. Compilateur `clang version 17.0.0` ; cible `i386-apple-darwin9` ; options `-std=c11 -O1 -Wall -Wextra -Werror -fvisibility=hidden -ffreestanding -nostdinc -fno-stack-protector -c` ; aucun téléchargement.

| Porte | Résultat |
| --- | --- |
| Compilation réelle de `qt_mov_pcm.c` vers `MH_OBJECT` Mach-O i386 | **PASS**, SHA-256 `2c984380e6b34514b27eb25dc101106e7d2d597c23aacd4813e8ae6c41180b0c`, 7 048 octets |
| Compilation réelle de `qt_mov_probe.c` vers `MH_OBJECT` Mach-O i386 | **PASS**, SHA-256 `b33b08f43a4f3db037afe7e259d91199c2966fd4648e2e073321739b1ab9ad07`, 1 260 octets |
| Contrôle de `MH_MAGIC`, CPU type 7 (i386), filetype 1 (object), tables nlist, visibilité privée | **PASS** |
| `extract_pcm`, `find_pcm`, `list_tracks`, `probe` déclarés private externals | **PASS**, n_type `0x1f` |
| Références externes du PCM (parseur associé, `memcmp`, `memcpy`, `memset`) | **PASS** : jeu exact ; `probe` ne référence que `memcmp` |
| Contre-exemple ELF i386 produit à partir de la même source | **PASS** : refus du vérificateur |
| Contre-exemple Mach-O x86_64 produit à partir de la même source | **PASS** : refus du vérificateur |
| Mismatch volontaire d'empreinte de source dans la recette Bash | **PASS** : arrêt avant la compilation ; source restaurée après la contre-épreuve |
| Recette intégrale depuis un petit dépôt Git **factice et isolé** contenant les vraies sources R6 | **PASS** : terminaison `QT-MOV-R6-CROSS-I386-OBJECT-PASS` |

La dernière épreuve valide le **lanceur et les chemins relatifs**, pas le contenu d'un checkout D4rling complet. Elle utilise un dépôt Git factice uniquement local, dont `origin` contient la chaîne canonique sans établir de connexion réseau. La recette reste **NON EXÉCUTÉE sur le 10400** et sur le 5700X.

## Interprétation et point d'arrêt

**GO :** les deux modules privés peuvent produire de véritables objets Mach-O i386 ciblant Darwin sous Clang 17, avec les symboles attendus et sans erreur de compilation. C'est une preuve supplémentaire de portabilité du code C R6 par rapport aux essais natifs x64.

**NON EXÉCUTÉ / NO GO :** lien `ld64` de la dylib QuickTime, `LC_ID_DYLIB`, `LC_REEXPORT_DYLIB` CoreServices → CarbonCore, chargeur `dyld`, exécution i386, appels `GetMediaSample`, sécurité des handles C4, CoreAudio, Logic Studio 8. **Un `MH_OBJECT` n'est pas un `MH_DYLIB`** : les dépendances restent des symboles indéfinis en attente de résolution. Aucune compatibilité runtime n'est inférée.

**BLOCKED :** C4-D intégré exige toujours le candidat Memory Manager authentique du 5700X et le build i386 cohérent. La suite de ce lot n'est **pas** la multiplication de tests hôte : elle consiste à appliquer, sur un environnement i386 autorisé, les portes de liaison et de chargement déjà documentées dans [C4-D](../quicktime-c4d-2026-11-10/README.md).

**Publication :** scripts + rapport uniquement dans `docs/evidence`, sans modifier `src/`, `cmake/`, les tests PCM existants ou les autres chantiers.
