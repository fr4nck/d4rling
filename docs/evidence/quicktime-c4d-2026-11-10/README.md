# D4rling — QuickTime C4-D : intégration CMake préparatoire (NO GO production)

**Date :** 10 novembre 2026  
**Périmètre :** préparation documentaire C4-D uniquement, sans modification des CMake de production, sans nouveau composant audio, BSD ou dyld.  
**Base technique des trois blobs CMake :** `a68172c3d960c5d66987a7dbf952b6afda8ea7e6` (parent C3 `747670a53d5a73af64470e5f60f8f3611a09a245`). **Réconciliation concurrente avant publication :** `master` a avancé au SHA `03eb62c421a88e2a5960e49f2812213e17473088` (+4 commits) ; comparaison GitHub : `AGENTS.md` et deux checkpoints documentaires modifiés/ajoutés, **aucun des trois fichiers CMake touché** et mêmes trois blobs revalidés. La nouvelle gouvernance de coordination a été relue.  
**Décision :** **GO pour une proposition CMake isolée et vérifiable ; NO GO pour code de production, build i386 intégré, activation de GetMediaSample ou annonce QuickTime fonctionnel**.

## 1. Provenance, règles, limites

- Dépôt canonique : [fr4nck/d4rling](https://github.com/fr4nck/d4rling), branche unique `master`; SHA de base vérifié via l'API GitHub avant création de cette note.
- Gouvernance consultée : `AGENTS.md` de D4rling, `PROJECT_STATE.md`, `ROADMAP.md`, `reproduction/README.md`, `reproduction/refs.lock.json`, `CREDITS.md` ; règles `AGT-001` à `AGT-014` dans le dépôt privé `fr4nck/PMSL-Arch` (consultées via la connexion privée ; contenu non reproduit). Ne pas recopier la gouvernance privée dans le dépôt public.
- C3 : [rapport et témoins archivés](../quicktime-e3-b2-c3-2026-11-09/README.md), `quicktime-c3.patch`, `macmemory-c2.patch`, `witness-c3.c`. C3 : **187/187 natifs Linux x64 + 187/187 Darwin i386 = 374** tests rapportés sur le banc historique, à ne pas confondre avec les contrôles C4-D de ce dossier.
- C4 local : [checkpoint C4 publié pendant cette préparation](../quicktime-e3-b2-c4-checkpoint-2026-11-10.md) ; résultats **rapportés**, non revérifiés ici : C4-A PASS, C4-B 114/114 hôte et 113/113 i386 + 1 SKIP, 5/5 mutants, non-régression C3 187/187 par environnement, C4-C PASS isolé avec deux dylibs ; **intégration de production NO GO**. Le candidat et les journaux C4 restent sur le 5700X inaccessible : **aucun accès, aucune reconstruction et aucune publication de ce candidat**.
- Les versions de compilation ou d'outillage du 5700X ne sont pas mesurées dans ce lot. L'environnement de tests statiques indépendant utilisé ici était Linux avec Python 3.13.5, CMake 3.31.6 et Git 2.47.3. Un test hors du poste cible ne qualifie pas l'exécution du poste cible.

## 2. Architecture CMake vérifiée à la base

| Élément lu | Mécanisme constaté | Conséquence C4-D |
| --- | --- | --- |
| `cmake/darling_parse_components.cmake` | `gui_stubs → gui + dev_gui_stubs_common`; `gui → system + dev_gui_common + iokitd` ; `cli → system → core` ; pas de composant `quicktime` explicite | Sélectionner `gui_stubs` engage des composants graphiques non nécessaires au test ciblé |
| `src/CMakeLists.txt` | Foundation est ajoutée sous `COMPONENT_cli OR COMPONENT_dev_gui_common` ; `frameworks` ensuite | `COMPONENTS=quicktime` doit inclure `cli` pour obtenir les prérequis de CoreServices sans le groupe GUI |
| `src/frameworks/CMakeLists.txt` | CoreServices ajouté sous `COMPONENT_cli OR COMPONENT_dev_gui_common`, avant QuickTime ; QuickTime ajouté dans le seul groupe `COMPONENT_gui_stubs` | Une nouvelle garde permet QuickTime seul, sans double cible et sans changer le chemin historique de `gui_stubs` |
| `src/frameworks/CoreServices/CMakeLists.txt` | `add_framework(CoreServices FAT ... DEPENDENCIES ... CarbonCore ...)` ; `reexport(CoreServices CarbonCore ${CarbonCore_BUILD})` | **Le réexport CarbonCore est déjà déclaré** ; pas de nouvelle directive de réexport à inventer dans C4-D |
| `src/frameworks/CoreServices/src/CarbonCore/CMakeLists.txt` | `MacMemory.cpp` inclus ; `add_framework(CarbonCore FAT CURRENT_VERSION VERSION A PARENT "CoreServices" ...)` | Le fournisseur visé est la sous-bibliothèque CarbonCore réelle, et non la copie de test |
| `cmake/use_ld64.cmake` | `reexport()` ajoute une dépendance à la cible et `-Wl,-reexport_library,<chemin>` | Vérifier l'effet Mach-O sur le véritable binaire et sa table d'exports/réexports |
| `cmake/darling_framework.cmake` | `DEPENDENCIES` est traduit en `target_link_libraries(<cible> PRIVATE ...)` | Ajouter `CoreServices` comme dépendance de QuickTime est la liaison minimale de premier choix |
| `src/frameworks/QuickTime/CMakeLists.txt` | `add_framework(QuickTime FAT CURRENT_VERSION ... DEPENDENCIES system)` | `system` seul n'exprime pas la dépendance de GetMediaSample à CarbonCore |
| `src/frameworks/CoreServices/include/CarbonCore/MacMemory.h` | Déclare `GetHandleSize` (deux fois, avec `Size` / `long`) et `SetHandleSize`, **pas `MemError`** | Une interface mémoire de production cohérente et un symbole `MemError` effectif restent des critères distincts du correctif CMake |
| `src/frameworks/CoreServices/src/CarbonCore/MacMemory.cpp` | Les fonctions historiques existent, mais `SetHandleSize` remplace directement le pointeur avec `realloc` ; pas de `MemError` dans cette unité | **Ne pas activer GetMediaSample C3 sur cette implémentation non sécurisée** |

Parcours visé : **QuickTime → CoreServices → CarbonCore (réexport du sous-framework)**. CoreServices gère déjà ses sous-frameworks et bibliothèques associées. La sélection ciblée évite `COMPONENTS=gui_stubs` ; elle n'évite ni les dépendances de `cli` ni les besoins réels du linker Mach-O. Les cycles `*_firstpass.dylib` sont préservés : ne pas ajouter de faux chemins, de bibliothèque hôte de substitution ou de `-undefined,suppress` dans QuickTime.

Références de méthode (documentation CMake 3.31) : [`add_subdirectory()`](https://cmake.org/cmake/help/v3.31/command/add_subdirectory.html) et [`target_link_libraries()`](https://cmake.org/cmake/help/v3.31/command/target_link_libraries.html). Le contrat décrit par CMake est confronté ici à la macro `add_framework` du fork ; **le lien final Mach-O n'a pas été observé**.

## 3. Proposition révisable — *non appliquée à la production*

Le fichier [`c4d-cmake-proposal.patch`](c4d-cmake-proposal.patch) contient **exactement trois changements de fichiers de production**, dont la base est épinglée par les empreintes Git :

1. `cmake/darling_parse_components.cmake` : composant logique `quicktime` dépendant de `cli`, et désactivation explicite de son drapeau dans la boucle d'initialisation. Chaîne : `quicktime → cli → system → core`.
2. `src/frameworks/CMakeLists.txt` : retirer QuickTime du bloc exclusivement `gui_stubs` ; l'ajouter **une seule fois** sous `if(COMPONENT_gui_stubs OR COMPONENT_quicktime)`. Pour `gui_stubs`, l'ancienne composante d'installation est maintenue ; pour `quicktime` seul, le nom de composante est `quicktime`. La compatibilité du packaging n'est pas encore qualifiée.
3. `src/frameworks/QuickTime/CMakeLists.txt` : ajouter `CoreServices` à `DEPENDENCIES` tout en conservant `system` et les autres options.

**Ce que le patch ne fait pas :** ne modifie ni `CarbonCore`, ni `CoreServices`, ni les réexports ; n'intègre pas `macmemory-c2.patch` ou `quicktime-c3.patch` ; ne rend pas `MemError` disponible ; ne prétend pas définir une ABI, un SDK ou un runtime i386 qualifié.

Empreintes de base (blobs Git, pas SHA-256) :

- `cmake/darling_parse_components.cmake` : `7605a01569f6634d0cf4c0a948c3c4acd893dde9`
- `src/frameworks/CMakeLists.txt` : `ea2f9c07e83e2520de3fbce792ef7c429d11dc5a`
- `src/frameworks/QuickTime/CMakeLists.txt` : `5c6d8ddd44341653be1e837133d5473c4d04ef6d`

Proposition : **SHA-256 `1f6caa834c45f43228602d4f76adaa177a92d6a5fa700aab4e15a3a149eed434`**. La somme correspond au fichier joint de 2 428 octets. Ne pas appliquer le patch si les blobs de base divergent.

## 4. Contrôles exécutés et limites

Tests locaux d'architecture **effectivement exécutés** dans un arbre isolé fait de copies exactes des trois blobs GitHub, sans mutation du dépôt :

| Contrôle | Résultat observé | Portée |
| --- | --- | --- |
| Comparaison `git hash-object` des 3 fichiers CMake avec la base distante | **3/3 PASS** | Identité des trois entrées testées |
| `git apply --check`, puis `git apply` en arbre temporaire ; comparaison des trois sorties au candidat | **PASS, 3/3 fichiers identiques** | Applicabilité du patch sur ces fichiers, **pas** un build |
| Invariants textuels du correctif proposé : drapeaux, garde, dépendance, cible unique | **5/5 PASS** | Contrôle statique, pas une évaluation complète de CMake |
| Mutants statiques : suppression du lien CoreServices, retrait de la garde ciblée, double cible QuickTime | **3/3 détectés** | Négatifs structuraux |
| `cmake -P` avec le parseur réel et le candidat, cas `quicktime`, `gui_stubs`, `cli`, `core`, remise à OFF, et 3 témoins négatifs (parseur initial, dépendance GUI injectée, drapeau non remis à OFF) | **8/8 PASS attendus** : 5 acceptations, 3 rejets | Exécution du **parseur des composants seulement**, ni configuration du projet complet ni build |
| Contrôles du vérificateur archivable `check_c4d.py`, exécuté sur arbre de qualification isolé | **PASS** : 3 empreintes de base, 5 invariants du graphe, application temporaire, 5 invariants candidat, 3 mutants, 8 cas CMake | L'arbre de qualification comportait des témoins textuels des autres macros ; ce résultat **ne valide pas la configuration complète de D4rling** |

**NON EXÉCUTÉ :** `cmake -S/-B` sur le dépôt complet ; Ninja ; compilation/édition de liens Mach-O i386 ; `otool`, `nm`, lecture des load commands et des réexports sur de nouvelles dylibs ; installation dans un préfixe ; tests C4-A/B/C locaux ; tests GetMediaSample contre CarbonCore réel ; tests Logic Studio 8. Aucun de ces résultats ne peut être inféré de `cmake -P`.

**FAIL non masqué :** aucun échec d'assertion dans la campagne finale bornée ; les trois rejets négatifs sont attendus. Une tentative antérieure du vérificateur sans tous les fichiers témoins a échoué par fichier absent ; l'arbre isolé a été complété et le vérificateur rejoué avec succès. Cela n'est pas une preuve d'intégration D4rling.

## 5. Reproduction et protocole pour la reprise i386

Avec un checkout **canonique**, propre et à la révision attendue ; sous **Bash Debian Linux/WSL2** ; lecture seule du dépôt, sans mise à jour ni sous-module ni installation :

```bash
cd "$(git rev-parse --show-toplevel)"
test "$(git remote get-url origin)" = "https://github.com/fr4nck/d4rling.git" || exit 1
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
python3 docs/evidence/quicktime-c4d-2026-11-10/check_c4d.py
```

Cette séquence **n'est pas une commande de démarrage sur le 5700X aujourd'hui** ; elle suppose le shell déjà situé dans le dépôt canonique. Vérifier d'abord le dépôt, la branche et l'absence de changements préexistants ; **ne pas effectuer de reset, stash, pull, checkout, installation ou nettoyage automatique**. Pour un clone où la base CMake aura évolué, le vérificateur devra refuser son hypothèse de blobs fixes.

Après récupération et vérification du C4 réel (pas de reconstitution à partir d'un résumé), protocole **à préparer, non exécuté** :

1. Prévol : ref Git à jour, `master`, fichiers modifiés protégés, sous-modules inchangés ; vérifier le statut et la provenance exacte du candidat local C4, ses empreintes, tests et références C3.
2. Dans **une copie de qualification autorisée, isolée et à base exacte**, contrôler `git apply --check` de `c4d-cmake-proposal.patch` ; ne pas l'appliquer au checkout de production. Configurer avec `-DCOMPONENTS=quicktime -DTARGET_i386=ON -DTARGET_x86_64=OFF` seulement après constat des outils et des révisions.
3. Vérifier la génération des cibles, l'absence d'activation des composants GUI, l'ordre de construction et les chemins de CoreServices/CarbonCore ; comparer avec un `COMPONENTS=gui_stubs` de qualification et les profils `cli/core`, sans redéployer les builds historiques.
4. Build Mach-O i386 **réel** des cibles QuickTime, CoreServices et CarbonCore. Inspecter les tranches, install names, références dylib, reexports, exports et imports : `GetHandleSize`, `SetHandleSize`, `MemError`. Contrôler les réexports CarbonCore effectifs, le cas `MemError` absent, les bibliothèques non résolues et les `*_firstpass` ; **un symbole absent, une mauvaise tranche ou un lien ambigu est FAIL, pas un SKIP**.
5. Dans un préfixe **neuf**, sous processus invité Mach-O i386, qualifier le contrat GetMediaSample/Memory Manager C4 : PCM synthétique, tailles exactes, conservation des Handle, realloc injecté en échec, null/invalide, overflow/bornes, erreurs, détachement QuickTime/CarbonCore, chargement sans fournisseur en témoin négatif, et non-régression C3.
6. Conserver journal de configuration et de lien, hashes des artefacts Mach-O et du préfixe, matrice tests/erreurs, témoin positif/négatif et état Git avant/après. Réconcilier les éventuelles erreurs avec le code effectif sans substituer artificiellement les dylibs.

**Ne pas lancer le build C4** avec le Memory Manager actuel : `MacMemory.h` ne déclare pas `MemError` ; `MacMemory.cpp` de production ne démontre pas les garanties C4 et ne fournit pas ce symbole dans l'unité consultée. La consolidation C4 valide et sa revue sont une condition préalable à la promotion, pas une justification de recopier C2.

## 6. Matrice GO / NO GO

| Porte | État | Motif et critère de changement |
| --- | --- | --- |
| A — Lecture du HEAD et des sources du graphe | **PASS (SRC)** | Entrées CMake réelles, SHA Git vérifiés |
| B — Proposition CMake limitée, non destructive | **PASS (DOC/STATIC)** | Patch archivé ; 3 fichiers, aucun changement de production |
| C — Parseur et témoins négatifs | **PASS (TEST statique)** | 8/8 CMake, 3/3 mutants structuraux, application isolée |
| D — Configuration complète et build CoreServices/CarbonCore/QuickTime i386 | **BLOCKED / NON EXÉCUTÉ** | Poste et candidat C4 local indisponibles, préfixe de qualification absent |
| E — Exports, réexports, erreurs mémoire et runtime i386 | **BLOCKED / NON EXÉCUTÉ** | Nécessite les dylibs réelles, la version C4 qualifiée et les négatifs |
| F — Intégration source/packaging de production | **NO GO** | Validation D et E manquante ; aucune source de production modifiée |
| G — QuickTime complet / Logic Studio 8 | **NO GO** | Aucun lancement applicatif qualifié par cette note |

## 7. Reprise exacte / coordination inter-conversations

**Dernier lot accompli :** C4-D architecture, proposition isolée, tests statiques et archivage documentaire. Checkpoint C4 concurrent intégré par référence, sans réutilisation des artefacts locaux indisponibles.  
**Fichiers publiés uniquement dans ce dossier :** `README.md`, `c4d-cmake-proposal.patch`, `check_c4d.py` ; aucune branche, sous-module, CI, outil audio ou `experiments/petite-victoire/` touché.  
**Prochain acte exact :** relire le HEAD `master` et cette note, accéder au 5700X quand disponible, vérifier le candidat C4-A/B/C **authentique**, puis exécuter la qualification de la section 5 en environnement isolé. Avant cela, la seule action utile est la revue documentaire du patch et du contrat de tests.  
**Interdits :** appliquer le patch de qualification directement sur `master` sans les portes, reconstituer C4 depuis C3, annoncer QuickTime/Logic fonctionnels, inventer un build, ouvrir BSD/dyld/audio/Cocoa, modifier Petite Victoire, contribuer au Darling officiel sans décision distincte.


## 8. Actualisation M2-R2 et arrêt des essais synthétiques (10 novembre 2026)

La section 7 décrit **l'archivage initial**, pas le dernier commit de ce dossier. Le dernier jalon publié et vérifiable est [C4-D-M2-R2](C4D-M2-R2-host-replay.md), commit [`c897c0e7`](https://github.com/fr4nck/d4rling/commit/c897c0e78276c3c5b281e7cbf8d7ea66957ebc0d) : **32/32 tests PASS, 0 SKIP** sur Linux x64, avec parseur Git épinglé et **fichiers Mach-O i386 synthétiques**. Le lot R1 précédent et ses deux SKIP historiques ne sont pas réécrits. [Test CLI reproductible](test_check_c4d_macho_cli.py) et [garde Mach-O](check_c4d_macho_i386.py) sont présents dans ce dossier.

**Décision de coordination :** sélectionner [`c4d-cmake-order-preserving.patch`](c4d-cmake-order-preserving.patch) (G2) comme **base prioritaire de qualification isolée** : il préserve l'ordre du bloc `gui_stubs` tout en préparant `COMPONENTS=quicktime` et `QuickTime → CoreServices`. L'ancien [patch C4-D initial](c4d-cmake-proposal.patch) reste archivé, **non promu et non supprimé**. G2 n'est **pas validé pour la production**.

**État des gates :** PASS uniquement sur le graphe CMake instrumenté, la liaison témoin ELF hôte et le parseur Mach-O avec fichiers synthétiques ; **NON EXÉCUTÉ** pour la compilation/lien Mach-O i386 réel, les réexports via ld64, les APIs mémoire authentiques et GetMediaSample ; **BLOCKED** tant que C4-A/B/C authentique et le poste 5700X ne sont pas accessibles ; **NO GO** pour fusionner le code C4-D dans `src/` / `cmake/` et pour déclarer QuickTime ou Logic opérationnels.

**Prochain acte exact (pas de travaux de préparation supplémentaires) :** reprendre sur un checkout et un build de référence préservés, vérifier le HEAD et les modifications locales, récupérer le candidat C4 authentique, appliquer G2 seulement à une copie autorisée, effectuer un build CarbonCore/CoreServices/QuickTime i386 cohérent, inspecter les trois dylibs avec M2, puis rejouer les vrais témoins C3/C4 positifs et négatifs. Avant ce prérequis, aucune série de nouveaux tests synthétiques n'est justifiée.
