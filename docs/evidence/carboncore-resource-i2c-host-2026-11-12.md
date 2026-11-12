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

## Portes encore ouvertes

1. I2-C1/C2 hote : matrice GCC/Clang O0/O2 + rejeu I1 obtenus ; verifier ensuite collisions et allocation cible avant d'elargir la revendication.
2. C1 negatif : collisions d'identifiants/noms dans `SetResInfo`, allocations et `ResError` en echec.
3. C2 : cas limites de `SetResLoad` avant ouverture, `ReleaseResource` et chargement pour plusieurs fichiers.
4. I2-C3 : `ChangedResource`, `WriteResource`, `UpdateResFile`, lecture/ecriture partielles et preuve des octets disque apres reouverture.
5. I2-C4 : recherches des fournisseurs et implementations `HomeResFile`, `GetResourceSizeOnDisk`, `GetMaxResourceSize`.
6. DarwIn Mach-O i386 puis application reelle : tous deux **NON QUALIFIES**.

Ne pas confondre test hote integre, lien Mach-O i386, execution invitee et compatibilite SoundHack/Logic 8.
