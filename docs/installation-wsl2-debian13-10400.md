# Installer le banc D4rling i386 sur Windows 11 / WSL2 / Debian 13

**Tutoriel expérimental — i5-10400, 10 novembre 2026.** Ce guide reproduit les étapes *effectivement réussies* sur le poste secondaire. Il ne prétend **pas** installer un runtime Darling complet ni exécuter Logic Studio 8. Les preuves proviennent des sorties de terminal communiquées par l'opérateur, et non d'une exécution en CI.

## Périmètre validé

Machine : Intel Core i5-10400, 6 cœurs/12 threads, Windows 11, 23,9 Go de RAM physique. Debian GNU/Linux 13.5 Trixie, architecture x86_64, noyau WSL2 `6.18.33.2-microsoft-standard-WSL2`, 11 Gio de RAM disponible à WSL, 3 Gio de swap.

| Étape | Résultat constaté |
| --- | --- |
| Debian 13.5 sous WSL2 | PASS |
| Outils Git/Python puis dépendances de compilation | PASS, aucun paquet manquant |
| Matérialisation du snapshot Carbon | PASS, 160/160 sous-modules, 5,7 Go environ |
| Tests Carbon sur l'hôte | 135/135 PASS (54 événements, 81 paramètres) |
| Tests de contrats C/C++ | PASS |
| Configuration CMake core-i386 | PASS |
| Build natif `darling mldr mldr32 darlingserver` | **179/179 PASS** |
| Analyse du binaire `mldr32` | ELF 32 bits i386 |
| `CoreFoundation_i386` + `CoreFoundation_x86_64` | Compilés PASS ; fat Mach-O i386 + x86_64 vérifié |
| Ancienne commande `system_c system CoreFoundation` | Échec de nom de cible, résolu par les cibles séparées |
| Installation privée core-i386 | **PASS**, dyld et libSystem Mach-O universels vérifiés |
| Témoin Carbon i386 + dylib dynamique | **Mach-O i386 compilés PASS** |
| Première exécution Darwin i386 (normal) | **PASS, exit 0 et marqueur exact** |
| Tests bypass et négatif | **PASS** : bypass code 0, absence de dylib code 1 attendu |
| QuickTime, Logic 8, JACK/MIDI, applications GUI | Non testés sur le 10400 |

Le clone de départ était sur `master` au commit `e76154b53614539f4fa34e4a0fab42b04ecebf35`. La commande de matérialisation crée un second arbre à partir du commit **historique épinglé** `b7d0cb6a79fe196657deb9711647f8486bcc5e5e` avec les correctifs Carbon documentés. Ce n'est **pas** une compilation des nouveaux changements de `master`.

## 1. Vérifications Windows (PowerShell)

~~~powershell
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, VirtualizationFirmwareEnabled
Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent
Get-Volume -DriveLetter C | Select-Object DriveLetter, SizeRemaining
wsl --status
wsl --list --verbose
~~~

Sur le 10400, `VirtualizationFirmwareEnabled=False` et `HypervisorPresent=True` ont été affichés, mais **Debian a bien démarré sous WSL2** : ne pas utiliser le premier indicateur comme seul critère. Ne pas modifier le BIOS sans erreur réelle. La distribution `docker-desktop` est restée séparée.

Si Debian est absente, dans **PowerShell** :

~~~powershell
wsl --install -d Debian
~~~

Lors du premier démarrage, créer un utilisateur Unix et son mot de passe ; ici, `franck`. Pour rouvrir Debian : `wsl -d Debian`.

## 2. Vérification de Debian (terminal Linux)

Les commandes suivantes et toutes les autres commandes Bash de ce guide se lancent **dans Debian**, pas dans PowerShell :

~~~bash
cat /etc/os-release
uname -m
uname -r
free -h
df -h /
df -h /mnt/c
~~~

Vérifier Debian **13** et architecture **x86_64**. `df -h /` donne la taille apparente du disque virtuel Linux : suivre aussi `df -h /mnt/c`, qui indique l'espace réellement libre sur le disque Windows. Lors de ces étapes, le libre Windows est passé d'environ 145 Go à 132 Go.

