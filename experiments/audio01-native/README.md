# D4RLING-AUDIO-01 — conservation du banc PulseAudio natif

Archive d'un banc de diagnostic produit dans une conversation ChatGPT du 4 novembre 2026 ; publication conservatoire le 8 novembre 2026.

**Périmètre strict :** programme Python natif Linux (x86_64) qui synthétise en mémoire un signal PCM 440 Hz, 1,25 s, 44,1 kHz, stéréo S16LE (amplitude 9 %) et peut le transmettre à PulseAudio par `libpulse-simple` lorsqu'on appelle explicitement `--play`. Le programme n'utilise pas les API Darwin, Mach-O, CoreAudio ou JACK.

**Fichiers conservés :**
- `audio01_native.py` : source Python lisible, disponible dans ce dossier.
- `D4RLING-AUDIO-01-original.zip.b64` : représentation Base64 **sans perte** de l'archive ZIP d'origine. Après décodage, ce ZIP contient `audio01_native.py` et `README.md` d'origine. Ce choix permet de conserver exactement l'archive binaire malgré l'interface de publication texte.
- Cette notice : contexte, provenance, checksum, limites et procédure de restauration.

**Empreintes SHA-256 vérifiées sur l'archive originale :**
- ZIP : `a16ee4ad467e233fd9dc767ab3c64a2e7d611dca1f279509899af4728a4affd5` (4 520 octets).
- `audio01_native.py` : `e40fff0002ebf2f61be67eb05421e51d5a7d089432502688a26a57f8ab17d083`.
- `README.md` dans le ZIP : `b703575261dd87aea4ed5d44ea6db22e7a8bd7c4c3403813c134d30cc25ee275`.

## Restaurer l'archive, sans dépendance ni téléchargement supplémentaire

Depuis une copie locale du dépôt, dans Bash sous Debian/WSL2 :

```bash
# D4RLING-AUDIO-01 / Debian WSL2 / Bash
# Repertoire de travail : copie locale du depot D4RLING
# Ecriture : uniquement dans /home/<utilisateur>/d4rling-audio01
# Installation / suppression / modification systeme : aucune
cd "$HOME/d4rling" || exit 1
mkdir -p "$HOME/d4rling-audio01"
base64 -d experiments/audio01-native/D4RLING-AUDIO-01-original.zip.b64 > "$HOME/d4rling-audio01/D4RLING-AUDIO-01-original.zip"
sha256sum "$HOME/d4rling-audio01/D4RLING-AUDIO-01-original.zip"
unzip -t "$HOME/d4rling-audio01/D4RLING-AUDIO-01-original.zip"
```

Comparer l'empreinte affichée à celle indiquée ci-dessus. Le nom du dossier où se trouve la copie locale est à ajuster si nécessaire.

## Tests et portée des preuves

Un autotest du générateur et de l'ABI ctypes a été exécuté sur l'environnement de conservation le 8 novembre 2026 : `SELF_TEST_PASS`, 55 125 frames, 220 500 octets PCM, `PASampleSpec=12`. **Ce n'est pas un essai sonore sur le 5700X**, ni une exécution Darwin i386. Aucun journal utilisateur n'est incorporé à cette archive.

Le programme distingue `SELF_TEST_PASS`, prévol `--probe`, et `PCM_SENT_TO_PULSE_SERVER_AUDIBILITY_UNVERIFIED`. L'acceptation du PCM par PulseAudio ne prouve pas que le son a été entendu.

## Propriété intellectuelle et confidentialité

Le ZIP contient uniquement le script original créé pour ce banc et une notice originale ; il ne contient **aucun exécutable Apple, QuickTime, ressource Logic/EXS24, échantillon sonore commercial, fichier tiers incorporé ou donnée personnelle identifiée lors de la revue**. Le script invoque dynamiquement PulseAudio sur la machine de test ; aucune bibliothèque PulseAudio n'est vendue ou redistribuée ici.

Cette vérification concerne **uniquement ces fichiers** : elle n'est pas une certification des droits de l'ensemble du fork, ni des autres archives audio du projet.

Voir aussi `docs/REPRISE-AUDIO-MUSIQUE-2026-11-08.md` (reprise des conversations) et `PROJECT_STATE.md` (historique et protections).
