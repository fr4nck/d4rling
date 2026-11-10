# D4rling — CarbonCore / Gestalt G1 : correction de la chute de contrôle

**Date :** 10 novembre 2026  
**Issue :** [#13 — SoundHack SH05](https://github.com/fr4nck/d4rling/issues/13)  
**Base :** `5f14b4e8f87bcaee0bb9a932bfc9c21a65e1adf4`, branche unique `master`  
**Décision :** **PASS tests C++ hôte (GCC et Clang), recette Darling/i386 NON EXÉCUTÉE**. Pas de lancement SoundHack ni qualification de `cbon`.

## Changement réel

Fichier de production : `src/frameworks/CoreServices/src/CarbonCore/Gestalt.cpp`.

- Source avant : blob Git `dffdd4cb26c7f191c6e2b5fc97298c79a8d75dff`.
- Source après : blob Git `a3c9e34ff39495849d1b2e4a23ec70d10a600074`.
- **Seul changement :** `break;` après le bloc des quatre sélecteurs `gestaltSystemVersion`, `Major`, `Minor`, `Patch`, avant `case gestaltSysArchitecture`.

Sans ce `break`, la valeur de version était systématiquement remplacée par `gestaltIntel = 10`. La séparation conserve le comportement de `gestaltSysArchitecture` et le retour `unimpErr` pour les sélecteurs inconnus.

Aucun nouveau sélecteur ni code de compatibilité Carbon n'est ajouté.

## Tests exécutés

Nouveau témoin : [`reproduction/fixtures/carboncore/check_gestalt_selectors.py`](../../reproduction/fixtures/carboncore/check_gestalt_selectors.py), blob Git `14d791f041c5f5d3a0e115b04e01a0c8085a0fa5`, SHA-256 `f06b3524871b782753d6770ad32641576d05ce10c01ea37b0f961f895034e63f`.

Le banc compile **le vrai fichier `Gestalt.cpp`** et le véritable `Gestalt.h` (blob `127736fadc13fd6d64a8d87b9f912613660acfbd`) sur un hôte Linux. Seuls `MacErrors.h` et `sys/sysctl.h` sont remplacés par des en-têtes et une fonction `sysctl` de test ; la traduction C++ de production n'est ni extraite ni réécrite. La compilation utilise `-Werror=implicit-fallthrough`.

Précontrôle sur la source d'origine non corrigée : **FAIL attendu** à la compilation ; GCC indique une chute de contrôle entre la fin du bloc version et `case gestaltSysArchitecture`. Ce résultat prouve que l'oracle détecte effectivement le défaut initial.

Contrôle après correction :

| Compilateur hôte | Cas fonctionnels | Résultat |
| --- | --- | --- |
| GCC 14.2.0 | 11/11 | **PASS**, retour 0 |
| Clang 17.0.0 | 11/11 | **PASS**, retour 0 |
| Python 3.13.5 | Compilation du témoin `py_compile` | **PASS** |

Les cas couvrent les quatre sélecteurs de version pour deux réponses `KERN_OSRELEASE` simulées (`20.4.0` et `19.6.3`), l'architecture Intel inchangée, un sélecteur inconnu, et `'cbon'` **toujours non implémenté** ; le témoin contrôle aussi le nombre d'appels au `sysctl` simulé.

Reproduction dans un checkout complet et à jour :

```bash
python3 -B reproduction/fixtures/carboncore/check_gestalt_selectors.py \
    --expected-source-blob a3c9e34ff39495849d1b2e4a23ec70d10a600074
python3 -B reproduction/fixtures/carboncore/check_gestalt_selectors.py \
    --compiler clang++ \
    --expected-source-blob a3c9e34ff39495849d1b2e4a23ec70d10a600074
```

Aucune écriture hors d'un répertoire temporaire pendant les tests ; aucune opération sur les sous-modules, les outils audio, les builds historiques ou `/opt`.

## Limites importantes

1. Le code existant lit `KERN_OSRELEASE`, qui est une **version de noyau Darwin**, alors que le sélecteur Apple `gestaltSystemVersion` représente une version de macOS. Les valeurs `0x1440` et `0x1360` du témoin reflètent **le calcul historique actuel**, pas une vérité macOS à conserver. Cette ambiguïté demeure un chantier distinct : [documentation Apple du sélecteur](https://developer.apple.com/documentation/coreservices/1470788-system_version_selectors/gestaltsystemversion).
2. `Gestalt('cbon')` n'est toujours pas pris en charge : sa valeur ne doit pas être inventée pour faire passer SoundHack. L'issue #13 reste **ouverte**.
3. Le chemin `sysctl` ignore toujours son code retour et ne garantit pas un tampon correctement terminé ou des champs `sscanf` initialisés en cas d'échec : **correction et tests spécifiques nécessaires** avant de déclarer l'API robuste.
4. Le banc est **hôte seulement** avec `sysctl` simulé. Aucun code Mach-O i386, aucun CarbonCore complet, aucun dyld, aucune exécution de SoundHack ni de Logic 8 n'a été testé.

**Conclusion :** le défaut de chute de contrôle est corrigé dans les sources. **PASS borné GCC/Clang ; NO GO compatibilité SoundHack complète.** Prochaine étape : sécuriser `sysctl` et le parsing sans prétendre résoudre la correspondance Darwin/macOS ; examiner indépendamment les contrats et les fonctionnalités réellement disponibles avant de déclarer `gestaltCarbonVersion`.
