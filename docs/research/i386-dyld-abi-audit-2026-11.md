# D4RLING — dossier de clôture : dyld `@rpath`, ABI Darwin i386 et faisabilité Logic 8

**Consolidation documentaire : 8 novembre 2026.**  
**Statut : recherche ouverte, qualification incomplète ; aucun GO pour Logic Pro 8.**

> Ce document sauvegarde les résultats utiles d'une conversation technique et des
> journaux de terminal communiqués par l'opérateur. Il ne remplace ni les rapports
> originaux du 5700X, ni une nouvelle exécution, ni une expertise de sécurité.
> Les niveaux de preuve doivent rester distincts : **SRC** (source inspectée),
> **OBS** (sortie expérimentale communiquée), **DOC** (documentation), **INF**
> (inférence), **HYP** (hypothèse), **OPEN** (non tranché).
> Les tests locaux n'ont **pas** été rejoués dans cette opération d'archivage.

## 1. Verdict de clôture

- **Acquis OBS :** un programme témoin Carbon Mach-O i386 terminant, avec appels
  événements/paramètres, peut sortir avec le marqueur exact
  `D4RLING-CARBON-EVENT-I386-OK`. Le chargement direct `@loader_path` est
  qualifié sur ce témoin. La variante `@rpath` avec correctif expérimental C2
  a aussi été qualifiée sur ce témoin (G1-R2/R3).
- **Constat OBS :** avec le dyld initial, des chemins `LC_RPATH` relatifs
  utilisant `@executable_path` ou `@loader_path` échouaient alors qu'un
  `LC_RPATH` absolu invité réussissait. La sonde B5 retournait `NULL` pour
  trois appels `realpath()`, sans enregistrer `errno`.
- **HYP forte dans les sources :** la passerelle des appels système BSD Darwin
  i386 pourrait ne pas convertir les erreurs négatives en convention CF/errno
  attendue par les stubs. **Ce mécanisme n'est pas encore prouvé dans les
  binaires installés ni relié causalement à B5 à l'exécution.**
- **V1 non conclusif :** le script d'inspection V0–V2 a rendu
  `PATTERN_ABSENT`, mais ses extraits dits i386 ressemblaient au x86_64
  (`cmpq`, `jb`, comparaison avec -4095). Sélection de tranche ou analyse
  fautive : **à contrôler sur le désassemblage brut**, pas de réfutation H-CF.
- **Non acquis :** exécution de Logic Pro 8, QuickTime 7, EXS24, séquenceur
  complet, CoreMIDI, AudioUnit/AUGraph généralisés, route audio faible latence
  fiable. Ne pas déduire une compatibilité applicative d'un témoin.
- **Décision :** conserver la PR #8 en brouillon, sans fusion ni généralisation
  du correctif C2. Finir V1, analyser V3 seulement si autorisé, puis produire
  l'étude de faisabilité Logic 8 (GO / GO limité / NO-GO).

## 2. Références immuables et état Git

