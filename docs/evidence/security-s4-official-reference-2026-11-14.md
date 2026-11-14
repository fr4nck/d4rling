# S4 — Security officiel, référence et chargement (14 novembre 2026)

**TEST / PASS S4**, limité au changement de référence et au chargement : le gitlink passe de `a536cfff5b857b214d939415cf6040e347fcf785` à la fusion officielle `84c0a3e1d25caa4cd370e850813aa527c31a2d12`. Le chargement Foundation → CFNetwork → Security et du CarbonCore complet réussit en i386 **sans `-dead_strip_dylibs`**. Aucun code de framework n'est modifié par S4.

## Références et différence réelle

Base du worktree privé : D4rling `0374b5537d6e88dde07e206f4e92a67d511d350c`. Les nouveaux travaux BSD/XNU et QuickTime sont préservés. Avant intégration, avance normale vers `700d4dd0e7e94f1ae89efec661257aafd9b337e3`, après lecture des nouveaux commits B11E. Aucun test ni correctif de son chantier, y compris le défaut TLV i386 de libdyld, n’est repris par S4. Security #16 est [fusionnée en amont](https://github.com/darlinghq/darling-security/pull/16), et Darling la référence depuis [`ca69bf50469abaf0d8746d1a6063bd137b919f7e`](https://github.com/darlinghq/darling/commit/ca69bf50469abaf0d8746d1a6063bd137b919f7e).

Ce n'est **pas** un changement de SHA à contenu identique :

| Référence | Arbre Git |
| --- | --- |
| Candidat D4rling `a536cfff…` | `da4a69973ca410b49b375f529ee635922ef408f3` |
| Fusion officielle `84c0a3e1…` | `6ceb9dc6d80bf9e2f5a277dc6d3478d4670258c1` |

Le candidat est un ancêtre de la fusion. Les sept commits supplémentaires correspondent aux fusions #14, #15 et #16 et à leurs changements. Le diff net contient **5 fichiers, 573 ajouts et 6 retraits** :

- `OSX/CMakeLists.txt` : neuf fichiers d'entrée du préprocesseur deviennent prérequis des exports ; `LINK_DEPENDS` force la reliaison des quatre cibles Security concernées.
- `OSX/libsecurity_keychain/lib/StorageManager.cpp` et `.h` : initialisation du trousseau utilisateur à la première utilisation, avec ses gardes et un nouveau membre de classe.
- `tests/exp-depends.sh` et `tests/login-keychain-first-use.c` : tests amont associés.

Le correctif `-upward_library` de #16 est présent dans les deux branches d'architecture et reste inchangé : `$<TARGET_FILE_DIR:Foundation>/./$<TARGET_FILE_NAME:Foundation>`. [Historique exact](security-s4-official-reference-2026-11-14/security-history.json).

## Construction adaptée, exécutée

Le nouveau membre de `StorageManager` interdit de réutiliser aveuglément l'ancienne archive. Les dépendances de compilation Ninja ont identifié **44 consommateurs** du header. Les **44 objets FAT ont été recompilés**, chacun contenant i386 et x86_64 ; l'archive complète a été reconstruite en remplaçant tous ces consommateurs. [Résultats et empreintes](security-s4-official-reference-2026-11-14/compile-results.json).

Les deux listes d'exports ont été régénérées depuis la source officielle et restent identiques en contenu. Les firstpass i386/x86_64, le helper circulaire final et les deux Security finaux ont été réellement liés, signés ad hoc et assemblés. Aucun firstpass n'est renommé en fournisseur final. Le nom Security.framework/Versions/A/Security et la dépendance montante vers Foundation sont conservés.

Construction **incrémentale**, Clang 19.1.7, banc 5700X / Debian WSL2 : les objets et outils inchangés proviennent du build qualifié `4be2603c62a6b0ec0148e60c7dff2e4f8b61c931`. Les 30 objets CarbonCore exacts de #2089 (`b52a309cfb2f4b020aa8e356df107ad92d6a76f3`) sont réutilisés. S4 ne prétend ni à une reconstruction complète du master courant, ni à une nouvelle qualification BSD/XNU. Les autres sous-modules du worktree ne sont pas récupérés implicitement ; les sources et dépendances réutilisées restent celles du banc épinglé. Le clone Security officiel est propre, son SHA est récupéré depuis l'URL amont, sans sous-module Security imbriqué à résoudre.

