# D4RLING — Audit croisé maloader-carbon et qualification i386 Tiger/Leopard

**Archive de décision : 8 novembre 2026.** Analyse documentaire en lecture seule, consolidée pour permettre la suppression éventuelle de la conversation d'origine. **Aucun portage, build, essai invité ni validation audio n'est revendiqué par cette archive.**

## 1. Sources et niveau de preuve

- D4RLING : [fr4nck/d4rling](https://github.com/fr4nck/d4rling), références examinées : `3ee68bbfabe5e737e47dc1551b9f6a0ff83b1610` (audit comparatif), `master` au 8 novembre 2026 pour les comptes rendus consolidés.
- maloader-carbon : [velle999/maloader-carbon](https://github.com/velle999/maloader-carbon), `35badcb9b595bb993bfeed457f36b2a95afbf8d9`.
- dyld Darling : [darlinghq/darling-dyld](https://github.com/darlinghq/darling-dyld/tree/63f667cf06d7ed59553adebb0c8d70a117135ac9), `63f667cf06d7ed59553adebb0c8d70a117135ac9`.
- Source historique i386 : [maloader original](https://github.com/shinh/maloader).
- Historique des observations et des corrections `@rpath` : [PR D4RLING #8](https://github.com/fr4nck/d4rling/pull/8), [journal de recherche dyld/ABI](i386-dyld-abi-audit-2026-11.md).

**Légende :** SRC = inspection des sources ; OBS = observations locales rapportées, non relancées ici ; TEST = test effectivement exécuté avec sortie archivée ; OPEN = non résolu. La présence d'une fonction n'est pas une preuve de fonctionnement ; STATIC, LINK et GUEST doivent toujours être distingués.

**But :** déterminer ce qui mérite d'être repris de maloader-carbon pour exécuter des applications macOS musicales i386 (Logic Studio/Logic Pro 8, EXS24, QuickTime), sans remplacer les composants plus complets de Darling par des simulations propres à des jeux.

## 2. Conclusion architecturale

**NE PAS importer maloader-carbon en bloc.** Darling possède déjà un chargeur Mach-O/dyld, les relocations classiques, les stubs i386 de cinq octets, la résolution des symboles indirects, les ordinals et les bibliothèques dépendantes, ainsi que CoreFoundation, HIToolbox, CarbonCore, CoreAudio et CoreMIDI (avec des degrés de complétude très variables).

Le code de maloader-carbon sert en priorité de **référence de comportements, d'exemples de formats et de témoins négatifs**. Les reprises intéressantes sont ciblées dans NIB/ATSUI/QuickDraw, puis éventuellement AppleDouble et Multiprocessing Services. N'effectuer aucune transplantation avant de vérifier le besoin sur un témoin réel et la compatibilité ABI i386, les frontières Darwin/Linux et la licence fichier par fichier.

### Matrice d'arbitrage

| Élément | État observé dans D4RLING/Darling | Intérêt de maloader-carbon | Décision |
| --- | --- | --- | --- |
| Mach-O classique : `__IMPORT,__jump_table`, relocations, ordinals, `MH_TWOLEVEL` | Dyld les traite en source | Cas de tests historiques | **TESTS UNIQUEMENT** ; ne pas remplacer dyld |
| `LC_RPATH`, `@loader_path`, `@executable_path` | Dyld les connaît ; anomalie de canonicalisation constatée sur un témoin i386 | Différentiel chargeur | **TESTS UNIQUEMENT** ; exploiter PR #8 |
| `pthread_cond_t` et ABI Darwin | Bibliothèque pthread Darwin dédiée | Comparaison des tailles et codes d'erreur | **TESTS ABI**, pas wrapper glibc importé |
| CoreFoundation/CFRunLoop | Implémentation étendue issue des composants Apple/Darling | Sous-ensemble simplifié, parfois adapté aux jeux | **ÉCARTER LE REMPLACEMENT** |
| Carbon Event Manager | Code et suites de régression déjà présents dans D4RLING | Exemples de timers et dispatch | **TESTS DE COMPARAISON** |
| NIB Carbon | `IBCarbonRuntime.c` comporte des stubs | `hle/nib.c` lit des NIB XML ; `hle/windows.c` construit une hiérarchie partielle | **ADAPTATION CIBLÉE** après témoin graphique |
| ATSUI / polices | `ATS.c` contient des réussites factices pour le dessin/les mesures | `hle/atsui.c` et `hle/fonts.c` exploitent FreeType | **ADAPTATION CIBLÉE**, vérifier styles, métriques, encodage et ABI |
| QuickDraw | `QD.c` très incomplet | `hle/quickdraw.c` : ports, GWorld, PixMap, CopyBits | **ADAPTATION CIBLÉE**, ne pas présumer CoreGraphics |
| AGL / OpenGL | Infrastructure AGL présente mais partielle | Liaison SDL/OpenGL spécifique | **RÉFÉRENCE TECHNIQUE**, pas portage global |
| Resource Manager / File Manager | Implémentations existantes mais partielles | `hle/files_*.c`, `hle/resources.c` | **COMPARAISON PAR API** |
| Forks AppleDouble | `ResourcesImpl.cpp` privilégie `com.apple.ResourceFork` | `hle/appledouble.c` lit les fichiers compagnons `._` | **ADAPTATION CONDITIONNELLE**, vérifier la couche VFS |
| Multiprocessing Services | Quelques fonctions déjà présentes | `hle/mp.c` couvre tâches, files et sémaphores | **ADAPTATION À LA DEMANDE**, vérifier ordonnancement et erreurs |
| Sound Manager SDL2 | CoreAudio HAL/AudioUnit/PulseAudio distincts | `hle/sound.c` et `hle/sound_mix.c` réalisent du PCM Sound Manager | **PAS DE REMPLACEMENT COREAUDIO** |
| QuickTime simulé et bricolages spécifiques Halo/AoEIII | Objectif de compatibilité générale | Stubs/contournements applicatifs | **ÉCARTER** |

Sources directement étudiées :
- [d4rling IBCarbonRuntime.c](https://github.com/fr4nck/d4rling/blob/3ee68bbfabe5e737e47dc1551b9f6a0ff83b1610/src/frameworks/Carbon/HIToolbox/src/IBCarbonRuntime.c) ; [maloader nib.c](https://github.com/velle999/maloader-carbon/blob/35badcb9b595bb993bfeed457f36b2a95afbf8d9/hle/nib.c) ; [maloader windows.c](https://github.com/velle999/maloader-carbon/blob/35badcb9b595bb993bfeed457f36b2a95afbf8d9/hle/windows.c).
- [d4rling ATS.c](https://github.com/fr4nck/d4rling/blob/3ee68bbfabe5e737e47dc1551b9f6a0ff83b1610/src/frameworks/ApplicationServices/ATS/src/ATS.c) ; [maloader atsui.c](https://github.com/velle999/maloader-carbon/blob/35badcb9b595bb993bfeed457f36b2a95afbf8d9/hle/atsui.c) ; [maloader fonts.c](https://github.com/velle999/maloader-carbon/blob/35badcb9b595bb993bfeed457f36b2a95afbf8d9/hle/fonts.c).
- [d4rling QD.c](https://github.com/fr4nck/d4rling/blob/3ee68bbfabe5e737e47dc1551b9f6a0ff83b1610/src/frameworks/ApplicationServices/QD/src/QD.c) ; [maloader quickdraw.c](https://github.com/velle999/maloader-carbon/blob/35badcb9b595bb993bfeed457f36b2a95afbf8d9/hle/quickdraw.c).
- [d4rling ResourcesImpl.cpp](https://github.com/fr4nck/d4rling/blob/3ee68bbfabe5e737e47dc1551b9f6a0ff83b1610/src/frameworks/CoreServices/src/CarbonCore/ResourcesImpl.cpp) ; [maloader appledouble.c](https://github.com/velle999/maloader-carbon/blob/35badcb9b595bb993bfeed457f36b2a95afbf8d9/hle/appledouble.c) ; [maloader mp.c](https://github.com/velle999/maloader-carbon/blob/35badcb9b595bb993bfeed457f36b2a95afbf8d9/hle/mp.c).
- [Darling dyld ImageLoaderMachOClassic.cpp](https://github.com/darlinghq/darling-dyld/blob/63f667cf06d7ed59553adebb0c8d70a117135ac9/src/ImageLoaderMachOClassic.cpp) ; [dyld ImageLoaderMachO.cpp](https://github.com/darlinghq/darling-dyld/blob/63f667cf06d7ed59553adebb0c8d70a117135ac9/src/ImageLoaderMachO.cpp) ; [maloader mach-o.cc](https://github.com/velle999/maloader-carbon/blob/35badcb9b595bb993bfeed457f36b2a95afbf8d9/mach-o.cc).

## 3. R1 — dyld et `realpath()` : état actualisé au 8 novembre

La présente comparaison avait d'abord conclu, à partir de B1–C6, que **le dyld instrumenté n'était observé que durant la première étape `vchroot`** : 38 traces par variante, aucune sur le processus Carbon de seconde étape. Cela ne constituait pas une preuve d'inefficacité du correctif C2.

**La suite de l'investigation existe déjà** : le [rapport dyld/ABI](i386-dyld-abi-audit-2026-11.md) documente le chargement depuis une *vue fusionnée du préfixe invité* et les campagnes **G1-R2/R3** :
- dyld initial : témoin `@rpath` en échec ;
- dyld privé C2 : témoin Carbon `@rpath` avec sortie 0 et marqueur ;
- G1-R3 : trois critères annoncés PASS (dépendance directe, relative rpath, négatif sans LC_RPATH).

Ce résultat est **OBS sur un témoin restreint**, non une validation générale ou sécuritaire de dyld, et le code C2 reste **NON FUSIONNÉ** dans [PR #8](https://github.com/fr4nck/d4rling/pull/8).

**Ne pas relancer B1–C6 et le protocole préliminaire R1-B7 comme si G1 n'avait pas eu lieu.** L'ancien R1-B7 (empreintes et instrumentation des tranches) peut être utilisé seulement en cas d'incohérence de provenance. La question de validation nouvelle est la suivante :

1. **V1 i386** : vérifier le désassemblage **réellement i386** des stubs/du dispatcher BSD et le traitement CF/errno. Le précédent analyseur a produit du code x86-64 étiqueté i386 : son verdict négatif est invalide.
2. **V3 conditionnel** : sur un binaire invité i386 connu bon, relever les retours et `errno` de `stat64`, `getattrlist`, `lstat64`, `realpath` ; ne pas interpréter une erreur sans sa convention ABI.
3. **Sécurité C2** : chemins longs, relatifs, symlinks, traversées, préfixes isolés, mode restreint ; un fallback non canonicalisé peut modifier les garanties de recherche des bibliothèques.
4. **Livrable** : la PR #8 ne quitte pas le brouillon tant que le correctif n'est pas explicable, requalifié, et suffisamment sûr pour son périmètre.

L'implémentation Darwin [`realpath.c`](https://github.com/darlinghq/darling-Libc/blob/5a38c8dabf9e76b39407c24bc13134e33e5594e6/stdlib/FreeBSD/realpath.c) appelle `getattrlist()` et ne recourt à `lstat()` que sur certaines erreurs. Le dossier ABI suspecte une différence de convention de retour i386. **Cette hypothèse H-CF n'est toujours pas prouvée dans les binaires exécutés.** B5 testait `/Volumes/SystemRoot`, pas `/` comme chemin principal indépendant.

## 4. R2 — dix contrats historiques, à exécuter seulement si un témoin les justifie

Les cas ci-dessous sont un **plan de tests**, pas une suite ayant déjà réussi. Ne pas réinventer les essais existants dans [`tests/regressions/macho-i386/`](https://github.com/fr4nck/d4rling/tree/dfacf834551aa22127bd1ceef2943f3023f2de59/tests/regressions/macho-i386).

| ID | Contrat positif | Contrôle négatif attendu | Priorité |
| --- | --- | --- | --- |
| R2-01 | Stub `S_SYMBOL_STUBS` i386 / `__IMPORT,__jump_table` de cinq octets appelle le bon import | Stub mal formé ou index indirect invalide, rejet propre | Haute |
| R2-02 | Relocation classique locale d'un pointeur après glissement d'adresse | Relocation hors segment, rejet | Haute |
| R2-03 | Export depuis dylib classique sans export trie moderne résolu | Symbole absent, erreur explicite | Moyenne |
| R2-04 | `MH_TWOLEVEL` : deux dylibs homonymes, ordinal de la bonne bibliothèque respecté | Ordinal invalide, échec contrôlé | Haute |
| R2-05 | Ordre d'exécution des initialisateurs de dépendances correct | Dépendance invalide ou initialisateur impossible, échec contrôlé | Moyenne |
| R2-06 | Import faible réellement facultatif | Import obligatoire absent, erreur | Moyenne |
| R2-07 | Mach-O universel : sélection réelle de la tranche i386 et dyld correspondant | Tranche manquante ou offsets invalides, rejet | Haute |
| R2-08 | Chaîne `@rpath` Leopard avec LC_RPATH et dépendance réelle | Contrôle sans LC_RPATH, échec attendu | **Déjà couvert partiellement** par PR #8 / G1 |
| R2-09 | Tables de symboles, offsets et tailles valides acceptés | Troncature/débordement/index hors plage, rejet sans corruption | Haute |
| R2-10 | Mapping/relocalisation à une adresse valide ; absence de collision | Mapping bas interdit ou collision, erreur explicite | Haute |

**Gates obligatoires :** STATIC (vérification Mach-O), LINK (édition de liens i386), GUEST (résultat de l'appel réellement observé sous Darling, avec témoin négatif). Un `PASS` de l'un n'implique jamais un `PASS` du suivant. Préserver logs, SHA-256, révisions, provenance des outils et statut SKIP/BLOCKED si une précondition manque.

**Priorisation :** R2-07 et R2-08 servent le diagnostic V1 et la qualification dyld déjà engagée ; R2-01/02/04/09/10 ne deviennent prioritaires à l'exécution qu'avec un binaire ancien ou une défaillance reproductible correspondante. Ne pas dérouler les dix cas par automatisme.

## 5. Plan des travaux après ce jalon

1. **Préserver les preuves locales** : vérifier l'existence de `/tmp/d4rl-g1-r1.nMO0yEhA`, `/tmp/d4rl-g1-r2.1Stj16FI`, `/tmp/d4rl-g1-r3.zfPDLfmC`, des rapports `$HOME/d4rl-v012.zIDwo8mW` et des sources C2/C4. Inventorier d'abord ; copier dans un **seul dossier durable choisi explicitement**, avec empreintes, sans effacer, modifier ni publier d'informations locales sensibles.
2. **Terminer V1** : inspection brute des vraies tranches i386 déjà installées de `libsystem_kernel.dylib` et de dyld, en lecture seule. Obtenir une conclusion certaine (ou BLOCKED motivé).
3. **V3 seulement si V1 le justifie** : contrôle d'`errno` dans un témoin Darwin i386 isolé ; pas de modification de dyld en production.
4. **À partir d'un témoin graphique réel** : choisir une fonction NIB/ATSUI/QuickDraw effectivement appelée, puis décider d'un portage limité, avec tests ABI et droits/licences.
5. **Audio et Logic** : ne pas conclure au fonctionnement de Logic Pro 8/EXS24. Les nouveaux résultats B14/C10 sont archivés séparément dans [la synthèse audio](../REPRISE-AUDIO-MUSIQUE-2026-11-08.md), avec la réserve majeure de l'audibilité non confirmée sur le flux C10.

## 6. Règles d'intégration et préservation

- Ne pas toucher au checkout historique `b7d0cb6` avec modifications locales protégées, aux préfixes et aux binaires installés.
- Aucun téléchargement silencieux, compilation, nouveau préfixe, montage, remplacement de dyld, publication amont ou suppression de fichiers sur la seule base de cette note.
- Pour un portage : comparer d'abord la fonction existante dans D4RLING, vérifier le contrat historique Apple, isoler la logique utile, garder un test positif et un test négatif, puis contrôler la licence de **chaque fichier**. Le dépôt maloader-carbon possède un `LICENSE` GPLv3 et certains fichiers HLE annoncent une option BSD simplifiée/GPLv3 ; vérifier le contexte et les tiers avant toute copie.
- Les succès observés sur Halo/AoEIII et les stubs QuickTime de maloader-carbon n'établissent pas une compatibilité Logic ou un CoreAudio complet.
- Préférer une branche principale unique pour les nouveaux travaux ordinaires ; ne pas fusionner la PR #8 expérimentale ni créer de PR vers Darling officiel sans décision spécifique.
- Ce fichier conserve les **conclusions et liens**, pas les octets des preuves expérimentales du 5700X.

**Jalon documentaire :** l'audit croisé est archivé ; les tests R2 sont spécifiés ; G1-R2/R3 rend l'ancien R1-B7 non prioritaire ; il reste principalement la preuve i386 V1, et la sauvegarde durable des logs locaux avant de clore la conversation.

## 7. Vérification V0 des preuves locales — 8 novembre 2026

**OBS : sortie Bash fournie par l'opérateur sur `Deniel@5700X` (Debian WSL2).** L'inventaire n'a effectué aucune écriture, aucune opération Git et aucun téléchargement. Les trois dossiers G1 dans `/tmp` existent encore au moment de ce relevé :

| Répertoire local | Volume `du -sh` | Contenu visible au niveau 2 |
| --- | ---: | --- |
| `/tmp/d4rl-g1-r1.nMO0yEhA` | 5.3 Mio | `exit-code.txt`, `stderr.log`, `stdout.log`, `prefix/.init.pid` |
| `/tmp/d4rl-g1-r2.1Stj16FI` | 11 Mio | `C2/stderr.log`, `C2/stdout.log`, `OLD/stderr.log`, `OLD/stdout.log` |
| `/tmp/d4rl-g1-r3.zfPDLfmC` | 16 Mio | `inputs-before.sha256`, `inputs-after.sha256`, rapports `NEGATIVE`, `LOADER_RPATH`, `DIRECT` |

Les sorties sont **tronquées à deux niveaux de profondeur pour l'inventaire** : aucune conclusion sur le contenu intégral des sous-répertoires ou sur leur nature privée. **Ces 32,3 Mio approximatifs n'ont pas encore été archivés durablement par le relevé.**

Également observés dans `/home/Deniel` : `d4rl-v012.zIDwo8mW` (61 Mio), `d4rl-v012-kit` (24 Kio), `d4rling-dyld-rpath-c0` (164 Kio), `d4rling-dyld-rpath-c2` (5.1 Mio), `d4rling-dyld-rpath-c4` (6.2 Mio). LLVM `llvm-lipo-19`, `llvm-objdump-19`, `llvm-nm-19` sont présents. Le dyld installé a les architectures `i386 x86_64` et le SHA-256 `0f048c39017e6194581a5084d0bc0656b446f9743337cc66829dd4dc685b86ed`. Le `libsystem_kernel.dylib` installé a `x86_64 i386` et le SHA-256 `f94ab6955869ce4e91d6df1319764e84bb5d1925341fbf3b6372268ace85dd2e`.

**Prochain ordre :** (1) copier/archiver les trois G1 de `/tmp` vers un seul répertoire privé durable sous `/home/Deniel`, vérifier archive et SHA, sans suppression des sources ; (2) contrôler la tranche effectivement i386 de l'ABI BSD sans modifier les installations. Cette entrée GitHub conserve les métadonnées, **pas** les journaux locaux ni leur contenu.
