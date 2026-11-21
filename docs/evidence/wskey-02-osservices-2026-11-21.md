# WSKEY-02 — `kWSMethodInvocationResult` dans OSServices : intégré et qualifié (21 novembre 2026)

**Mise à jour du 21/11 au soir : le statut BLOCKED ci-dessous est obsolète.**
Le diff relu a été qualifié sur le 5700X, puis intégré à `master` par
[`941183fa`](https://github.com/fr4nck/d4rling/commit/941183fa6badb1af72ecc371769ca12758b1ca81).
Preuves et provenance : [synthèse r4](wskey-02-qualif-r4-5700x-2026-11-21.md).

| Niveau | Statut |
| --- | --- |
| Symbole implémenté dans OSServices, réexporté par CoreServices | **OUI** — `master` `941183fa`, diff identique au candidat relu (SHA-256 `2690d4e3…`) |
| Exports, liaison forte et témoins invités i386/x86_64, avec négatifs | **PASS rapporté** — 5700X, passe r4, 64/64 ; non rejoué par l'auteur de cette mise à jour |
| Build complet de `master` (Darling CI) | **PASS observé** — [run 44945137873](https://github.com/fr4nck/d4rling/actions/runs/44945137873) |
| Résolution du symbole dans Logic 8 original | **NON OBSERVÉE** — Logic non relancé ; prochain obstacle `dyld` inconnu |

Le texte qui suit est le checkpoint d'origine, conservé tel quel ; son statut
BLOCKED décrit l'état d'avant la qualification sur le 5700X.

---

## Checkpoint d'origine : candidat relu, intégration BLOCKED (21/11, avant qualification)

**Statut d'origine (obsolète) : BLOCKED.** La définition candidate est prête, compilée et vérifiée en
Mach-O i386 et x86_64 au niveau objet, puis relue par un agent distinct de
l'auteur (« accepté avec réserves »). Elle **n'est pas intégrée à `master`** :
la qualification exigée sur le vrai build et en invité Darling (i386 et x86_64)
n'a pas pu être exécutée depuis l'environnement de l'agent.
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur.

**Un symbole résolu ne serait pas un Logic fonctionnel.** Même intégré et
qualifié, ce candidat ne ferait que lever, au mieux, le premier échec `dyld`
connu. Le prochain obstacle reste à observer.

## Contrat du lot

| Rubrique | Contenu |
| --- | --- |
| Objectif | Définir `kWSMethodInvocationResult` dans OSServices, exporté via le réexport existant de CoreServices, en i386 et x86_64. |
| Obstacle levé | Premier échec `dyld` de Logic 8 : `_kWSMethodInvocationResult` (DotMacKit vers CoreServices). |
| Base | `fr4nck/d4rling` `master` `36e5235eddae661b7105af3fc1f0540daee55108`. Sous-modules non récupérés dans l'environnement de l'agent (151 absents). |
| Entrée | Valeur `"/Result"` observée sur macOS 15.7.9 x86_64 : [WSKEY-01](wskey-01-macos-2026-11-21.md). |
| Écritures du candidat | `src/frameworks/CoreServices/src/OSServices/WSMethodInvocation.c` (nouveau), `src/frameworks/CoreServices/src/OSServices/CMakeLists.txt` (+1 ligne). |
| Hors périmètre | Tout autre symbole, en-tête WebServicesCore, CMake racine, CI, sous-modules, lancement de Logic. |
| Critère PASS d'intégration | Build canonique ; export dans OSServices et réexport par CoreServices en i386 et x86_64 ; témoins invités liés fortement à CoreServices, valeur `"/Result"` ; contrôle négatif contre l'OSServices actuel. |

## Conventions examinées

- `src/frameworks/CoreServices/src/OSServices/` ne contient que `empty.c` (vide).
  OSServices est construit `FAT` avec `PARENT "CoreServices"`.
- CoreServices réexporte OSServices en entier par `reexport()`, c'est-à-dire
  `-Wl,-reexport_library` (`cmake/use_ld64.cmake`), donc `LC_REEXPORT_DYLIB`.
  `reexport.exp` ne liste que 31 symboles libm/fenv de libSystem.
- Les constantes `CFString` des frameworks voisins suivent la forme
  `const CFStringRef k… = CFSTR("…");`, par exemple SearchKit (`SKAnalysis.c`)
  et `CoreServices/constants.m`.
- Aucune autre définition de `kWSMethodInvocationResult` dans l'arbre
  principal. Les sous-modules (dont `corefoundation` et `cfnetwork`, aussi
  réexportés par CoreServices) n'étaient pas récupérés : à vérifier par
  `git grep -n kWSMethodInvocationResult --recurse-submodules` sur un checkout complet.
- Aucun en-tête WebServicesCore n'existe dans le SDK du dépôt ; le candidat
  n'en ajoute pas.

## Diff candidat relu (non intégré)

SHA-256 du diff : `2690d4e36a01747a51bb8957fa3ded339afeab31a0c82ae15a313959d71ba7be`.
Le nouveau fichier a le blob `f7a79b87`, le CMake modifié le blob `644f6a97`.
Pour l'appliquer : `git apply` sur `36e5235e`, puis `git add` des **deux seuls
chemins**, et contrôle du blob et du SHA-256 avant tout commit.

```diff
diff --git a/src/frameworks/CoreServices/src/OSServices/CMakeLists.txt b/src/frameworks/CoreServices/src/OSServices/CMakeLists.txt
index a1319fa7..644f6a97 100644
--- a/src/frameworks/CoreServices/src/OSServices/CMakeLists.txt
+++ b/src/frameworks/CoreServices/src/OSServices/CMakeLists.txt
@@ -14,6 +14,7 @@ add_framework(OSServices
 
 	SOURCES
 		empty.c
+		WSMethodInvocation.c
 
 	DEPENDENCIES
 		CoreFoundation
diff --git a/src/frameworks/CoreServices/src/OSServices/WSMethodInvocation.c b/src/frameworks/CoreServices/src/OSServices/WSMethodInvocation.c
new file mode 100644
index 00000000..f7a79b87
--- /dev/null
+++ b/src/frameworks/CoreServices/src/OSServices/WSMethodInvocation.c
@@ -0,0 +1,25 @@
+/*
+ This file is part of Darling.
+
+ Copyright (C) 2026 Darling Developers
+
+ Darling is free software: you can redistribute it and/or modify
+ it under the terms of the GNU General Public License as published by
+ the Free Software Foundation, either version 3 of the License, or
+ (at your option) any later version.
+
+ Darling is distributed in the hope that it will be useful,
+ but WITHOUT ANY WARRANTY; without even the implied warranty of
+ MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
+ GNU General Public License for more details.
+
+ You should have received a copy of the GNU General Public License
+ along with Darling.  If not, see <http://www.gnu.org/licenses/>.
+*/
+
+#include <CoreFoundation/CoreFoundation.h>
+
+// WebServicesCore (WSMethodInvocation.h), exported by OSServices and
+// re-exported by CoreServices. Value observed on macOS 15.7.9 x86_64:
+// docs/evidence/wskey-01-macos-2026-11-21.md
+const CFStringRef kWSMethodInvocationResult = CFSTR("/Result");
```

## Résultats

### TEST hôte — objets Mach-O (niveau objet, pas un build Darling)

Le fichier candidat a été compilé par `clang-18 -target {i386,x86_64}-apple-macos10.7
-std=c11 -Wall -Wextra -Werror -O2`. L'en-tête CoreFoundation était un
remplaçant : il ne déclare que `CFStringRef` et la macro `CFSTR` de `CFString.h`
(`__builtin___CFStringMakeConstantString`). Code de retour 0 sur les deux
architectures. Inspection par `llvm-nm -m` et `llvm-objdump --macho` de ces
objets produits par le test :

| Contrôle | i386 | x86_64 |
| --- | --- | --- |
| `_kWSMethodInvocationResult` | `(__DATA,__const) external` | `(__DATA,__const) external` |
| Taille de la variable | 4 octets | 8 octets |
| Relocation de la variable | vers `__DATA,__cfstring` | vers `__DATA,__cfstring` |
| `__cfstring` : isa | relocation `___CFConstantStringClassReference` | idem |
| `__cfstring` : drapeaux, longueur | `0x7c8`, `7` | `0x7c8`, `7` |
| `__TEXT,__cstring` | `2f526573756c7400` (`/Result`) | `2f526573756c7400` (`/Result`) |
| `empty.c` actuel (référence précédente) | aucun symbole | aucun symbole |

### TEST hôte — simulation de liaison x86_64 (synthétique)

Avec `lld -flavor darwin` et des bibliothèques remplaçantes (CoreFoundation, libSystem) :
- l'OSServices candidat exporte `_kWSMethodInvocationResult` ;
- le CoreServices factice le réexporte (`LC_REEXPORT_DYLIB`) ;
- une sonde liée à CoreServices seul lie le symbole fortement :
  `__DATA_CONST __got … CoreServices _kWSMethodInvocationResult` ;
  `nm -m` affiche `(undefined) external … (from CoreServices)`.

**Contrôle négatif :** contre un OSServices construit depuis `empty.c`, la
liaison échoue (`lld: error: undefined symbol: _kWSMethodInvocationResult`,
code 1). lld ne gère pas Mach-O i386 : **aucune liaison i386 n'a été simulée.**

### Non exécuté — BLOCKED

- build réel (ld64 de cctools-port, vrais en-têtes CoreFoundation, drapeaux CMake du projet) ;
- export dans l'OSServices construit et réexport par le CoreServices construit, en i386 et x86_64 ;
- témoins invités Darling i386/x86_64 (liaison forte, valeur, contrôle négatif) ;
- relance de Logic (hors autorisation de ce lot).

**Cause :** les builds, préfixes et stages de qualification invitée sont
privés et résident sur le 5700X. L'environnement de l'agent n'a ni
sous-modules, ni ld64 Darling, ni préfixe. Aucune installation, aucun
téléchargement de sous-module et aucune construction parallèle n'ont été
tentés.

## Revue

Agent relecteur distinct de l'auteur, 21/11/2026 : **accepté avec réserves**,
aucun défaut bloquant. Diff relu identique au SHA-256 ci-dessus. Réserves :

1. Qualification sur le vrai build et en invité requise avant intégration :
   c'est la condition BLOCKED de ce lot.
2. `const CFStringRef` place la variable en `__DATA,__const`. C'est sans
   effet sur le nom lié ni sur la valeur lue, et c'est la forme dominante
   (SearchKit). En revanche, la compilation échouerait si un futur en-tête
   déclarant `extern CFStringRef` sans `const` était inclus dans ce fichier.
3. La valeur i386 est supposée identique à la valeur x86_64 observée, pas
   observée. Le relecteur propose de le dire dans le commentaire, ce qui
   demanderait une nouvelle revue du diff modifié.
4. Le commentaire renvoie à la preuve WSKEY-01, publiée avec ce checkpoint.
5. Le commit d'intégration devra porter la ligne `Revue:` et **pas** `[skip ci]`.

## Prochaine action exacte (5700X, checkout canonique, mission autorisée)

1. Appliquer ce diff sur `master` (`36e5235e` ou plus récent, après relecture des nouveaux commits).
2. Reconstruire OSServices et CoreServices dans le build de référence, sans modifier les builds protégés.
3. Pour chaque architecture (`lipo -thin i386`, puis `-thin x86_64`) :
   - `llvm-objdump --macho --exports-trie` sur OSServices doit montrer `_kWSMethodInvocationResult` ;
   - `--dylibs-used` sur CoreServices doit montrer le réexport d'OSServices.
4. Témoins invités i386 et x86_64. Chacun déclare
   `extern const CFStringRef kWSMethodInvocationResult;`, se lie à CoreServices
   seul (liaison forte), vérifie non-nullité, `CFStringGetTypeID` et la valeur
   `2f526573756c74`, l'égalité à `CFSTR("/Result")` et la différence avec
   `CFSTR("Result")`. Contrôle négatif : la même liaison contre le
   CoreServices actuel doit échouer.
5. Si tout passe : intégrer par commit direct sur `master` avec `Revue:`, puis,
   **sous autorisation applicable**, relancer le banc Logic pour classer le
   prochain obstacle `dyld`.
