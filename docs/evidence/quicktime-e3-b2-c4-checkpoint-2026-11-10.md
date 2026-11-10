# D4rling — QuickTime E3-B2 C4 : checkpoint partagé

**Date :** 10 novembre 2026  
**Statut :** résultats C4 **rapportés depuis le 5700X**, **non rejoués** par la conversation qui publie cette note ; intégration de production **NO GO**.

## Références et provenance

- Dépôt : `fr4nck/d4rling`, branche `master`.
- C3 archivé au commit `747670a53d5a73af64470e5f60f8f3611a09a245`, sous `docs/evidence/quicktime-e3-b2-c3-2026-11-09/`.
- Campagne C4 rapportée par l'opérateur : checkout local propre à `747670a5`, répertoire de validation `validation/qt-next/e3/b2/mm-c4/`, rapport local `RESULTAT-C4.md`.
- Les sources, scripts et journaux de C4 sont **uniquement locaux**. Leur contenu intégral, leurs octets, leurs empreintes et les résultats expérimentaux ne sont **pas vérifiables depuis ce dépôt GitHub**. Ne pas reconstruire approximativement le patch C4 à partir de ce résumé.

## Compte rendu C4 transmis (non certifié indépendamment)

| Lot | Résultat rapporté | Limite |
| --- | --- | --- |
| C4-A : six fonctions du Memory Manager | PASS, candidat isolé | Non appliqué à `master` |
| C4-B : témoin natif Linux x64 instrumenté | 114/114 deux fois, code 0 | Contrôles ASan/UBSan/LSan rapportés |
| C4-B : témoin Mach-O Darwin i386 | 113/113 + 1 SKIP, code 0 | La limite d'allocation massive n'a pas été testée |
| C4-B : régression C3 natif | 187/187 | Memory Manager C4 candidat |
| C4-B : régression C3 i386 | 187/187 | Memory Manager C4 candidat |
| C4-B : mutants négatifs | 5/5 détectés | Échecs intentionnels |
| C4-C : deux dylibs i386 distinctes | 187/187, code 0 | Test isolé, **pas un véritable CarbonCore CMake** |

Le rapport mentionne également quatre essais non retenus ou corrigés : `r1` (compilation), `r2` (oracle de `MemError`), `r3` (allocation massive i386), `integ-r1` (install name incohérent). Les preuves et corrections correspondantes restent dans les journaux locaux.

**Réserves C4 :** déplacement de bloc non provoqué en i386 ; débordement de `HandAndHand` non testé ; pas de build des vrais frameworks ; pas de validation audio, QuickTime complet ou Logic Studio 8. La mort du processus après `malloc(0x7fffffff)` ne permet pas d'attribuer la cause au seul allocateur Darwin : conserver le SKIP et ne pas relancer l'allocation dangereuse.

## Prochain lot C4-D — intégration CMake

Points établis par lecture des sources GitHub :
1. `src/frameworks/QuickTime/CMakeLists.txt` déclare `system` comme seule dépendance.
2. QuickTime C3 archivé requiert `GetHandleSize`, `SetHandleSize` et `MemError`.
3. `src/frameworks/CoreServices/CMakeLists.txt` réexporte `CarbonCore` ; `src/frameworks/ApplicationServices/CMakeLists.txt` dépend déjà de `CoreServices`.
4. `src/frameworks/CMakeLists.txt` sélectionne `CoreServices` par `cli` ou `dev_gui_common`, QuickTime par `gui_stubs`. `gui_stubs` entraîne `gui` dans `cmake/darling_parse_components.cmake`.
5. Le `MacMemory.cpp` publié ne contient pas le candidat C4 et n'exporte pas `MemError`. **Un simple ajout CMake de `CoreServices` ne suffit pas à rendre C3 opérationnel en production.**

**Depuis ChatGPT classique et GitHub, sans 5700X :** préparer une revue de la liaison, un candidat CMake minimal isolé et la procédure de qualification ; ne pas intégrer de production non testée.

**À reprendre sur le 5700X :** relire le patch C4 local réel, construire les vrais frameworks avec lui, valider les exports et install names i386, les dépendances et le chargement, puis rejouer C3 contre ces frameworks. C4-D restera **NO GO production** jusqu'à ces preuves.

## Coordination entre conversations

Avant **chaque** lot et publication : consulter le HEAD courant de `master`, examiner les derniers commits et leurs diffs, comparer les fichiers du lot et respecter `AGENTS.md` (« Coordination inter-conversations »). Après chaque évolution achevée et vérifiée, publier un commit atomique ; les résultats seulement rapportés doivent rester des checkpoints documentaires, sans masquer leur provenance. Ne pas écraser les modifications concurrentes ni modifier Petite Victoire.
