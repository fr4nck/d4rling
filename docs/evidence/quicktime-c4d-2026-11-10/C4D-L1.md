# D4rling — C4-D-L1 : liaison `add_framework` vers CoreServices (témoin ELF hôte)

**Date :** 10 novembre 2026.  
**Base de référence GitHub vérifiée au début du lot :** `master` = `84020b2d72c3dc098c90e06fc024507c10d6bbab`.  
**Statut :** **PASS expérimental sur le mécanisme de liaison CMake hôte**, **NO GO production / Mach-O i386**.
**Réconciliation inter-conversations avant publication :** HEAD `fcc2713c5cd6a1fcc247e6948e952c90eadd058a`, deux commits supplémentaires exclusivement sur `reproduction/fixtures/test_bsd_i386_r4_b_readonly.py`. Les CMake et les fichiers C4-D visés restent inchangés ; cette livraison n'écrase aucun travail BSD.


## Pourquoi ce lot

Le lot [C4-D-G1](C4D-G1.md) a qualifié la sélection des composants avec un `add_framework()` simulé (8/8 profils et 7/7 mutations). Le maillon suivant était de vérifier que **la véritable fonction `add_framework()` de D4rling transmet `DEPENDENCIES CoreServices system` à `target_link_libraries()`**. D'après la [documentation officielle CMake 3.31](https://cmake.org/cmake/help/v3.31/command/target_link_libraries.html), une dépendance sur une cible CMake existante fournit le chemin de sa bibliothèque et un ordre de reconstruction ; un nom de bibliothèque sans cible ne fournit pas cette même garantie. Le test distingue ces cas, sans simuler CarbonCore C4.

## Sources vérifiées

- `cmake/darling_framework.cmake` : blob Git **`f9a8ede1560936a3c5d1c140ade89b632135d4d9`**. La fonction `add_framework()` correspond aux **133 premières lignes**, extraites de cette version, SHA-256 de cet extrait (avec LF final) : **`83def2451ccfb1c94eed9c3c0ad2a811759e2f137a3808275182941cb3f70439`**.
- Trois CMake de base épinglés : `7605a01569f6634d0cf4c0a948c3c4acd893dde9`, `ea2f9c07e83e2520de3fbce792ef7c429d11dc5a`, `5c6d8ddd44341653be1e837133d5473c4d04ef6d`.
- Patch documentaire C4-D inchangé : [`c4d-cmake-proposal.patch`](c4d-cmake-proposal.patch), SHA-256 `1f6caa834c45f43228602d4f76adaa177a92d6a5fa700aab4e15a3a149eed434`.
- Script neuf : [`check_c4d_link_host.py`](check_c4d_link_host.py), blob Git **`90db6720e63f37803f9d964e2f5f389533509a9c`**.

## Méthode exécutée

Sur un environnement Linux x86_64 isolé (Python 3.13.5, CMake 3.31.6, Ninja 1.12.1, GCC 14.2.0, Git 2.47.3) :

1. Lecture des trois CMake réels et vérification de leurs blobs ; vérification SHA-256 du patch ; `git apply --check` puis `git apply` **sur copies temporaires uniquement**.
2. Extraction et contrôle de l'**authentique fonction `add_framework()`** ; le banc de cette session n'avait que l'extrait de 133 lignes vérifié contre GitHub (pas le module complet), donc option de qualification locale `--fragment-fixture`. Le **mode normal** du script publié exige le blob du module complet dans le checkout canonique.
3. Exécution de `cmake -S … -B …` et `ninja` sur un **petit projet ELF synthétique original**. Le fichier `src/frameworks/QuickTime/CMakeLists.txt` provient du vrai dépôt puis reçoit **le patch isolé**. Les autres fonctions `add_darling_library`, `make_fat`, `generate_sdk_framework`, `remove_sdk_framework` et `InstallSymlink` sont des stubs explicitement limités à ce banc. Les sources C de QuickTime, CoreServices et de l'exécutable sont de **simples témoins synthétiques**.
4. Contrôle des propriétés CMake : `LINK_LIBRARIES=CoreServices;system`, alias `QuickTime_A`, `DYLIB_INSTALL_NAME=/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime`. Exécution d'un binaire hôte qui appelle une fonction QuickTime témoin utilisant un symbole fourni par la fausse cible CoreServices. Code de retour : **0**. Le lien observable contient `libCoreServices.so`.

**Résultat positif : 1/1 PASS** (configuration, compilation, liaison ELF, exécution).

## Témoins négatifs

| Mutation isolée | Phase de rejet observée | Résultat |
| --- | --- | --- |
| Omission de `CoreServices` dans `DEPENDENCIES` | Configuration : `QT_LINK_INPUTS_WRONG` | **Détecté** |
| Suppression de la cible fournisseur `CoreServices` | Édition de liens hôte | **Détecté** |
| Cible présente mais symbole fournisseur absent | Édition de liens hôte | **Détecté** |
| Macro modifiée pour ignorer `FRAMEWORK_DEPENDENCIES` | Configuration : `QT_LINK_INPUTS_WRONG` | **Détecté** |
| Version `A` changée en `B` | Configuration : alias `QuickTime_A` absent | **Détecté** |

**5/5 détectés.** Les premiers passages ont révélé deux attentes de phase/erreur incorrectes dans l'oracle du banc (le cas « dépendance supprimée » est rejeté dès la configuration ; la mauvaise version est d'abord détectée par l'alias). Elles ont été corrigées, puis la campagne entière a été rejouée : **1 positif et 5 négatifs PASS**. Aucun échec intermédiaire n'est présenté comme un test Darling.

## Reproduction — à la racine d'un checkout canonique et propre

```bash
python3 docs/evidence/quicktime-c4d-2026-11-10/check_c4d_link_host.py
```

Le script exige les blobs Git épinglés, un compilateur C hôte, `cmake`, `ninja` et `git`. Il refuse silencieusement **aucune** variation de source : un écart de base est un arrêt. Pour la campagne **effectivement exécutée ici**, seule l'option `--fragment-fixture` a été utilisée, car le miroir de qualification contenait l'extrait identique de 133 lignes au lieu du module complet ; **le mode normal sur le checkout complet n'a pas été exécuté ici**.

La procédure ne crée ni branche, ni installation, ni préfixe permanent ; l'ensemble du build hôte et des mutations est produit sous un dossier temporaire puis effacé. Aucun SDK externe, sous-module, code C4 local, ni fichier de production modifié.

## Décisions et prochain acte

- **PASS — SRC / TEST hôte :** transcription du lien `CoreServices;system` par `add_framework()` sur le projet synthétique épinglé ; symbole fourni, binaire exécuté ; cinq négatifs rejetés.
- **NON EXÉCUTÉ :** vrai `darling_lib.cmake` et ld64, configuration CMake du dépôt complet, build i386, chargement d'un vrai framework CarbonCore, table Mach-O des imports/réexports, `MemError` de C4, Logic Studio 8.
- **BLOCKED :** intégration C4 authentique sur 5700X toujours indisponible.
- **NO GO production :** aucune modification de `cmake/`, `src/`, `Petite Victoire`, audio, BSD ou dyld.

**Prochain acte exact :** au retour de l'accès à la source C4 réelle, qualifier le graphe D4rling complet et les véritables dylibs i386, avec vérification de l'install name, des imports `GetHandleSize`, `SetHandleSize` et `MemError`, des réexports CarbonCore et du protocole GetMediaSample. Ne jamais substituer le témoin ELF à une qualification Mach-O.
