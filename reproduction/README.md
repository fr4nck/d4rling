# Reproduire et reprendre D4RLING

Ce dossier transforme les essais locaux en entrées de travail accessibles
depuis GitHub. Commencer par [PROJECT_STATE.md](../PROJECT_STATE.md).
Les commandes ci-dessous s'exécutent dans **Bash Debian 13 amd64**, sous WSL2
ou Linux x86_64. Les instructions PowerShell sont signalées explicitement.

## Contenu livré

- `dependencies.lock.json` : 54 paquets de build/outillage avec versions
  réellement relevées ; les manques sont explicites.
- `submodules.lock.json` : 160 révisions récursives et URL publiques.
- `refs.lock.json` : base historique, branches de travail et profils CMake.
- `patches/carbon-local.patch` : copie des neuf modifications locales,
  applicable à b7d0cb6 ; les fichiers originaux restent inchangés.
- `snapshots/parameters.c` : test historique ignoré par Git, désormais conservé.
- `snapshots/mldr-pr6.c` : source du correctif RPC optionnel, épinglée à PR #6.
- `fixtures/` : sources des petits programmes i386 et du témoin Carbon,
  y compris le pont atomique utilisé lors des essais.
- `materialize.py`, `configure.sh`, `build-carbon-probe.py` et `run-guest.sh` :
  reconstruction dans de nouveaux dossiers et banc à préfixe neuf.
- `restore-private.py` et `verify-archive.py` : transfert de l'état local complet
  sans installer ni lancer automatiquement ce qu'il contient.

## 1. Préparer une machine distincte

