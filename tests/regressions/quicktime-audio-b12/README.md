# QT-B12 : premier MOV lu par QuickTime et rendu par PulseAudio

Témoins du lot B12 (14 novembre 2026). Rapport :
[docs/evidence/quicktime-b12-2026-11-14.md](../../../docs/evidence/quicktime-b12-2026-11-14.md).

Chaîne exercée : MOV → `NewMovieFromDataRef` / `GetMediaSample` (vrai
`QuickTime.framework`) → HAL `CoreAudio.framework` de production (backend
PulseAudio) → enveloppe `/usr/lib/native/libpulse.dylib` → libpulse ELF de
l'hôte → serveur PulseAudio WSLg (`/mnt/wslg/PulseServer`). Aucun PCM n'est
injecté après QuickTime et aucun backend n'est remplacé.

| Fichier | Rôle |
| --- | --- |
| `make_demo_mov.py` | Générateur original et déterministe du MOV de démonstration et de son oracle (`demo-oracle.json`) |
| `extract-native.c` | Recoupement natif du MOV avec l'extracteur `qt_mov_pcm.c` qualifié en B11E-R1 |
| `b12-play.c` | Lecteur témoin : `GetMediaSample` → IOProc CoreAudio ; modes `play` et `stoprestart` ; `-DB12_NO_AUDIO` : partie QuickTime seule |
| `ca-probe.c` | Sonde CoreAudio : images, périphérique, format, IOProc **silencieux** |
| `pa-tool.c` | Observateur hôte (libpulse hôte, sans `pactl`) : serveur, flux connectés, capture du moniteur du puits |
| `verify_audio.py` | Oracles : PCM `GetMediaSample` = générateur ; analyse de capture (Goertzel, motif L/R, durée, silence après la fin, trou après Stop) |
| `bitexact.py` | Capture du moniteur identique, échantillon par échantillon, au PCM du MOV |
| `tools/` | Compilation Mach-O, banc invité (variante transmettant `PULSE_SERVER`), orchestration d'un essai |

## MOV de démonstration

Arpège de la majeur : La4 440 Hz, Do#5 554,365 Hz, Mi5 659,255 Hz, La5 880 Hz.
Chaque note dure 0,5 s, crête à 8192 (-12 dBFS), avec des rampes de 10 ms.
Notes 1 et 4 sur les deux canaux, note 2 à gauche seulement, note 3 à droite
seulement.

Format : `twos` S16BE stéréo 44 100 Hz, 88 200 trames (2,0 s), MOV de
353 329 octets, SHA-256
`a63a98ed2bd4dfaa8a911fbbfc8f95b1ee4f8f7e3c1b73a8e47d6849e454b4d0`. PCM SHA-256
`21622b0ba081ed77b167ab4526d1431771890d8844217654ceb3cf85a5b57530`.
`GetMediaSample` le livre en 6 appels (dernier : 25 120 octets). Avec des
blocs de 1 024 trames, le dernier bloc du périphérique est partiel (136 trames).

## Reproduction (Bash, Debian WSL2)

Installation privée du build B11E à `master` ; espace
`$HOME/d4wrling-work/validation/quicktime-b12-<date>` contenant ce dossier en
`probe/`, ses scripts en `tools/`, et `media/` produit par le générateur.

```sh
python3 -I probe/make_demo_mov.py media
clang-19 -std=gnu11 -O1 -Wall -Wextra -Werror probe/pa-tool.c -o build/pa-tool -lpulse-simple -lpulse
CXX=1 bash tools/build.sh x86_64 build probe/b12-play.c QuickTime CoreServices CoreAudio CoreFoundation
PULSE_SERVER=unix:/mnt/wslg/PulseServer bash tools/b12-run.sh p1 x86_64 play 8     # sortie sonore
PULSE_SERVER=unix:/mnt/wslg/PulseServer bash tools/b12-run.sh s1 x86_64 stoprestart 9
python3 -I probe/bitexact.py runs/b12/p1/gms.pcm runs/b12/p1/monitor.raw
```

`PULSE_SERVER` doit désigner le chemin **hôte** de la socket : la libpulse ELF
s'exécute avec la vue de fichiers de l'hôte. Le chemin
`/Volumes/SystemRoot/…` échoue. Les libellés doivent rester courts, à cause de
la limite de 108 octets du socket shellspawn du préfixe.

## Limites

- **i386 bloqué par un prérequis de l'hôte.** `mldr32` est un ELF i386 et
  l'enveloppe libpulse charge `libpulse.so.0` dès l'initialisation de
  CoreAudio. L'hôte n'a pas de libpulse 32 bits : le processus s'arrête avant
  `main` (`Cannot load libpulse.so.0 (ELF)`, code 134). La partie QuickTime
  i386 (`-DB12_NO_AUDIO`) passe.
- La capture prouve la réception par le serveur, pas l'audition : seule une
  écoute humaine peut confirmer le son.
