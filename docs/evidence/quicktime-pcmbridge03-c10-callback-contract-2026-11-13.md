# Bridge 03 — contrat de callback CoreAudio C10 (13 novembre 2026)

**Nature de preuve :** sortie *lecture seule* du terminal 5700X fournie par l'opérateur ; inspection des sources C10 locales `src/audio_worker.cpp`, `src/transport.c` et `src/pulse_host.c`. Aucun build, aucune exécution CoreAudio, aucun son, aucune écriture et aucun test de compatibilité Logic 8 pour ce lot. Code C10 local absent de `master` ; ne pas le présenter comme code GitHub.

## Entrée qualifiée

- Rapport Bridge 02 `.../qt-pcmbridge02.l6aF2xzN/result.json`, SHA-256 `62d5ecdde89f622e571f079a36907a9d4150a26edb9b4c9ba117af2a2b8494f1`.
- Contrôle local `BRIDGE02_INPUT=PASS`, `status=QT_PCM_BRIDGE02_PASS`, `guest_exit=0`, `protected_inputs=UNCHANGED`.
- Fichiers sources lus sans modification, hashes :
  - `C10/src/audio_worker.cpp`: `3d75c5f39d4325658344c14a460002d6b4337a5baaef5dc2a5a78f843f1ad5bb`.
  - `C10/src/transport.c`: `71e682ba8138b6bb3d09e2179297dab08b154ea99d19316afa1fe93be4e5b0a1`.
  - `C10/src/pulse_host.c`: `89cbd31202294267fe51a347572b18ee05915e60a1d6cc6e3fb03f40239904d8`.
- Sortie finale : `BRIDGE03_CALLBACK_CONTRACT=INSPECTED`, `COREAUDIO_EXECUTION=NOT_STARTED`, `AUDIO=NOT_RUN`, `FILES_MODIFIED=0`.

## Flux observé dans le code, pas encore exécuté avec QuickTime

`audio_worker.cpp` lignes 28–38 définit `render(AudioDeviceID,const AudioTimeStamp*,const AudioBufferList*,const AudioTimeStamp*,AudioBufferList*,const AudioTimeStamp*,void*)`, puis compte les tentatives et vérifie **`now`**, **`when`**, **`out`** non nuls, **`out->mNumberBuffers==1`**, `out->mBuffers[0].mData` non nul, **`mNumberChannels==2`**, **`mDataByteSize==8192`**, puis appelle **`pv::Playback::render(static_cast<float*>(out->mBuffers[0].mData),1024)`** et incrémente le compteur callback. La source n'utilise pas le paquet QuickTime Bridge 02.

`audio_worker.cpp` lignes 54–86 sélectionne le périphérique CoreAudio de sortie, enregistre l'IOProc via `AudioDeviceCreateIOProcID`, démarre `AudioDeviceStart`, appelle `d4rl_mock_pump()` sur le chemin B14 puis vérifie qu'un callback supplémentaire a eu lieu. Les chemins Stop détruisent l'IOProc. Cela est la structure du banc **C10**, pas une qualification autonome d'une HAL générique.

`transport.c` (ABI i386) impose par `_Static_assert` `sizeof(void*)==4`, `sizeof(pa_sample_spec)==12` et `offsetof(pa_sample_spec,channels)==8`. Il utilise un protocole FIFO avec en-têtes 32 octets, paquets et champs entiers little-endian (`put32`/`get32`).

`pulse_host.c` lignes 59–101 vérifie le format exact de sortie : **`PA_SAMPLE_FLOAT32LE` / 44 100 Hz / 2 canaux** ; la requête `version=3, op=2` exige **`length=8192`**. `write_pcm()` refuse tout Float32 non fini ou d'amplitude absolue supérieure à 1, attend une capacité suffisante du stream, transmet via `pa_stream_write`, puis enregistre les compteurs/mesures. La mécanique de second uncork lors de Stop/Play reste le sujet **AUD-C11-A1**, et ne doit pas être modifiée par Bridge 03.

## Décision : porte suivante

- **Format Bridge 02 conforme au consommateur C10 pour ce vecteur fini** : 551 frames interpolées 8k→44,1k et 473 frames nulles, soit 1 024 frames / 8 192 octets ; FNV-1a 64 : `460bcbe2c02d9d4d`. Ce paquet reste un *artefact de démonstration*, pas une politique de streaming ou une preuve de qualité audio.
- **Bridge 03 candidat** : dans une nouvelle zone isolée, qualifier d'abord le *contrat d'IOProc* et la consommation mémoire d'un paquet de 8 192 octets avec gardes, champs invalides et lecture unique, en réutilisant le témoin QuickTime Bridge 02 sans modifier C10. Ce test de callback direct demeure **hors CoreAudio réel** ; ne pas utiliser `COREAUDIO_PASS` pour le décrire.
- Intégration suivante, **distincte et non autorisée implicitement** : véritable enregistrement du callback `AudioDeviceIOProc` dans la HAL B14, transport FIFO, hôte PulseAudio (muet en premier), orchestration C10 ; définir et protéger les autres espaces de travail et résoudre les collisions potentielles avec AUD-C11 avant de lancer une telle campagne.
- Pas de changement production, pas de copie de binaires commerciaux, pas de son, pas d'installation, pas de mouvement de fichiers historiques.

**Verdict actuel : `BRIDGE03_CALLBACK_CONTRACT=INSPECTED`.** `BRIDGE02=PASS` pour le paquet hors audio. `COREAUDIO_WITH_QUICKTIME=NOT_TESTED`, `AUDIO=NOT_TESTED`, `LOGIC8=NOT_TESTED`.
