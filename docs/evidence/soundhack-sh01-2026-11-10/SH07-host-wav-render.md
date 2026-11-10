# SH07 — Hôte : WAV PCM16 traité par le RealFFT original de SoundHack

10 novembre 2026 — **HOST WAV RENDER PASS**, limité à un traitement de fichiers sur Linux, sans invité Darwin i386, sans lecture matérielle et sans exécutable SoundHack.app.

## Objectif et preuve

Transformer réellement un fichier audio WAV en un second WAV par une coupe fréquentielle en utilisant le code original de Tom Erbe. Qualifier le format, la transformation, la conservation de la durée et les refus des entrées dangereuses. Aucun changement CarbonCore, QuickTime, BSD, CoreAudio ou Petite Victoire.

**Sources originales** : tomerbe/SoundHack@df6f0bc89243b93573b391afa5ab371cce56ac95 (licence MIT), Math/FFT.c Git blob **b132ab450a71b451f5ae9e5649c98a6a41c9f9e9**, Math/FFT.h Git blob **f31c2d41526d3768ad7cb0f10993847d2bd6ae84**. Les deux fichiers ont été vérifiés avec git hash-object dans une zone temporaire privée; aucun code source tiers ni binaire propriétaire n'est publié dans ce lot. La licence des nouveaux témoins est GPL-3.0-or-later.

## Chaîne réellement exécutée

SH07 ajoute wav_fft_render.py, qui réutilise la vérification des empreintes de fft_host_probe.py (SH06), compile le FFT.c original inchangé en bibliothèque temporaire hôte, ouvre un WAV mono PCM signé 16 bits, exécute RealFFT avant/après une suppression de bins, applique une synthèse par recouvrement pondéré (fenêtre de Hann périodique, hop N/4, normalisation de la somme des fenêtres au carré), et crée le WAV de sortie exclusivement (aucun écrasement). Aucun accès réseau ni installation, et la bibliothèque compilée est détruite avec son répertoire temporaire.

Bornes : 1 MiB par entrée, 384 000 échantillons maximum, mono PCM16 non compressé, fréquence d'échantillonnage entre 8 et 192 kHz, FFT 256/512/1024/2048 points, rayon 0 à 6 bins. Le filtre est une démonstration de coupe spectrale et non un modèle d'effet SoundHack identique. La sortie saturée est quantifiée en PCM16 et la fréquence ciblée est arrondie à un bin.

## Mesures observées (GCC 14.2 / Python 3.13.5 / Linux x86_64)

Signal généré : 1 seconde, mono PCM16, 48 000 échantillons, 0,45 sin(750 Hz) + 0,25 sin(3 000 Hz). Filtrage : FFT 1024, rayon 2 bins centré sur 3 000 Hz. Mesure indépendante de l'amplitude de chaque raie par produits scalaires sin/cos sur tous les échantillons :

| Composante | WAV original | WAV filtré | Observation |
| --- | ---: | ---: | --- |
| 750 Hz | 0,449980913 | 0,449981183 | composante conservée |
| 3 000 Hz | 0,249987953 | 0,000221391 | atténuation ≈ 61,1 dB |
| Durée / échantillons | 1 s / 48 000 | 1 s / 48 000 | inchangé |

SHA-256 WAV original : 6555ab92ecbac9f24fdde12d221324b83076c725f83fd91e21737ea791071dd8. SHA-256 WAV filtré : d21df4541490bddc7d0c67c4002ad59983c806e4bd5b4d66df7bc183d82b2efb. Ces deux WAV sont des signaux de test originaux privés à la session, pas des fichiers binaires committés dans Git.

### Régressions

- 18/18 tests unitaires SH07 avec les sources originales épinglées, incluant : cas numérique WAV réel, fichier court non multiple du hop, silence, mutation d'empreinte source, refus WAV tronqué/non-WAV/stéréo/PCM8/taille ou fréquence invalide, non-écrasement de fichier existant ou symlink, sortie absente si erreur.
- 18 cas sans sources externes : 14 PASS / 4 SKIP, aucune réussite fictive.
- Suite SoundHack SH01–SH07 réunie dans une zone de qualification privée : **79 tests, 78 PASS / 1 SKIP**, 0 échec, avec source FFT originale disponible (un test SH05 exige un checkout complet absent dans cette zone). Aucun CI payant.

## Reproduction (Bash Linux, depuis la racine D4rling)

Les sources MIT doivent exister dans un chemin autorisé, sans téléchargement implicite. Le script n'installe rien et ne modifie pas le dépôt ni une installation Darling :

    export SOUNDHACK_MATH_DIR=/chemin/autorise/SoundHack/Math
    python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 -p 'test_wav_fft_render.py' -v
    python3 reproduction/fixtures/soundhack-i386/wav_fft_render.py \
      --math-dir "$SOUNDHACK_MATH_DIR" --input /chemin/du.wav \
      --output /chemin/nouveau.wav --notch-hz 3000 --fft-size 1024 --radius-bins 2

Exit 0 : HOST_WAV_RENDERED borné ; exit 3 : INCONCLUSIVE. Le refus d'écraser une sortie existante est intentionnel. Ne pas interpréter la sortie comme une preuve de lecture de l'application, de GUI, de driver, de son entendu, de dyld, ou d'ABI i386.

## Chantiers en parallèle

SH05 reste un blocage potentiel avant MainLoop dans Gestalt.cpp (sélecteur Carbon 'cbon' absent ; chute de contrôle 'sysv' vers architecture) : issue [#13](https://github.com/fr4nck/d4rling/issues/13) attribuable au chantier CarbonCore. Les sources SoundHack confirment aussi les dépendances QuickTime non opérationnelles ; pas de modification production ici. L'archive d'exécutable 0.896 officielle (UCSD) n'a pas pu être téléchargée à cause d'une panne de résolution DNS depuis l'environnement ; les imports réels et les étapes SH-LOAD/GUI/FILE/DSP/AUDIO restent à qualifier en invité.
