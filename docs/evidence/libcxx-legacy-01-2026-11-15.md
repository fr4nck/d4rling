# LIBCXX-LEGACY-01 — ABI historique libc++ Darwin

**TEST / LIBCXX_LEGACY_01_PASS — 15 novembre 2026**, 5700X / Debian WSL2. Cinq symboles résolus dans les deux architectures, négatifs discriminants et non-régression C++ dans des invités Darwin réels. Aucune application complète qualifiée.

## État et port minimal

- Master initial : `290dae25cf39c6508422b6d94759f6cb1a6c3afe`. AGENTS identique à celui lu pour MLD-ASLR-01, blob `17dc1d3fde68704f3463209a3bb524db954792f3` ; règles et état des espaces privés revérifiés.
- D4rling épingle libc++ à **`caf34a8ca7837354e7bd49f9ae28018943bb7dd3`**, où `_LIBCPP_ABI_VERSION` n'est pas défini. Le correctif n'est donc **pas déjà présent**.
- [Darling-libcxx #8](https://github.com/darlinghq/darling-libcxx/pull/8), Lubos Dolezel : correctif `c8cb41d8d64a8db10745e85042a879463711908a`, fusion officielle **`061279ebb3944b11bbbc76ae7fd77077841f8c74`**.
- Comparaison Git des arbres : **un seul fichier**, `include/__config_site`, six lignes ajoutées/une remplacée. Pas de nouvelle version LLVM, option CMake globale ou autre changement de module. [Diff exact archivé](libcxx-legacy-01-2026-11-15/config-change.patch).
- Le commit D4rling avance uniquement le **gitlink libc++** vers cette fusion officielle. Le module de qualification est dans un checkout détaché privé ; aucune nouvelle branche d'intégration.
- Avant publication, master a avancé à `12cd0e16c76a830d40071ba0f475cbd728ac5ab5` par `d619d8aa7` et `12cd0e16c` (tests/preuves AudioToolbox B13). Ces commits sont repris par avance rapide et conservés ; aucun de leurs fichiers n'est modifié ou testé par ce lot.

## Mécanisme documenté et surface observée

La documentation LLVM **15.0.7**, [ABI stability](https://github.com/darlinghq/darling-libcxx/blob/061279ebb3944b11bbbc76ae7fd77077841f8c74/docs/DesignDocs/ABIVersioning.rst), décrit ABI 1 comme stable et ABI 2 comme instable. La page hébergée de la version 15 n'était pas accessible par l'outil web ; la documentation primaire du checkout épinglé a été lue directement.

Dans `include/__config`, la branche `_LIBCPP_ABI_VERSION == 1` active `_LIBCPP_DEPRECATED_ABI_LEGACY_LIBRARY_DEFINITIONS_FOR_INLINE_FUNCTIONS`. `src/memory.cpp` utilise ce contrôle pour réémettre les définitions hors ligne de `__shared_count` et `__shared_weak_count`. La configuration Darwin étant écrite à la main, il faut définir la macro dans `__config_site` ; définir seulement une option CMake n'est pas le correctif porté. Le namespace ABI **`__1` est conservé**, aucune activation de l'ABI 2.

Le témoin de [Darling #2112](https://github.com/darlinghq/darling/pull/2112), commit `6649be99dac6a54e29a09d661fa095bf8ac3c532`, ouvre `/usr/lib/libc++.1.dylib` puis recherche sans adaptation ces cinq noms via `dlsym` :

```text
_ZNSt3__119__shared_weak_count12__add_sharedEv
_ZNSt3__119__shared_weak_count10__add_weakEv
_ZNSt3__119__shared_weak_count16__release_sharedEv
_ZNSt3__114__shared_count12__add_sharedEv
_ZNSt3__114__shared_count16__release_sharedEv
```

Ces noms reçoivent un underscore Mach-O supplémentaire dans l'export trie. Les cinq sont absents de la référence et présents dans le candidat **sur les deux tranches**. L'export trie passe de **1 962 à 1 972** entrées par architecture : cinq méthodes demandées, `error_categoryC2` et quatre constructeurs/destructeurs `valarray<size_t>` historiques. **Aucun export retiré**. Les dix ajouts découlent de l'ABI 1 du code LLVM épinglé ; aucun symbole synthétique ajouté. [Delta i386](libcxx-legacy-01-2026-11-15/export-delta-i386.json), [delta x86_64](libcxx-legacy-01-2026-11-15/export-delta-x86_64.json).

## Construction réellement exécutée

Le build core conservé à `4be2603c62a6b0ec0148e60c7dff2e4f8b61c931`, son SDK source Darling, ses outils Clang 19/cctools, libSystem et libc++abi sont réutilisés **en lecture seule**. Le module de référence reste propre à `caf34a8c`, le candidat propre à `061279eb`. Le diff entre eux est contrôlé avant le build.

**46 unités FAT par variante**, donc 92 compilations de fichiers universels / 184 tranches i386+x86_64, ont été reconstruites avec deux tâches maximum. Tous les fichiers sont recompilés : le changement de configuration concerne toute libc++, pas seulement memory.cpp. Les dépendances produites doivent mentionner le `__config_site` de la variante concernée. Lien et signature ad hoc des deux dylibs réussis. [Unités, retours et SHA](libcxx-legacy-01-2026-11-15/compile-results.json), [environnement](libcxx-legacy-01-2026-11-15/environment.json), [entrées de liaison épinglées](../../tests/regressions/libcxx-legacy-01/link-inputs.json).

Les images ont toutes deux l'identité `/usr/lib/libc++.1.dylib`, versions courante/compatibilité inchangées. [UUID et empreintes](libcxx-legacy-01-2026-11-15/images.json). SHA-256 FAT :

- Référence : `ab895b490b01e2058c596949d68f8677a82a8cce3a015b794d010334775ad1ee`.
- Candidat : `a8ccb2e73854dba9b889c211e1ec0c6bc60b4381db547d6286abc932f2dbc39f`.

Les témoins sont de vrais Mach-O, pointeur 4/8 octets selon l'architecture. Le témoin officiel est inchangé, origine et blob contrôlés. Un second témoin original possède cinq références **fortes** aux mêmes symboles, vérifie leur provenance par `dladdr` et ne les appelle pas : aucune disposition de classe privée ou signature d'appel n'est inventée. Il sert à distinguer lookup dlsym et binding ordinaire lors du démarrage.

## Exécution native et négatifs

La recette `reproduce.py --stage ... --run` a été exécutée intégralement dans une nouvelle sortie : **36 cas**, 32 succès et quatre échecs attendus. Elle réutilise les reconstructions déjà effectuées, vérifie leurs empreintes et crée de nouveaux préfixes. [Résultats structurés](libcxx-legacy-01-2026-11-15/results.json), [sorties/erreurs et teardown](libcxx-legacy-01-2026-11-15/executions.txt).

| Contrôle | i386 | x86_64 |
| --- | --- | --- |
| Témoin officiel, référence | 5 FAIL attendus, RC1 | 5 FAIL attendus, RC1 |
| Témoin officiel, candidat | **5/5 PASS**, RC0 | **5/5 PASS**, RC0 |
| Liaison forte, référence | Symbole absent avant main, RC134 attendu | Symbole absent avant main, RC134 attendu |
| Liaison forte, candidat | **5 adresses liées**, fournisseur libc++, RC0 | **5 adresses liées**, fournisseur libc++, RC0 |
| Sept tests LLVM inchangés, référence | **7/7 PASS**, RC0 | **7/7 PASS**, RC0 |
| Sept tests LLVM inchangés, candidat | **7/7 PASS**, RC0 | **7/7 PASS**, RC0 |

Les tests existants couvrent `shared_ptr::reset`, `weak_ptr::lock`, `weak_ptr::expired`, construction/what de `bad_weak_ptr`, copie/déplacement de `std::function`, catégorie d'erreur générique et construction/destruction de `valarray`. Le test valarray exerce plusieurs types et leurs destructeurs ; il ne mesure pas spécifiquement chaque instanciation hors ligne `size_t`. Ils sont compilés contre les en-têtes candidats et le même exécutable est exécuté contre les deux dylibs : assertions actives (`__assert_rtn` vérifié), sources et SHA listés dans [le manifeste LLVM](../../tests/regressions/libcxx-legacy-01/regressions.json). Les 28 exécutions de non-régression passent. Le test bad_weak_ptr ne constitue pas une qualification de propagation d'exceptions ou du TLS.

Chaque cas vérifie **le SHA du fichier FAT sélectionné avant création du préfixe**, puis l'UUID de sa tranche dans le message `dyld: loaded: ... /usr/lib/libc++.1.dylib`. Le candidat observé n'est donc pas déduit de la simple présence d'un fichier construit. Le runner réutilise le banc à mappings délégués, `setgroups` vérifié, namespaces privés et timeout 45 s, sans `--map-root-user`. Sélection seulement dans la copie runtime privée du lot, aucune écriture dans un overlay actif ou un préfixe historique.

## Protections, tentatives et limites

Les 36 cas retrouvent **41 → 41 montages hôte** et aucun PID dans leur namespace possédé. Cache ld.so, base dpkg et paramètres ASLR/mmap suivis : mêmes empreintes avant/après. Les runtimes S4 et MLD d'origine ont été revérifiés sur **6 013 fichiers chacun**, avec les trois chargeurs MLD attendus ; ils sont intacts. Le canon est resté propre à `747670a53d5a73af64470e5f60f8f3611a09a245` et la source libc++ de référence à `caf34a8c`.

Les tentatives privées non qualifiées sont conservées : lecture initiale d'un exécutable Clang comme texte interrompue sans écriture ; premier lien d'un témoin C++ i386 refusé parce qu'une seconde option `-target` x86_64 n'avait pas été remplacée ; première étiquette de préfixe x86_64 refusée avant exécution à cause de l'underscore. Ces problèmes de recettes ont été corrigés ; architectures et assertions sont contrôlées avant la série finale. Aucun de ces essais n'est déclaré PASS.

Ce lot qualifie des exports, leur liaison Darwin et sept comportements C++ identifiés. Il ne qualifie ni toute la suite LLVM, ni tous les consommateurs libc++, ni une application complète. Le target dynamique cxx est reconstruit ; cxx_static et ses consommateurs ne sont pas reconstruits/reliés dans cette campagne. Aucun changement ou essai sur AudioToolbox B13, Fontconfig/LOGIC-L1, TLS libdyld ou Petite Victoire. Aucune installation globale, nouveau paquet, préfixe historique ou remplacement de l'installation canonique.

**Aucune conclusion n'est tirée sur l'utilisation de ces cinq symboles par Logic Pro 8.** Le second témoin de #2112, **ptrace-wait4**, reste à expertiser ; il n'est pas importé, compilé ou exécuté et aucun deuxième chantier n'est ouvert.

[Recette complète](../../tests/regressions/libcxx-legacy-01/README.md). Les commandes brutes, bibliothèques et journaux complets restent privés ; la publication contient les sources originales de test/driver, les références des tests LLVM et les preuves expurgées, sans chemin personnel ou binaire propriétaire. Provenance : Lubos Dolezel pour les correctifs/tests officiels, LLVM pour les régressions sous Apache-2.0 WITH LLVM-exception ; drivers et témoin complémentaire originaux avec assistance IA. Notices conservées.