| Référence | Révision / statut de référence |
| --- | --- |
| Dépôt | [fr4nck/d4rling](https://github.com/fr4nck/d4rling), branche par défaut `master` |
| Checkout historique des tests | [`b7d0cb6a79fe196657deb9711647f8486bcc5e5e`](https://github.com/fr4nck/d4rling/commit/b7d0cb6a79fe196657deb9711647f8486bcc5e5e), **avec neuf modifications locales protégées**, non comprises dans le commit |
| dyld | [`darlinghq/darling-dyld@63f667cf06d7ed59553adebb0c8d70a117135ac9`](https://github.com/darlinghq/darling-dyld/tree/63f667cf06d7ed59553adebb0c8d70a117135ac9) |
| xnu/émulation | [`darlinghq/darling-xnu@fa29287aa2f0115271e091f1031f53c9e024005d`](https://github.com/darlinghq/darling-xnu/tree/fa29287aa2f0115271e091f1031f53c9e024005d) |
| Libc | [`darlinghq/darling-Libc@5a38c8dabf9e76b39407c24bc13134e33e5594e6`](https://github.com/darlinghq/darling-Libc/tree/5a38c8dabf9e76b39407c24bc13134e33e5594e6) |
| darlingserver | [`89751e64bc6c2082f7725061824ee0e33395b0de`](https://github.com/darlinghq/darlingserver/tree/89751e64bc6c2082f7725061824ee0e33395b0de) |
| [PR #8](https://github.com/fr4nck/d4rling/pull/8) | **OPEN / DRAFT / NOT MERGED**, tête `fb36bb8364c563c847d71892d46ba510def893d5`, base `3ee68bbfabe5e737e47dc1551b9f6a0ff83b1610`, état vérifié le 8 novembre |
| Candidat source C2 | [`reproduction/patches/dyld-rpath-realpath-fallback.patch` dans PR #8](https://github.com/fr4nck/d4rling/blob/fb36bb8364c563c847d71892d46ba510def893d5/reproduction/patches/dyld-rpath-realpath-fallback.patch), **non appliqué au `master`** |
| Inventaire historique | [`PROJECT_STATE.md`](../../PROJECT_STATE.md), [`reproduction/README.md`](../../reproduction/README.md), [`docs/d4rling-reprise-2026-10-29.md`](../d4rling-reprise-2026-10-29.md) |

Le README de la PR #8 conserve le descriptif **historique initial** de Phase B ;
les essais locaux ultérieurs C2/G1 ne constituent pas une validation CI
publique de cette PR. Ce document ajoute leur compte rendu, **pas leurs
journaux originaux**.

## 3. Campagnes `@rpath` — chronologie et limites

| Lot | Résultat communiqué | Portée |
| --- | --- | --- |
| B1 | `@loader_path` NORMAL/BYPASS : sortie 0, marqueur ; variante `LC_RPATH=@executable_path` : sortie 1, dylib non trouvée | Comparaison sur le même témoin |
| B2 | `LC_RPATH=@executable_path` échoue ; sans `LC_RPATH`, échec attendu | Ne prouve pas à lui seul la cause |
| B3 | `LC_RPATH` invité **absolu** : sortie 0, marqueur, trace « RPATH successful expansion » | Un chemin absolu fonctionne |
| B4 | `LC_RPATH=@loader_path` : sortie 1, dylib absente | Chemin relatif défaillant |
| B5 | `realpath()` invité retourne `NULL` sur trois chemins ; sonde i386 elle-même sortie 0 | **Pas de mesure d'errno** |
| G1-R1 | Copie expérimentale C4 instrumentée utilisée dans l'overlay privé ; chargement Carbon observé | La composition exacte de C4 restait à vérifier |
| G1-R2 | A/B à préfixes frais : dyld original `exit=1` sans marqueur ; dyld C2 `exit=0` avec marqueur | Contre-épreuve positive pour **ce témoin** |
| G1-R3 | Trois cas : `@loader_path` direct, `@rpath` avec `LC_RPATH`, négatif `@rpath` sans `LC_RPATH` ; **3/3 critères annoncés PASS** | Pas de validation générale de dyld ou de sécurité |

Le correctif candidat change `ImageLoaderMachO::getRPaths()` : il conserve
`realpath()` comme voie nominale et, en cas d'échec, utilise sous conditions
le chemin absolu déjà chargé (`@loader_path` / `@executable_path`).
Cette solution peut changer la canonicalisation des liens, des chemins et
les hypothèses de sécurité. **Symlinks, chemins restreints, normalisation et
autres contre-exemples non qualifiés**. Elle ne corrige pas nécessairement la
cause sous-jacente.

Empreintes de référence rapportées : dyld d'installation
`0f048c39017e6194581a5084d0bc0656b446f9743337cc66829dd4dc685b86ed` ;
dyld expérimental C2
`e9eb381e5ca1e85bde3101d18e47ea2fc51579b6dcf31ee866f1845b964dedb6` ;
dyld C4 instrumenté (rapport historique)
`31726881163edca38f9d457c23291b564aade17bcf0702f7fc2b854b6db6b57b`.
La présence/identité actuelle des fichiers correspondants sur le poste
**n'a pas été revérifiée lors de l'archivage**.

## 4. Architecture de lancement établie par lecture des sources (D1/D2)

La comparaison C2/original échouait tant que le mauvais dyld était modifié.

1. `darlingserver` démarre `vchroot` via `mldr` et transmet
   `__mldr_DYLD_ROOT_PATH=LIBEXEC_PATH`.
2. `mldr` convertit cette variable en `DYLD_ROOT_PATH` pour le processus
   de démarrage. Son dyld vient de **l'installation**.
3. `vchroot` établit le préfixe invité, efface `DYLD_ROOT_PATH` avant
   d'exécuter `launchd`.
4. Les processus invités ultérieurs résolvent leur racine via RPC
   `vchroot_path` et utilisent le dyld de la **vue fusionnée du préfixe**.
5. Le programme i386 bascule vers `mldr32` et utilise la tranche i386 du dyld.
6. `ImageLoaderMachO::getRPaths()` consulte `realpath()` pour les
   `LC_RPATH` relatifs `@loader_path` et `@executable_path`.

Références de code :
[`mldr.c`](https://github.com/fr4nck/d4rling/blob/b7d0cb6a79fe196657deb9711647f8486bcc5e5e/src/startup/mldr/mldr.c),
[`vchroot.c`](https://github.com/fr4nck/d4rling/blob/b7d0cb6a79fe196657deb9711647f8486bcc5e5e/src/vchroot/vchroot.c),
[`ImageLoaderMachO.cpp`](https://github.com/darlinghq/darling-dyld/blob/63f667cf06d7ed59553adebb0c8d70a117135ac9/src/ImageLoaderMachO.cpp).

Les deux dyld (amorçage vs programme Carbon) expliquent l'inefficacité
de plusieurs modifications précédentes de l'installation. Ne pas remplacer
les fichiers de l'installation ni l'overlay actif pour « tester rapidement » ;
les expérimentations G1 ont utilisé des préfixes frais isolés.

## 5. D3 — hypothèse H-CF sur les erreurs BSD i386

**Contrat Darwin i386 de référence (DOC/SRC) :** un appel système échoué
est signalé par `CF=1` avec un numéro d'erreur positif dans `eax` ;
le stub appelle `cerror`, qui définit `errno` et renvoie `-1`.

**Dans les sources Darling épinglées (SRC) :**

- Les stubs BSD i386 exécutent `call __darling_bsd_syscall`, puis
  `jnb` (test du drapeau CF) pour éviter `tramp_cerror` si pas d'erreur :
  [`gen/bsdsyscalls/SYS.h`](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/gen/bsdsyscalls/SYS.h).
- Le dispatcher i386 appelle une fonction d'émulation, puis exécute
  `addl $56,%esp` et `ret`, sans traduire explicitement une valeur de
  retour négative en `CF=1` / `errno` positif :
  [`bsd_syscall.S`](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall.S).
- `getattrlist` peut renvoyer `-EINVAL` ; le `realpath` statique de dyld
  n'essaie son repli `lstat` que si `errno` vaut `ENOTSUP` ou `EINVAL`.
  Sans propagation correcte d'errno, il peut renvoyer `NULL` :
  [`getattrlist_generic.c`](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/helper/xattr/getattrlist_generic.c),
  [`realpath.c`](https://github.com/darlinghq/darling-Libc/blob/5a38c8dabf9e76b39407c24bc13134e33e5594e6/stdlib/FreeBSD/realpath.c).
- Les suffixes i386 `$INODE64` / `$UNIX2003` orientent les appels de
  `realpath` vers `stat64`, `lstat64`, `statfs64`, `getattrlist`.
  Le `sys_statfs` i386 ancien, non implémenté, **n'est pas identifié comme
  la cause de ce chemin dyld**.
- Le chemin x86_64 contient, lui, un traitement explicite du résultat
  négatif dans les stubs.

**Limite : H-CF n'est pas démontrée dans les binaires i386 installés.**
En particulier, `realpath("/")` n'est pas une sonde indépendante :
l'initialisation `rootdev` peut d'abord appeler `stat("/")`.
L'ancien `realpath` B5 n'enregistrait pas `errno`.
Le constat source suggère un défaut d'ABI potentiellement plus large que dyld,
mais on ne peut pas encore attribuer à cette seule cause tous les échecs
Carbon, QuickTime ou CoreAudio.

## 6. V0–V2 : dernier relevé local communiqué (lecture seule)

L'opérateur a exécuté un script `d4rl-v012.sh` dans Debian WSL2 sur le 5700X.
SHA-256 du script **annoncé** :
`59d9f0327f6b62407409c37c05225ca1723170b0312edfed5bfd0864e8f9c112`.
Le code intégral de ce script **n'a pas été audité indépendamment ici**.

| Relevé | Sortie du script | Interprétation conservatrice |
| --- | --- | --- |
| V0 | 145 fichiers de logs ; 32 avec « Did find » ; chaînes distinctes `/Users:`, `/usr:` | Indice cohérent avec D3, non preuve unique |
| V0 | 27 répertoires d'essais trouvés ; rapports G1-R1/R2/R3 présents | **À sauvegarder hors `/tmp`** |
| O5 | Sources C0 et C4 retrouvées, chacune avec 2/2 marqueurs C2 ; blobs distincts | C4 **semble** intégrer C2, équivalence pas démontrée |
| O6 | Source B5 retrouvée ; aucune référence à `errno` | La mesure dynamique d'errno reste manquante |
| Provenance | `libsystem_kernel.dylib`, `libsystem_c.dylib`, `dyld` marqués `BUILD_OUTPUT_MATCH` ; 17 fichiers sources clés sans différence relevée ; neuf modifications locales | Contrôles internes du script, pas audit indépendant des empreintes |
| V1 « i386 » | `IMM=$0xdc`, `cmpq`, `jb`, `GW_INDIRECT_CALL=NOT_FOUND` | **Incompatible avec le motif i386 recherché ; analyseur ou tranche probablement erroné** |
| V1 | `HCF_BINARY_KERNEL=NOT_SUPPORTED_STATIC`, idem DYLD | **NE PAS retenir comme réfutation** : l'extrait désassemblé n'est pas validé |
| Témoin | x86_64 `cmpq` / `negq` présents | Confirme seulement le motif x86_64 dans la méthode |
| V2 | dyld `_realpath$DARWIN_EXTSN` associé à `getattrlist`, `lstat64`, `stat64`, `statfs64` ; aucun ancien `statfs` relevé | Cohérent avec l'analyse des sources ; sélection de tranche à vérifier |
| Intégrité | `INTEGRITY=PASS` | Verdict **produit par le script lui-même**, pas preuve externe |

Après V1, une tentative manuelle a échoué : l'option
`--dis-symname=SYMBOL` a été refusée par `llvm-objdump-19`.
Une syntaxe corrigée avec argument séparé a été proposée, **sans sortie
ultérieure communiquée**. On ne dispose donc toujours **pas** du
désassemblage i386 brut confirmant ou infirmant H-CF.

### Critère de clôture technique de V1

Lire explicitement la tranche `i386` du `libsystem_kernel.dylib` et du dyld
**réellement installés**, puis comparer le dispatcher, `getattrlist`,
`lstat64`, `stat64`, `statfs64` et `tramp_cerror` au contrat.
Ne pas se fier aux seules étiquettes `PATTERN_PRESENT` ou
`PATTERN_ABSENT` d'un analyseur. Si le binaire est dépouillé de ses
symboles, utiliser une méthode de lecture par adresse **sans installer
d'outil ni modifier le poste**. Un contrôle runtime d'errno (V3) nécessitera
une décision distincte.

## 7. Preuves locales à archiver EN PRIVÉ avant suppression du chat

Aucune des sources privées suivantes n'a été copiée sur GitHub par
cette publication. Les chemins sont des **indices tirés des journaux**,
à vérifier sur le poste ; l'existence au 8 novembre n'est pas attestée.

| Élément recherché | Emplacement rapporté |
| --- | --- |
| Résumé et détails V0–V2 | `$HOME/d4rl-v012.zIDwo8mW/summary.txt`, `detail/` |
| Script V0–V2 | `$HOME/d4rl-v012-kit/d4rl-v012.sh` |
| Rapports G1-R1/R2/R3 | `/tmp/d4rl-g1-r1.nMO0yEhA`, `/tmp/d4rl-g1-r2.1Stj16FI`, `/tmp/d4rl-g1-r3.zfPDLfmC` |
| Sources expérimentales C0/C2/C4 | `$HOME/d4rling-dyld-rpath-c0/`, `$HOME/d4rling-dyld-rpath-c2/`, `$HOME/d4rling-dyld-rpath-c4/` |
| Campagnes B1–B5 | `$HOME/d4rling-dyld-rpath-01-runtime/`, `$HOME/d4rling-dyld-rpath-b2/` à `-b5/` |
| Checkout historique protégé | `$HOME/d4rling-ui/d4rling-carbon-qualif/` **ne pas modifier, nettoyer, reset ni checkout** |
| Build et installation | Arbres privés existants, potentiellement volumineux : **ne pas dupliquer automatiquement** |

Pour l'archive privée : inventaire des fichiers présents et des volumes
d'abord ; copie vers un **unique répertoire explicitement choisi**, avec
empreintes SHA-256 et vérification des copies ; pas de suppression, de
téléchargement ni de transfert de binaires/licences/logs bruts vers ce dépôt.
Les `/tmp` peuvent disparaître au redémarrage. Ce document public
préserve les **conclusions**, pas les **preuves originales**.

## 8. Autres investigations utiles à la faisabilité Logic Studio 8

Ces repères ont été explorés documentairement ; ils ne justifient aucune
annonce de compatibilité Logic 8.

- **Rosemary / RoMach0 :** [Froststrap/RoMach0](https://github.com/Froststrap/RoMach0)
  réimplémente des interfaces Darwin/macOS avec chargeur Mach-O et émulation
  x86-64. Le README étudié ne démontrait pas l'exécution de Logic i386.
- **Maloader / maloader-carbon :**
  [shinh/maloader](https://github.com/shinh/maloader) et
  [velle999/maloader-carbon](https://github.com/velle999/maloader-carbon).
  Le second annonce l'exécution de Halo Mac i386 avec Sound Manager/SDL2,
  et un blocage d'Age of Empires III sur CoreAudio. **Témoignage du README,
  non reproduction indépendante.** Architecture ciblée, pas Carbon universel.
- **CoreAudio déjà dans Darling :**
  [`src/CoreAudio` à b7d0cb6](https://github.com/fr4nck/d4rling/tree/b7d0cb6a79fe196657deb9711647f8486bcc5e5e/src/CoreAudio) :
  classes AudioHardware/PulseAudio, AudioConverter, AudioQueue et infrastructure
  AudioUnit partielles. Dans cette révision,
  [`AUGraph.cpp`](https://github.com/fr4nck/d4rling/blob/b7d0cb6a79fe196657deb9711647f8486bcc5e5e/src/CoreAudio/AudioToolbox/AUGraph.cpp)
  est vide ;
  [`AudioQueueOutput.cpp`](https://github.com/fr4nck/d4rling/blob/b7d0cb6a79fe196657deb9711647f8486bcc5e5e/src/CoreAudio/AudioToolbox/AudioQueueOutput.cpp)
  contient des `unimpErr` ;
  [`HostTime.mm`](https://github.com/fr4nck/d4rling/blob/b7d0cb6a79fe196657deb9711647f8486bcc5e5e/src/CoreAudio/CoreAudio/HostTime.mm)
  retourne `0`. Code présent ≠ moteur temps réel qualifié.
- **Références historiques utiles :** anciens SDK Mac OS X 10.4–10.6,
  utilitaires Core Audio, [IOAudioFamily Apple](https://github.com/apple-oss-distributions/IOAudioFamily),
  [JACK2 / pilote CoreAudio](https://github.com/jackaudio/jack2/tree/develop/macosx/coreaudio),
  [Soundflower original](https://github.com/RogueAmoeba/Soundflower-Original),
  et archives de la liste [CoreAudio Apple](https://www.mail-archive.com/coreaudio-api@lists.apple.com/).
  Ce sont des contrats, des exemples et des composants **partiels**, non
  une distribution complète de CoreAudio Linux. Vérifier les licences
  de chaque fichier avant toute importation.

## 9. Prochaine décision : estimation, pas extension aveugle

Avant de poursuivre le développement :

1. Clore V1 par le vrai désassemblage i386 ; mesurer `errno` en V3
   seulement si le diagnostic l'exige et après autorisation.
2. Auditer l'inventaire **exact** des dépendances importées par les binaires
   de Logic Pro 8 et leurs versions d'API, sans supposer qu'un framework
   présent suffit.
3. Réaliser une matrice CoreAudio/AudioUnit/CoreMIDI : code existant, stubs,
   fonctionnalités absentes, tests, contraintes de pont i386→Linux64 et
   temps réel.
4. Produire des fourchettes **argumentées** en journées d'ingénierie et
   une analyse de risque pour les scénarios :
   **A** interface/démarrage, **B** lecture audio/MIDI limitée,
   **C** station de travail fiable, effets/instruments et faible latence.
5. Comparer ce coût au maintien d'un environnement macOS historique ;
   rendre un verdict **GO / GO limité / NO-GO**. Aucun nombre de jours
   ou probabilité n'est prétendu établi à la date de ce document.

### Règles de reprise

- Aucune réécriture du passé : distinguer résultat SRC, OBS, TEST et
  inférence ; aucune « correction » inventée des anciens journaux.
- Ne pas toucher aux neuf changements locaux protégés, aux préfixes
  actifs ni aux installations privées.
- Aucun téléchargement silencieux ni création de fichiers dispersés ;
  annoncer volume, destination et autorisation avant action locale.
- Pas de modification C2/PR #8, ni de nouveau test runtime, par défaut.
- **Ce document est la synthèse publique de reprise**, et non une archive
  de la conversation entière, du D3 intégral ni des artefacts d'essai.

---

**État administratif de cet archivage :** création de ce seul document
Markdown sur la branche `master`. Aucune modification de code, sous-module,
configuration, PR #8, binaire ou donnée du poste 5700X.


## 10. Qualification V1-R2 — preuves binaires i386 et reprise après archivage (8 novembre 2026)

**Statut : OBS ; V1 extraction/disassemblage PASS, diagnostic H-CF encore OPEN.** L'opérateur a fourni la sortie Bash de `G1-RECOVERY + V1` puis de `V1-R2` sur le 5700X. Aucun essai dynamique n'a été réalisé dans cette étape et aucun fichier de l'installation n'a été remplacé.

### Archivage G1 confirmé

- L'archivage initial intégral de `/tmp` échouait normalement sur les sockets Unix Darling et sur les chemins `prefix.workdir/work` inaccessibles. L'archive partielle n'était pas qualifiée.
- Une reprise a créé **`/home/Deniel/d4rling-preuves/g1-v1-recovery.hpfVdVIF/G1-preuves.tar.gz`** en excluant les préfixes d'exécution. `gzip -t`, les huit fichiers obligatoires dans l'index et `sha256sum -c` ont rendu PASS. L'archive compressée fait environ **16 Kio**, car les préfixes sont exclus. Elle représente les **preuves sélectionnées**, non l'environnement d'exécution complet. Les trois répertoires originaux de `/tmp` n'ont pas été supprimés.
- Une première tentative V1 avait rejeté à tort la tranche i386 parce que le contrôle comparait littéralement la sortie de `llvm-lipo-19 -archs`, avec son espace final éventuel. **Faux échec du script**, non du binaire ; corrigé dans V1-R2.

### V1-R2 : tranches et symboles vérifiés

Répertoire de résultat : `/home/Deniel/d4rling-preuves/g1-v1-recovery.hpfVdVIF/v1-r2.5VyVqC4c` (25 Mio). Deux tranches sont reconnues `Mach-O i386`, les symboles sont accessibles et `llvm-objdump-19` a terminé avec succès.

| Binaire installé | SHA-256 universel | SHA-256 tranche i386 | Ancrages i386 |
| --- | --- | --- | --- |
| `usr/lib/system/libsystem_kernel.dylib` | `f94ab6955869ce4e91d6df1319764e84bb5d1925341fbf3b6372268ace85dd2e` | `b9d71878c48f858002b8daf759109969ac9935b2cc4d7bf645e78daecafc2e52` | `__darling_bsd_syscall` 0x492f1 ; `tramp_cerror` 0x3d5a8 ; `_getattrlist$UNIX2003` 0x3dc08 ; `_lstat64` 0x3e3fc ; `_stat64` 0x3fb9c |
| `usr/lib/dyld` | `0f048c39017e6194581a5084d0bc0656b446f9743337cc66829dd4dc685b86ed` | `8e5d39fa6b349eb0047a1096848210e367158cca1e038ad189865c155eba91d5` | `__darling_bsd_syscall` 0xe7415 ; `tramp_cerror` 0xe10d4 ; `_realpath$DARWIN_EXTSN` 0xab410 ; `_getattrlist$UNIX2003` 0xe1244 ; `_lstat64` 0xe1418 ; `_stat64` 0xe18cc |

**Fait binaire relevé :** dans les deux tranches i386, les wrappers `getattrlist$UNIX2003`, `lstat64` et `stat64` appellent `__darling_bsd_syscall`, puis exécutent `jae` pour éviter la branche d'erreur ; les branches d'erreur utilisent des pointeurs/trampolines `cerror`. Par exemple, dans dyld, `0xe1249 calll 0xe7415` puis `0xe124e jae 0xe125e`; dans libsystem_kernel, `0x3dc0d calll 0x492f1` puis `0x3dc12 jae 0x3dc22`.

**Hypothèse statique forte :** le code source `bsd_syscall.S` épinglé exécute `addl $56,%esp` immédiatement avant `ret` en i386, écrasant les flags, dont CF. Si ce même code est présent dans les binaires, la condition `jae` du wrapper pourrait refléter une restauration de pile plutôt que la convention Darwin des erreurs BSD. La sortie V1-R2 ne publie que les deux premiers `nop` du dispatcher et **ne démontre pas encore** la présence exacte des instructions finales de ce dispatcher dans les binaires installés.

### Dernier contrôle requis pour V1

Lire des extraits ciblés du désassemblage **déjà généré**, autour de `__darling_bsd_syscall` et des wrappers `getattrlist$UNIX2003` pour **les deux tranches i386**. Observer impérativement le corps complet du dispatcher, le traitement effectif du résultat d'appel et les instructions de retour ; ne pas inférer un code binaire depuis la seule source. Un diagnostic V1 peut alors conclure statiquement (avec limites), sans prétendre qu'un défaut dynamique est prouvé avant un témoin d'erreur invité. Ne pas réextraire ni redésassembler les binaires si les fichiers existants sont intacts.

**Conservation :** cette note GitHub archive les sorties et empreintes textuelles publiées par l'opérateur, pas les exécutables ou logs bruts privés.
