# SoundHack SH16 — liaison Mach-O i386 réelle sur le i5-10400

**Observation transmise par l'opérateur le 10 novembre 2026 ; consignée le 15 novembre 2026.**
**Qualification : `SH16_MACHO_I386_DYLIB_EXPORTS_PASS` (compilation, liaison et contrôles structurels bornés).**
**Pas de lancement dans l'invité D4rling, de SoundHack.app ni de sortie audio.**

## Chaîne effectivement exercée

- Machine : Intel Core i5-10400, Debian WSL2, espace Linux existant `~/atelier`.
- Dépôt canonique local : `fr4nck/d4rling`, `master@3f103d08f4d1ef32a655aac49972c9481977454b`. Ce n'est pas le HEAD distant actuel.
- Reconstruction historique protégée : `d4rling-10400/source@b7d0cb6a79fe196657deb9711647f8486bcc5e5e`, sous-module `darlinghq/cctools-port@d9456c221e1f462e17c0b3297748bc089d5a861e`.
- Lieur ELF64 natif du build historique : `build-core-i386/src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld`, SHA-256 `b88aea04e3166e3cc677bc7b4b934ee8010bba351a9b14984f71a84b19ba5faf`.
- SDK Apple absent/non requis. Sources authentiques `tomerbe/SoundHack@df6f0bc89243b93573b391afa5ab371cce56ac95`, `Math/FFT.c` (blob Git `b132ab450a71b451f5ae9e5649c98a6a41c9f9e9`) et `FFT.h` (`f31c2d41526d3768ad7cb0f10993847d2bd6ae84`), récupérées et validées par hash pendant SH16. Pas de redistribution de ces sources dans D4rling.
- Objets compilés Darwin i386 : `FFT.o` **3 236 octets** et `globals.o` **384 octets**, avec les constantes originales déclarées par le témoin. `InitFFTTable`, `FFT` et `RealFFT` restent les fonctions originales de Tom Erbe.
- `libSystem.B.dylib` de l'installation privée historique : Mach-O universel avec tranche i386, vérifiée par `llvm-lipo-19`.
- Liaison effective : le vrai lieur cctools exécuté sur ces deux objets et le `libSystem` privé, code **0**. Sortie exclusive dans `d4rling-10400/validation/soundhack-sh16/libSoundHackFFT_i386.dylib`, **8 688 octets**, SHA-256 `c578572e4679985a76d79c61717a5339799c3e638d0347963f130df38db76ed1`.

## Contrôles et limites des preuves

Le premier script SH16 s'était arrêté sur un faux négatif : `llvm-objdump` imprimait `OBJECT` alors que le script cherchait littéralement `MH_OBJECT`. Le second script a directement vérifié l'en-tête Mach-O sur les objets (`filetype=1`), puis sur la dylib (`filetype=6`), confirmé la tranche i386 et retrouvé les exports `_FFT` et `_RealFFT`. La sortie du terminal transmis donne :

```text
SOURCE_PIN_PASS: FFT.c
SOURCE_PIN_PASS: FFT.h
MACHO_I386_HEADER_PASS: FFT.o, filetype=1, bytes=3236
MACHO_I386_HEADER_PASS: globals.o, filetype=1, bytes=384
FFT_OBJECT_AND_EXPORTS=PASS
SH16_STAGE=REAL_LINK
LD_EXIT=0
MACHO_I386_HEADER_PASS: libSoundHackFFT_i386.dylib, filetype=6, bytes=8688
SH16_MACHO_I386_DYLIB_EXPORTS_PASS
c578572e4679985a76d79c61717a5339799c3e638d0347963f130df38db76ed1
GUEST_EXECUTED=NO
SOUNDHACK_APP_EXECUTED=NO
AUDIO_TESTED=NO
```

**Nature de la preuve :** résultat directement fourni par l'opérateur depuis le 10400 ; l'agent n'a pas eu accès à cette machine, ni revérifié les octets de la dylib. Les vérifications d'en-tête et d'exports sont bornées : elles ne prouvent pas le chargement dynamique effectif, la résolution de tous les symboles à l'exécution ni la précision numérique.

Le `master` distant et le dépôt historique n'ont pas été modifiés par ces scripts. Aucun quatrième projet à la racine de `~/atelier`, aucune installation globale, aucun nettoyage destructif et aucune écriture sur volume Windows.

## Jalon suivant, sans nouveau système parallèle

**SH17** doit exécuter un témoin i386 lié explicitement à la dylib SH16 en réutilisant le vrai `reproduction/run-guest.sh` et le préfixe privé historique. Le témoin doit appeler `InitFFTTable`, `FFT`, `RealFFT`, vérifier des oracles numériques indépendants, puis signaler séparément le chargement invité et le calcul. Résultat **`SOUNDHACK_SH17_GUEST_FFT_PASS`** exclusivement après le code retour invité et les marqueurs réels. Les rapports de tests du 10400 doivent rester étiquetés « observation opérateur » tant que non rejoués.
