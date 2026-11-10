# SoundHack SH13 — chemins réels du lieur cctools-port Darwin i386

**10 novembre 2026. Statut : CORRECTION DU REPÉRAGE / TESTS HÔTE PASS.**
**Aucune liaison Mach-O i386, exécution invitée ou sortie audio qualifiée.**

## Défaut confirmé dans SH12

Le sous-module canonique de D4rling est `darlinghq/cctools-port@d9456c221e1f462e17c0b3297748bc089d5a861e`.
Son fichier [`cctools/ld64/src/ld/Makefile.am`](https://github.com/darlinghq/cctools-port/blob/d9456c221e1f462e17c0b3297748bc089d5a861e/cctools/ld64/src/ld/Makefile.am) contient `bin_PROGRAMS = ld`. C'est ce sous-répertoire qui construit le programme, non directement `cctools/ld64/src`.

Avant SH13, `sh12_cctools_replay.py` ne consultait que les niveaux parents `.../ld64/src` (ainsi que leurs variantes de racine). Un vrai lieur construit sous `.../ld64/src/ld/ld` pouvait donc être présent mais non découvert, conduisant à un faux `LINKER_ABSENT`.

Le build utilise également Libtool pour l'édition de liens : selon la configuration, `.../src/ld/ld` peut être un script enveloppe et le véritable exécutable ELF se trouver dans `.../src/ld/.libs/ld`. **Il s'agit d'un emplacement à rechercher, pas d'un chemin observé lors d'une construction réelle dans ce conteneur.**

## Correctif borné

Les 4 chemins de recherche SH12 existants sont conservés et 8 emplacements sont ajoutés (4 racines × `src/ld` et `src/ld/.libs`) ; seul l'ordre de détection change. Aucune compilation ni recherche récursive du domicile n'est ajoutée. Les protections existantes demeurent : chemin dans l'arbre cctools-port désigné, fichier régulier non symbolique, exécutable ELF64 pour l'architecture hôte, hachage SHA-256, refus de candidats multiples, puis appel au contrôle de liaison SH11 strict.

Fichiers modifiés : `reproduction/fixtures/soundhack-i386/sh12_cctools_replay.py`; nouveau test `test_sh13_ld64_build_paths.py`. Pas de changement à CarbonCore, QuickTime, BSD, CoreAudio, Logic ou Petite Victoire.

## Exécution et preuves (hôte Linux isolé, sans 5700X)

- **8/8 tests SH13 PASS** : nouvelle sortie `src/ld/ld`, alternative `.libs/ld`, disposition CMake historique et build Autotools séparé, rejet d'un script enveloppe, refus de symlink, non-sélection ambiguë et compatibilité des anciens chemins.
- **Suite SH09–SH13 : 85/85 PASS, 0 FAIL, 0 SKIP**, avec le véritable objet SH08 et le ZIP SH10 épinglé fournis localement ; Python 3.13 et outils de compilation préinstallés. Les tests de découverte SH13 utilisent des **en-têtes ELF synthétiques jamais exécutés** ; ils ne prouvent ni provenance du lieur ni résultat de liaison.
- `python -m py_compile` des deux fichiers SH13 : PASS.
- Aucun cctools `ld64` utilisable n'a été trouvé sur cet hôte ; aucune nouvelle `MH_DYLIB` i386 ni exécution invitée n'a été produite.

### Reproduction

Bash, depuis le checkout canonique de D4rling sur Linux ou WSL2, sans installation ni accès réseau :

```sh
python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 \
  -p 'test_sh13_ld64_build_paths.py' -v
python3 reproduction/fixtures/soundhack-i386/sh12_cctools_replay.py \
  --sh10-package /authorized/path/d4rling-SH10-archive-i386.zip \
  --build-root /authorized/existing/build-core-i386
```

La seconde commande est la vérification effective et inchangée de SH12 : sans vrai lieur elle doit retourner `LINKER_ABSENT` (code 3). Un candidat identifié par son chemin et son SHA-256 n'est pas encore une preuve de provenance du sous-module. `LINK_STRUCTURE_PASS` ne vaut qu'après une vraie liaison et un contrôle Mach-O strict, jamais un PASS SoundHack invité ou audio.

## Prochain obstacle matériel

Un `ld64` construit depuis ce sous-module et disponible dans **le même environnement** que le ZIP SH10 reste nécessaire. Le rapport [10400 WSL2 core i386](../../qualification/10400-wsl2-core-i386-2026-11-10.md) atteste la compilation `mldr32`, mais **n'atteste aucune construction de cctools ld64**. Ne pas inférer ce dernier de la présence d'un build CMake fonctionnel.

Aucune modification aux sources cctools-port, aucun téléchargement, installation système, nettoyage de checkout ou essai sur le 5700X n'a été effectué.
