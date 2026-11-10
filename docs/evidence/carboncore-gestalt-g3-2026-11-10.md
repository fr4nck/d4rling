# D4rling — CarbonCore / Gestalt G3 : analyse stricte de KERN_OSRELEASE

**Date :** 10 novembre 2026  
**Révisions :** G2 `db76e8b94cabcb983c99fd0526d4700be713849a` ; départ du lot `cdef597a0d9fb392e03c5ba7b4131b45a34a26a1` ; prépublication `c897c0e78276c3c5b281e7cbf8d7ea66957ebc0d` (un nouveau commit QuickTime M2-R2 sans fichier commun).  
**Statut :** **PASS tests de la vraie unité C++ sur Linux x64 ; Mach-O i386 NON EXÉCUTÉ ; intégration SoundHack/Logic NO GO**.

## Problème et correctif de production

Le G2 vérifiait les échecs de `sysctl`, mais analysait la version du noyau Darwin avec `sscanf("%d.%d.%d")`. Cette analyse admettait des suffixes (par exemple `20.4.0-extra` et `20.4.0.1`), et la conversion en `int` pouvait déborder pour des champs trop grands. Le résultat historique `0x100 * maj + 0x10 * min` pouvait lui aussi déborder.

Dans `src/frameworks/CoreServices/src/CarbonCore/Gestalt.cpp` :

- Entrée G2 : blob Git `8d7374b490e6270575e6a4e5e88864d8583797f7`.
- Nouveau candidat G3 : blob Git `3b1ad1fb069e99b45f6336b8b6d41ad991538bf0`, SHA-256 `2d6fed6e2c36f7e5c4c58a04d907d71bc8e5e608a4c5b0b48737a02643527496`.
- Nouveau parseur local `static bool parseReleaseNumber` : exactement trois composantes décimales non signées séparées par des points ; refus des préfixes, espaces et suffixes ; détection de dépassement avant multiplication/addition, sans conversion non définie.
- Encodage historique `gestaltSystemVersion` calculé en `long long`, avec refus si supérieur à `INT_MAX`. Les sélecteurs individuels peuvent renvoyer une composante légale à `INT_MAX` sans débordement.
- Conservation de la terminaison mémoire, du traitement des erreurs de G2, des quatre sélecteurs, de `gestaltSysArchitecture` et du retour `unimpErr` pour `cbon` inconnu.

**Attention :** `KERN_OSRELEASE` est une version de noyau **Darwin**, pas de macOS. Les valeurs de succès G3 restent volontairement celles du fork : il ne s'agit **pas encore d'une implémentation conforme du sélecteur Apple de version macOS**.

## Qualification réellement exécutée (hors 5700X)

Le banc existant `reproduction/fixtures/carboncore/check_gestalt_selectors.py` est **étendu**, sans créer de suite parallèle :

- Entrée G2 : blob Git `21aa1c339564636af30fc1c1eec7ff74dedb35c7`.
- G3 : blob Git `7bde6afe6826ae82bb0ead4264f07f50a5080a50`, SHA-256 `6a3b602104b53431f3d2511913b0519d3959bb7b0aeea8196f8f400253f51b23`.
- En-tête réel `CarbonCore/Gestalt.h` : blob Git `127736fadc13fd6d64a8d87b9f912613660acfbd`.
- Le banc compile **le véritable `Gestalt.cpp`** avec ce véritable en-tête. Seuls les en-têtes `sysctl` et `MacErrors` et la réponse de `sysctl` sont simulés sur Linux.
- **38/38 cas PASS sous GCC et 38/38 sous Clang** : parcours G2 conservés, suffixes, composantes manquantes ou supplémentaires, espaces, signes, nombres hors `INT_MAX`, cas limites représentables, débordement de l'encodage, contrôle d'erreur de `sysctl`, `nullptr`, architecture et `cbon` non implémenté.
- **Mutation détectée sur les deux compilateurs** : supprimer la vérification de fin de chaîne produit l'échec attendu de l'oracle « suffix rejected ». Il s'agit d'une contre-épreuve dans le banc, **pas** d'un correctif de production.
- Python `py_compile` : PASS. Linux hôte ; compilation avec `-std=c++17 -O0 -Wall -Wextra -Werror=implicit-fallthrough -Wno-multichar`. Codes de retour globaux : 0.

Reproduction sur un checkout contenant les blobs attendus :

```bash
python3 -B reproduction/fixtures/carboncore/check_gestalt_selectors.py \
  --compiler g++ --expected-source-blob 3b1ad1fb069e99b45f6336b8b6d41ad991538bf0
python3 -B reproduction/fixtures/carboncore/check_gestalt_selectors.py \
  --compiler clang++ --expected-source-blob 3b1ad1fb069e99b45f6336b8b6d41ad991538bf0
```

Les tests sont isolés en répertoires temporaires et ne modifient ni le checkout Git, ni les installations ou artefacts historiques. Aucun téléchargement, SDL, audio, SDK, sous-module ou 5700X sollicité. **Pas de build CMake complet ni de CI exécutée pour G3.**

## Sources du contrat et prochain travail

- [Apple — `gestaltSystemVersion`](https://developer.apple.com/documentation/coreservices/1470788-system_version_selectors/gestaltsystemversion) : il s'agit de la version du **système d'exploitation**, avec un encodage historique borné et des règles de saturation. Ne pas assimiler un numéro de noyau à une version macOS.
- Le dépôt contient déjà `src/frameworks/CoreServices/SystemVersion.plist` (`ProductVersion=11.7.4`) et `SystemVersionCompat.plist` (`ProductVersion=10.16`) au moment de l'analyse. Ils constituent des pistes *existantes*, pas une autorisation de forcer une valeur ni la preuve de la version exposée à chaque processus.
- [Issue #13](https://github.com/fr4nck/d4rling/issues/13) : `gestaltCarbonVersion` (`cbon`) n'est pas implémenté. Ne pas retourner un succès de façade sans fonctionnalité Carbon sous-jacente.
- **Prochaine porte G4 :** choisir le fournisseur effectif et le contrat de version macOS (compatible avec les processus i386 et la politique de compatibilité existante), puis écrire les tests qui discriminent les versions, avant de modifier la valeur renvoyée. Traiter `cbon` indépendamment, en contrôlant les véritables services disponibles.

**Décision : GO pour le durcissement borné de la source et ses tests ; NO GO pour annoncer SoundHack, Logic 8 ou le moteur audio fonctionnels.** Les autres travaux QuickTime/BSD/SoundHack sont laissés intacts.
