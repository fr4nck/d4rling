# CarbonCore I2-A — correction des caches globaux de recherche

**Date : 12 novembre 2026.** Dépôt : `fr4nck/d4rling`, branche unique `master`. Base du sous-lot : `d0f15b28c64b00a1e92121d516d69ab8d732d6d0`.

**Verdict : PASS hôte ciblé sur les trois fonctions de cache extraites octet pour octet de `Resources.cpp`. NON QUALIFIÉ : compilation et liaison des trois unités de production, Darwin i386, SoundHack, Logic Studio 8.**

## Constat et périmètre

Le prévol [I2](carboncore-resource-i2-preflight-2026-11-12.md) identifie plusieurs défauts. I2-A corrige uniquement les caches globaux `resourcesOfType`, `resourcesOfTypeMap` et `resourcesOfTypeNameMap` dans `src/frameworks/CoreServices/src/CarbonCore/Resources.cpp`.

- Avant correction, les trois caches conservaient les entrées du type précédemment demandé lors d'un changement de type : les conteneurs n'étaient pas vidés.
- `resourcesOfTypeNameMap` comparait la variable de type du cache d'ID (`resourcesOfTypeMapCacheType`) plutôt que celle de son propre cache (`resourcesOfTypeNameMapCacheType`).
- Correctif minimal : trois `rv.clear()` en cas de changement de type et correction du sélecteur de cache des noms. Le modèle de données et les API restent inchangés.
- `SetResInfo()` et ses invalidations de cache, `ResError()`, `SetResLoad(FALSE)`, `LoadResource()`, la persistance, l'ouverture/fermeture et les codes d'erreur sont **hors du correctif I2-A**. Ces risques déjà relevés restent ouverts.

## Provenance démontrée

- Source de référence : blob Git `dd8a4ffdc0f49a927f648ce9694940f52a2325de` (`Resources.cpp` complet).
- Extrait exact contenant les trois fonctions : blob `a38d4e6c8eea4833699291129adcadcc3f1ec9bb` (1892 octets).
- Extrait candidat des trois fonctions après correction : `fb81dbcfbeb931a4227737b8e93292e1023f0bc2`.
- Source complète candidate `Resources.cpp` : blob `21ce32edade0235704a3f69378f66ffa1e77ece5`. Le test reproductible épingle le SHA de l'extrait de cette source.
- Code tiers sous licence GPL Darling inchangé en dehors de ces quatre éditions locales.

## Tests réellement exécutés — hôte Linux

Le banc `tests/regressions/carboncore-resource-i2-cache/check_caches.py` extrait les trois fonctions depuis le fichier de production, les compile telles quelles avec des fixtures C++ minimales de types et de ressources, puis vérifie 21 assertions sur trois types de ressources, deux identifiants et deux noms. Les seules substitutions sont les structures hôte nécessaires à l'appel des fonctions. **Ce test n'est pas la compilation du `Resources.cpp` complet et ne lie pas `MacMemory.cpp` et `ResourcesImpl.cpp`.**

| Compilateur | Optimisation | Ancien extrait | Nouveau code |
| --- | --- | --- | --- |
| GCC 14.2 | -O0 | 9/21 PASS, 12 FAIL | **21/21 PASS** |
| GCC 14.2 | -O2 | 9/21 PASS, 12 FAIL | **21/21 PASS** |
| Clang 17 | -O0 | 9/21 PASS, 12 FAIL | **21/21 PASS** |
| Clang 17 | -O2 | 9/21 PASS, 12 FAIL | **21/21 PASS** |

ASan et UBSan activés sur toutes ces compilations. Quatre mutations négatives ont été rejetées par des **assertions** sous les deux compilateurs : suppression de chacun des trois effacements et retour du mauvais sélecteur de cache des noms (4/4 par compilateur). Aucun échec de compilation n'est compté comme mutant tué.

Le runner `run.sh` exécute GCC/Clang -O0/-O2, puis les mutants -O0. Le banc crée uniquement des fichiers temporaires et refuse une version inattendue des trois fonctions. Aucune installation Darling ni machine 5700X n'est touchée.

### Reproduction après publication

```sh
bash tests/regressions/carboncore-resource-i2-cache/run.sh
```

## Limites et prochain sous-lot

La preuve porte sur le chemin de cache extrait : aucune API publique `GetResource`, `GetNamedResource` ou `SetResInfo` n'a été exécutée, aucun chargement/écriture de resource fork ni lien des trois unités n'a été testé. `ResError()`, `SetResLoad(FALSE)` et le contrôle des caches après changements de ressources demandent un véritable banc d'intégration.

**Prochain acte I2-B :** assembler réellement `MacMemory.cpp` M2, `ResourcesImpl.cpp` R2/I1 et `Resources.cpp` public, y compris les chemins FSRef, puis reproduire successions de recherches ID/nom après `SetResInfo`, erreurs et chargements différés. Ne pas présenter I2-A comme une validation générale CarbonCore.
