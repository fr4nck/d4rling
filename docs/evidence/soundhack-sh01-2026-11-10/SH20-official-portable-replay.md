# SoundHack SH20 — reprise portable de l'application officielle sur le 5700X

**16 novembre 2026 — lot logiciel prêt pour rejeu, pas encore de validation du vrai binaire sur le 5700X.**

## Objectif, contexte et réutilisation

Les preuves [SH17](SH17-10400-guest-fft-pass.md) qualifient la FFT
originale sur invité i386. [SH18](SH18-10400-official-dmg-acquisition.md)
démontre que l'installation 0.896 officielle contient un véritable
`SoundHack.app` universel PowerPC+i386, extrait avec 8 fichiers et un
exécutable SHA-256
`6fb11c708079ca3b8f91dc53ab0d8ae732fbb8be32f0e22e34114764b9be089c`.
SH19 a fourni un auditeur statique réutilisant `macho_audit.py`
([preuves](SH19-original-app-static-gate.md)), mais ce binaire historique
n'est prouvé présent **que sur le poste 10400**. Le 5700X dispose de
builds privés D4rling, pas d'une copie démontrée du paquet SH18.

Le livrable SH20 est
`reproduction/fixtures/soundhack-i386/sh20_official_replay.py` :
reconstruire l'application originale localement, dans **un stage privé neuf**,
avec extraction **uniquement de l'entrée HFS+**
`SH896/SoundHack 0.896 - Universal Binary.pkg/Contents/Archive.pax.gz`.
Cette sélection évite de rejouer l'extraction globale du DMG, qui échouait
sur deux symlinks `Contents/Resources` sans raison de les déverrouiller.

Les fichiers source SH20 sont indépendants du code de production et ne
modifient aucun build, préfixe, installation, sous-module ou fichier historique.
`experiments/petite-victoire/` est inchangé. Pas de redistribution
dans GitHub de SoundHack, de ses ressources, de l'archive officielle ou
d'un composant Apple propriétaire.

## Provenance et authentification

- ZIP officiel UCSD : `https://tre.ucsd.edu/wordpress/wp-content/uploads/2016/12/SH896.dmg_.zip`,
  SHA-256 `47c9596bcf9d6aa8ae98c0dd4231accf05cb5bff555a9b95f0ba70bb7db504ae`.
- Image `SH896.dmg` : **1 361 910 octets** ; signature UDIF `koly` ;
  SHA-256 `269b0446d45e6ab155c96c53bd89c4e69d709e28b29fae8837e9643b06fb25ee`.
- Payload original `Archive.pax.gz` : SHA-256
  `8896cf91dd4eab673f2b2d2fd1113aa6af260dd21ff70ccbc74c26cb37bca719`.
- Exécutable Mach-O universel `SoundHack.app/Contents/MacOS/SoundHack` :
  SHA-256 `6fb11c708079ca3b8f91dc53ab0d8ae732fbb8be32f0e22e34114764b9be089c`.
- 7-Zip 26.06 portable GNU/Linux x86_64 :
  `https://github.com/ip7z/7zip/releases/download/26.06/7z2606-linux-x64.tar.xz`,
  SHA-256 `2b539cf067b2ad48e1baa5093dbaa8818b73542d1222a0ffde9dc5f2922ea62e`.

Les cinq empreintes sont exigées. Une différence arrête le lot,
sans remplacement silencieux. Le seul exécutable hôte utilisé pour
l'extraction est le 7zz issu de son archive épinglée ; il ne lance
aucun code Mac du fournisseur. L'ancien format `CPIO-ODC` est
parsé en Python standard avec limites de taille, chemins strictement
relatifs, aucune extraction de liens symboliques et **huit fichiers**
comme inventaire historique observé. SH19 valide ensuite architecture
i386/PPC, `MH_EXECUTE`, `Info.plist` et dépendances.

## Tests réellement exécutés

- Syntaxe Python : PASS (`python3 -m py_compile` sur les deux nouveaux fichiers).
- `python3 -B -m unittest -v test_sh20_official_replay` :
  **19 tests, 19 PASS** dans l'environnement de test distinct.
- Couvre ZIP AppleDouble ignoré, DMG manquant/tronqué, signature UDIF,
  CPIO ODC malformé/tronqué, chemin traversant, lien symbolique,
  doublon, hash exécutable incorrect, mauvais binaire 7zz,
  archive 7zz conforme, sortie exclusive, sysroot manquant,
  HFS symlink bloqué et parcours intégré **simulé** jusqu'à
  SH19 (témoin de rapport JSON simulé).
- Les contenus d'essai sont **synthétiques** :
  aucune vraie archive SoundHack ni HFS original n'a été rechargé
  dans cet environnement. Les fonctions de téléchargement officiel,
  la lecture 7zz HFS+ réelle sur 5700X et le parseur SH19 sur le
  **véritable** exécutable ne sont **pas** validés par ces 19 tests.
- La conformité de l'extraction des fourches de ressources historiques
  (Resource Fork) n'est pas démontrée.

## Reprise ciblée / barrière de fin

Exécuter une fois le bloc Bash de reprise publié dans la conversation
sur **Debian WSL2 du 5700X**, avec
répertoire `/home/Deniel/d4wrling-work/validation` existant.
Le bloc télécharge explicitement les scripts SH20/SH19 et l'auditeur
Mach-O depuis un commit SHA immuable, valide leur hash Git blob,
puis, **sans installation système**, télécharge les deux archives
officielles avec leurs SHA-256 épinglés. Pas de Git pull/rebase/reset,
pas de compilation, pas de guest run, pas d'écriture hors du stage,
sauf la copie du rapport dans le presse-papiers Windows.

Condition SH20 finale : `SH20_OFFICIAL_APP_REPLAY_STATIC_PASS`
et empreinte du véritable Mach-O identique à SH18, avec une liste
de dépendances **observée sur le 5700X**. Tout échec d'un accès réseau,
d'une archive ou de SH19 demeure `BLOCKED` et n'autorise pas SH-LOAD.
Le prochain chantier après ce résultat : sélectionner **le premier
blocage applicatif i386 authentifié** et construire un témoin invité borné ;
ne pas toucher aux lots Logic/Carbon/QuickTime/audio détenus par d'autres.

**Niveau de preuve de la publication : `SH20_TOOL_SYNTHETIC_19_PASS` ;
`REAL_APP_5700X=NOT_RUN` ; `SH_LOAD=NOT_RUN` ; `GUI=NOT_RUN` ;
`DSP=NOT_RUN` ; `AUDIO=NOT_RUN`.**
