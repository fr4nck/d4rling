# D4rling — CarbonCore / Gestalt G2 : échecs sysctl et paramètres bornés

**Date :** 10 novembre 2026  
**Référence :** [G1](carboncore-gestalt-g1-2026-11-10.md), commit `c6587b6f64d06fd897578bde5e1455c447f4fcee`, issue [#13](https://github.com/fr4nck/d4rling/issues/13).  
**Statut :** **PASS borné sur compilateurs hôtes GCC/Clang ; Darwin i386 NON EXÉCUTÉ ; SoundHack NO GO**.

## Modification réelle

Fichier : `src/frameworks/CoreServices/src/CarbonCore/Gestalt.cpp`.

- Blob G1 : `a3c9e34ff39495849d1b2e4a23ec70d10a600074`.
- Blob G2 : `8d7374b490e6270575e6a4e5e88864d8583797f7`.
- Refus d'un pointeur `value == nullptr` par `paramErr` avant la sélection, sans appeler `sysctl`.
- Initialisation du tampon `char version[32] = {}` et des trois composants entiers à zéro ; vérification du résultat de `sysctl`, longueur non nulle et bornée ; terminaison explicite à l'indice `version_len`.
- Refus explicite d'une chaîne de version incomplète ou de composantes négatives. En cas d'échec, la réponse est mise à zéro et `unimpErr` est renvoyé plutôt qu'un succès avec des données indéfinies.
- **Chemin de succès, sélecteurs et encodage de version existants conservés.** G1 préserve le `break` entre version et architecture.

Les codes d'erreur sont ceux déjà présents dans `CarbonCore/MacErrors.h`. Le choix `unimpErr` sur un échec de lecture/format est un repli explicite du fork, **pas une affirmation de correspondance exhaustive aux erreurs Apple**.

## Test reproductible

Fichier existant renforcé : [`check_gestalt_selectors.py`](../../reproduction/fixtures/carboncore/check_gestalt_selectors.py), blob Git G2 `21aa1c339564636af30fc1c1eec7ff74dedb35c7`, SHA-256 `90e9ec2bc67275686926cf212cb16716b32ed619bcecbc963b9851d911305e34`.

Le banc compile la **vraie unité C++ `Gestalt.cpp`** avec le `Gestalt.h` public de ce dépôt, Git blob `127736fadc13fd6d64a8d87b9f912613660acfbd`. Seuls `MacErrors.h` et `sys/sysctl.h` sont simulés pour la compilation hôte ; aucun binaire Darwin, processus Darling, installation, source propriétaire ni variante de production artificielle.

| Contrôle | GCC 14.2.0 | Clang 17.0.0 |
| --- | --- | --- |
| Version simulée `20.4.0`, quatre sélecteurs | 4/4 PASS | 4/4 PASS |
| Version simulée `19.6.3`, quatre sélecteurs | 4/4 PASS | 4/4 PASS |
| Architecture, sélecteur inconnu, Carbon `cbon` non implémenté | 3/3 PASS | 3/3 PASS |
| `sysctl` en échec, réponse vide, longueur incohérente | 3/3 PASS | 3/3 PASS |
| Chaîne mal formée, composante négative | 2/2 PASS | 2/2 PASS |
| Réponse `sysctl` sans NUL ; pointeur utilisateur nul | 2/2 PASS | 2/2 PASS |
| **Total** | **18/18 PASS** | **18/18 PASS** |

Les tests compilent avec `-Wall -Wextra -Werror=implicit-fallthrough`. Python 3.13.5, Linux Debian 13 x64, tests dans des dossiers temporaires. Code retour des deux exécutions : **0**.

Reproduction depuis un checkout dont les sources ont les empreintes attendues :

```bash
python3 -B reproduction/fixtures/carboncore/check_gestalt_selectors.py \
    --expected-source-blob 8d7374b490e6270575e6a4e5e88864d8583797f7
python3 -B reproduction/fixtures/carboncore/check_gestalt_selectors.py \
    --compiler clang++ \
    --expected-source-blob 8d7374b490e6270575e6a4e5e88864d8583797f7
```

## Risques non clos et garde de promotion

**Attention :** `KERN_OSRELEASE` renseigne toujours la version du noyau **Darwin**, pas la version macOS attendue par la documentation Apple de `gestaltSystemVersion`. Les valeurs de tests `0x1440` et `0x1360` correspondent uniquement à l'algorithme historique du fork, sans valeur de vérité pour macOS. La correction du domaine version reste séparée.

`cbon` n'est toujours pas implémenté : aucune valeur Carbon n'est inventée. SoundHack peut donc toujours être bloqué au démarrage et l'issue #13 reste ouverte. Les erreurs d'un appel Apple natif, la gestion de chaînes de noyau atypiques, la conversion de versions supérieures et l'ensemble des ABI 32 bits n'ont pas été qualifiées ici.

**NON EXÉCUTÉ :** build CMake complet, linker Mach-O i386, CarbonCore sur Darling, dyld, GUI, moteur audio et Logic 8.

**GO** pour la correction source et son banc hôte reproductible ; **NO GO** pour déclarer une compatibilité SoundHack/Logic. Prochain acte : mener une revue indépendante du contrat de version macOS sans confondre version Darwin et OS produit ; évaluer la faisabilité réelle de `gestaltCarbonVersion` avant tout retour de capacité, puis qualification i386 dès accès au 5700X.

Cette livraison ne touche ni Petite Victoire, ni QuickTime, ni les sous-modules, ni BSD, ni la CI ou les installations.
