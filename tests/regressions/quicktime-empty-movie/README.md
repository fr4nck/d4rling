# Q-A2 — Movie vide et échelle de temps

Première implémentation bornée, base
`c07936a796727b8bf47d896875fc2382d50cbd28`.
Le code de production reste dans les deux fichiers QuickTime existants ;
aucun CMake ni autre sous-système n'est modifié.

## Contrat couvert

- `EnterMovies` initialise un environnement unique **non réentrant**.
  Les appels répétés sont idempotents et conservent les objets vivants.
- `NewMovie(0)` alloue un Movie vide, opaque (`struct MovieType**`),
  avec une échelle initiale de 600 unités/s. Tous les flags non nuls sont
  refusés avec `unimpErr` (-4), y compris une demande de movie actif.
- `GetMovieTimeScale` lit l'état propre à cet objet.
  `SetMovieTimeScale` accepte une valeur strictement positive ; l'objet
  vide n'a aucune durée, piste ni édition à rescaler. Valeur invalide :
  `paramErr` (-50), sans modification.
- `DisposeMovie` libère l'objet. `ExitMovies` libère les objets encore
  vivants et désinitialise ; la reprise repart à 600. Un arrêt répété est
  sans effet dans ce sous-ensemble.
- `GetMoviesError` renvoie **puis efface** l'erreur courante des fonctions
  implémentées. NewMovie sans initialisation : -2020 ; manque mémoire :
  -108 ; objet non possédé/NULL : -2010. Les autres stubs ne sont pas
  intégrés à cette gestion d'erreur.
- Types publics réutilisés : `TimeScale = SInt32`, `OSErr = SInt16`
  de MacTypes. Flags en SInt32 : largeur du long Darwin i386, même lors du
  banc LP64/LLP64 hôte. Liaison C explicite pour les sept fonctions.

Ce sous-ensemble ne fournit ni movie actif, time base générale, fichier,
piste, données, lecture audio/vidéo, interface ou transfert multithread.
La liste d'objets sert à la propriété mémoire/au nettoyage. Elle ne détecte
pas les pointeurs périmés dont l'adresse a été recyclée. Les handles ne
doivent pas être déréférencés/modifiés par le client ou partagés entre threads.

## Tests réellement exécutés

Windows x64, Python 3.11.9, MSVC 14.51.36231 :

- Avant : vrais source/header d'origine ; le test de création sans objet
  termine à 1. Les contrats C++ typés sont rejetés à la compilation.
- Après : **4 059 contrôles, 0 échec, 0 allocation vivante**, dont
  1 000 cycles créer/lire/modifier/détruire, deux objets indépendants,
  bornes de type, valeurs 600/44 100/INT32_MAX, erreurs consommées,
  refus de flags, échec d'allocation injecté, réinitialisation et nettoyage
  de ressources vivantes.
- Les contrats C++ utilisent les vraies déclarations et se lient au C
  de production. La suite C exécute les sept fonctions corrigées.

Le banc compile **tout QuickTime.c**, le vrai QuickTime.h et le vrai
MacTypes.h. Substitutions hôte identifiées dans `host/` :
ConditionalMacros, Availability, sys/types ; omission du seul attribut
constructor de STUB_VERBOSE ; malloc/free enveloppés pour compter les
allocations et injecter une panne. Aucune logique Movie n'est substituée.
Ce n'est pas un build Mach-O, un essai Darwin i386 ni une validation complète
des dépendances réelles de MacTypes.

## Reproduction

Les chemins désignent un checkout/copie **indépendant**, une copie de base
d'origine et les outils déjà installés. Le dossier résultat doit être neuf :

```powershell
python tests/regressions/quicktime-empty-movie/run.py --source CHEMIN_SOURCE_CORRIGEE --baseline CHEMIN_BASE_ORIGINE --mac-types CHEMIN_BASIC_HEADERS --out NOUVEAU_RESULTAT --vcvars CHEMIN_VCVARS64_BAT
```

Le runner refuse un résultat existant, ne télécharge ni n'installe rien.
Il charge l'environnement MSVC dans un processus enfant et écrit uniquement
dans le nouveau résultat. Les logs bruts contiennent des chemins locaux et
restent privés. Les fixtures `host/` ne doivent jamais entrer dans la
compilation de production.

## Contrats primaires et provenance

- [Apple, Initializing QuickTime](https://developer.apple.com/library/archive/documentation/QuickTime/Conceptual/QT_InitializingQT/InitializingQT/InitializingQTfinal.html) :
  initialisation préalable, EnterMovies répété sans équilibrage nécessaire.
- [Apple, Inside Macintosh: QuickTime](https://vintageapple.org/inside_r/pdf/QuickTime_1993.pdf) :
  défaut 600 et GetMoviesError consommant l'erreur courante.
- [Header Apple 10.5 Movies.h consulté](https://github.com/phracker/MacOSX-SDKs/blob/master/MacOSX10.5.sdk/System/Library/Frameworks/QuickTime.framework/Versions/A/Headers/Movies.h),
  blob consulté `38955205981b3d9ed35f538e40e9b0470edd0757` :
  type Movie opaque et contrats de la génération visée. Aucun SDK incorporé.
- [MacTypes du dépôt épinglé](https://github.com/fr4nck/d4rling/blob/c07936a796727b8bf47d896875fc2382d50cbd28/basic-headers/MacTypes.h),
  blob `cf1b240c0893cedccb92280c51a94a2253f1d984`.
- [Apple, codes Movie Toolbox](https://developer.apple.com/library/archive/documentation/QuickTime/RM/MovieBasics/MTEditing/L-Chapter/12MovieToolboxConstan.html) :
  erreurs et initialisation.
- [Apple, Movie Time and Space](https://developer.apple.com/library/archive/documentation/QuickTime/RM/MovieInternals/MTTimeSpace/B-Chapter/2MovieTimeandSpace.html) :
  échelle et changement de coordonnées temporelles.

Implémentation et tests originaux préparés avec OpenAI Codex pour fr4nck,
GPL-3.0-or-later ; notices existantes conservées. Aucun code Apple fermé,
média commercial ou code d'un autre projet copié. Les valeurs invalides et
flags non supportés sont les restrictions explicites de cette première
implémentation, sans prétendre reproduire tous les cas historiques.
