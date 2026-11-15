# AUDIO-I386 — fermeture exacte de `libpulse0:i386` et voie privée (15 novembre 2026)

Lot indépendant de B11E-R2 (`GetMediaSample`) et du chantier audio C10/C11.
Objectif : établir exactement ce qui manque à l'hôte pour que le CoreAudio i386
de Darling charge `libpulse.so.0`, sans rien installer.

## Verdicts

| Critère | Statut |
| --- | --- |
| Authentification des index i386 | **PASS** (OBS) : 3 `InRelease` vérifiés par `sqv`, 4 index conformes à leur SHA-256 signé |
| Fermeture exacte de `libpulse0:i386` | **PASS** (OBS sur index) : 21 paquets, 9 117 220 octets à télécharger, 24 635 Kio installés |
| Mise à jour amd64 imposée | **Aucune** dans l'état actuel des index (OBS) : les 21 paquets sont `Multi-Arch: same`, à la même version que leur équivalent amd64 installé |
| Ensemble privé (sans glibc i386) | **Établi** (OBS + HYP) : 18 paquets, 6 257 784 octets ; besoin ELF déduit des équivalents amd64, à confirmer à l'extraction |
| Chargeur de `mldr32` | **Établi** (OBS + DOC) : `libc6:i386` livrerait le chemin de l'interpréteur actuel ; empreinte du remplaçant NOT_RUN |
| Cache `ld.so.cache` privé dans le banc B12 | **PASS** (TEST, contrôle sans nouvelle bibliothèque) : 3/3 essais |
| CoreAudio i386 avec libpulse privée, rejeu B12 i386 | **NOT_RUN** : téléchargement des paquets binaires non autorisé à ce stade |
| ALSA | Non requis (SRC : `wrap_elf(asound)` commenté dans `src/CoreAudio/CMakeLists.txt`) |

Aucune installation, aucun paquet binaire téléchargé, aucun changement d'APT,
de dpkg, des architectures, de `/etc` ou des bibliothèques amd64. Aucun code
de production modifié. Le travail FreeType/Fontconfig de LOGIC-L1 n'a pas été
repris ; la fermeture ffmpeg d'AudioToolbox n'a pas été entreprise.

## Base

- `fr4nck/d4rling@a007a5399d40868588d8cf7fbba97b726506ffa3`, relu après `69bde0a6` (règles GUI et frontière hôte/invité), `47dcaf11` (preuves MOV B11E) et `a007a539` (FreeType ELF32 privé de LOGIC-L1).
- Hôte : Debian 13 amd64 (WSL2), sans architecture étrangère. Paquets 32 bits existants : `libc6-i386` 2.41-12+deb13u4 et `lib32gcc-s1` 14.2.0-19.
- Installation Darling du banc B12 (B11E, `libdyld` officielle) ; `mldr32` `4f46a458…`.

## Index Debian i386

[`fetch_indexes.sh`](../../tests/regressions/audio-i386-pulse-private/fetch_indexes.sh) et [`verify_indexes.py`](../../tests/regressions/audio-i386-pulse-private/verify_indexes.py) ; résultat dans [`indexes.json`](../../tests/regressions/audio-i386-pulse-private/indexes.json).

| Suite | Date | Signataires (sqv) | Index |
| --- | --- | --- | --- |
| trixie (13.7) | 12/09/2026 07:55 UTC | 3 clés de l'archive Debian | `Packages.xz` `1e864b05…` (9 436 656 o) ; `Contents-i386.gz` `4bdf044f…` (11 094 695 o) |
| trixie-updates | 14/11/2026 20:06 UTC, valide jusqu'au 21/11 | 2 clés | `Packages.xz` `eea860c5…` (1 108 o) |
| trixie-security | 14/11/2026 20:03 UTC, valide jusqu'au 21/11 | 2 clés | `Packages.xz` `bb980809…` (252 000 o) |

Les index stable et sécurité sont identiques à ceux de LOGIC-L1. Ils ont été
recopiés depuis ce banc puis revalidés contre les `InRelease` téléchargés le
15 novembre. Les sources de l'hôte comprennent aussi trixie-backports,
exclu car Debian le marque `NotAutomatic`.

## Fermeture exacte

[`resolve_closure.py`](../../tests/regressions/audio-i386-pulse-private/resolve_closure.py)
reproduit les choix d'apt sur cet hôte : priorités égales, version la plus haute,
`Depends` et `Pre-Depends`, alternatives dans l'ordre. Une dépendance peut être
satisfaite par un paquet installé `Architecture: all` ou `Multi-Arch: foreign`.
apt lui-même n'a pas été exécuté. Résultat complet :
[`closure-libpulse0-i386.json`](../../tests/regressions/audio-i386-pulse-private/closure-libpulse0-i386.json).

