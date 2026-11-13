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

## Complément C11-A1 : chemin du second uncork (13 novembre 2026)

**OBS rapportée** par l'opérateur du 5700X, non rejouée par l'agent : sortie de lecture seule avec vérification SHA-256 `89cbd31202294267fe51a347572b18ee05915e60a1d6cc6e3fb03f40239904d8` du `src/pulse_host.c` local, SHA des logs `pulse.log` = `3628072b0ac00a18d3f22efb88c2fce28373a39150d4ed6359ad12aad6c2866b` et `guest.log` = `545bf5d93e1166b1aed4d3282cabbbd0ac90716437e88b5b623e2b4f07c29fc2`. Code source lignes 20–164 et logs de r11 ont été communiqués textuellement ; la provenance du binaire exécuté n'a pas été contrôlée directement par l'agent.

**Inférence forte sur le chemin de contrôle (pas encore cause PulseAudio démontrée)** :

- `suspend_stream()` exécute avec succès `pa_stream_cork(stream,1)` puis `pa_stream_flush()`, et remet `corked=1`, `prefilled=0`.
- `write_pcm()` incrémente `bytes` et `blocks` après `pa_stream_write` et l'écriture de capture, puis, lorsque `corked && ++prefilled >= 2`, appelle `operation(pa_stream_cork(stream,0,completed,NULL))` **avant** `corked=0`, `starts++` et le marqueur `C10_PULSE_UNCORKED=PASS`.
- Stop : `bytes=11296768` (1 379 blocs). Sortie d'erreur : `bytes=11313152` (1 381 blocs). Les **deux blocs supplémentaires = 16 384 octets** correspondent exactement au seuil de préremplissage, sans nouvel `UNCORKED=PASS` ; le `status:2` est attribué dans la branche `if(!write_pcm(...))` à l'opération RPC C10.
- Le second `C10_COREAUDIO_START` est à `435530.988051` et le `C10_COREAUDIO_STOP` consécutif à `435531.990420`, environ 1,002 s plus tard. L'attente `operation()` a précisément une échéance de 1,0 s : **timeout plausible**, sans exclusion d'un échec immédiat ou d'un callback négatif. Les heures du log invité ne donnent pas seules le temps de réponse PulseAudio exact.

**Diagnostic A1 raffiné :** la **branche en échec** est fortement localisée dans la demande d'uncork asynchrone du deuxième Play, sous réserve de vérification du lien entre source et binaire r11. Le **motif** reste à départager : `pa_stream_cork` renvoie NULL ; opération `RUNNING` à 1 s ; `CANCELLED` ; état `DONE` sans `success=1` ; erreur de contexte/flux. Ne pas augmenter arbitrairement les délais ni changer l'ordonnancement avant instrumentation.

**Suite bornée :** fabriquer une seule copie instrumentée hors du dépôt et des campagnes historiques ; compiler si les dépendances libpulse sont déjà présentes, **ne pas exécuter de son** ni le banc C10 avant autorisation distincte. Source de production, QuickTime, moteur Logic, HAL et backend C++ : inchangés. A1 reproduction instrumentée = **NON EXÉCUTÉE** ; A2 correctif = **NON COMMENCÉ**.