## 3. Git, Python et dépôt de travail

~~~bash
cd "$HOME"
sudo apt-get update
sudo apt-get install -y --no-install-recommends git python3 ca-certificates
mkdir -p "$HOME/atelier"
if [ -d "$HOME/atelier/d4rling/.git" ]; then
  echo "Depot deja clone"
elif [ -e "$HOME/atelier/d4rling" ]; then
  echo "STOP : destination occupee, ne pas supprimer"
else
  git clone https://github.com/fr4nck/d4rling.git "$HOME/atelier/d4rling"
fi
cd "$HOME/atelier/d4rling" || exit 1
git log -1 --oneline
git status --short
~~~

Une seconde commande `git clone` sur le même chemin produit « destination path already exists » : cela n'invalide pas le premier clonage. Ne pas faire de `git reset --hard`, de nettoyage agressif, ni de `git pull` automatique pendant la qualification. Le dépôt `master` évolue dans d'autres chantiers ; noter le SHA utilisé.

## 4. Dépendances de compilation

~~~bash
cd "$HOME/atelier/d4rling" || exit 1
python3 reproduction/dependencies.py --mode simulate > "$HOME/atelier/dependencies-simulate.log" 2>&1
echo "Simulation, code de retour : $?"
tail -n 15 "$HOME/atelier/dependencies-simulate.log"

set -o pipefail
python3 reproduction/dependencies.py --mode install 2>&1 | tee "$HOME/atelier/dependencies-install.log"
echo "Installation, code de retour : $?"
python3 reproduction/dependencies.py --mode check
~~~

Le 10400 a installé les outils requis, dont **Clang 19, CMake et Ninja**, avec code 0 et `missing: []`. Le contrôle a signalé `version_drift: ["ca-certificates", "gzip"]` et `qualified_reference: false` : ces deux paquets ne correspondaient plus aux versions enregistrées. **Ne pas les rétrograder** pour maquiller ce résultat. La commande `check` peut rendre un code non nul pour une dérive même si tous les paquets sont installés.

## 5. Matérialiser la base historique séparée

~~~bash
cd "$HOME/atelier/d4rling" || exit 1
BASE="$HOME/atelier/d4rling-10400"
SRC="$BASE/source"
mkdir -p "$BASE"
if [ -e "$SRC" ] || [ -L "$SRC" ]; then
  echo "STOP : source deja presente, pas d'ecrasement"
else
  python3 reproduction/materialize.py --output "$SRC" 2>&1 | tee "$BASE/materialize.log"
  echo "Materialisation, code de retour : $?"
fi
test -f "$SRC/D4RLING-REPRODUCTION.json" && cat "$SRC/D4RLING-REPRODUCTION.json"
du -sh "$SRC"
df -h /mnt/c
~~~

Sur le 10400 : code 0, vérification des **160 sous-modules**, patch Carbon historique et fichier `parameters.c` restaurés. Le correctif RPC optionnel `--with-rpc-fix` n'a **pas** été demandé. Ne pas supprimer une destination existante pour relancer.

## 6. Tests Carbon hôte

~~~bash
SRC="$HOME/atelier/d4rling-10400/source"
CC=clang-19 CXX=clang++-19 sh "$SRC/tests/regressions/carbon-events/run.sh"
CC=clang-19 CXX=clang++-19 sh "$SRC/tests/regressions/carbon-contracts/run.sh"
~~~

Résultats vérifiés dans les sorties du poste : **135/135 PASS** pour événements et paramètres, contrats C et C++ PASS. Ces tests hôte ne prouvent pas le chargement de CoreFoundation dans un processus Darwin.

## 7. Configurer puis construire les quatre exécutables natifs

~~~bash
ROOT="$HOME/atelier/d4rling"
BASE="$HOME/atelier/d4rling-10400"
SRC="$BASE/source"
BUILD="$BASE/build-core-i386"
mkdir -p "$BASE/logs"

if [ -f "$BUILD/CMakeCache.txt" ]; then
  echo "Configuration existante : reutilisation"
elif [ -e "$BUILD" ]; then
  echo "STOP : build occupe"
