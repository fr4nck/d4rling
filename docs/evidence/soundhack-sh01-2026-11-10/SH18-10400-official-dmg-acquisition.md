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