Sur Windows, utiliser les commandes WSL documentées par
[Microsoft](https://learn.microsoft.com/en-us/windows/wsl/basic-commands).
Vérifier la distribution disponible avec `wsl --list --online`, installer
Debian avec WSL2 si nécessaire, puis vérifier **Debian 13**, amd64.
Ne pas supposer que le nom « Debian » garantit une version précise.

Dans Debian, Git, Python 3 et les certificats permettent de récupérer le dépôt.
Ce bootstrap modifie seulement le nouveau poste :

```bash
sudo apt-get update
sudo apt-get install --no-install-recommends git python3 ca-certificates
git clone https://github.com/fr4nck/d4rling.git d4rling-resume
cd d4rling-resume
python3 reproduction/dependencies.py --mode print
python3 reproduction/dependencies.py --mode simulate
python3 reproduction/dependencies.py --mode install
python3 reproduction/dependencies.py --mode check
```

Le mode install demande les paquets disponibles de Debian 13 ; un résultat
de build ultérieur doit enregistrer les versions réellement installées.
`--exact` refuse une version indisponible ou un paquet sans version relevée.
Il n'effectue pas de substitution silencieuse. Pour un rejeu de versions
anciennes, conserver les paquets ou utiliser un miroir historique
[Debian Snapshot](https://snapshot.debian.org/), puis vérifier le manifeste.

La liste officielle
[Darling](https://docs.darlinghq.org/build-instructions.html) et le
`debian/control` épinglé ont été comparés au relevé local.
`libfreetype-dev` est le fournisseur observé (le nom historique
`libfreetype6-dev` est une transition). `libelf-dev` est demandé pour un
nouveau build mais n'était pas installé lors du relevé : aucune version
historique n'est inventée pour lui.

Référence observée : Debian 13.5, Clang/LLVM 19.1.7, CMake 3.31.6,
Ninja 1.12.1, GCC 14.2, Python 3.13, pkg-config 1.8.1, noyau WSL2
6.18.33.2. Un autre noyau est un nouvel environnement à qualifier.
Ruby/Claude Code ne sont pas requis ; JACK et PulseAudio i386 sont des
jalons audio ultérieurs, pas des prérequis silencieusement installés.

## 2. Reconstituer les sources historiques

Choisir une destination **inexistante**, sur le disque Linux de préférence.
La procédure en ligne clone la base exacte, initialise les sous-modules,
vérifie leurs commits, applique la copie des neuf modifications puis restaure
le test ignoré. Elle n'utilise jamais le checkout protégé existant.

```bash
mkdir -p "$HOME/d4rling-rebuild"
python3 reproduction/materialize.py \
  --output "$HOME/d4rling-rebuild/source"
```

Pour tester le correctif RPC en supplément, ajouter `--with-rpc-fix`.
Le choix est enregistré dans `D4RLING-REPRODUCTION.json`.
Le défaut RPC `-111` ne devient pas « corrigé » par cette option.

À partir de l'archive privée restaurée, la variante hors ligne conserve
l'arbre de sources complet et les fichiers ignorés :

```bash
python3 reproduction/materialize.py \
  --from-local "$HOME/d4rling-restored/home/d4rling-ui/d4rling-carbon-qualif" \
  --output "$HOME/d4rling-rebuild/source"
```

Le Git historique est un clone partiel/promisor : une copie complète de ses
fichiers de travail ne signifie pas que tous les objets de toute l'histoire
Git sont disponibles hors ligne. Ne pas essayer de le « réparer » par reset.
La restauration conserve les sources et les sous-modules nécessaires au HEAD ;
les commits publics restent récupérables depuis GitHub. Le chemin en ligne
crée un clone indépendant.

## 3. Contrôles hôte avant compilation complète

```bash
SRC="$HOME/d4rling-rebuild/source"
CC=clang-19 CXX=clang++-19 \
  sh "$SRC/tests/regressions/carbon-events/run.sh"
CC=clang-19 CXX=clang++-19 \
  sh "$SRC/tests/regressions/carbon-contracts/run.sh"
CC=clang-19 CXX=clang++-19 SANITIZE=address \
  sh "$SRC/tests/regressions/carbon-events/run.sh"
```

Ces contrôles utilisent l'adaptateur CF identifié par le runner. Ils
ne prouvent pas le runtime CoreFoundation. Les tests hôte publiés
sur la branche i386 et ceux du bitmap RPC se récupèrent à leurs commits
[épinglés](refs.lock.json) dans une copie séparée ; ne pas fusionner toutes
les branches pour faire disparaître une erreur de dépendance.

## 4. Construire dans un nouvel arbre

```bash
bash reproduction/configure.sh "$SRC" "$HOME/d4rling-rebuild/build-i386" core-i386
cmake --build "$HOME/d4rling-rebuild/build-i386" --target darling mldr mldr32 darlingserver --parallel 2
```

Puis, selon le jalon à requalifier, construire les bibliothèques et leurs
dépendances par le graphe :

```bash
cmake --build "$HOME/d4rling-rebuild/build-i386" --target system_c system CoreFoundation --parallel 2
```

Le linker Mach-O Darling est un produit cctools du build :
`src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld`.
Ce n'est pas un `ld64` supposé présent dans PATH.
L'existence d'une bibliothèque x86_64 ne valide pas sa tranche i386.

Les profils `core-x64` et `audio-x64` utilisent leurs propres arbres.
Le profil audio choisit `COMPONENTS=gui`. Le CoreAudio32 reste bloqué tant
que sa chaîne de fournisseurs ELF32 n'est pas qualifiée.
Limiter le parallélisme selon la RAM ; le poste historique avait 64 Go.

Les profils frais fixent explicitement Metal et bytecode Python2 à OFF,
DEBIAN_PACKAGING=ON et un préfixe privé. Les anciens caches utilisaient AUTO et `/usr/local` :
ces différences sont intentionnelles et enregistrées. **Ne pas déplacer
un CMakeCache puis prétendre que le build est relocalisé.**

Le mode DEBIAN_PACKAGING désactive le hook historique `shutdown-user.sh`.
`install-private.py` vérifie ce choix et le préfixe, refuse une destination
existante, puis construit et assemble seulement sous le nouvel arbre :

```bash
python3 reproduction/install-private.py \
 --build-dir "$HOME/d4rling-rebuild/build-i386" --build --jobs 2
```

Il ne lance ni sudo ni runtime. L’installation privée produite se trouve dans
`$HOME/d4rling-rebuild/build-i386/private-install` ; utiliser ce chemin
comme valeur de --installation ci-dessous. Le build complet des bibliothèques
et leur assemblage restent des étapes à qualifier sur le poste de destination.
Les installations historiques déjà assemblées sont conservées dans l’archive.

## 5. Reconstruire puis tester le témoin Carbon i386

Avec une installation **privée cohérente** contenant notamment CoreFoundation
et libSystem i386, le script reconstruit les sources enregistrées du témoin :

```bash
python3 reproduction/build-carbon-probe.py \
 --source "$SRC" --build "$HOME/d4rling-rebuild/build-i386" \
 --installation "$HOME/d4rling-private-install" \
 --output "$HOME/d4rling-rebuild/carbon-probe"
```

Critères de build : Mach-O i386, dépendance `@loader_path/libD4CarbonEvents.dylib`,
exports des quatre API événement/paramètres, aucune utilisation des objets
anciens non documentés.

Exécution **explicite**, après validation de l'installation privée :

```bash
bash reproduction/run-guest.sh "$HOME/d4rling-private-install" \
 "$HOME/d4rling-rebuild/carbon-probe/carbon-dynamic-i386" normal 20
```

Attendre code 0 et la ligne `D4RLING-CARBON-EVENT-I386-OK` dans stdout.
Rejouer avec `bypass`, puis retirer la dylib d'une **copie** du programme
pour le contrôle négatif. Un code retour seul ne suffit pas.
Chaque essai emploie un préfixe neuf, stdin=/dev/null, et un espace
user/mount/PID/IPC/UTS/network propre, avec timeout et descendants bornés.
Les journaux restent dans le nouveau dossier affiché. Aucun signal n'est
envoyé par PID à un serveur historique.

Les témoins Qt statiques/dynamiques et trap sont également conservés comme
sources. `qt_start_loop.s` contient volontairement une boucle sans fin :
son timeout ne doit pas être transformé en preuve d'échec de dyld.

## 6. Restaurer le paquet privé sur un autre poste

Copier **le dossier recovery entier** sur le nouveau poste, puis dans Bash :

```bash
cd /chemin/du/paquet/recovery
sha256sum -c SHA256SUMS
python3 restore-private.py D4RLING-project-state-2026-10-29.tar.gz \
 --supplement D4RLING-restricted-manifest-2026-10-29.tar.gz \
 --output "$HOME/d4rling-restored"
```

L'archive principale contient les arbres D4RLING, y compris les sources
avec Git et sous-modules, les fichiers ignorés, les builds, rapports et
installations. Le complément ne contient que le manifeste protégé de
l'installation /opt. `D4RLING-recovery-metadata-2026-10-29.tar.gz`
conserve en plus manifestes de paquets/configuration, exports accessibles
des chats et pièces jointes, scripts de reprise et inventaire détaillé.
Les caches de conversation sont bornés par ce que l'outil a rendu ;
les éventuelles troncatures sont enregistrées, jamais présentées comme
un export intégral de tous les messages ChatGPT.

La restauration se fait sous une destination neuve, sans écriture dans
`/usr/local` ou `/opt`, sans chown/suid et sans démarrer de daemon.
Les symlinks connus du HOME et des deux installations sont réancrés
dans la copie restaurée ; les chemins absolus internes des anciens caches
ou binaires ne sont pas magiquement corrigés. Pour changer de racine de
build, utiliser la recette fraîche. Les anciens journaux restent des preuves.

Core dumps et fichiers spéciaux/transitoires (sockets, FIFO, devices) ne sont
pas nécessaires à la reproduction et ne sont pas réactivés. L'état mémoire
d'un daemon en cours d'exécution n'est pas sauvegardé par une archive de projet.
Conserver le paquet privé hors de GitHub ; les paquets système Debian eux-mêmes
restent à récupérer si leurs .deb ne sont pas disponibles sur le nouveau poste.

## Validation de cette livraison

Voir [validation.md](validation.md) pour les contrôles effectivement exécutés
sur la copie indépendante, l'archive et les nouveaux scripts.
Une construction intégrale sur un second ordinateur n'est pas revendiquée.
Un échec doit conserver commande, version, étape et journal, et rester un échec.

## Pour la prochaine reprise

Lire l'état racine ; choisir un jalon fonctionnel et un témoin positif/négatif ;
utiliser les sources et références de ce dossier ; mettre à jour l'état avec le
résultat. Ne pas reproposer les inventaires déjà terminés, inventer une
installation Claude/JACK, ou confondre audit, compilation, chargement, exécution
et compatibilité d'une application.