else
  bash "$ROOT/reproduction/configure.sh" "$SRC" "$BUILD" core-i386 \
    2>&1 | tee "$BASE/logs/cmake-config.log"
fi

set -o pipefail
cmake --build "$BUILD" --target darling mldr mldr32 darlingserver --parallel 2 \
  2>&1 | tee "$BASE/logs/core-native-build.log"
echo "Build, code de retour : $?"

find "$BUILD" -type f \
  \( -name darling -o -name mldr -o -name mldr32 -o -name darlingserver \) \
  -exec file {} \;
df -h /mnt/c
~~~

**Résultat du 10400 : 179/179 étapes PASS.** `darling`, `mldr`, `darlingserver` sont ELF64 x86-64 ; `mldr32` est ELF32 Intel i386. Au moins un avertissement de compilation est resté présent. `--parallel 2` évite de saturer les 11 Gio de RAM WSL.

Aucune installation système `/usr/local`, aucun runtime Darling et aucun serveur invité ne sont lancés par ces commandes.

## 8. L'échec réellement rencontré : cible CoreFoundation absente

L'ancienne recette proposait :

~~~bash
cmake --build "$BUILD" --target system_c system CoreFoundation --parallel 2
~~~

Sur le 10400 :

~~~text
ninja: error: unknown target 'CoreFoundation'
~~~

Cette erreur se produit pendant **la recherche des cibles par Ninja**, avant le build des frameworks. Le code source contient un sous-projet `src/external/corefoundation`, mais la présence de ce dossier ne garantit pas une cible de construction exactement nommée `CoreFoundation`.

**Diagnostic réalisé sur le 10400 :** les commandes d'inventaire
`cmake --build ... --target help` et `ninja -t targets all` ont réussi.
Le filtrage initial par `grep` a produit surtout des chemins internes
`src/external/xnu/.../libsystem_kernel` ; **aucun nom de cible CoreFoundation
n'était identifié dans cet affichage**. Cela ne prouve pas que les véritables
cibles sont absentes.

**Analyse des sources épinglées (non encore requalifiée sur la machine) :**

- Le sous-module historique
  `darlinghq/darling-corefoundation` à
  `a3640a77410cf1825f7855172b1551ae7917c461` utilise
  `add_separated_framework(CoreFoundation ...)`.
- La macro `cmake/darling_framework.cmake` définit des cibles de
  compilation `CoreFoundation_i386` et `CoreFoundation_x86_64`,
  et un représentant générique `CoreFoundation` de type **IMPORTED** :
  une cible importée peut participer aux dépendances sans constituer
  une cible Ninja compilable directement.
- Le sous-module `darling-Libc` crée `system_c` et
  `darling-Libsystem` crée `system`.

**Nouveau prévol limité aux noms exacts (aucune compilation) :**

~~~bash
BUILD="$HOME/atelier/d4rling-10400/build-core-i386"

for TARGET in system_c system CoreFoundation_i386 CoreFoundation_x86_64; do
  if ninja -C "$BUILD" -t query "$TARGET" > /dev/null 2>&1; then
    echo "PRESENT : $TARGET"
  else
    echo "ABSENT  : $TARGET"
  fi
done
~~~

**Résultat du prévol (10/11/2026) :** les **quatre** noms sont
`PRESENT` dans le Ninja du 10400 : `system_c`, `system`,
`CoreFoundation_i386` et `CoreFoundation_x86_64`.

## 9. CoreFoundation i386 — compilation réussie sur le 10400

Sans reconfiguration ni changement de profil, l'opérateur a exécuté :

~~~bash
BUILD="$HOME/atelier/d4rling-10400/build-core-i386"
LOG="$HOME/atelier/d4rling-10400/logs"
mkdir -p "$LOG"

cmake --build "$BUILD" --target CoreFoundation_i386 --parallel 2 \
    > "$LOG/corefoundation-i386-build.log" 2>&1
RC=$?
echo "Code de compilation : $RC"
tail -n 20 "$LOG/corefoundation-i386-build.log"
~~~

**Constat réel : `PASS : CoreFoundation_i386`, 3418/3418 étapes.**
La dernière étape a lié
`src/external/corefoundation/CoreFoundation_i386`.
Les étapes ont également impliqué l'édition de liens de
`src/external/icu/icuSources/libicucore.A.dylib`.