Security universel SHA-256 : `f2b2e87cbe7cca03e49e20184e6a54779a4b482aebf4b450a05d5d0821f3433b`. Dans le témoin HomeResFile, dyld charge sa tranche i386 UUID `24ec595216393f4797ed79438fb55277`, distincte du candidat précédent ; l'empreinte de l'image chargée égale celle du fichier construit. Les [UUID et SHA des images effectivement chargées](security-s4-official-reference-2026-11-14/loaded-images.json) et [résultats structurés](security-s4-official-reference-2026-11-14/results.json) fixent les entrées réelles.

## Résultats

| Contrôle réellement exécuté | Verdict borné |
| --- | --- |
| 44 recompilations FAT, archive, exports, firstpass/helper/final, signature/lipo | **PASS** |
| Exports publics avant/après | **PASS**, ensembles identiques : 4080 i386, 4148 x86_64 |
| Régression de commande longue #16, options générées depuis le CMake officiel | **PASS 4 cas** : deux erreurs originales reproduites, deux liaisons corrigées |
| Test amont des prérequis d'exports | **PASS**, neuf entrées ; contre-épreuve avant #14 : **FAIL attendu, RC 6** |
| Quatre arêtes `LINK_DEPENDS` firstpass/final, i386/x86_64 | **PASS**, absentes dans la contre-épreuve ancienne |
| Foundation → CFNetwork → Security → CarbonCore complet | **PASS**, sans suppression des dépendances |
| HomeResFile normal / bypass | **88/88 PASS + 88/88 PASS** |
| 28 imports Security de CFNetwork et contexte SSL, deux architectures | **PASS de présence et du scénario borné** |
| Négociation SSL sur transport fermé | **PASS du chemin d'échec**, `-9806`, aucune session connectée |
| Carbon Events i386 | **PASS**, `D4RLING-CARBON-EVENT-I386-OK` |
| Sans Security / sans helper final, nouvelles vues privées | **FAIL reproduits attendus**, RC 2, image manquante nommée par dyld |
| Test amont login-keychain-first-use | Compilation et liaison **PASS** ; exécution **BLOCKED** : il exige un utilisateur non root, le banc qualifié fournit UID/EUID Darwin 0 |
| TLS complet, certificats, confiance, trousseau | **NON QUALIFIÉS** |

Les résultats anciens sont conservés dans [la preuve précédente](security-i386-loading-2026-11-14.md) ; ils ne remplacent pas les essais ci-dessus. Le test de trousseau n'a pas été lancé prématurément : le code officiel exclut explicitement root de l'initialisation. Aucune garde n'a été contournée. Une première commande de liaison de ce témoin omettait CoreFoundation ; l'ajout de sa dépendance déclarée a permis la liaison, sans modification de source.

## Reproduction et protections

[Recette Bash complète et vérificateur](../../tests/regressions/security-official-reference/README.md). Les commandes exactes de compilation/lien et les journaux bruts restent dans l'espace de validation privé, avec les empreintes des entrées réutilisées. Le test d'exports utilise les blocs du véritable fichier CMake, un graphe Make isolé et le script amont ; le contrôle des arêtes vérifie aussi les dépendances de cible, pas uniquement la présence d'une option dans la commande.

Nouveaux préfixes courts, mappings délégués, `setgroups=allow`, namespaces PID/mount privés, timeout de 45 secondes, aucun `--map-root-user`. Les nombres de montages et de darlingserver avant/après concordent pour chaque essai. Le checkout canonique est resté propre ; les anciens préfixes et les fichiers protégés du banc précédent sont vérifiés en lecture seule. Les vues négatives partagent uniquement des fichiers immuables du **nouveau** stage ; leur CarbonCore sélectionnable est une copie indépendante. Aucun fichier historique n'est supprimé ou réécrit.

Provenance : qualification originale avec assistance OpenAI Codex, code officiel Darling/Security et tests existants ; aucun nouvel algorithme cryptographique, code Apple restreint, désassemblage ou décompilation Apple. Les modifications amont de StorageManager sont conservées telles quelles, attribuées par leur historique. Les nouveaux scripts suivent GPL-3.0-or-later et utilisent l'identité Git humaine autorisée.
