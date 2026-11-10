# D4rling — QuickTime C4-D-G1 : vérification du graphe CMake

**Date :** 10 novembre 2026  
**Base distante contrôlée avant le lot :** `master` = `65796a630aefc882a262c9227115aa0ad4ceb61a`.  
**Portée :** banc de qualification indépendant ; aucune source de production ni patch C4-D modifiés.

## Acquisition / reproductibilité

Trois CMake récupérés depuis GitHub connecté, puis recopiés dans un espace de qualification Linux isolé. Les empreintes Git des entrées ont été contrôlées avec `git hash-object` :

- `cmake/darling_parse_components.cmake` : `7605a01569f6634d0cf4c0a948c3c4acd893dde9`
- `src/frameworks/CMakeLists.txt` : `ea2f9c07e83e2520de3fbce792ef7c429d11dc5a`
- `src/frameworks/QuickTime/CMakeLists.txt` : `5c6d8ddd44341653be1e837133d5473c4d04ef6d`

Patch C4-D préexistant : SHA-256 `1f6caa834c45f43228602d4f76adaa177a92d6a5fa700aab4e15a3a149eed434` ; blob Git `534567a22515fd738ed7057a0e6b0fbcfb45fd12`. `git apply --check` et `git apply` : **PASS** sur ces copies seulement.

**Environnement exécutant :** Linux x86_64, Python 3.13.5, CMake 3.31.6, Git 2.47.3. Aucun réseau direct disponible dans le conteneur de test : les contenus ont été lus via GitHub connecté et la concordance des blobs a été contrôlée. Pas de clone, sous-module, package, SDK, préfixe ou machine 5700X utilisés.

## Banc C4-D-G1

Source : [`check_c4d_graph.py`](check_c4d_graph.py), SHA-256 `f77f81002173439140884203f4e593322b0953f86b3e292904840d625ae70fcb`.

Le banc utilise `cmake -S … -B …` avec `project(... LANGUAGES NONE)`, le **vrai parseur** et les deux **CMake de framework réellement lus** (après patch). Les autres répertoires sont remplacés dans chaque copie temporaire par des cibles de trace ; `add_framework`, `generate_sdk_framework` et `remove_sdk_framework` sont des fonctions instrumentées, **pas les macros de liaison/build de Darling**.

Exécution reproduite :
```bash
python3 docs/evidence/quicktime-c4d-2026-11-10/check_c4d_graph.py
```

**Tests positifs : 8/8 PASS** : `quicktime`, entrée avec espaces/majuscules, `quicktime,cli`, `gui_stubs`, `quicktime,gui_stubs`, `cli`, `core`, `stock`. Critères vérifiés par traces : cible QuickTime unique ou absente selon profil ; CoreServices présent et configuré avant QuickTime quand applicable ; sélection graphique attendue ; nom de composante d'installation ; dépendances `CoreServices;system`.

**Mutants négatifs : 7/7 détectés** : parseur prépatch, lien CoreServices absent, garde QuickTime absente, dépendance GUI imposée, déclaration QuickTime dupliquée, composante d'installation incorrecte et suppression du chemin historique `gui_stubs`. Les rejets sont attendus.

**Incident de banc non masqué :** le premier passage a échoué sur le cas `core` parce que le banc exigeait une trace non vide. Or ce profil ne crée aucun sous-framework dans ce graphe et l'absence de fichier de trace est correcte. L'oracle a été ajusté pour accepter un ensemble vide, puis **les 8 positifs et 7 négatifs ont été relancés avec succès**. Aucun fichier de production modifié.

## Statut et arrêt

| Critère | Décision |
| --- | --- |
| Exactitude des entrées et patch | **PASS** |
| Application du patch isolé | **PASS** |
| Configuration CMake instrumentée des sélecteurs | **PASS : 8/8** |
| Contrôles négatifs | **PASS : 7/7 détectés** |
| Configuration CMake du projet complet | **NON EXÉCUTÉ** |
| Liens et réexports Mach-O i386 | **BLOCKED** |
| Intégration des sources C4 locales réelles | **BLOCKED** |
| Production QuickTime / Logic Studio 8 | **NO GO** |

**Prochain acte exact :** lors de l'accès au 5700X et au candidat C4 **authentique**, contrôler l'environnement canonique et les empreintes, qualifier une vraie configuration CMake i386, construire CoreServices/CarbonCore/QuickTime, examiner install names/imports/réexports, exécuter les témoins positifs et négatifs avec des dylibs de production cohérentes. Aucun résultat CMake simulé ne remplace cette qualification.

**Coordination :** ajout documentaire et banc dans `docs/evidence/quicktime-c4d-2026-11-10/`, pas de modification du correctif `c4d-cmake-proposal.patch`, pas d'autre branche ni de changement de Petite Victoire, BSD, dyld ou audio. La tête distante doit être relue avant commit.
