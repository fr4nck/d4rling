# CarbonCore I2-B — invalidation des recherches après SetResInfo

**Date : 12 novembre 2026.** Projet `fr4nck/d4rling`, branche `master`.
**Base source :** `Resources.cpp` au commit I2-A `e71690f1a9ce943d65083e1073ae8d91fe0e55cb`, Git blob `21ce32edade0235704a3f69378f66ffa1e77ece5`.

## Défaut démontré

La fonction publique `SetResInfo(Handle, ResID, ConstStr255Param)` met à jour les entrées `idMap` et `nameMap` du catalogue privé, mais ne déclenche pas `clearCaches()`. Si les caches globaux `resourcesOfTypeMap()` et `resourcesOfTypeNameMap()` ont déjà été construits pour le type courant, les recherches continuent à présenter les anciens ID/noms. Le correctif I2-A (vidage lors d'un **changement de type**) ne suffit pas lorsque le type reste identique.

**Correctif I2-B :** appeler `clearCaches()` après les mises à jour réussies de `SetResInfo`. Aucune autre API de production n'est modifiée. Les signatures, le modèle mémoire et les retours d'erreur existants sont inchangés.

## Preuve de provenance

Les vrais extraits des fonctions de cache du `Resources.cpp` I2-A, de `SetResInfo` et de `clearCaches` ont été extraits et leurs empreintes contrôlées. Fichiers candidats :

- `SetResInfo` avant correction : `9b0ce6e3d26e563bd8aee07a65f543333f1b5850`
- `SetResInfo` corrigé : `1a94fafd537d96d7b63b7cd305172894ca0aa6be`
- `clearCaches` : `66d54449ecd9d005dd46fb9d7d1201d1e08f51f5`
- Trois caches après I2-A : `fb81dbcfbeb931a4227737b8e93292e1023f0bc2`
- `Resources.cpp` complet candidat : `3d9add9d7e1ed0125c7f2114857169c32044ba70`

## Tests réellement exécutés

Le banc `tests/regressions/carboncore-resource-i2-setresinfo/check_setresinfo.py` compile ensemble les extraits effectifs de `SetResInfo`, des trois caches et de `clearCaches` avec des structures hôte minimales. Deux ressources de même type sont recherchées par ID et nom avant/après modification, plus un handle inconnu.

| Hôte | Ancien extrait | Candidat |
| --- | --- | --- |
| GCC 14.2 -O0 | 13/20 PASS, 7 FAIL | **20/20 PASS** |
| GCC 14.2 -O2 | 13/20 PASS, 7 FAIL | **20/20 PASS** |
| Clang 17 -O0 | 13/20 PASS, 7 FAIL | **20/20 PASS** |
| Clang 17 -O2 | 13/20 PASS, 7 FAIL | **20/20 PASS** |

ASan/UBSan activés à chaque passage. Une mutation supprimant l'invalidation a été **tuée par assertions sous GCC et Clang** (1/1 par compilateur).

Reproduction depuis un checkout du commit I2-B :

```sh
bash tests/regressions/carboncore-resource-i2-setresinfo/run.sh
```

Les scripts épinglent les empreintes de source et du fragment testé, et écrivent leurs produits de compilation uniquement dans un dossier temporaire.

## Limites

**PASS hôte limité aux véritables fonctions extraites.** Le banc ne compile pas la totalité de `Resources.cpp`, ne lie pas `MacMemory.cpp` et `ResourcesImpl.cpp`, et n'exerce pas les vrais `FSRef`, les fonctions publiques de recherche, les resource forks sur disque ni l'invité i386.

Les conflits d'identifiants/noms en entrée de `SetResInfo` ne sont **pas résolus par ce correctif** : ce chemin doit être qualifié avant d'étendre son contrat. Les autres points I2 (gestion `ResError`, `SetResLoad(FALSE)`, `LoadResource`, fermeture et persistance) restent ouverts. Ne pas conclure à la prise en charge de SoundHack/Logic Studio 8.

**Prochain gate :** compilation et liaison de l'unité publique complète avec les vrais modules M2/R2-I1, puis vérification des parcours `GetResource` / `GetNamedResource` / `SetResInfo` et traitement des collisions.
