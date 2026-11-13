# D4rling — Bridge 02 / contrat tampon QuickTime → C10 (13 novembre 2026)

**Source de preuve :** sortie du prévol lecture seule transmis par l'opérateur du 5700X (Bash Debian WSL2) ; les fichiers C10 locaux n'ont **pas** été ouverts par cet agent. Lecture du code `AudioHardwareImpl.cpp` effectuée séparément sur GitHub. Aucune exécution audio, compilation ou modification de production lors de ce prévol.

## Versions et contrôles

- Dépôt GitHub de coordination : `fr4nck/d4rling` `master@74e10efa604470c08a8e2a925e646640d33aca01` au prévol de ce checkpoint.
- Checkout historique 5700X : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/source@5b521087d79d4348ebe312e622a05f1f8b55c110`, modifications préexistantes `security` et `CarbonEventsCore.c` inchangées.
- Bridge 01 R1 rapport `qt-pcmbridge01-r1.HOhpTUvF/result.json` : `QT_PCM_BRIDGE01_R1_PASS`, `guest_exit=0`, `protected_inputs=UNCHANGED`.
- C10 local : `/home/Deniel/d4wrling-work/petite-victoire-v0.1/C10`, source `src/audio_worker.cpp` SHA `3d75c5f39d4325658344c14a460002d6b4337a5baaef5dc2a5a78f843f1ad5bb`, `src/transport.c` SHA `71e682ba8138b6bb3d09e2179297dab08b154ea99d19316afa1fe93be4e5b0a1`, `src/pulse_host.c` SHA `89cbd31202294267fe51a347572b18ee05915e60a1d6cc6e3fb03f40239904d8`.
- Binaires C10 authentifiés par SHA : `CoreAudio-B14.dylib` `9512aa6a39d0d31abe4634235eb44194bd90d3904f847ea7b2fe8da0b1023721`; `libpulse-B14.dylib` `440a30ea7ad5ec252cb19f17cc2b78baef9c8c4e98753f548e9bfb3f9eb873b1`; `petite-victoire-C10-i386` `26105cd7a64844e1b4b511959468338ff213b31da384e6e50cbcb3fe7152cc6f`. Le programme et les dylibs sont Mach-O i386.
- `SOURCE_FILES_MISSING=0`, `CONTRACT_SOURCE_REVIEW=COMPLETE`, `FILES_MODIFIED=0`, `COREAUDIO_EXECUTION=NOT_TESTED`, `RESAMPLING=NOT_TESTED`, `AUDIO=NOT_RUN`.

## Contrats observés et limites

| Propriété | QuickTime C3 / Bridge 01 R1 | C10 B14 / hôte Pulse |
|---|---|---|
| PCM | `twos`, SInt16 big-endian ; conversion testée en Float32 natif | `PA_SAMPLE_FLOAT32LE` attendu explicitement par `pulse_host.c` |
| Canaux | Mono source → 2 canaux entrelacés dans le témoin | 2 canaux |
| Fréquence | 8 000 frames/s (100 frames → 12 500 µs) | 44 100 frames/s |
| Octets/trame de destination | 2 canaux × 4 octets = 8 | 2 × 4 = 8 |
| Bloc callback | Non applicable au convertisseur mémoire | `audio_worker.cpp` contrôle `mDataByteSize=8192` et `mNumberChannels=2` : 1 024 frames |

**Défaut distinct constaté dans le source du backend historique** `src/CoreAudio/CoreAudio/AudioHardwareImpl.cpp` (GitHub) : `mBytesPerFrame` et `mBytesPerPacket` sont calculés avec le facteur `mSampleRate`, produisant 352 800 octets au lieu de 8 pour 44,1 kHz Float32 stéréo. Cette observation statique **ne prouve pas que le chemin B14/C10 en cours emprunte ce constructeur**, et n'autorise pas de correctif transversal depuis le chantier QuickTime. AUD-C11-A1 poursuit son diagnostic indépendant du Stop/Play.

## Critères pour le lot hors audio Bridge 02

1. Vérifier les SHA source et binaires C10 sans lancer C10, PulseAudio ni son. Réutiliser l'artefact QuickTime/Bridge 01 R1 déjà qualifié.
2. Dans un **nouveau témoin privé Mach-O i386**, appeler `GetMediaSample` sur le même MOV synthétique de 100 frames, puis convertir son PCM S16BE mono en Float32LE stéréo **à 44 100 Hz** via un rééchantillonneur **de démonstration isolé**. Ne pas intégrer ce candidat dans le moteur audio.
3. Fixer une convention de longueur pour le test fini : `floor(100*44100/8000)=551` frames et reste `2000/8000` d'une frame de sortie. Le vrai moteur devra spécifier séparément phase continue, fin de flux et alimentation multi-blocs. Utiliser un padding explicite de `1024-551=473` frames de silence pour former **un seul bloc C10 8 192 octets**. Ce remplissage est un artefact de test, pas une politique d'écoute validée.
4. Comparer **tous les octets des 8 192** à un oracle distinct réalisé en Python, vérifier borne de sortie, signe, canal gauche/droite, padding et entrées invalides. Réduire au maximum les chemins implicites.
5. Exécution en namespace invité isolé, sans réseau, audio, installation, nettoyage, git write, modification de préfixes historiques. Sauvegarder `result.json`, hashes et marqueurs d'une nouvelle campagne ; distinguer pass de conversion/horaire de toute vraie `CoreAudio API` ou sortie acoustique.

**Statut actuel : Bridge 02 en conception/qualification, non encore exécuté.** `COREAUDIO=NOT_TESTED`, `AUDIO=NOT_TESTED`, `LOGIC8=NOT_TESTED`.
