# CarbonCore I2-C — liaison des trois unites de production et API publiques (12 novembre 2026)

## Provenance

Depot : `fr4nck/d4rling`, branche unique `master`.
Sources authentiques compilees sur runner Linux GitHub Actions : `MacMemory.cpp`, `ResourcesImpl.cpp`, `Resources.cpp`.
En-tete public : `src/frameworks/CoreServices/include/CarbonCore/Resources.h` conserve, non remplace par une API simulee.
Adaptations exclusivement hote : `FSRef`/noms de forks, signatures xattr Darwin, types transitifs non disponibles sur Linux. Le compilateur inclut `cstring` pour compenser la transitivite Darwin ; les comparaisons signe/non signe sont avertissements, pas erreurs de ce banc.
Aucune installation 5700X ou 10400 modifiee.

## I2-C1 — recherches publiques et ResError

- Premier banc publie : `ef3cb9fcb41f0a5f02bf2ea2b1a150035eec79c2`.
- Qualification de base reelle, CI `43221391104` : **25 PASS, 5 FAIL**, GCC 14 host `-O0`, ASan/UBSan. Deux erreurs etaient des attentes incorrectes du temoin : type manquant = `resNotFound` ; index nul = `inputOutOfBounds`. Trois erreurs etaient des etats `ResError` non remis a zero apres succes.
- Correction de production `8b1c1da648fc506570f2f79fa1b6b93f27a57cbb` : `CountResources`, `GetResource`, `Get1Resource`, `GetIndResource`, et chemins de recherche utilisant `getHandle()` propagent explicitement l'etat de succes/echec. Le temoin controle recherches par ID et nom, deux forks, alternance des types, fichier courant, `SetResInfo`, caches et erreurs.
- Commit de synchronisation du runner : `7591822585b26b3b04f3eba2aebc3c139cb5013f`.
- **CI `43221597846` PASS : 30/30 GCC `-O0` + 30/30 GCC `-O2` + 30/30 Clang `-O0` + 30/30 Clang `-O2` = 120 assertions positives, ASan/UBSan.** Log GitHub Actions conserve.
- Limitations : pas de test de collision ID/nom, d'echec d'allocation cible, de mutation negative, ni de Mach-O i386. Tests C1 sur fork synthetique, pas de vrai fichier historique Apple.

## I2-C2 — SetResLoad et LoadResource

- Temoin de chargement differe ajoute dans `f05e0569a9c70ed79fb4527bf5cc72de907f7413`.
- **CI `43222067227` FAIL attendu au linker** : trois `undefined reference to LoadResource` avec les vraies unites M2/R2/Resources. L'absence d'implementation n'est plus seulement une deduction statique.
- Candidat correctif source : `c8c4dd67c14baa377fb5d6d693b5f074efeac8db`. `getHandle(bool loadData=true)` conserve le comportement I1 par defaut. Les recherches publiques respectent `SetResLoad(FALSE)` et creent un vrai master pointer vide via `NewEmptyHandle()` de M2. `LoadResource` charge le contenu via `ReallocateHandle()`, conserve le master pointer en cas de purge et propage les erreurs.
- Runner CI repointe sur ces blobs et rejeu I1 integre dans `28a47191ace482495e3c9482959281f1dbc4244e`.
- **CI `43222535745` PASS (controle des logs GitHub) : 44/44 assertions I2-C1+C2 × GCC/Clang O0/O2 = 176/176 PASS, et I1 54/54 × 4 = 216/216 PASS. Total 392 assertions reussies, ASan/UBSan. Le test utilise de vraies unites C++ avec adaptations FSRef/xattr hote. Aucune preuve Mach-O i386 ou application reelle.**

## I2-C3 — API publique de persistance (CI `43223510649`)

- Commit de test `68f3c88e83ca7116cee5dcd21ace62f0cd3bed77`.
- Compilations et liens reels des trois unites de production reussis sous GCC/Clang `-O0/-O2` avec ASan/UBSan.
- **62/62 assertions par configuration, soit 248/248 PASS**, plus rejeu I1 **54/54 par configuration, soit 216/216 PASS** : total 464 PASS.
- Les API `ChangedResource`, `WriteResource`, `UpdateResFile`, `ReadPartialResource`, `WritePartialResource` et la reouverture d'un fork synthetique sont exercees. Les tests controlent les octets relus du disque, l'absence de mutation du handle lors de l'ecriture partielle, les bornes et le rejet des ecritures sur fork en lecture seule.
- Aucun correctif supplementaire de production n'a ete necessaire pour ce parcours.
- Les cas de panne physique d'ecriture, de concurrence et de vrais resource forks Apple demeurent ouverts ; ne pas transformer le resultat en qualification Mach-O i386.

## I2-C4 — symboles publics d'appartenance et de taille

- Consultation Apple Resource Manager : `HomeResFile` retourne le numero du fichier de ressource ; `GetResourceSizeOnDisk` mesure la taille exacte sur disque ; `GetMaxResourceSize` lit la taille en memoire (ou calcule une approximation depuis la resource map lorsque dechargee). Un handle invalide renvoie respectivement -1 / -1 avec `resNotFound`.
- Baseline test `5d0a6081167f46a85c8400f267e709bd3d179643`, CI `43223822145` : **echec au linker sur les trois fonctions**, references non resolues dans le vrai assemblage hote. Ne pas le compter comme test positif.
- Candidat production `fa82b561a172271e6f5f71bdf7aa8a158d41acef` : implementations reelles et controle taille memoire 5 octets / disque 3 octets avant persistance. La qualification sur la CI `43224272183` est encore ouverte au moment de cet ajout.

## Portes encore ouvertes

1. I2-C1/C2 hote : matrice GCC/Clang O0/O2 + rejeu I1 obtenus ; verifier ensuite collisions et allocation cible avant d'elargir la revendication.
2. C1 negatif : collisions d'identifiants/noms dans `SetResInfo`, allocations et `ResError` en echec.
3. C2 : cas limites de `SetResLoad` avant ouverture, `ReleaseResource` et chargement pour plusieurs fichiers.
4. I2-C3 : `ChangedResource`, `WriteResource`, `UpdateResFile`, lecture/ecriture partielles et preuve des octets disque apres reouverture.
5. I2-C4 : recherches des fournisseurs et implementations `HomeResFile`, `GetResourceSizeOnDisk`, `GetMaxResourceSize`.
6. DarwIn Mach-O i386 puis application reelle : tous deux **NON QUALIFIES**.

Ne pas confondre test hote integre, lien Mach-O i386, execution invitee et compatibilite SoundHack/Logic 8.
