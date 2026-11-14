# Rejouer la qualification Security i386

Shell : **Bash sous Debian WSL2**, avec les outils et builds qualifiés existants. Aucun téléchargement, installation, nettoyage ou modification du checkout canonique n'est requis. Le stage privé du 14 novembre doit être conservé ; son absence bloque la recette native. Les témoins sont de vrais Mach-O, pas des adaptateurs hôte.

## Vérification puis exécution dans de nouveaux préfixes

Depuis le worktree privé D4rling contenant ce dossier :

```bash
set -Eeuo pipefail
stage="$HOME/d4wrling-work/validation/security-i386-20261114"
test -f "$stage/RESULTS.json"
python3 tests/regressions/security-i386-loading/reproduce.py --stage "$stage"
python3 tests/regressions/security-i386-loading/reproduce.py --stage "$stage" --run
```

`--run` conserve tous les nouveaux préfixes et journaux. Attendus : 88/88 normal et bypass, Carbon Events, 28 imports Security et test SSL borné sur les deux architectures, chargement minimal, échecs explicites sans Security/helper, contrôle du CarbonCore élagué. Un échec de précondition arrête la recette ; aucune substitution n'est créée.

Les commandes exactes de compilation/lien réellement utilisées sont dans le stage privé `commands/*.json`. `--rebuild-links` permet de rejouer les liaisons finales, signatures et compilation des deux témoins SSL avec leurs sorties privées. La qualification initiale a exécuté ces commandes ; le mode composé `--rebuild-links` n'a pas été exécuté comme campagne supplémentaire. Le vérificateur contrôle 92 entrées de build existantes, les artefacts privés et les fichiers protégés avant toute action.

## Régression du défaut de commande longue, sans préfixe Darling

Le test est dans le sous-module Security au commit `a536cfff5b857b214d939415cf6040e347fcf785`. Il n'exige aucun SDK ; les bibliothèques synthétiques ne définissent aucune API Security.

```bash
set -Eeuo pipefail
stage="$HOME/d4wrling-work/validation/security-i386-20261114"
ld64="$HOME/d4wrling-work/validation/upstream-sync-20261114/build-gui-i386/src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld"
test -x "$ld64"
python3 src/external/security/darling/tests/test-upward-filelist.py   --clang /usr/bin/clang-19 --ld "$ld64"   --output "$stage/filelist-replay-$(date +%s%N)"
```

La génération CMake utilise les blocs d'options du vrai fichier corrigé. Le test force le mode `-filelist` dans une exécution réelle et conserve les commandes/diagnostics. Avec Clang 19.1.7, les deux cas originaux échouent sur `-filelist` et les deux corrigés passent. Un futur compilateur réparé peut aussi réussir les cas originaux.

`security-smoke.c` est un témoin d'allocation/état/destruction SSL et de refus d'un transport fermé. Il vérifie aussi que les 28 noms proviennent du vrai Security. **Ce n'est pas un test de négociation TLS réussie, de confiance ou de certificats.** `carboncore-load-probe.c` est le reproducteur minimal `dlopen` du blocage initial.

[Rapport, révisions et limites](../../../docs/evidence/security-i386-loading-2026-11-14.md).