Le linker a émis des **avertissements non bloquants** :
`-rpath` sur une OS dylib, initialiseurs statiques dans des fichiers
Objective-C, et alias `.objc_class_name_NSObject` préexistants.
Aucune correction ni validation d'innocuité de ces avertissements n'est revendiquée.
L'espace libre Windows après la compilation était d'environ **133 Go**.

**Frontière de preuve :** le lien de `CoreFoundation_i386` a réussi,
mais le format du fichier produit, ses dépendances, l'assemblage fat,
l'installation privée et l'exécution effective d'un Mach-O i386
restent à contrôler séparément. Les cibles `system_c` et `system`
étaient présentes ; leur statut de sortie n'a pas été vérifié
indépendamment dans cet échange.

### Résultat de la tranche x86_64 et vérification du fat Mach-O — PASS

Le **10 novembre 2026**, le 10400 a contrôlé le fichier i386,
compilé la seconde architecture avec :

~~~bash
cmake --build "$BUILD" --target CoreFoundation_x86_64 --parallel 2
~~~

puis vérifié les trois fichiers avec `file` et avec `lipo -info`
du cctools intégré au build. Sorties attestées :

~~~text
CoreFoundation_i386: Mach-O i386 dynamically linked shared library
CoreFoundation_x86_64: Mach-O 64-bit x86_64 dynamically linked shared library
CoreFoundation: Mach-O universal binary with 2 architectures
Architectures in the fat file: i386 x86_64
~~~

**PASS : les deux architectures compilent et le fichier universel contient
bien i386 et x86_64.** Le binaire `CoreFoundation` est le produit assemblé
par la macro `add_separated_framework`; la cible Ninja `CoreFoundation`
reste non directement constructible, d'où l'usage de ses deux cibles
spécialisées.

La sortie du linker x86_64 contient des avertissements non bloquants
sur des symboles `NSObject` préexistants. Ils restent à analyser : une
bibliothèque liée n'est **pas encore** une bibliothèque chargée dans
un invité Darwin. Espace libre Windows observé : **133 Go**.

**Non démontré à ce stade :** dépendances dynamiques effectivement résolues,
installation privée cohérente, lancement de `dyld`, tests Carbon dans
le guest, QuickTime, Logic Studio 8 et audio/MIDI.

## 10. Construction complète et installation privée core-i386 — PASS (10400)

**Validation obtenue le 10 novembre 2026.** Dans le build historique déjà
configuré, l'opérateur a exécuté le script de contrôle et d'assemblage :

~~~bash
ROOT="$HOME/atelier/d4rling"
BUILD="$HOME/atelier/d4rling-10400/build-core-i386"
LOG="$HOME/atelier/d4rling-10400/logs"
PREFIX="$BUILD/private-install"

test -f "$BUILD/CMakeCache.txt" || exit 1
test -f "$ROOT/reproduction/install-private.py" || exit 1
if [ -e "$PREFIX" ] || [ -L "$PREFIX" ]; then
    echo "STOP : installation privee deja presente, ne pas ecraser"
    exit 1
fi
mkdir -p "$LOG"

python3 "$ROOT/reproduction/install-private.py" --build-dir "$BUILD" --build --jobs 2 \
    > "$LOG/private-core-stage.log" 2>&1
RC=$?
echo "Installation privee : code $RC"
tail -n 20 "$LOG/private-core-stage.log"
~~~

Ce script vérifie `DEBIAN_PACKAGING=ON`, le préfixe privé, l'absence
du hook historique `shutdown-user.sh`, puis effectue le build des
dépendances restantes et `cmake --install` **sans sudo**.

**Résultat réel : `PASS : installation privee`**, avec les marqueurs :

~~~text
PRIVATE_INSTALLATION=/home/franck/atelier/d4rling-10400/build-core-i386/private-install
RUNTIME_EXECUTED=NO
~~~

Formats des composants **installés**, vérifiés avec `file` :

