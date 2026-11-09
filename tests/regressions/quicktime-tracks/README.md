# QT-MOV-02 / E3-B1 : pistes et médias

`GetMovieTrackCount`, `GetMovieIndTrack`, `GetTrackMedia`,
`GetMediaSampleCount` et `GetMediaTimeScale` suivent les contrats Apple
(QuickTime Movie Track and Media Reference ; « Locating Tracks ») : index de
piste de 1 au nombre de pistes, NIL quand la piste ou le média est introuvable.
Types du SDK 10.5 : `Track` = `struct TrackType **`, `Media` =
`struct MediaType **`. Apple déclare les compteurs et l'index en `long`
(32 bits en Darwin i386) ; le header D4rling emploie `SInt32` pour garder
cette largeur sur un hôte LP64.

Toutes les pistes `moov/trak` sont listées dans l'ordre du conteneur, quel que
soit leur type, par `d4rl_qt_mov_list_tracks` (extension privée de
`qt_mov_pcm.c`). Un média existe quand `mdia` contient `hdlr`, `mdhd` (échelle
1..INT32_MAX) et un `minf/stbl/stsz` bien formé : version et flags nuls, table
de tailles présente exactement quand la taille d'échantillon vaut 0, avec une
entrée de 4 octets par échantillon (R1, contrôle par division, sans lecture
des entrées). Son nombre d'échantillons est le compte `stsz`. Un `stsz` mal
formé laisse la piste listée, sans média (`invalidMedia`). Compter des pistes vidéo n'implique aucun codec ni aucune lecture.
Track et Media sont des handles stables pendant la vie du film, retrouvés par
comparaison d'adresses (jamais déréférencés s'ils sont inconnus) et invalidés
par `DisposeMovie` ou `ExitMovies`.

Codes d'erreur (non documentés par Apple pour ces fonctions, choix D4rling) :
index hors 1..n `badTrackIndex` (-2028) ; piste inconnue `invalidTrack`
(-2009) ; piste sans média ou média inconnu `invalidMedia` (-2008) ; table
des pistes illisible alors que le film s'ouvre `badPublicMovieAtom` (-2002)
avec 0 piste ; environnement non initialisé -2020.
Limite : une adresse libérée puis réutilisée peut désigner un nouvel objet,
comme pour Movie (Q-A2).

Qualification du 9 novembre 2026 : natif ASan/UBSan/LSan avec injection
d'échecs d'allocation 69/0 ; Mach-O i386 sous D4rling 61/0 (normal et
bypass) ; non-régressions E3-A R3, QT-NEXT et Q-A3 v2 ; mutants
d'association piste/média détectés ; 4 600 exports inchangés.
