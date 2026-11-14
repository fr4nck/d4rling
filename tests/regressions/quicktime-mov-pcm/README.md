# QT-MOV-02 / E3-A : PCM possédé par les objets Movie

`NewMovieFromDataRef` (référence pointeur) copie la piste PCM prise en charge
dans une mémoire appartenant au Movie, libérée par `DisposeMovie` et
`ExitMovies`. Aucune API publique nouvelle, aucun export : l'extracteur privé
`qt_mov_pcm.c` (visibilité cachée) réutilise `qt_mov_probe.c`. La copie est
bornée par le tampon de l'appelant. Un film sans PCM exploitable s'ouvre comme
avant, sans échantillons. Échec d'allocation : `memFullErr` (-108), sans film
ni allocation orpheline. Aucun son n'est joué. À cette date, `GetMediaSample`,
`GetTrackMedia` et `GetMovieIndTrack` étaient des stubs ; ils ont été
implémentés depuis ([pistes](../quicktime-tracks/README.md),
[B11E](../quicktime-getmediasample-b11e/README.md)).

Sous-ensemble PCM : une piste `soun`, `stsd` v0 `twos`/`sowt` 16 bits,
1-2 canaux, fréquence entière égale à l'échelle `mdhd`, une entrée `stts`
(durée 1) et `stsc`, `stsz` constant = octets par frame (la valeur héritée 1
est refusée), un seul `stco` dans un `mdat`.

`witness.c` est un témoin boîte blanche : il lit la disposition privée
`qt_movie_internal.h`, sans fonction exportée. `test_mov_pcm.c` qualifie
l'extracteur seul.

Qualification du 9 novembre 2026 (5700X, WSL2) : natif Linux x64 avec
ASan/UBSan/LSan et injection d'échecs d'allocation, 46/0, extracteur 20 103/0 ;
Mach-O i386 sous D4rling, 38/0 (2 normal, 1 bypass), mémoire stable après
1 000 cycles et `ExitMovies` ; non-régressions QT-NEXT 5 118/0 et Q-A3 v2 62/0 ;
mutant sans conservation et mutant alias détectés ; 4 600 exports identiques
à la référence Q-A4. Cible CMake/ninja `QuickTime` non construite (BLOCKED).

## R3 : références de données (9 novembre 2026)

L'extraction n'a lieu que si le descriptif `stsd` a ses six octets réservés
nuls et si son `dataReferenceIndex` (base 1) désigne, dans `minf/dinf/dref`,
une entrée version 0 de type `alis` ou `url ` portant exactement le flag
self-reference `0x000001` (QTFF, Data Reference Atoms). Une référence externe
n'est jamais suivie, même si `stco` pointe vers le `mdat` local : le Movie
s'ouvre alors sans échantillons, durée et échelle inchangées.
Mal formé (`BAD_MOVIE`) : octet réservé non nul, index 0 ou hors table,
`dinf`/`dref` absent, nombre d'entrées incohérent, entrée tronquée.
Non pris en charge (`UNSUPPORTED`) : en-tête `dref` de version ou flags non
nuls ; entrée de version différente de 0 ou flags différents de `0x000001`
(dont toute référence externe) ; type `rsrc` ou autre. La documentation lue ne dit pas
ce que contient une self-reference : ses données éventuelles sont ignorées.

Qualification R3 : extracteur 20 149/0 et témoin Movie 48/0 en natif
(ASan/UBSan/LSan, injection d'allocations) ; Mach-O i386 sous D4rling 40/0
(normal et bypass) ; QT-NEXT 5 118/0 ; Q-A3 v2 62/0 ; mutants « flag
self-reference ignoré » et « référence non résolue » détectés en natif, le
premier aussi en i386 ; 4 600 exports identiques à la référence Q-A4.