| Chemin relatif à `private-install` | Format |
| --- | --- |
| `bin/darling` | ELF x86-64 PIE **setuid** |
| `libexec/darling/usr/libexec/darling/mldr` | ELF x86-64 PIE |
| `libexec/darling/usr/lib/dyld` | **Mach-O universel i386 + x86_64** (dynamic linker) |
| `libexec/darling/usr/lib/libSystem.B.dylib` | **Mach-O universel i386 + x86_64** |

Le bit `setuid` de `bin/darling` fait partie des caractéristiques à
surveiller avant l'exécution. Aucun runtime invité n'a été exécuté lors
de cette installation. Espace libre Windows après le jalon : **132 Go**.

La procédure ne doit **jamais être relancée** sur le même préfixe déjà
créé : le script refuse volontairement une destination existante.
Conserver ses journaux et l'intégralité des fichiers.

## 11. Témoin Carbon Mach-O i386 — construction PASS (10400)

Le 10/11/2026, la commande suivante a reconstruit le témoin historique
dans un **nouveau** dossier, sans écraser les sources ni l'installation :

~~~bash
ROOT="$HOME/atelier/d4rling"
BASE="$HOME/atelier/d4rling-10400"
BUILD="$BASE/build-core-i386"
PRIVATE="$BUILD/private-install"
OUT="$BASE/carbon-probe"

test ! -e "$OUT" && test ! -L "$OUT" || {
    echo "STOP : temoin deja present"
    exit 1
}
python3 "$ROOT/reproduction/build-carbon-probe.py" \
    --source "$BASE/source" \
    --build "$BUILD" \
    --installation "$PRIVATE" \
    --output "$OUT"
~~~

**Sortie réelle :**

~~~text
CARBON_I386_PROBE_BUILD=PASS
RUNTIME_EXECUTED=NO
~~~

Les commandes `file` et `llvm-lipo-19 -archs` ont confirmé :

- `carbon-dynamic-i386` : **exécutable Mach-O i386** ;
- `libD4CarbonEvents.dylib` : **bibliothèque dynamique Mach-O i386** ;
- architecture du témoin exécutable : `i386`.

## 12. Première exécution invitée Carbon i386 — PASS (10400)

L'opérateur a invoqué le lanceur borné **existant**, sans modifier le
framework ni réinstaller Darling :

~~~bash
ROOT="$HOME/atelier/d4rling"
BASE="$HOME/atelier/d4rling-10400"
PRIVATE="$BASE/build-core-i386/private-install"
PROBE="$BASE/carbon-probe/carbon-dynamic-i386"

bash "$ROOT/reproduction/run-guest.sh" \
    "$PRIVATE" "$PROBE" normal 20
~~~

Le script prépare un **nouveau préfixe** ainsi que de nouveaux espaces
user/mount/PID/IPC/UTS/réseau, vérifie les identités d'espaces à l'intérieur,
et borne l'exécution par `timeout`. La sortie attestée est :

~~~text
REPORT=/tmp/d4rl-replay.3pBmFjCD
EXIT_CODE=0
D4RLING-CARBON-EVENT-I386-OK
PASS : execution Carbon i386
~~~

Le marqueur figure dans le fichier `stdout.log` du rapport ; le
code retour et le marqueur ont été vérifiés **ensemble** par le bloc
de qualification. C'est la **première exécution positive effective d'un
programme Mach-O i386** sur le banc 10400. Cela apporte une preuve
fonctionnelle pour ce témoin Carbon et sa bibliothèque `@loader_path`,
au-delà d'une compilation.

`stderr.log` a signalé **sept fois**
`sh: 1: xdg-user-dir: not found`, ainsi que :
`Warning: failed to increase FD rlimit: Operation not permitted`.
Ce sont des avertissements **non bloquants dans ce test précis**,
pas des anomalies démontrées corrigées. Rien ne prouve que
l'environnement invité soit complet pour d'autres logiciels.

**Portée limitée :** le succès positif de ce témoin historique ne
valide ni le mode `bypass`, ni l'échec attendu en l'absence de dylib,
ni les évolutions récentes de `master`, ni les frameworks QuickTime,
ni Logic Studio 8, ni l'audio/MIDI.

