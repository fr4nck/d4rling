# D4rling — QuickTime C4-D-R1 : réexport CoreServices → CarbonCore

**Date :** 10 novembre 2026  
**Statut :** **PASS CMake instrumenté / NO GO production**  
**Révision de départ :** `afed46219191cb0d93cdb2e09f92e0413c14cfeb` (correctif G2 de préservation d'ordre). Avant publication, `master` a avancé au SHA `bb6ebd2e28fdbaf260e4d81c65110dabfe74466b` (+4 commits SoundHack/BSD) ; les sources CMake et le périmètre QuickTime C4-D visés n'ont pas changé.

## But et nouveauté

Les lots C4-D-G1/G2 ont testé la sélection des composants, et C4-D-L1 la dépendance CMake de QuickTime vers CoreServices sur un projet ELF hôte synthétique. **R1 exerce le maillon suivant, CoreServices → CarbonCore**, avec les *vrais* `CMakeLists.txt` de CoreServices et CarbonCore et le corps authentique de `reexport()` extrait de `cmake/use_ld64.cmake`.

Le programme [`check_c4d_reexport.py`](check_c4d_reexport.py) est versionné sous `docs/evidence/` ; **aucun fichier de production n'a été modifié**.

## Provenance épinglée

| Fichier public relu sur GitHub | Blob Git attendu |
| --- | --- |
| `src/frameworks/CoreServices/CMakeLists.txt` | `3fac3be55879c09a21827c8335073ab36b4fd9b9` |
| `src/frameworks/CoreServices/src/CarbonCore/CMakeLists.txt` | `85f36aa6d5a4e976688dc4cafa70e42c34af02ff` |
| `src/frameworks/QuickTime/CMakeLists.txt` | `5c6d8ddd44341653be1e837133d5473c4d04ef6d` |
| `cmake/use_ld64.cmake` (pour la reprise normale) | `374f4352864aaef6157ca63cd0fac3cb9e653ab2` |

Script R1 : blob Git **`2d79fcb93ec09d3cb71dd041721a1dbd8af12213`**, SHA-256 **`d0a9058ff28c4560b9673c966746eb983e1bdac3340035a7666eae91c780008e`**.

Le script vérifie les blobs des trois CMake avant chaque essai. En usage normal, il vérifie aussi le blob du fichier `use_ld64.cmake`, en extrait le vrai corps de `reexport()` et refuse tout écart. Le test exécuté ici utilisait `--fragment-fixture` : le miroir de qualification ne contenait que les **quatre lignes authentiques** de la fonction `reexport()`, et non les autres lignes de `use_ld64.cmake`. Cette distinction est intentionnelle et le mode normal n'a pas été exécuté sur un checkout complet.

## Ce qui a réellement été exécuté

Environnement : Linux x86_64 isolé, Python 3.13.5, CMake 3.31.6, Git 2.47.3, sans 5700X, réseau direct, sous-module, SDK, préfixe, installation ou lancement de Darling.

- **Vrai CMake évalué :** `src/frameworks/CoreServices/CMakeLists.txt`, `src/frameworks/CoreServices/src/CarbonCore/CMakeLists.txt` et `src/frameworks/QuickTime/CMakeLists.txt` épinglés. Un unique ajout temporaire `CoreServices` dans `QuickTime DEPENDENCIES` représente la dépendance du candidat G2, **sans prétendre appliquer le patch G2 entier**.
- **Vraie fonction évaluée :** `reexport()` de `use_ld64.cmake` (extrait exact).
- **Doublures de banc clairement limitées :** `add_framework()`, génération SDK et autres sous-frameworks non CarbonCore ; leurs cibles sont des `add_custom_target()`. Les vraies sources C/C++ ne sont pas compilées.
- **Oracles CMake :** dépendance ordonnée CarbonCore, présence unique du chemin `-Wl,-reexport_library,<build>/src/frameworks/CoreServices/src/CarbonCore/CarbonCore`, onze flags de réexport des sous-frameworks déclarés, CarbonCore lié par CoreServices, `QuickTime → CoreServices;system`, parent de CarbonCore, inclusion effective du nom `MacMemory.cpp` dans sa liste de sources.

**Commande réellement exécutée sur le miroir isolé :**

```bash
python3 docs/evidence/quicktime-c4d-2026-11-10/check_c4d_reexport.py --fragment-fixture
```

| Contrôle | Résultat |
| --- | --- |
| Configuration CMake positive du réexport et du graphe | **1/1 PASS** |
| Absence de `reexport(CarbonCore)` | Détectée |
| Mauvais chemin de réexport | Détecté |
| Remplacement du drapeau de réexport | Détecté |
| Suppression de l'ordre de construction via `add_dependencies` | Détectée |
| Dépendance CoreServices omise de QuickTime | Détectée |
| CarbonCore absent de la liste des dépendances de CoreServices | Détecté |
| Parent du sous-framework incorrect | Détecté |
| Source `MacMemory.cpp` absente de CarbonCore | Détectée |

**Bilan : 1 positif PASS ; 8/8 mutations rejetées comme attendu.** Aucun test hôte ne transforme un simple flag de liaison en preuve de réexport Mach-O. Deux erreurs du script de qualification ont été détectées avant la campagne réussie (concaténation Python et création du dossier temporaire `cmake/`), puis corrigées ; la version publiée est celle effectivement exécutée avec code retour 0.

## Reproduction

Sur un checkout à jour contenant les quatre blobs d'origine et les documents R1 :

```bash
python3 docs/evidence/quicktime-c4d-2026-11-10/check_c4d_reexport.py
```

Le script s'arrête si un fichier attendu a changé. Toutes les écritures de test sont limitées à un répertoire temporaire, sans toucher au checkout. Il n'installe aucun paquet.

Le contrat utilisé suit [`add_dependencies()` de CMake 3.31](https://cmake.org/cmake/help/v3.31/command/add_dependencies.html) et [`set_property()` de CMake 3.31](https://cmake.org/cmake/help/v3.31/command/set_property.html) ; le test vérifie la propriété `MANUALLY_ADDED_DEPENDENCIES` et le texte `LINK_FLAGS`, sans prouver l'édition de liens réelle.

## Limites et décision

- **PASS (TEST hôte, CMake instrumenté)** : déclaration et construction de la dépendance/réexport CoreServices → CarbonCore, avec entrée QuickTime C4-D.
- **NON EXÉCUTÉ** : configuration totale de D4rling, vraie macro `add_framework()` dans ce banc R1 (traitée séparément par L1), génération SDK, compilateur C/C++ Darling, ld64, artefact Mach-O i386 et lancement invité.
- **BLOCKED** : incorporation du véritable Memory Manager C4 local, vérification des exports `GetHandleSize`, `SetHandleSize`, `MemError`, test `GetMediaSample` contre les frameworks réels.
- **NO GO production** : aucun CMake ou fichier source de production appliqué.

**Prochain acte exact :** réconcilier les checkpoints C4-D-G2, L1 et R1 ; à la disponibilité du 5700X et de son candidat C4 authentique, qualifier un vrai build i386 CoreServices/CarbonCore/QuickTime et ses imports/réexports par outils Mach-O, avec témoins positifs et négatifs. Ne pas relancer C3/C4 local par supposition ou introduire un stub pour franchir artificiellement cette porte.
