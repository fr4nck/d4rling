# AUDIO-I386 : fermeture PulseAudio ELF32 et voie privée

Inventaire du 15 novembre 2026. Rapport :
[docs/evidence/audio-i386-pulse-inventory-2026-11-15.md](../../../docs/evidence/audio-i386-pulse-inventory-2026-11-15.md).

Ces outils établissent ce qu'il faut à l'hôte pour que le CoreAudio i386 de
Darling charge `libpulse.so.0` ELF32. Ils préparent aussi une mise à
disposition **privée** de cette bibliothèque, selon la méthode FreeType de
LOGIC-L1 (`a007a5399`). Ils n'appellent jamais apt. Ils ne modifient ni
dpkg, ni les architectures, ni `/etc`, ni aucune bibliothèque amd64.

| Fichier | Rôle |
| --- | --- |
| `fetch_indexes.sh` | Télécharge seulement les métadonnées Debian trixie i386 dans un dossier neuf : 3 `InRelease`, 3 `Packages.xz`, `Contents-i386.gz` |
| `verify_indexes.py` | Authentifie chaque `InRelease` avec `sqv` et le trousseau Debian installé, puis contrôle la taille et le SHA-256 de chaque index ; écrit `indexes.json` |
| `resolve_closure.py` | Calcule la fermeture `Depends`/`Pre-Depends` exacte d'un paquet i386, avec les mêmes choix qu'apt sur cet hôte (dépôts trixie, trixie-updates et trixie-security, version la plus haute, sans backports) ; confronte chaque paquet `Multi-Arch: same` à sa version amd64 installée |
| `loader_facts.py` | Relève en lecture seule l'interpréteur de `mldr32`, les liens, propriétaires et empreintes du chargeur ELF32, `ld.so.conf.d`, et les chemins que `libc6:i386` livrerait d'après `Contents-i386` |
| `private_pulse.py` | `plan` : épingle les 18 paquets à extraire sur les index authentifiés, sans téléchargement. `prepare … --allow-download` : télécharge les paquets épinglés, vérifie leur SHA-256, extrait avec `dpkg-deb --extract` (aucun script de paquet), construit un `ld.so.cache` privé et vérifie que chaque `DT_NEEDED` ELF32 est résolu |
| `run-guest-ldc.sh` | Banc invité QT-B12 avec une seule différence : `LDCACHE` est monté en lecture seule sur `/etc/ld.so.cache`, dans l'espace de noms de montage du cas uniquement ; l'empreinte vue à l'intérieur est journalisée (`PREFLIGHT ns_ldcache`) |
| `run-ldc.sh`, `b12-run-ldc.sh` | Équivalents de `run.sh` et `b12-run.sh` de QT-B12 avec `LDCACHE` ; sorties dans l'espace AUDIO-I386 |
| `ldc-marker.c` | Marqueur ELF32 inerte du cache de contrôle |
| `pa32-native.c` | Client natif ELF32, sans Darling : `dlopen("libpulse.so.0", RTLD_NOW)`, fichiers mappés, connexion réelle au serveur et informations du serveur ; ne joue rien |
| `observe-maps.sh` | Observateur hôte en lecture seule : fichiers ELF mappés par les processus de l'utilisateur qui chargent une libpulse |
| `indexes.json`, `closure-libpulse0-i386.json`, `packages-private-pulse.json`, `loader-facts.json`, `control-runs.json` | Résultats de l'inventaire et des contrôles |
| `results-b12-i386.json` | Résultats du 15 novembre : fermeture ELF32 extraite, sonde native, sondes CoreAudio i386, 10 essais B12 i386, mappages observés |

## Reproduction (Bash, Debian 13 amd64, WSL2)

```sh
W=$HOME/d4wrling-work/validation/audio-i386-deps-<date>
mkdir -p "$W/tools" && cp tests/regressions/audio-i386-pulse-private/*.{py,sh} "$W/tools/"
bash "$W/tools/fetch_indexes.sh" "$W/index-20261115"            # métadonnées seulement
python3 -I "$W/tools/verify_indexes.py" "$W/index-20261115"
python3 -I "$W/tools/resolve_closure.py" "$W/index-20261115" libpulse0 "$W/closure-libpulse0-i386.json"
python3 -I "$W/tools/private_pulse.py" plan "$W"                # aucun téléchargement de paquet
python3 -I "$W/tools/loader_facts.py" "$W/index-20261115" "$INST/libexec/darling/usr/libexec/darling/mldr32" "$W/loader-facts.json"
```

Le nom `index-20261115` est attendu par `private_pulse.py`. Les index
Debian évoluent : la sécurité et trixie-updates expirent le 21 novembre 2026,
et la prochaine version intermédiaire remplacera l'index stable. Avec
d'autres index, la fermeture doit être recalculée. Une version épinglée
absente de l'index fait échouer `plan`, sans substitution silencieuse.

Contrôle du banc, sans nouvelle bibliothèque : construire le cache de
contrôle (voir `ldc-marker.c`), puis lancer :

```sh
LDCACHE=$W/control-cache/ld.so.cache PULSE_SERVER=unix:/mnt/wslg/PulseServer \
  bash "$W/tools/run-ldc.sh" ldci3k "$B12/build/ca-probe-i386" normal 60   # attendu : 134, libpulse absente
LDCACHE=… bash "$W/tools/run-ldc.sh" ldcx8s "$B12/build/ca-probe-x86_64" normal 60 2500   # attendu : 0, callbacks
```

## Rejeu B12 i386 (exécuté le 15 novembre 2026)

Le téléchargement des 18 paquets binaires (6 257 784 octets) exige un
accord explicite de l'opérateur, d'où l'option `--allow-download` :

```sh
python3 -I "$W/tools/private_pulse.py" prepare "$W" "$W/private-pulse-<date>" --allow-download
C=$W/private-pulse-<date>/ld.so.cache
LDCACHE=$C PULSE_SERVER=unix:/mnt/wslg/PulseServer bash "$W/tools/run-ldc.sh" ca32p "$B12/build/ca-probe-i386" normal 60 2500
LDCACHE=$C LAYER=$B12/layers/libdyld-tlvfs PULSE_SERVER=unix:/mnt/wslg/PulseServer bash "$W/tools/b12-run-ldc.sh" p32a i386 play 8
python3 -I "$B12/probe/bitexact.py" "$W/runs/b12/p32a/gms.pcm" "$W/runs/b12/p32a/monitor.raw"
LDCACHE=$C LAYER=… bash "$W/tools/b12-run-ldc.sh" s32a i386 stoprestart 9   # second passage : bitexact.py … <alignement + 44100>
```

Contrôle natif, hors Darling, dans un espace de noms utilisateur et de
montage dédié :

```sh
gcc -m32 -std=gnu11 -O1 -Wall -Wextra -Werror pa32-native.c -o pa32-native -ldl
env PULSE_SERVER=unix:/mnt/wslg/PulseServer unshare --user --map-users=0:$(id -u):1 --map-groups=0:$(id -g):1 --mount \
  /bin/bash -c 'mount --make-rprivate / && mount --bind "$1" /etc/ld.so.cache && mount -o remount,bind,ro /etc/ld.so.cache && exec "$2"' x "$C" ./pa32-native
```

Un libellé déjà utilisé comme préfixe QT-B12 (par exemple `p32o`) est
refusé par le banc avant tout lancement : choisir un libellé neuf.

`PULSE_SERVER` désigne le chemin **hôte** de la socket. Les libellés
restent courts (limite de 108 octets du socket shellspawn).