## 13. Contre-épreuves bypass et absence de dylib — PASS (10400)

Le 10/11/2026, l'opérateur a réexécuté le témoin Carbon dans
l'installation privée, en préservant l'original et en créant un dossier
de qualification distinct :

`~/atelier/d4rling-10400/qualif-carbon-bypass-negative-01`.

**BYPASS :** le script `reproduction/run-guest.sh` a créé un nouveau
préfixe isolé, puis exécuté le même témoin avec `mode=bypass`.
Résultat observé :

~~~text
REPORT=/tmp/d4rl-replay.9YHFzVcw
EXIT_CODE=0
D4RLING-CARBON-EVENT-I386-OK
PASS : BYPASS
~~~

**NÉGATIF :** l'opérateur a **copié seulement l'exécutable**
`carbon-dynamic-i386` dans le nouveau sous-dossier `no-dylib/`,
sans la bibliothèque `libD4CarbonEvents.dylib`. Il n'a pas touché
à la dylib originale. Nouvelle exécution en mode `normal` :

~~~text
REPORT=/tmp/d4rl-replay.zbOnD7yx
EXIT_CODE=1
dyld: Library not loaded: @loader_path/libD4CarbonEvents.dylib
Reason: no suitable image found
PASS : NEGATIF (echec attendu)
~~~

La ligne `Library not loaded` et la raison `no suitable image found`
sont apparues dans les sorties du chargeur. Le marqueur positif était
**absent**. Le banc exigeait simultanément code 1, marqueur absent
et diagnostic explicite du chargeur.

Les deux exécutions ont produit des avertissements
`xdg-user-dir: not found` et de `FD rlimit`, comme lors de l'essai
normal. Ils n'ont pas modifié ces verdicts et ne sont pas corrigés.

**Bilan du témoin historique : 3/3 PASS**

| Épreuve | Code | Vérification |
| --- | --- | --- |
| NORMAL | 0 | Marqueur attendu présent |
| BYPASS | 0 | Marqueur attendu présent |
| NÉGATIF sans dylib | 1 attendu | Marqueur absent, diagnostic dyld explicite |

Les journaux de contre-épreuves ont été conservés sous
`qualif-carbon-bypass-negative-01/`. **Ce succès qualifie ce
parcours historique Carbon i386, pas QuickTime, Logic 8,
l'audio/JACK ou les développements récents de `master`.**

## 14. Qualification sur master récent — prévol R4-F, aucune écriture sur le 10400

**Statut : prévol local NON ENCORE EXÉCUTÉ ; le lancement R4-F antérieur
est suspendu jusqu'à réconciliation de l'existant.** Le témoin Carbon
historique est qualifié 3/3 PASS et son installation doit rester intacte.

