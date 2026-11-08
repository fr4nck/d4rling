# QT-NEXT : NewMovieFromDataRef (référence pointeur) et GetMovieDuration

**Périmètre :** `NewMovieFromDataRef` accepte uniquement une référence de type
`'ptr '` (`PointerDataRefRecord`) contenant un fichier MOV complet ou un atome
`moov` seul. Le parseur privé QT-MOV-01 (`qt_mov_probe.c`, visibilité cachée)
lit `moov/mvhd` ; les octets ne sont pas conservés. `GetMovieDuration`
renvoie la durée lue (`TimeValue`, SInt32).

**Restrictions volontaires (non implémentées, pas de faux succès) :**
- flags non nuls : `unimpErr` (-4) ; autre type de référence : `cantFindHandler` (-2003) ;
  référence nulle ou vide : `invalidDataRef` (-2012) ;
- atomes tronqués/invalides, version ou échelle invalides : `badPublicMovieAtom` (-2002) ;
  pas de `moov`/`mvhd` : `noMovieFound` (-2048) ; durée hors SInt32 (dont la
  sentinelle « inconnue ») : `invalidDuration` (-2014) ; en cas d'échec `*m = NULL` ;
- `*id` n'est pas modifié : la documentation Apple (Movie Toolkit Reference,
  `NewMovieFromDataRef`) ne décrit `id` que pour les ressources de film ;
- `SetMovieTimeScale` ne rescale pas une durée non nulle : `unimpErr`, film inchangé ;
- aucune piste, média, échantillon PCM, lecture, ni référence handle/fichier/URL.

## Qualification (8 novembre 2026, 5700X, WSL2 Debian)

`witness.c` compilé en Mach-O i386 (clang 19, cctools ld64), exécuté sous
D4rling dans des namespaces privés, préfixes neufs (méthode Q-A3/Q-A4) :

| Essai | Résultat |
| --- | --- |
| Candidat `@loader_path`, 2 × normal + 1 × bypass | 5 118 contrôles, 0 échec |
| Candidat au chemin canonique du framework (overlay ro, empreinte vérifiée), normal + bypass | 5 118 / 0 |
| Mutant sans garde de durée | échoue (19) |
| `QuickTime.c` d'origine | échoue (5 075) |
| Témoin Q-A3 v2 (7 fonctions Q-A2), banc et chemin canonique | 62 / 0, mémoire stable |
| Framework sans QuickTime | `Library not loaded`, code 1 |

Framework candidat comparé à la référence Q-A4 : mêmes 4 600 exports,
mêmes dépendances, mêmes symboles non définis et commandes de chargement.
Le parseur reste qualifié sur hôte x64 (5 038 contrôles, ASan/UBSan).
**Non démontré :** construction par la cible CMake/ninja `QuickTime`
(composant `gui_stubs`), slice x86_64, applications réelles.

Code original GPL-3.0-or-later, préparé avec Claude Code pour fr4nck ; aucun
code ni média Apple incorporé.
