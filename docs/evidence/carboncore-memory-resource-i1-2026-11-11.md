# CarbonCore I1 — intégration réelle Memory Manager M2 / Resource Manager R2

**Date : 11 novembre 2026.** Périmètre : D4rling `fr4nck/d4rling`, branche unique `master`.
**Base observée :** `f39df0d5802c9b35cc07d14b77a9b5efe0d4f183` (R2).
**Décision : PASS hôte pour les deux unités liées, NON QUALIFIÉ pour les appels publics `Resources.cpp`, l'ABI Mach-O i386, SoundHack et Logic Studio 8.**

## Sources primaires / contrat

- [Apple Resource Manager Reference](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Resource_Manager/Reference/reference.html), `GetResource` : après purge du contenu d'un handle connu, le Resource Manager recharge le bloc si `SetResLoad(FALSE)` n'interdit pas le chargement. Le master pointer est conservé ; son contenu nul ne signifie pas qu'il faut ignorer la demande.
- [Apple Memory Manager Reference](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Memory_Manager/memory_mgr.pdf) : le master pointer et le contenu alloué sont deux niveaux distincts ; `EmptyHandle` conserve le handle et `ReallocateHandle` recrée un bloc.
- [Apple TB40](https://leopard-adc.pepas.com/technotes/tb/tb_40.html) : les opérations `ReadPartialResource/WritePartialResource` opèrent sur disque, et ne doivent pas changer implicitement les octets du handle déjà chargé.

## Diagnostic reproduit sur les vraies unités de production

Le conteneur isolé héberge des **copies dont les empreintes Git correspondent** aux sources publiques :

- `MacMemory.cpp` M2 : `26dfea4803ad1499a542f8843862f8998dc5f292`, inchangé.
- `MacMemory.h` : `91be5171aee4910f7910f465a1da96519127a96e`, inchangé.
- `ResourcesImpl.cpp` R2 avant : `033d5cc3720b45925249113eab9dea94772e3de1`.
- `ResourcesImpl.h` R2 : `1eb79e93c2ad5d91b1b205fe6824b776332a65da`, inchangé.

En compilant M2 et R2 **ensemble**, le premier essai hôte a révélé une dépendance implicite aux constantes d'erreur (`paramErr`, `memFullErr`) : ajout d'un `#include <CarbonCore/MacErrors.h>` dans `ResourcesImpl.cpp`. Cela durcit l'autonomie de compilation ; **ce diagnostic hôte ne prouve pas un échec de la chaîne d'en-têtes de production Darwin**.

Le test fonctionnel provoque ensuite `EmptyHandle(handle)` sur une ressource chargée. R2 renvoyait ce handle avec `*handle == nullptr` lors de `ResourceData::getHandle()`, sans restaurer les données. Une assertion a échoué. L'ancien banc de développement a ensuite déclenché ASan dans **une vérification du banc**, parce qu'une lecture supposait indûment cinq octets dans un tampon de trois ; la vérification a été bornée. Cette trace ASan ne doit **pas** être présentée comme un dépassement directement causé par une opération de production.

## Correctif I1

Dans `ResourceData::getHandle()` :

1. Vérifier que la taille de `dataBacking` est représentable en `long`.
2. Si aucun master pointer n'existe, conserver le chemin existant `PtrToHand`.
3. Si **le master pointer existe mais `*data == nullptr`** (bloc vidé ou purgé), appeler **la véritable fonction M2** `ReallocateHandle(data, taille)`, contrôler `MemError()` et recopier `dataBacking`.
4. En cas d'échec de l'une des allocations M2, ne ni fabriquer un succès ni remplacer le master pointer : `getHandle()` retourne `nullptr` et l'appel pourra être retenté.
5. Conserver exactement le même handle après rechargement, y compris pour une ressource de longueur logique zéro.

Aucun changement à `MacMemory.cpp`, `MacMemory.h`, `ResourcesImpl.h`, `Resources.cpp`, CMake, aux préfixes installés ni aux travaux QuickTime/HIToolbox.

**Nouveau blob `ResourcesImpl.cpp` :** `f176a1f86d41a772b7fa034788dae2a4889a70eb`.

## Test hôte réellement exécuté

Le runner `tests/regressions/carboncore-memory-resource-i1/run.sh` compile et lie **les vraies unités C++ M2 et R2** avec GCC/Clang ; seules les déclarations d'API MacTypes/MacErrors/xattr et l'équivalent Linux de `malloc_size` sont remplacées par des en-têtes hôte. **Les fonctions `MemError`, `NewHandle`, `DisposeHandle`, `HLock`, `HUnlock`, `EmptyHandle`, `ReallocateHandle`, `SetHandleSize` et `PtrToHand` proviennent de la vraie unité M2**, sans stub mémoire.

| Compilateur hôte | Configuration | Résultat | ASan / UBSan |
| --- | --- | --- | --- |
| GCC 14.2 | `-O0` | **54/54 PASS** | activés |
| GCC 14.2 | `-O2` | **54/54 PASS** | activés |
| Clang 17 | `-O0` | **54/54 PASS** | activés |
| Clang 17 | `-O2` | **54/54 PASS** | activés |

Ces essais couvrent : ouverture d'une ressource `STR ` synthétique, taille et contenu exacts, interdiction de `DisposePtr` sur un bloc possédé par un handle, `HLock` / refus de purge `memPurErr`, purge puis rechargement au même master pointer, agrandissement et sauvegarde/relecture, séparation handle chargé et écritures partielles, fichier en lecture seule, échec des deux allocations de `ReallocateHandle`, reprise après échec, `ReleaseResource` / nouveau handle, et ressources de taille zéro.

**Contre-épreuves : 2/2 mutations rejetées par assertions sous chacun des deux compilateurs**, indépendamment : désactivation de la branche de rechargement ; suppression de la copie des données persistantes. Les deux mutations compilent et échouent sans invocation d'une application ou d'un loader.

Reproduction sur Linux, depuis le checkout du commit I1 :

```sh
bash tests/regressions/carboncore-memory-resource-i1/run.sh g++
D4_I1_OPT_LEVEL=-O2 bash tests/regressions/carboncore-memory-resource-i1/run.sh g++
bash tests/regressions/carboncore-memory-resource-i1/run.sh clang++
D4_I1_OPT_LEVEL=-O2 bash tests/regressions/carboncore-memory-resource-i1/run.sh clang++
python3 -B tests/regressions/carboncore-memory-resource-i1/check_mutations.py g++
python3 -B tests/regressions/carboncore-memory-resource-i1/check_mutations.py clang++
```

Les scripts épinglent les blobs de la source, des tests et des shims, utilisent des fichiers temporaires et refusent une source modifiée sans requalification. Aucune branche ni installation n'est mise à jour par les tests.

## Hors périmètre / poursuite

- `Resources.cpp` n'a **pas** été lié avec les vrais headers et `ResourcesImpl` dans ce lot ; les chemins `GetResource`, `ChangedResource`, `WriteResource`, `SetResLoad` et `ResError` devront être qualifiés via le point d'entrée public, et le contrat de dirty flag `resChanged` est encore à revoir.
- Aucun build CMake complet, aucune bibliothèque Darwin i386, aucun appel du vrai `getxattr/setxattr` Darling, aucun resource fork Apple réel et aucun logiciel SoundHack/Logic exécuté.
- `SetResLoad(FALSE)` n'est pas qualifié pour tous les états (master pointer absent/vide) ; les tests I1 utilisent les chemins disponibles, pas la couverture complète de l'API publique.
- Les limites R2 de remplacement d'inode, de conservation d'attributs/ACL et de concurrence sur fichier restent ouvertes. Les accès simultanés au **même** handle ne sont pas couverts.
- Pour le 5700X, la prochaine porte est un **build/chargement Darwin i386 dans une copie isolée**, sans toucher aux préfixes historiques. Réconcilier d'abord le vrai point d'entrée public avant de promouvoir une compatibilité applicative.

**Verdict : I1 réel M2+R2 PASS hôte, I1 API publique/invité i386 NO GO à ce stade.**
