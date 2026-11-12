# CarbonCore I2 — preflight et contre-audit de l'API publique Resource Manager

**Date : 12 novembre 2026.**

**Statut : BLOCKED pour la promotion de code de production ; audit statique verifie du HEAD, checkpoint documentaire uniquement.**

## Provenance et concurrence

- Depot canonique : `fr4nck/d4rling` ; branche unique `master`.
- Premier HEAD de cette session : `2458bf14c35883811acc0d72f369385b7e061b0a` (I1).
- HEAD ulterieur observe : `17f8cc83babd1c20d8d5997baac3c35f5480bf0b`. Ce dernier commit touche exclusivement `docs/evidence/quicktime-c4d-2026-11-10/C4D-C3-M2-host-5700x-2026-11-12.md`. Il n'a pas modifie les trois sources visees.
- `Resources.cpp` : Git blob `dd8a4ffdc0f49a927f648ce9694940f52a2325de`.
- `Resources.h` : Git blob `ac14501bf9967c63a1d071e0b7ab8125a1a7ec55`.
- `ResourcesImpl.cpp` I1 : Git blob `f176a1f86d41a772b7fa034788dae2a4889a70eb`.
- `MacMemory.cpp` M2 : Git blob `26dfea4803ad1499a542f8843862f8998dc5f292`.

Les fichiers ont ete inspectes directement via le connecteur GitHub. Aucun test de I2 sur les trois unites liees n'a ete execute dans cette session. Le conteneur hote utilise au debut de l'audit a ete reinitialise et les copies de fichiers precedemment presentes dans `/mnt/data` ont disparu. Les qualifications hote I1 (54/54) sont **historiques** et ne sont pas des tests I2 rejoues.

## Sources techniques primaires

- [Apple, Resource Manager Reference](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Resource_Manager/Reference/reference.html) : fonctions de ressources, recherche, chargement et erreurs.
- [Apple, Technical Note TB40](https://leopard-adc.pepas.com/technotes/tb/tb_40.html) : lecture et ecriture partielles sur disque, distinctions avec les handles deja charges.
- Source de production `src/frameworks/CoreServices/src/CarbonCore/Resources.cpp`, et en-tetes `Resources.h` / `ResourcesImpl.h` au blobs ci-dessus.

## Defauts et limites demontres par lecture du code (non qualifies en execution)

1. **Cache des recherches nommees** : `resourcesOfTypeNameMap()` compare `resourcesOfTypeMapCacheType` au lieu de `resourcesOfTypeNameMapCacheType`. Une succession de recherches par ID puis par nom peut conserver un cache vide/perime. Le cache de noms a deja sa propre variable de type, mais elle n'est pas utilisee dans cette condition.
2. **Invalidation cache absente pour certains changements** : `SetResInfo()` change des ID/noms et leurs maps locales sans appeler `clearCaches()`. Les resultats globaux de `GetResource` / `GetNamedResource` peuvent conserver l'ancienne correspondance. Une mutation est necessaire pour demontrer le parcours public exact.
3. **Erreurs de lecture non fiables** : `GetResource()` renvoie directement `ResourceData::getHandle()` sans mettre `g_lastError` a `noErr` en cas de succes, ni convertir un echec d'allocation en code d'erreur explicite. `CountResources()` ne met pas non plus l'erreur a jour. `g_lastError` est une variable globale et non un etat isole par thread ; verifier le contrat de ResError avant de decider du changement.
4. **SetResLoad non conforme a prouver** : `SetResLoad(Boolean)` modifie seulement le drapeau statique `Resources::setCreateHandles(load)` utilise a l'ouverture/au chargement initial ; `GetResource()` appelle toujours `getHandle()`, lequel alloue le bloc meme quand le drapeau est faux. L'API Apple distingue le choix du chargement des donnees de l'existence du master pointer. Ce chemin doit etre teste avec un fichier ouvert et `SetResLoad(false)`, puis `LoadResource`.
5. **Declarations publiques sans implementation trouvee dans Resources.cpp** : `LoadResource`, `HomeResFile`, `GetResourceSizeOnDisk`, `GetMaxResourceSize` figurent dans `Resources.h`, mais aucune definition correspondante n'apparait dans l'unite `Resources.cpp` inspectee. Verifier leurs autres fournisseurs/exportations durant le prevol de lien avant de conclure a un symbole absent de toute la dylib. Ne pas leur substituer des fonctions no-op.
6. **FSOpenResourceFile** ne verifie pas `ref` / `refNum` nuls avant d'utiliser ces pointeurs ; les erreurs sont renvoyees au niveau retour, mais `ResError` reste un etat separe. Faire un negatif controle et ne pas ecraser un pointeur de retour invalide.

## Banc I2 a executer en premier

Le banc doit compiler les **trois vraies unites** `MacMemory.cpp`, `ResourcesImpl.cpp` et `Resources.cpp` avec les vrais headers Carbon si disponibles ; les seules substitutions hote acceptees sont celles requises par l'ABI Darwin pour les types `FSRef`, fonctions de chemin et xattrs. Les shims de tests **ne doivent pas simuler les fonctions du Memory Manager ou du Resource Manager testees**.

Criteres, avec un fichier resource fork original synthetique et deux fichiers ouverts :

- Ouverture et selection : `FSOpenResourceFile`, `UseResFile`, `CurResFile`, `CloseResFile` ; verifier les chemins d'erreur/absence.
- Recherche par ID et par nom avec deux types et deux IDs, successifs, alternes et apres `SetResInfo`. Comparer `GetResource` / `Get1Resource` / `GetNamedResource` / `Get1NamedResource` ; invalider et verifier les caches.
- `ResError` apres succes, echec, puis nouveau succes ; echec d'allocation simule via M2, sans faux `noErr`.
- `SetResLoad(false)` : conserver un handle non charge, puis forcer le chargement via `LoadResource` ; re-purger et recharger en preservant le master pointer. Verifier la signature et l'export de `LoadResource` avant le test.
- `ChangedResource` marque en memoire ; `WriteResource` / `UpdateResFile` propagent les erreurs d'ecriture ; `ReadPartialResource` / `WritePartialResource` respectent les bornes et la separation disque/memoire (TB40).
- Rejouer I1 (54 assertions, ancien lot) sur les fichiers candidats pour detecter les regressions, mais **ne pas confondre ce compte avec les nouveaux tests I2**.
- GCC/Clang `-O0/-O2`, ASan/UBSan ; au moins deux mutations qui reintroduisent un cache perime ou un faux succes. Reporter le nombre exact de nouveaux cas testes et leurs journaux.

**Gate STOP** : sans compilation et tests effectivement executes sur la vraie unite publique, ne pas modifier la production, ne pas annoncer un PASS I2 ni une compatibilite Mach-O i386 / SoundHack / Logic Studio 8. Ne pas toucher aux prefixes installes, aux repertoires historiques du 5700X, ni a x86_64/Cocoa.

**Prochain acte** : etablir un checkout de qualification reproductible de ce HEAD dans un environnement de developpement avec ses en-tetes, puis reproduire les six categories de tests avant un petit commit de code.