Les règles de `AGENTS.md` (en particulier sections « Prévol sans mutation »
et « Protéger l'environnement ») imposent **l'inventaire local avant toute
mise à jour Git, récupération de sous-module ou création de build**. La
précédente proposition combinant `git fetch`, `git submodule update
--init --recursive` et création automatique d'un build neuf a été
**retirée** : elle pouvait générer des téléchargements volumineux et
multiplier les artefacts sans vérifier les copies déjà disponibles.

**Étape immédiate :** prévol **strictement en lecture seule** de
`~/atelier/d4rling` et `~/atelier/d4rling-10400` :
branche, HEAD, origin, modifications Git, présence de
`reproduction/qualify-mldr32-current.sh`, options R4-F dans les
sources, sous-modules locaux concernés, build(s) et sorties déjà présents.
Utiliser `GIT_NO_LAZY_FETCH=1` et ne pas lancer
`git fetch`, `pull`, `merge`, `submodule update`,
`sync`, ni la compilation dans ce premier prévol.

**Décision après résultats :** privilégier le build déjà réutilisable.
Un **seul** build séparé nouveau serait justifié uniquement si les
sources récentes ne peuvent techniquement pas être compilées dans
un build cohérent déjà existant et si leur disponibilité est confirmée.
Le script
[`reproduction/qualify-mldr32-current.sh`](../reproduction/qualify-mldr32-current.sh)
requiert une destination inexistante et ne fait **ni installation ni guest** :
ne pas l'exécuter automatiquement.

**Critère futur :** R4-F affichera
`R4F_COMPILE_DEFINITION_SCOPE_PASS` et
`R4F_CURRENT_MASTER_MLDR32_BUILD_PASS` seulement après réelle
compilation i386. Les changements récents de `master` ne sont pas
qualifiés par le succès Carbon historique. QuickTime C4-D reste un
chantier indépendant, non intégrable à ce stade.


### Résultat du 10400 : compilation isolée de l'objet R4-F (10/11/2026)

Après inventaire local **sans réseau ni écriture**, l'opérateur a confirmé :

- Canon `~/atelier/d4rling` : `master` propre à
  `77988d3a784afc07ba039f75e4be177b65b9241d` (**pas le dernier HEAD
  GitHub**) ; les trois sous-modules
  `darlingserver`, `cctools-port`, `xnu` ne sont **pas initialisés
  dans ce checkout**, mais leurs SHA épinglés sont **identiques** à
  ceux du snapshot historique déjà présent.
- Racine `~/atelier` : un **troisième dossier de 760 Kio** existe,
  `d4rling-r4f-20261110-182414`. Il contient un CMakeCache et des
  fichiers temporaires de configuration, mais il **n'est pas un second
  checkout complet**. Ne pas l'effacer, le déplacer ou en créer un autre.
- Le lot R4-F a **réutilisé ce troisième dossier existant** pour y produire
  `r4f-current-mldr32.o` et `r4f-current-mldr32.o.d`. Le code
  `src/startup/mldr/mldr.c` du canon local, diagnostic R4-F activé,
  a été compilé avec Clang 19 en **ELF32 i386 relocatable**.
- Marqueurs observés :
  `R4F_OBJECT_COMPILE=PASS`,
  `R4F_LINK=NON_TESTE`,
  `R4F_RUNTIME=NON_TESTE`,
  `HISTORICAL_BUILD_MODIFIED=NON`,
  `INSTALLATION_MODIFIED=NON`.
- **Un seul avertissement Clang** :
  `src/startup/mldr/stack.c:132`,
  `%x` attend `unsigned int` tandis que l'argument est actuellement
  casté en `unsigned long`. Il ne constitue pas un échec du compileur ;
  la correction et sa non-régression x86_64/i386 n'ont **pas** été
  validées sur le 10400 à cette étape.

**Verdict exact : `R4F_OBJECT_COMPILE=PASS`**, pas
`R4F_CURRENT_MASTER_MLDR32_BUILD_PASS`. Un objet `.o`
ELF32 ne suffit pas à établir l'édition de liens, l'existence d'un
`mldr32` exécutable récent, ou son fonctionnement invité.
Une liaison avec des objets d'autres révisions ne serait pas une
qualification cohérente de `master`.

**Décision de rangement :** conserver uniquement les répertoires déjà
présents, sans `git fetch`, `submodule update`, nouvel arbre
CMake, duplication des 5,7 Gio de sources, installation ou nettoyage
automatique. Le prochain essai devra d'abord choisir un chemin de
liaison **cohérent et réutilisable** à partir des sources réellement
disponibles. Les anciens répertoires `/tmp/d4rl-replay.*` restent
inchangés ; aucune suppression implicite.

## Précautions

Conserver **un seul atelier de travail** dans `$HOME/atelier` et **aucun fichier à la racine de `C:\`**. Ne pas altérer `C:\\WINDOWS\\system32`, la distribution Docker, le dépôt `master`, l'arbre historique ou les logs. Ne rien supprimer ou déplacer sans validation préalable. Tous les échecs sont à conserver et à documenter comme tels.

## Références

- [Qualification core-i386 sur le 10400](qualification/10400-wsl2-core-i386-2026-11-10.md)
- [Reproduction historique](../reproduction/README.md)
- [État du projet](../PROJECT_STATE.md)

**À compléter :** qualification Darwin i386 des développements récents de `master`, applications QuickTime, CoreAudio/JACK et Logic Studio 8. Le témoin Carbon historique NORMAL/BYPASS/NÉGATIF est clos à 3/3 PASS.
