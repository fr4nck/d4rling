# D4rling — QuickTime C4-D-G2 : revue de préservation de l'ordre CMake

**Date :** 10 novembre 2026. **Statut : PASS de configuration instrumentée / NO GO production.**

## Pourquoi ce lot

Le patch C4-D publié par le lot précédent (`65796a63`) déplace `add_subdirectory(QuickTime)` de sa position d'origine, entre `QTKit` et `ScreenSaver`, à la fin du groupe `gui_stubs`. La conséquence sur les sous-projets réels n'est pas démontrée, mais le déplacement est évitable.

Le [patch G2](c4d-cmake-order-preserving.patch) **préserve le bloc `gui_stubs` et son ordre historique**, ajoute séparément `if (COMPONENT_quicktime AND NOT COMPONENT_gui_stubs)` après ce bloc, et conserve les deux autres modifications du patch C4-D initial : `quicktime → cli` dans le parseur et dépendance `CoreServices` dans QuickTime.

**Le patch G2 est une proposition documentaire indépendante.** Il n'est pas appliqué à `master`, ne remplace pas `c4d-cmake-proposal.patch` et ne modifie aucun fichier d'une autre conversation. La revue n'affirme pas que le patch initial produit une régression réelle.

## Provenance et vérifications exécutées

Les trois fichiers d'origine ont été lus sur GitHub et leurs octets reconstitués dans un arbre temporaire indépendant. `git hash-object` confirme, dans cet ordre :

- `cmake/darling_parse_components.cmake` — `7605a01569f6634d0cf4c0a948c3c4acd893dde9`
- `src/frameworks/CMakeLists.txt` — `ea2f9c07e83e2520de3fbce792ef7c429d11dc5a`
- `src/frameworks/QuickTime/CMakeLists.txt` — `5c6d8ddd44341653be1e837133d5473c4d04ef6d`

Proposition : SHA-256 **`23d944e589826b039109b3dcf371d1038eee73786c1ce38b21070a280de09eac`**, blob Git **`9f0734df65e58eb654b00ec8a7bc47e6c9e1a698`**, 2 098 octets.

Sur Linux x86_64 avec CMake 3.31.6, Git 2.47.3 et Python 3.13.5 :

| Contrôle | Résultat |
| --- | --- |
| `git apply --check` sur les trois sources épinglées | PASS |
| `git apply` sur copies temporaires | PASS |
| Configurations CMake instrumentées du vrai parseur et `src/frameworks/CMakeLists.txt` | **7/7 PASS** : `quicktime`, `gui_stubs`, `quicktime,gui_stubs`, `cli`, `core`, `stock`, `all` |
| Mutant ordre inversé `QTKit → ScreenSaver → QuickTime` | **Rejeté** |
| Mutant double déclaration QuickTime lors de `quicktime,gui_stubs` | **Rejeté** |
| Contrôle statique supplémentaire sur le patch C4-D-G2 | Applicabilité vérifiée |

La configuration instrumentée surcharge `add_subdirectory` pour tracer l'ordre, sans configurer les véritables sous-frameworks. Les tests sont **réellement exécutés** sur copies, mais ne prouvent ni la configuration complète du projet, ni son graphe de compilation, ni un lien Mach-O, ni une exécution i386. Les anciens témoins C4-D-G1 et C4-D-L1 conservent leurs propres contrats et leur patch d'origine.

## Coordination et reprise

Ce lot s'ajoute à l'historique existant ; les travaux concurrents BSD et QuickTime ont été relus via comparaison de commits. Il n'introduit aucune nouvelle branche, modification de production, installation, correctif `MacMemory.cpp` ou changement à Petite Victoire.

**Prochaine étape utile :** quand le 5700X et le candidat Memory Manager C4 authentique seront disponibles, comparer les deux propositions CMake, sélectionner la version conservatrice sous réserve de revue, et qualifier le véritable build `CarbonCore/CoreServices/QuickTime` i386 et les tests C3/C4 dans un préfixe isolé. **Production : NO GO**.
