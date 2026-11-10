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
| Build demandé `system_c system CoreFoundation` | **FAIL : cible Ninja `CoreFoundation` inconnue** |
| Bibliothèques Darwin complètes, installation privée, programme invité | Non testés sur le 10400 |
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

**Commande de diagnostic à exécuter maintenant** (lecture seule et génération de logs privés) :

~~~bash
BUILD="$HOME/atelier/d4rling-10400/build-core-i386"
LOG="$HOME/atelier/d4rling-10400/logs"
mkdir -p "$LOG"

cmake --build "$BUILD" --target help > "$LOG/targets-help.txt" 2>&1
grep -iE 'CoreFoundation|system_c|libSystem|(^|[ /])system([ /:]|$)' \
  "$LOG/targets-help.txt" | head -n 50 || true

ninja -C "$BUILD" -t targets all > "$LOG/targets-all.txt" 2>&1
grep -iE 'corefoundation|libsystem|system_c' \
  "$LOG/targets-all.txt" | head -n 50 || true
~~~

Ensuite, sélectionner les **noms exacts** réellement exposés par CMake/Ninja et tester les bibliothèques par étapes, sans deviner une cible ni reconfigurer au hasard.

## 9. Installation privée et test Mach-O : à faire

Les scripts existants `reproduction/install-private.py`, `build-carbon-probe.py` et `run-guest.sh` documentent les prochaines étapes. **Aucune installation privée cohérente ni exécution du témoin Carbon Mach-O i386 sur le 10400 ne sont encore prouvées.** Ne pas présenter le build des quatre exécutables ELF comme une installation de Logic 8.

Ordre de validation futur : frameworks nécessaires → installation privée isolée **sans sudo** → construction d'un Mach-O i386 → essais positifs et négatifs dans l'invité → QuickTime et audio → applications réelles.

## Précautions

Conserver **un seul atelier de travail** dans `$HOME/atelier` et **aucun fichier à la racine de `C:\\`**. Ne pas altérer `C:\\WINDOWS\\system32`, la distribution Docker, le dépôt `master`, l'arbre historique ou les logs. Ne rien supprimer ou déplacer sans validation préalable. Tous les échecs sont à conserver et à documenter comme tels.

## Références

- [Qualification core-i386 sur le 10400](qualification/10400-wsl2-core-i386-2026-11-10.md)
- [Reproduction historique](../reproduction/README.md)
- [État du projet](../PROJECT_STATE.md)

**À compléter après résultats réels :** noms de cibles pour libSystem/CoreFoundation, installation privée et exécution invitée i386.