| Rôle | Paquets i386 (tous de trixie) |
| --- | --- |
| Base, fournie aujourd'hui en biarch | `libc6` 2.41-12+deb13u4, `libgcc-s1` et `gcc-14-base` 14.2.0-19 |
| Client PulseAudio | `libpulse0` 17.0+dfsg1-2+b1, `libasyncns0`, `libsndfile1`, `libflac14`, `libogg0`, `libvorbis0a`, `libvorbisenc2`, `libopus0`, `libmpg123-0t64`, `libmp3lame0` |
| Système | `libsystemd0` 257.13-1~deb13u1, `libcap2`, `libdbus-1-3` |
| X11 | `libx11-6`, `libx11-xcb1`, `libxcb1`, `libxau6`, `libxdmcp6` (`libx11-data`, `all`, déjà installé) |

Les 21 versions sont identiques aux versions amd64 installées. Dans l'état
actuel des index, apt n'aurait donc aucune raison de mettre à jour une
bibliothèque amd64 pour respecter l'égalité de version `Multi-Arch: same`. Une
nouvelle version intermédiaire ou une mise à jour de sécurité de l'un de ces
paquets changerait ce constat : il faudrait recalculer la fermeture.

Recommandés, non installés avec `--no-install-recommends` : `libidn2-0`
(par `libc6`), `dbus` (satisfait par `dbus` amd64, `Multi-Arch: foreign`) et
`libzstd1` (par `libsystemd0`).

Correctif de l'estimation du 14 novembre : les « environ 25 Mo » étaient la
taille installée. Le téléchargement complet représente 9,1 Mo.

## Ensemble privé

[`private_pulse.py plan`](../../tests/regressions/audio-i386-pulse-private/private_pulse.py)
épingle chaque paquet sur son enregistrement authentifié (nom, version, SHA-256)
et écrit [`packages-private-pulse.json`](../../tests/regressions/audio-i386-pulse-private/packages-private-pulse.json).
Il n'extrait rien en privé de `libc6`, `libgcc-s1` et `gcc-14-base`. Comme pour
FreeType, la glibc ELF32 et son interpréteur restent ceux de `libc6-i386`. Il
reste 18 paquets, soit 6 257 784 octets, dont 2 842 992 pour `libopus0`.

