# D4rling — QuickTime C4-D-E2 : chaîne de trois bibliothèques ELF hôte

**Date :** 10 novembre 2026  
**Base lue :** `11ba99bddefc59cb1b29e794fdcd0fbf4492a152` (`master`) ; depuis `e8ddb307` seul SH05 SoundHack a été publié, sans chevauchement C4-D.  
**Statut :** **PASS sur témoin de liaison hôte**, **NO GO production / Mach-O i386**.

## Nouveauté par rapport à G1, L1 et R1

Les lots précédents exerçaient séparément la sélection des composants, la fonction réelle `add_framework()` avec un fournisseur synthétique et le contrat CMake de réexport. E2 exerce **en une exécution** la chaîne de bibliothèques distinctes `QuickTime → CoreServices → CarbonCore`, puis un exécutable ELF qui traverse effectivement les trois bibliothèques. L'objectif est de détecter une rupture de liaison entre les deux maillons ; il ne s'agit pas de valider le mécanisme Mach-O de réexport.

Script reproductible : [`check_c4d_chain_host.py`](check_c4d_chain_host.py), blob Git `1b6fab67d44d036d8e8c76a53a290b742f1586e2`, SHA-256 `27ec4071a4b661ded74ae635760968317c84bcbafeb66480c52c54992f43be17` (12 351 octets).

## Entrées de GitHub authentifiées par `git hash-object`

| Fichier CMake de production (lu et copié, jamais modifié) | Blob Git |
| --- | --- |
| `src/frameworks/CoreServices/CMakeLists.txt` | `3fac3be55879c09a21827c8335073ab36b4fd9b9` |
| `src/frameworks/CoreServices/src/CarbonCore/CMakeLists.txt` | `85f36aa6d5a4e976688dc4cafa70e42c34af02ff` |
| `src/frameworks/QuickTime/CMakeLists.txt` | `5c6d8ddd44341653be1e837133d5473c4d04ef6d` |

Le module GitHub `cmake/use_ld64.cmake`, blob Git attendu `374f4352864aaef6157ca63cd0fac3cb9e653ab2`, définit `reexport()`. Le script vérifie la forme exacte de cette fonction. En utilisation normale, il exige le module complet et son empreinte ; **pour l'exécution présente**, le miroir ne disposait que de l'extrait authentique de quatre lignes (`--fragment-fixture`). Le mode normal sur un checkout complet n'a pas été exécuté dans ce lot.

## Méthode et modifications limitées au banc

- Les véritables `CMakeLists.txt` des trois frameworks sont évalués par CMake sur des **copies temporaires**. Un ajout temporaire `CoreServices` à `QuickTime DEPENDENCIES` matérialise la dépendance du candidat C4-D, sans appliquer aucun patch au dépôt.
- Les cibles et sources hôtes sont **synthétiques** : `add_framework()`, `make_fat` et les générateurs SDK ne sont **pas** la chaîne de compilation D4rling ; les autres sous-frameworks de CoreServices sont des interfaces CMake témoins. Le vrai `MacMemory.cpp`, `QuickTime.c` et `GetMediaSample` ne sont pas compilés.
- La fonction `reexport()` du linker Darling est évaluée et ses onze drapeaux sont contrôlés, dont le chemin CarbonCore, l'ordre via `MANUALLY_ADDED_DEPENDENCIES`, l'appartenance de `MacMemory.cpp` à la liste de sources et la présence de CarbonCore dans `LINK_LIBRARIES`.
- Les options Mach-O (`-reexport_library`, `-reexported_symbols_list`) sont retirées **uniquement du target ELF synthétique**, après vérification, pour permettre la liaison GNU/Linux. Ce retrait interdit toute conclusion sur leur comportement sous `ld64`.
- Le build produit trois bibliothèques ELF hôtes, confirme avec `readelf -d` les relations `DT_NEEDED` QuickTime → CoreServices et CoreServices → CarbonCore, puis lance un exécutable témoin ; code retour positif = **0**.

## Campagne effectivement exécutée

**Environnement :** Linux x86_64 isolé, Python 3.13.5, CMake 3.31.6, Ninja 1.12.1, GCC 14.2.0, Git 2.47.3, GNU readelf 2.44. Aucun 5700X, SDK, installation, préfixe privé ou processus Darling utilisé.

Commande sur le miroir exact des trois CMake et l'extrait épinglé de `reexport()` :

```bash
python3 docs/evidence/quicktime-c4d-2026-11-10/check_c4d_chain_host.py --fragment-fixture
```

| Épreuve | Phase | Résultat |
| --- | --- | --- |
| Chaîne des trois bibliothèques ELF puis témoin | Configuration, compilation, lien, `readelf`, exécution | **PASS 1/1** |
| QuickTime sans dépendance CoreServices | Configuration | Rejet attendu |
| CoreServices sans dépendance CarbonCore | Configuration | Rejet attendu |
| Réexport CarbonCore supprimé | Configuration | Rejet attendu |
| Réexport avec chemin incorrect | Configuration | Rejet attendu |
| Symbole CarbonCore manquant | Édition de liens hôte | Rejet attendu |
| Symbole CoreServices manquant | Édition de liens hôte | Rejet attendu |
| CarbonCore retourne une mauvaise valeur | Exécution, code 7 | Rejet attendu |

**Bilan :** **1/1 témoin positif, 7/7 témoins négatifs détectés**, fin globale avec code retour 0. Le script a aussi passé `python3 -m py_compile`. Les scripts de reproduction n'écrivent que dans un dossier temporaire ; aucune source ni installation de production n'a été touchée.

Reproduction depuis un checkout complet à la base CMake attendue :

```bash
python3 docs/evidence/quicktime-c4d-2026-11-10/check_c4d_chain_host.py
```

## Limites, décision et reprise

**PASS limité au banc hôte ELF.** Les réexports de symboles Mach-O ne sont pas reproduits par le mécanisme ELF ; la vraie macro de construction `add_framework()` est testée séparément en C4-D-L1 et **substituée dans E2**. Une réussite des deux bancs ne constitue pas automatiquement un build Darling intégré.

**NON EXÉCUTÉ / BLOCKED :** configuration de tout D4rling, build des vrais CarbonCore/CoreServices/QuickTime i386, ABI, `dyld`, `MemError`, GetMediaSample, moteur audio et Logic Studio 8. Le Memory Manager C4 authentique est uniquement sur le 5700X, inaccessible pendant ce lot.

**NO GO pour `master` en production.** Le candidat C4-D reste un patch isolé ; l'exécution hôte ne permet pas de le promouvoir. Prochaine porte utile : récupérer le candidat C4 réel, construire les véritables bibliothèques Mach-O i386 dans une installation privée cohérente et rejouer les témoins C3/C4 contre celles-ci. Les prochains tests purement synthétiques ne doivent pas remplacer cette étape.

**Coordination :** pas de modification des dossiers SoundHack, BSD, Petite Victoire, dyld ou CoreAudio, ni de fichier CMake de production. Avant tout nouveau lot, relire le HEAD, les commits apparus entre-temps et ce checkpoint.
