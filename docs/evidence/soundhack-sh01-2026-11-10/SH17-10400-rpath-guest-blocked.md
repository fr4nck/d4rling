# SoundHack SH17 — premier lancement invité i386 : blocage du chargeur `@rpath`

**Date de réception des preuves : 15 novembre 2026. Source : sortie du terminal i5-10400, Debian WSL2, transmise par l'opérateur.** L'assistant ne dispose pas du poste et n'a pas rejoué cette exécution.

**Verdict : `SH17_GUEST_LOAD=BLOCKED_RPATH`.** Le binaire du témoin a été compilé et lié, puis réellement lancé via le lanceur invité privé de D4rling. Il n'a **pas** exécuté les fonctions de SoundHack, car le chargeur n'a pas trouvé la dylib FFT SH16. Ce n'est pas un échec numérique FFT.

## Observations

- Dépôt local `master@3f103d08f4d1ef32a655aac49972c9481977454b` ; source/build/installation historiques 10400 préservés.
- `SH17_PREFLIGHT=PASS`, `SH17_STAGE=COMPILATION`, `SH17_STAGE=LINK` ; l'exécutable invité `sh17-fft-guest-i386` a pour SHA-256 `a7e37d973ebd34d302166321b0ab72e711a830a506d4c1f23f7c9001853699b0`.
- `SH17_STAGE=VRAI_INVITE_DARLING_I386` ; vrai `reproduction/run-guest.sh` utilisé sur l'installation privée 10400, code retour **1** et rapport conservé sous `/tmp/d4rl-replay.LWNjIZ2A`.
- Sortie de `dyld` : `Library not loaded: @rpath/libSoundHackFFT_i386.dylib` ; `Reason: no suitable image found`. Les chemins de fallback `/Users` et `/usr` n'aboutissent pas.
- `No shared cache present` est également affiché ; son rôle causal n'a pas été établi.
- Aucun marqueur positif `SOUNDHACK_SH17_...PASS` observé ; `SOUNDHACK_SH17_GUEST_FFT_PASS` **NON acquis**.

## Interprétation bornée et reprise

La dylib SH16 existe réellement et a été liée sur le 10400 : `libSoundHackFFT_i386.dylib` (8 688 octets ; SHA-256 `c578572e4679985a76d79c61717a5339799c3e638d0347963f130df38db76ed1`). Son nom d'installation est `@rpath/libSoundHackFFT_i386.dylib`. La première liaison de SH17 utilisait `-rpath @executable_path`. Il reste à établir par essai pourquoi ce chemin ne permet pas à `dyld` de localiser la dylib.

Le banc Carbon i386 historique utilisait `@loader_path/libD4CarbonEvents.dylib` et a passé les contrôles NORMAL/BYPASS/NÉGATIF sur le 10400. Le test discriminant proposé pour SH17 consiste donc à **conserver la dylib exacte SH16**, mais produire **un nouvel exécutable de témoin seulement** dont la commande `LC_LOAD_DYLIB` référence directement `@loader_path/libSoundHackFFT_i386.dylib`. `llvm-install-name-tool-19 -change` est adapté à cette opération ; le lieur cctools peut réémettre un exécutable avec `-headerpad_max_install_names` si l'ancien n'a pas assez de place. Vérifier le nouveau `LC_LOAD_DYLIB` avant le lancement, puis exiger code invité 0 et tous les marqueurs numériques.

Le script de reprise est fourni **directement en bloc Bash dans la conversation**, pas comme ZIP ; **il n'a pas encore été exécuté sur le 10400**. Aucune nouvelle installation, récupération réseau, mise à jour Git, suppression ou modification des sources, de la bibliothèque SH16, du build et du préfixe privé.

La prochaine preuve possible est `SOUNDHACK_SH17_GUEST_FFT_PASS` uniquement après exécution effective et vérification des oracles dans l'invité i386. Le lancement de SoundHack.app et la sortie audio restent hors de cette épreuve.