Besoin au niveau ELF (HYP, à confirmer à l'extraction) : la chaîne `DT_NEEDED`
des mêmes versions amd64 sur l'hôte est la suivante :
- `libpulse.so.0` → `libpulsecommon-17.0.so` et `libdbus-1.so.3` ;
- `libpulsecommon` → `libsndfile`, `libX11-xcb`, `libX11`, `libxcb`, `libsystemd`, `libasyncns` ;
- `libsndfile` → FLAC, Vorbis, Opus, mpg123, LAME ;
- `libsystemd` → `libcap` ;
- `libxcb` → `libXau`, `libXdmcp`.

Les 18 paquets sont donc tous nécessaires, et aucun ne demande `libgcc_s`.
`libpulse.so.0` amd64 porte un `RUNPATH` absolu vers
`/usr/lib/x86_64-linux-gnu/pulseaudio`. Le `ld.so.conf` privé liste donc aussi
le sous-dossier `pulseaudio` extrait. En mode `prepare`, le script exige que
chaque `DT_NEEDED` ELF32 soit résolu dans l'arbre privé ou dans `/usr/lib32`.

## Chargeur ELF32, `libc6:i386` et `mldr32`

Faits relevés par
[`loader_facts.py`](../../tests/regressions/audio-i386-pulse-private/loader_facts.py) ;
détail dans [`loader-facts.json`](../../tests/regressions/audio-i386-pulse-private/loader-facts.json).

| Chemin | Nature | Propriétaire | Empreinte |
| --- | --- | --- | --- |
| `PT_INTERP` de `mldr32` | `/lib/ld-linux.so.2` | — | — |
| `/lib` | lien → `usr/lib` | base-files | — |
| `/usr/lib/ld-linux.so.2` | lien → `../lib32/ld-linux.so.2` | **aucun** (créé par le postinst de `libc6-i386`) | — |
| `/usr/lib32/ld-linux.so.2` | fichier | `libc6-i386` | `73e22dd4…` ; MD5 conforme à `libc6-i386.md5sums` |
| `/usr/lib32/libc.so.6` | fichier | `libc6-i386` | `f2ed3495…` |
| `/usr/lib/i386-linux-gnu` | absent | — | — |
| `/etc/ld.so.cache` | fichier | — | `3ffa6037…` (inchangé du début à la fin) |

`ld.so.conf.d` déclare `/lib32` et `/usr/lib32` dans
`zz_i386-biarch-compat.conf` (`libc6-i386`) ; aucun répertoire i386 multiarch
n'y figure.

Ce que ferait l'installation de `libc6:i386` :

- **Contents-i386 (OBS)** : `libc6:i386` livre `usr/lib/ld-linux.so.2`, `usr/lib/i386-linux-gnu/ld-linux.so.2` et `etc/ld.so.conf.d/i386-linux-gnu.conf`.
- **Scripts de `libc6-i386` (DOC)** : le postinst crée le lien seulement s'il manque, car il « is also contained in the multiarch libc package ». Le postrm précise qu'il « is also installed by the native multiarch package as a proper file ». Le fichier `.triggers` surveille ce chemin.
- **Conséquence (DOC + OBS)** : `libc6:i386` prendrait possession du chemin exact de l'interpréteur de `mldr32`, et le chargeur de tous les processus Darling i386 deviendrait le sien. Le nouveau fichier `ld.so.conf.d` modifierait en outre le cache système de tous les processus 32 bits de l'hôte.
- **Non vérifié** : l'identité binaire entre ce chargeur et celui de `/usr/lib32`, et la cible exacte du nouveau chemin. Il faudrait l'archive `libc6_2.41-12+deb13u4_i386.deb` (2 721 896 octets, `67bb4b54…`), qui n'a pas été téléchargée. La version est identique ; la compilation ne l'est pas forcément (biarch amd64 d'un côté, port i386 de l'autre).

La voie privée évite ces trois effets. Elle ne touche pas l'interpréteur de
`mldr32`, ne livre aucun fichier dans `/usr/lib` ou `/etc`, et seuls les
processus d'un cas lancé avec `LDCACHE` voient la nouvelle résolution. Elle
n'impose donc pas de requalifier les bancs i386 existants.

## Contrôle du cache privé dans le banc B12

[`run-guest-ldc.sh`](../../tests/regressions/audio-i386-pulse-private/run-guest-ldc.sh)
reprend le banc invité QT-B12, avec mappages délégués et sans `--map-root-user`.
Il y ajoute un montage en lecture seule de `LDCACHE` sur `/etc/ld.so.cache`,
dans l'espace de noms de montage du cas uniquement. Le lanceur filtrant
`LD_LIBRARY_PATH`, c'est la méthode qualifiée par LOGIC-L1.

Contrôle sans nouvelle bibliothèque : le cache système, plus un seul marqueur
ELF32 inerte ([`ldc-marker.c`](../../tests/regressions/audio-i386-pulse-private/ldc-marker.c)),
empreinte `ce9b37bf…`. Un cache construit sans marqueur était identique au
cache de l'hôte, donc incapable de prouver le montage.
Résultats dans [`control-runs.json`](../../tests/regressions/audio-i386-pulse-private/control-runs.json).

| Cas | Retour | Observation |
| --- | ---: | --- |
| `ca-probe` i386 | 134 | `Cannot load libpulse.so.0 (ELF)` : comportement inchangé, attendu |
| `ca-probe` x86_64 | 0 | Périphérique `PulseAudio`, Float32 stéréo 44,1 kHz |
| `ca-probe` x86_64, IOProc silencieux 2,5 s | 0 | Start/Stop 0, 106 callbacks de 8 192 octets |

Dans les trois cas :
- le cache vu dans l'invité est `ce9b37bf…`, et celui de l'hôte reste `3ffa6037…` ;
- montages 41 → 41, darlingserver 0 → 0, aucun processus résiduel ;
- `dpkg --print-foreign-architectures` reste vide ;
- `/var/lib/dpkg/status`, `/etc/ld.so.cache`, les deux chemins du chargeur et les sources APT ont les mêmes SHA avant et après le plan.

## Rejeu B12 i386 préparé

Commandes dans le [README](../../tests/regressions/audio-i386-pulse-private/README.md#rejeu-b12-i386-préparé-non-exécuté),
non exécutées. Ordre prévu :
1. extraction privée (`prepare --allow-download`) ;
2. `ca-probe` i386, avec la `libdyld` officielle puis l'overlay TLV ;
3. IOProc silencieux ;
4. `b12-run-ldc.sh` i386 `play` avec l'overlay TLV, plus comparaison au bit près de la capture ;
5. `stoprestart` ;
6. contre-épreuve avec la `libdyld` officielle.

Critère d'arrêt : le premier obstacle exécuté est consigné tel quel. Une
capture conforme ne vaut pas `B12_AUDIBLE=PASS`.

Points ouverts (OPEN) :
- comportement de la libpulse ELF32 et de ses threads dans `mldr32` ;
- effet du défaut TLS i386 de `libdyld` sur CoreAudio ;
- éventuels autres `wrap_elf` chargés par le programme i386 complet, avant ou après libpulse.

**Suite exécutée le même jour :** extraction privée et rejeu B12 i386 réussis, voir [AUDIO-I386 / B12](audio-i386-b12-pulse-2026-11-15.md). Le besoin ELF des 18 paquets est confirmé sur les fichiers extraits.

## Limites

- La fermeture vaut pour les index datés ci-dessus ; trixie-updates et la sécurité expirent le 21 novembre 2026.
- Le besoin ELF de l'ensemble privé est déduit des binaires amd64 de même version.
- AudioToolbox i386 exigera ensuite ffmpeg ELF32 (`libavcodec.so.61`, etc.), hors périmètre.
- Fontconfig ELF32 relève de LOGIC-L1 : les deux chantiers pourront partager un cache privé, mais aucune fusion n'est faite ici.
- `B12_AUDIBLE` reste NOT_CONFIRMED en x86_64.

Outils et témoins originaux écrits avec assistance IA, à partir des formats
publics Debian (Release, Packages, Contents), des scripts installés de
`libc6-i386` et des mécanismes publics de Darling. Aucun paquet, binaire Apple
ou chemin personnel publié ; les journaux bruts restent dans l'espace privé
AUDIO-I386 du 5700X.
