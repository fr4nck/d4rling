# SoundHack SH10 — archive statique Darwin i386, sans liaison dynamique

**10 novembre 2026 — `DARWIN_ARCHIVE_PASS` (hôte Linux, structure seulement).**
Le jalon **ne valide ni** une dylib Mach-O liée, ni le démarrage de SoundHack,
ni une ABI exécutée dans D4rling, ni une sortie audio, ni Logic Studio 8.

## Entrées et provenance

- Source FFT originale de Tom Erbe, SoundHack 0.896, licence MIT :
  `tomerbe/SoundHack@df6f0bc89243b93573b391afa5ab371cce56ac95`.
  Les fichiers `Math/FFT.c` et `FFT.h` d'origine restent **hors du dépôt**.
- Objet SH08 authentique et inchangé : `i386-apple-darwin9`, `MH_OBJECT`,
  3 236 octets, SHA-256
  `c5e059e4ce39e2f1b95a925d0eebcac09ded0c36748db0e422b1bca3b7ee1409`.
- Réutilisation de `i386_link_gate.py` SH09 pour le contrôle de l'objet,
  la compilation des constantes `Pi` et `twoPi` et la validation de sortie
  de liaison, et de `macho_audit.py` pour l'inspection Mach-O.
- Sous-module canonique `src/external/cctools-port` :
  `darlinghq/cctools-port@d9456c221e1f462e17c0b3297748bc089d5a861e`.
  Sa documentation reconnaît le support de la cible i386, mais **aucun
  exécutable cctools ld64 local n'est disponible dans le conteneur de test**.

## Résultats réellement exécutés

Outils préinstallés du conteneur isolé : Clang 17, LLVM `llvm-ar` et
`llvm-objdump` 17, Python 3.13.5. Aucun paquet installé, téléchargement,
5700X, WSL2, SDK Apple, système invité ou modification des sources originales.

`llvm-ar --format=darwin rcD` a produit une vraie archive statique Darwin,
`!<arch>`, avec un index `__.SYMDEF`. Le contenu a été relu par `llvm-ar`,
`llvm-objdump` et le lecteur Mach-O de D4rling :

| Propriété | Observation |
| --- | --- |
| Archive statique | `libSoundHackFFT_i386.a`, 4 000 octets |
| SHA-256 d'archive | `c11833539630b5aa70d6d63a44d4063eb11a12f0f316884094b0b64f38707169` |
| Premier membre | `fft.o`, objet original 3 236 octets, six définitions FFT |
| Deuxième membre | `globals.o`, objet i386 de 384 octets, définitions `_Pi`, `_twoPi` |
| Alignement Darwin | le membre FFT est stocké avec quatre octets `0x0a` de remplissage ; son préfixe original est inchangé |
| Indéfinis restant après rapprochement | `_sin`, `_sinf` |
| Reproductibilité | deux constructions indépendantes : archives byte-identiques |
| Lien dynamique | `LINK_TOOLCHAIN_BLOCKED`, aucun MH_DYLIB produit |

**Attention :** `llvm-ar p` renvoie un objet FFT de 3 240 octets à cause du
remplissage Darwin (4 retours ligne). Le SHA-256 du **préfixe original** reste
`c5e059...1409`. Prendre naïvement le SHA-256 de l'objet extrait (avec son
remplissage) ferait annoncer à tort une mutation. Le code vérifie
explicitement les octets originaux et le remplissage autorisé.

Tentative réelle de liaison par le seul lieur disponible :

    ld64.lld: error: missing or unsupported -arch i386

L'interface du script accepte le chemin d'un **véritable** cctools-port
`ld64` déjà compilé ; ce chemin n'a pas été testé ici. Le mode `--ld64`
utilise `-arch i386 -dylib -macosx_version_min 10.5 -undefined dynamic_lookup
-install_name ... -all_load` pour obliger le lieur à incorporer les deux
membres. Même si un lieur annonçait zéro, il n'y aurait PAS de PASS sans
une bibliothèque i386 correctement structurée. Une sortie avec `LC_DYLD_INFO`
non décodée reste `LINK_UNVERIFIED` (code 3), jamais un PASS de résolution
ABI. Le test de faux lieur sans sortie est détruit.

## Qualification et contre-épreuves

- **20/20 SH10 tests PASS** : archive Darwin, ordre et identité des membres,
  index de symboles, conservation de l'objet original, déterminisme,
  faux archiver, faux lieur (sans fichier / fichier non Mach-O),
  mauvaise architecture, empreinte différente, membre altéré,
  index non Darwin, contrôle des arguments transmis à cctools, refus
  d'écraser un fichier ou lien symbolique, absence de compilateur et
  refus réel de `ld64.lld` 17 ; témoin SH08 original exécuté.
- **41/41 tests SH09 + SH10 PASS**, sans SKIP ni échec dans le conteneur
  possédant l'objet SH08. Aucun des tests ne prétend que SoundHack a démarré.
- Pas de nouvelle dépendance Python ni moteur d'archivage Mach-O parallèle.
- Script et tests Python compilés (`py_compile`) avec succès.

## Reproduction (Bash Linux, checkout canonique D4rling)

Prérequis : objet i386 authentique SH08 déjà obtenu et SHA-256 confirmé ;
Clang, Python 3, `llvm-ar`, `llvm-objdump` préinstallés. Les chemins suivants
sont indicatifs, sans téléchargement ni installation implicite :

    export SH08_I386_OBJECT=/authorized/path/original-sh08-target.o
    python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 -p 'test_darwin_archive_gate.py' -v
    python3 reproduction/fixtures/soundhack-i386/darwin_archive_gate.py \
      --object "$SH08_I386_OBJECT" --output /authorized/new/FFT-i386.a

`--output` est facultatif et **crée exclusivement** un chemin nouveau.
Le mode par défaut efface les objets temporaires. Pour tenter un lieur
cctools-port déjà accessible depuis le même environnement :

    python3 reproduction/fixtures/soundhack-i386/darwin_archive_gate.py \
      --object "$SH08_I386_OBJECT" --ld64 /authorized/canonical/build/path/to/ld64

Codes de sortie : `0` pour `DARWIN_ARCHIVE_PASS` (ou une liaison structurelle
vérifiée sans dyld info opaque), `2` pour contrat invalidé, `3` pour entrée,
compilateur, outil ou liaison inconclusive. **Une archive de 4 Ko n'est ni
une dylib chargeable ni un programme i386 exécutable.**

## Passage à SH11

Ne pas improviser un nouveau lieur ni modifier les frameworks partagés.
Le prochain test positif de liaison réclame un cctools-port ld64 véritable,
provenant d'un build D4rling cohérent, accessible au même hôte que les objets.
L'objet FFT et l'archive SH10 peuvent ensuite entrer dans l'interface de
qualification existante. Même en cas de liaison réussie, l'exécution invitée
et le son réel sont des jalons indépendants. L'issue CarbonCore `#13` reste
à traiter par son propriétaire, notamment le sélecteur `gestaltCarbonVersion`.
