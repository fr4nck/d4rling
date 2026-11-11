# D4rling — CarbonCore / Gestalt G4 : version macOS du produit, erreurs Gestalt et limite Carbon

**Date :** 11 novembre 2026  
**Base observée :** `master` = `c4d294da6c3b66a9b5b4cb997a5d2db9001821e3` au prévol.  
**Issue :** [#13 (SoundHack SH05)](https://github.com/fr4nck/d4rling/issues/13).  
**Statut :** **PASS hôte GCC + Clang** ; **build et exécution Mach-O i386 NON EXÉCUTÉS**, **SoundHack et Logic Studio 8 NON QUALIFIÉS**.

## Contrats et informations examinés

- Les sélecteurs Apple `gestaltSystemVersion` (`sysv`) et `gestaltSystemVersionMajor/Minor/Patch` (`sys1/sys2/sys3`) désignent le **système d'exploitation**, pas son noyau. `sysv` encode historiquement des chiffres hexadécimaux de type BCD (ex. 10.4.0 -> `0x1040`, 10.10.5 -> `0x1095` par saturation de la composante mineure à 9). Les composantes individuelles restent entières et non saturées.
- Le préfixe Darling est alimenté par `src/frameworks/CoreServices/SystemVersion.plist` (`ProductVersion=11.7.4`) et `SystemVersionCompat.plist` (`ProductVersion=10.16`). Les deux ressources sont installées par `CoreServices/CMakeLists.txt`.
- Le sous-module **XNU épinglé par ce dépôt** (`src/external/xnu` = `fa29287aa2f0115271e091f1031f53c9e024005d`) expose `kern.osproductversion` et lui affecte `EMULATED_OSPRODUCTVERSION="11.7.4"`. Il expose séparément `KERN_OSRELEASE` = `20.6.0`. L'implémentation `copyout_string` inclut l'octet NUL dans la longueur retournée. Voir [configuration épinglée](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/darling/src/libsystem_kernel/emulation/CMakeLists.txt) et [fournisseur sysctl épinglé](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/helper/misc/sysctl_kern.c).
- Les erreurs Gestalt définies par `CarbonCore/MacErrors.h` sont `gestaltUnknownErr=-5550` (valeur non disponible) et `gestaltUndefSelectorErr=-5551` (sélecteur non reconnu). `paramErr=-50` est conservé pour un pointeur de sortie nul.
- `gestaltCarbonVersion` (`'cbon'`) désigne une version d'API Carbon **effective**. Les services Carbon de ce fork sont partiels : CarbonCore, HIToolbox et leurs réexports contiennent encore des implémentations incomplètes. La présence d'une dylib ou de `DYLIB_CURRENT_VERSION` ne certifie pas une version Carbon 1.x. **Aucune valeur Carbon n'est revendiquée** et SoundHack conserve donc son blocage `cbon`.

## Implémentation G4

1. `Gestalt.cpp` interroge `sysctlbyname("kern.osproductversion")` plutôt que `KERN_OSRELEASE`. Pas de lecture directe des ressources ni de dépendance ajoutée à CoreFoundation : le fournisseur XNU épinglé fournit la même version produit que le plist principal.
2. Réutilisation de l'analyse décimale bornée introduite en G3, avec refus des signes, suffixes, champs incomplets, débordements et NUL intermédiaires ; versions produit à deux ou trois composantes ; contrôle de la taille et du NUL terminal.
3. `sysv` encode les composantes dans quatre nibbles hexadécimaux (ex. `11.7.4 -> 0x1174`) avec saturation à 9 des composantes mineure et corrective. Un numéro majeur au-delà de 99 est **non représentable** dans le format historique et renvoie `gestaltUnknownErr`, sans débordement. Les sélecteurs `sys1/sys2/sys3` retournent les entiers exacts.
4. `Gestalt.h` expose `gestaltCarbonVersion = 'cbon'` et l'alias `gestaltSystemVersionBugFix = gestaltSystemVersionPatch`. Un sélecteur inconnu, y compris `cbon` non revendiqué, renvoie désormais `gestaltUndefSelectorErr` ; les erreurs de source produit ou de représentation renvoient `gestaltUnknownErr` et une sortie nulle.
5. Conservation des correctifs G1 (non-chute de contrôle), G2 (vérification sysctl, pointeur nul) et G3 (conversion numérique stricte), ainsi que de `gestaltSysArchitecture`. Aucun ajout x86_64/Cocoa ni changement aux installations, sous-modules, CMake ou fonctionnalités audio.

**Limite de compatibilité connue :** `SystemVersionCompat.plist` annonce 10.16, mais ce correctif n'implémente pas un basculement de version par processus. Il choisit exclusivement la version produit retournée par l'émulation XNU épinglée. Le parcours effectif `sysctlbyname` en invité i386 et le comportement d'une éventuelle politique de compatibilité restent à vérifier. Les valeurs encodées ne prouvent pas que les autres API associées à macOS 11 soient implémentées.

## Preuve hôte — unités de production réelles

Banc mis à jour : [`reproduction/fixtures/carboncore/check_gestalt_selectors.py`](../../reproduction/fixtures/carboncore/check_gestalt_selectors.py).

Le banc compile **les vrais `Gestalt.cpp` et `Gestalt.h`**. Seuls l'en-tête d'erreurs, l'en-tête sysctl et la fonction `sysctlbyname` sont simulés pour Linux. Dossier de travail temporaire uniquement. Empreintes publiées :

- `Gestalt.cpp` Git blob `c0fd988f3995b24d0a2ea8215f77bdb3fd83d809`.
- `Gestalt.h` Git blob `1d465bdb2fe1511d976f87f2d19769aa98ba1847`.
- Banc Python Git blob `003400aef3269f9315cd660fda134d3cadc9699c`.

| Environnement | Régression | Mutants négatifs | Résultat |
| --- | --- | --- | --- |
| Debian hôte, GCC 14.2.0 | 62/62 | 2 détectés | **PASS** |
| Debian hôte, Clang 17.0.0 | 62/62 | 2 détectés | **PASS** |

Cas : `11.7.4`, `10.16`, `10.10.5`, `8.6.0`, versions à deux éléments, composantes distinctes, saturation, erreurs historiques, sortie nulle, architecture, `cbon` non annoncé, réponses système malformées/vides/tronquées et limites de `int`. Mutants : refus d'une chaîne suffixée ; interdiction de retomber sur `kern.osrelease`.

Reproduction depuis le checkout `master` correspondant :

```sh
python3 -B reproduction/fixtures/carboncore/check_gestalt_selectors.py \
  --compiler g++ --expected-source-blob c0fd988f3995b24d0a2ea8215f77bdb3fd83d809
python3 -B reproduction/fixtures/carboncore/check_gestalt_selectors.py \
  --compiler clang++ --expected-source-blob c0fd988f3995b24d0a2ea8215f77bdb3fd83d809
```

Les rapports G1 (11 tests), G2 (18) et G3 (38) demeurent archivés comme preuves **historiques** de leurs révisions respectives ; leurs valeurs de noyau ne représentent pas la nouvelle API G4.

## Critères séparés pour le 5700X

**Non exécuté ici :** build CMake global, vraie bibliothèque `CarbonCore` i386, résolution du symbole `sysctlbyname` par libSystem/ABI i386, exécution du vrai `sysctlbyname` via XNU, résultat `Gestalt` en binaire Mach-O, interface SoundHack, QuickTime, CoreAudio, démarrage de Logic Studio 8.

Quand le 5700X est disponible, dans **une copie isolée sans toucher aux installations et arbres historiques** : vérifier les blobs HEAD et le sous-module XNU épinglé ; compiler l'unité de production pour Darwin i386 ; contrôler le lien et les imports `sysctlbyname` ; exécuter un petit Mach-O i386 interrogeant `sysv/sys1/sys2/sys3/sysa/cbon` et comparer avec les réponses produit réellement exposées au processus ; confirmer ensuite seulement la progression de SoundHack `CapabilityCheck()`. **Ne pas assimiler le passage de `sysv` au passage de `cbon`.**

**Verdict : GO source G4 et régressions hôtes ; NO GO compatibilité SoundHack/Logic en invité, issue #13 ouverte.**
