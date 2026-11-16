# SoundHack SH18 — acquisition authentifiée du DMG officiel 0.896 sur le 10400

**15 novembre 2026 — `SH18_DMG_EXTRACTED=PASS` (preuve transmise par le terminal de l'opérateur, Debian WSL2 i5-10400).**

## Inventaire préalable

Le prévol en lecture seule a examiné les répertoires existants `~/atelier`, `~/Downloads` et `~/Applications` (lorsqu'ils existaient), sans suivre les liens symboliques : `SH18_CANDIDATES=0`, `SH18_INVENTORY=READ_ONLY_COMPLETE`. Cela ne prouve **pas** l'absence de SoundHack dans tous les volumes ou emplacements Windows.

## Source officielle et archivage réel

La page officielle SoundHack annonçait un lien « Universal Binary » vers `http://tre.ucsd.edu/wordpress/wp-content/uploads/2016/12/SH896.dmg_.zip`. La voie HTTPS correspondante a été employée par l'opérateur :

`https://tre.ucsd.edu/wordpress/wp-content/uploads/2016/12/SH896.dmg_.zip`

L'archive acquise sous `~/atelier/d4rling-10400/validation/soundhack-sh18/SH896.dmg_.zip` a été vérifiée avec :

- **Taille** : 1 247 567 octets.
- **SHA-256** : `47c9596bcf9d6aa8ae98c0dd4231accf05cb5bff555a9b95f0ba70bb7db504ae`.
- **Structure ZIP** : `SH896.dmg` (1 361 910 octets), `__MACOSX/` (répertoire de métadonnées), `__MACOSX/._SH896.dmg` (1 866 octets, AppleDouble).
- Le premier script d'acquisition a échoué sans extraction, car il comptait les deux noms terminant par `.dmg`, dont le **fichier AppleDouble** ; statut `SH18_ACQUISITION=ZIP_ONLY`.

Le second script, **sans réseau**, a reconnu l'archive par son SHA-256, sélectionné exactement l'entrée `SH896.dmg`, vérifié le CRC ZIP et extrait exclusivement le véritable DMG dans :

`~/atelier/d4rling-10400/validation/soundhack-sh18/SH896-original.dmg`

- **Taille DMG** : 1 361 910 octets.
- **SHA-256 DMG** : `269b0446d45e6ab155c96c53bd89c4e69d709e28b29fae8837e9643b06fb25ee`.
- **Signature** : terminaison UDIF `koly` confirmée par lecture des 512 derniers octets.
- `file` décrit `zlib compressed data` ; cette étiquette seule n'implique pas l'absence d'un conteneur DMG, car la signature `koly` est constatée.

`7zz` / `7z` absents sur le 10400 à cette étape : `SH18_DMG_LIST=NOT_TESTED`, `SH18_APP_EXECUTED=NO`, `SH18_DMG_MOUNTED=NO`.

## Suite strictement ciblée

Lire le DMG avec l'outil Linux **portable officiel 7-Zip 26.06** (pas d'installation système), si son asset est téléchargeable depuis `ip7z/7zip`. L'archive x86-64 `7z2606-linux-x64.tar.xz` a une empreinte officielle `sha256:2b539cf067b2ad48e1baa5093dbaa8818b73542d1222a0ffde9dc5f2922ea62e`, vérifiée via les métadonnées GitHub de la release du **7 novembre 2026**.

Le Shell proposé conserve le nouvel exécutable portable et les fichiers extraits **exclusivement** sous `validation/soundhack-sh18/`, inspecte `SoundHack.app/Contents/MacOS/*` sans exécuter les binaires, puis qualifie séparément l'extraction et les architectures. La capacité d'extraction de ce DMG exact et les éventuels fichiers `.app` **ne sont pas encore démontrés**.

**Aucune modification de dépôt Git, build D4rling, installation historique, global Debian, source FFT ou système Windows.** Les sorties sont des observations du terminal de l'opérateur, pas une réexécution par GitHub/CI.

## Complément HFS+ / paquet hérité (preuve opérateur, 15 novembre 2026)

L'opérateur a téléchargé **7-Zip 26.06 Linux x64 portable**, à partir de
`ip7z/7zip`, et vérifié l'archive avant usage : SHA-256
`2b539cf067b2ad48e1baa5093dbaa8818b73542d1222a0ffde9dc5f2922ea62e`.
Le logiciel `7zz-26.06` a reconnu et listé le DMG :
`Type=Dmg`, flux `2.hfs` (8 265 728 octets),
`Type=HFS`, `Method=HFS+`. La liste montre un dossier
`SoundHack 0.896 - Universal Binary.pkg` sous le volume `SH896`.

Une tentative d'extraction globale dans
`validation/soundhack-sh18/SoundHack896-extracted/` a terminé avec
`Sub items Errors: 2`, correspondant exclusivement **dans la sortie
transmise** aux liens du paquet `Contents/Resources/` suivants :

- `SoundHack 0.896 - Universal Binary.bom` → `../Archive.bom` ;
- `SoundHack 0.896 - Universal Binary.pax.gz` → `../Archive.pax.gz`.

7-Zip a refusé ces liens avec `Dangerous link path was ignored` ;
cette défense n'a **pas été contournée**. Le script s'est arrêté sur
`SH18_APP=BLOCKED: 7zz extraction failed; destination retained`.
La destination et les fichiers présents sont préservés ; leur inventaire
complet n'a pas encore été relevé. **Aucun SoundHack.app extrait n'est
qualifié** et aucun lancement d'application ou test audio n'est revendiqué.

Le prochain essai évite de répéter l'extraction globale du DMG. Il doit
localiser le vrai `Contents/Archive.pax.gz` dans l'extraction partielle,
vérifier son format `cpio`/tar après décompression gzip, puis extraire
**uniquement** la famille `SoundHack*.app` dans un répertoire neuf avec
gardes sur chemins, symlinks, doublons et taille. Le préfixe privé et les
sources historiques de D4rling restent intacts.

Source technique : [Documentation historique Apple sur PackageMaker](https://leopard-adc.pepas.com/documentation/Darwin/Conceptual/KEXTConcept/KEXTConceptPackaging/packaging_kext.html)
(explique `Archive.pax.gz`, `Archive.bom` et `Contents/Resources`).

## SH18 — extraction contrôlée du véritable bundle Universal Binary (observation opérateur du 16 novembre 2026)

Le script `SH18_PAX`, exécuté **en lecture hors réseau** sur le 10400, a trouvé **une seule archive** du paquet de l'image partiellement extraite :

`SoundHack896-extracted/SH896/SoundHack 0.896 - Universal Binary.pkg/Contents/Archive.pax.gz`

- SHA-256 de `Archive.pax.gz` : `8896cf91dd4eab673f2b2d2fd1113aa6af260dd21ff70ccbc74c26cb37bca719`.
- Après décompression gzip : **1 658 199 octets**, structure **CPIO odc** (`070707`), **14 entrées**.
- Un seul bundle applicatif : `SoundHack.app` ; **8 fichiers ordinaires** extraits ; **0 lien symbolique** inclus dans ce bundle.
- Destination isolée : `~/atelier/d4rling-10400/validation/soundhack-sh18/SoundHack896-payload/SoundHack.app/`.
- Exécutable d'origine : `Contents/MacOS/SoundHack`, **Mach-O universel à deux architectures `ppc` + `i386`**, confirmé indépendamment par `file` et `llvm-lipo-19 -archs` dans le terminal.
- SHA-256 de cet exécutable universel : **`6fb11c708079ca3b8f91dc53ab0d8ae732fbb8be32f0e22e34114764b9be089c`**.
- Marqueurs de fin : **`SH18_PAYLOAD=EXTRACTED_FOR_REVIEW`**, **`SH18_APP_EXECUTED=NO`**.

**Statut acquis : `SH18_ORIGINAL_UNIVERSAL_APP_EXTRACTED_PASS` (preuve opérateur, non rejouée par l'agent).** Ce n'est ni la validation des dépendances Carbon/QuickTime/CoreAudio ni celle des ressources historiques du bundle (dont d'éventuelles resource forks), ni un démarrage de SoundHack.app. Le code de production D4rling, son préfixe, le build historique, le dépôt local et les autres travaux sont restés inchangés.

Suite ciblée **SH19** : auditer directement le `MH_EXECUTE` i386 interne au FAT, les commandes `LC_LOAD_DYLIB`, les ressources/Info.plist et la disponibilité des dépendances dans le sysroot privé. Ne pas supposer qu'une extraction de huit fichiers suffit à restituer les ressources Carbon ; ne pas déclarer un lancement applicatif avant un vrai essai invité borné.
