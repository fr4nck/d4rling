# Q-A2 — preuve du sous-ensemble Movie vide

**8 novembre 2026.** Base publique :
`c07936a796727b8bf47d896875fc2382d50cbd28`.
[Contrat, limites et reproduction](../../tests/regressions/quicktime-empty-movie/README.md).

| Vérification | Résultat |
| --- | --- |
| Contrats typés C++ sur le header d'origine | FAIL attendu, compilation code 2 |
| NewMovie original, appelé avec sa déclaration d'origine | FAIL attendu, programme code 1 (NULL) |
| Vrai QuickTime.c corrigé, suite C et contrats C++ | Compilation et lien code 0 |
| Suite sur les sept fonctions corrigées | **4 059 contrôles / 0 échec**, code 0 |
| Allocation/échec d'allocation/nettoyage ExitMovies | **0 allocation vivante** au terme de la suite |
| ABI/runtime Darwin i386, fichier, pistes, lecture ou Player | **NON TESTÉS** |

Il existe un vrai état alloué par NewMovie, lu/modifié par Get/SetMovieTimeScale,
puis libéré par DisposeMovie ou ExitMovies. Les objets sont indépendants.
La valeur initiale 600 n'est pas un retour constant du getter. Les options
non supportées échouent sans allocation ; les erreurs sont observables et
GetMoviesError les consomme.

La compilation utilise les vrais source/header complets et MacTypes du dépôt,
avec seulement les dépendances de plateforme hôte identifiées par le README.
Tous les autres corps de fonctions/stubs sont conservés à l'identique.
Aucun importeur MOV ni nouvelle dépendance de production.

Les trois lancements du runner sont conservés : les deux premiers ont
échoué avant compilation (chargement de l'environnement MSVC puis résolution
de cl.exe) ; le runner a été corrigé. Le troisième exécute la série complète
ci-dessus sans modification de production entre ces lancements.
Les logs/objets locaux ne sont pas candidats à publication.

Cette preuve complète Q-A1 : le défaut de contrat alors constaté est corrigé
pour ce sous-ensemble. L'oracle de métadonnée Q-A1 reste un banc séparé sans
importeur. La compatibilité QuickTime/QTKit/Player, Logic et Petite Victoire
ne sont pas revendiquées. Aucun composant partagé ni produit Petite Victoire
n'a été modifié.

**Suite utile :** qualifier compilation/export puis exécution de ce même
cycle en Mach-O i386 dans un espace isolé existant ; aucun nouveau backend,
codec ou importeur n'est nécessaire pour ce prochain contrôle.
