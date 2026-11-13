# AUD-C11-A1 — prévol du défaut de reprise Play/Stop/Play

**Date :** 13 novembre 2026. **Périmètre :** CoreAudio / PulseAudio i386 seulement. **État :** diagnostic incomplet, aucune correction proposée, aucun test audio réel effectué dans cette session.

## Provenance

- Dépôt canonique `fr4nck/d4rling`, `master`, inspection initiale au SHA `0d9a02f3a0876080a2ab1ac638d34af4098da5b2`. Avant publication, `master` a avancé à `ea0fa13c5c739c5f4581c5588579c84913a52832` (checkpoint QuickTime disjoint).
- [Issue #9](https://github.com/fr4nck/d4rling/issues/9), ouverte au moment du prévol. Elle **rapporte** l'essai local C10/r11, sans publier les journaux originaux.
- Le `git/trees` récursif de l'instantané initial (29 368 entrées, `truncated=false`) ne contient aucun `pulse_host.c`. Le banc C10/r11 et ses journaux ne sont pas récupérables depuis `master`.
- Sources du backend natif lues, mais **non exécutées** : `src/CoreAudio/CoreAudio/pulse/AudioHardwareStreamPAOutput.cpp` (blob `278630f0296b38167796a94d9d9b5f3c05f93d25`) et `src/CoreAudio/CoreAudio/pulse/AudioHardwareStreamPA.cpp` (blob `0db6ebda74ae08b9281d70853b694d27cbd04a1c`).

## Observation historique distincte de la vérification

L'issue #9 rapporte premier Play OK, Stop avec `cork` et `flush`, puis second Play : deux blocs / 16 384 octets, `C10_PROTOCOL_ERROR version:3 op:2 status:2`, `C10_RPC_FAIL op:2`, hôte sorti avec statut 14, sans second `C10_PULSE_UNCORKED=PASS`. **Ces résultats n'ont pas été reproduits ici.** Le `status:2` du protocole C10 ne doit pas être interprété comme une erreur PulseAudio avant lecture du mapping local.

## Distinction architecturale décisive

Le backend C++ présent dans `master` utilise notamment `pa_stream_begin_write`, `pa_stream_write` et `pa_stream_connect_playback`. Sa méthode `AudioHardwareStreamPA::stop()` appelle `pa_stream_disconnect`. Le banc B14/C10 décrit dans l'issue repose sur un hôte ELF64 privé, un transport FIFO/RPC et une séquence `cork` + `flush` à Stop. **Ne pas corriger automatiquement le backend C++ pour expliquer un échec encore non localisé dans l'hôte C10.**

Documentation primaire PulseAudio : [streams](https://www.freedesktop.org/software/pulseaudio/doxygen/streams.html), [stream.h](https://www.freedesktop.org/software/pulseaudio/doxygen/stream_8h.html), [async API](https://www.freedesktop.org/software/pulseaudio/doxygen/async.html). `pa_stream_cork()` renvoie une `pa_operation*` et termine de manière asynchrone ; distinguer pointeur nul, état de l'opération, callback `success`, timeout, état du stream et `pa_context_errno`. Les accès à un contexte PulseAudio doivent respecter le contrat de thread du mainloop.

## Test discriminant et critère de sortie A1

Dans une **copie privée** du vrai banc C10 (aucune modification des runs r01–r11) :

1. Lire `src/pulse_host.c` réellement utilisé, `write_pcm()`, les appels de reprise et la table de correspondance `op:2 / status:2` ; relever SHA-256 des sources, hôte et binaires de qualification.
2. Identifier chaque retour d'échec de `write_pcm()` et la transition après Stop, sans changer timing ni comportement.
3. Instrumenter de manière ciblée : état contexte/stream, `pa_stream_is_corked`, `pa_stream_writable_size`, taille PCM, résultat `pa_stream_write`, création/fin/callback de `pa_stream_cork`, erreur `pa_context_errno/pa_strerror`, timeout et étape RPC.
4. Reproduire le second Play de façon contrôlée **uniquement lorsque l'exécution audio aura été autorisée** ; aucun audio n'a été lancé par ce checkpoint.

**A1 = BLOCKED (source et journaux C10/r11 non accessibles dans cette session).** **A2 = NON COMMENCÉ.** Aucun PASS i386, acoustique ou Logic 8 nouveau n'est revendiqué. Le prévol du dépôt et la distinction entre les implémentations sont, eux, vérifiés directement.
