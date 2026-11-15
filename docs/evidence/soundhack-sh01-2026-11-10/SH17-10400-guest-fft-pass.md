# SoundHack SH17 — FFT originale exécutée dans l'invité Darling i386

**15 novembre 2026 — `SOUNDHACK_SH17_GUEST_FFT_PASS` (observation opérateur sur i5-10400, Debian WSL2).**

**Portée acquise :** la véritable bibliothèque SoundHack SH16 a été chargée par `dyld` depuis un exécutable Mach-O i386 ; `InitFFTTable()`, `FFT()` et `RealFFT()` ont réellement été appelées dans l'invité D4rling. Le témoin a terminé avec code **0**, et les quatre marqueurs attendus ont été présents dans `stdout.log`. **Non acquis :** application SoundHack, GUI, codecs, traitements de fichiers audio, restitution sonore, ou prise en charge générale de toutes tailles FFT.

## Provenance et environnement

- Source de cette qualification : **sortie intégrale du terminal** `franck@DESKTOP-0OTERF7`, transmise par l'opérateur. L'assistant n'a pas exécuté le binaire sur ce PC et n'a pas accès aux octets de ses journaux.
- Dépôt local : `master@3f103d08f4d1ef32a655aac49972c9481977454b` ; dépôt distant à une autre révision, sans mise à jour locale pendant l'essai.
- Reconstitution : `~/atelier/d4rling-10400/source@b7d0cb6a79fe196657deb9711647f8486bcc5e5e`, build/installation privés historiques inchangés ; cctools-port `d9456c221e1f462e17c0b3297748bc089d5a861e`.
- Bibliothèque réelle et inchangée : `validation/soundhack-sh16/libSoundHackFFT_i386.dylib`, SHA-256 `c578572e4679985a76d79c61717a5339799c3e638d0347963f130df38db76ed1` (8 688 octets). Fonctions FFT issues de `tomerbe/SoundHack@df6f0bc89243b93573b391afa5ab371cce56ac95`.
- Objet témoin existant réutilisé ; **nouvel exécutable uniquement** `validation/soundhack-sh16/sh17-fft-guest-loaderpath-i386`, SHA-256 `6c126699e6a2797cc9c337ebb20ade655084a0ef202e834034f544a89e6b6374`.
- Lieur cctools de la reconstruction historique et `libSystem.B.dylib` i386 de l'installation privée ; pas de nouvel arbre CMake, téléchargement, installation système, mutation Git ou suppression.

## Cause corrigée et méthode

Le premier exécutable SH17, SHA-256 `a7e37d973ebd34d302166321b0ab72e711a830a506d4c1f23f7c9001853699b0`, avait réellement atteint `dyld` mais échoué avec `EXIT_CODE=1`, car `@rpath/libSoundHackFFT_i386.dylib` était introuvable ; rapport de contre-épreuve `/tmp/d4rl-replay.LWNjIZ2A`. Voir [rapport d'échec conservé](SH17-10400-rpath-guest-blocked.md).

Pour le second essai, le véritable `ld` cctools a lié l'objet témoin **sans recompiler la FFT**, avec `-headerpad_max_install_names` ; `llvm-install-name-tool-19 -change` a remplacé **uniquement dans le nouvel exécutable** `@rpath/libSoundHackFFT_i386.dylib` par `@loader_path/libSoundHackFFT_i386.dylib`. Un contrôle indépendant des commandes de chargement Mach-O a rendu `SH17_DIRECT_LOADER_PATH=PASS` avant l'exécution. La dylib SH16 est restée inchangée (SHA-256 vérifié).

Le lanceur existant `reproduction/run-guest.sh` a lancé ce nouvel exécutable en `normal`, avec namespaces privés et timeout **25 s**, puis donné :

```text
SH17_STAGE=REAL_DARLING_GUEST
REPORT=/tmp/d4rl-replay.iZCCcM8i
EXIT_CODE=0
=== GUEST STDOUT ===
SOUNDHACK_SH17_INIT_PASS
SOUNDHACK_SH17_COMPLEX_FFT_PASS
SOUNDHACK_SH17_REAL_IMPULSE_PASS
SOUNDHACK_SH17_GUEST_FFT_PASS
=== GUEST STDERR ===
Setting up a new Darling prefix ...
sh: 1: xdg-user-dir: not found
Warning: failed to increase FD rlimit: Operation not permitted
SOUNDHACK_SH17_GUEST_FFT_PASS
SOUNDHACK_APP_EXECUTED=NO
AUDIO_TESTED=NO
```

Le `stderr` comporte des avertissements de préfixe `xdg-user-dir` et `FD rlimit`, **non bloquants dans cette exécution** ; ils ne sont pas corrigés ou supprimés ici.

## Oracle numérique réellement exercé

Le programme appelle la bibliothèque originale, pas un substitut FFT. Le [témoin source SH17](../../../reproduction/fixtures/soundhack-i386/sh17_fft_guest.c) vérifie des tables `gOmegaPi*` après `InitFFTTable`, une FFT complexe sur deux impulsions (8 valeurs complexes, spectre pair/impair analytique), l'inverse de cette FFT, puis une FFT réelle d'impulsion (16 valeurs réelles en représentation compactée), et son inverse ; les bords du tampon portent des sentinelles. Précision des comparaisons : environ `0.0005` à `0.001` absolu selon la vérification. **Les tailles invalides, les signaux audio et les spectres arbitraires ne sont pas testés.**

La copie du témoin source publiée a été **reconstituée depuis le bloc Bash livré à l'opérateur**. Son identité octet par octet avec le fichier local du 10400 n'est **pas démontrée par hash**. Un Clang disponible dans l'environnement séparé de l'assistant a néanmoins compilé cette source en vrai `MH_OBJECT` Darwin i386 ; compilation hôte distincte de l'essai invité.

## Verdict, suites et protections

**`SOUNDHACK_SH17_GUEST_FFT_PASS` — PASS invité borné et rapporté**, preuve de chargement, appel et calcul sur les signaux définis. Le passage `@rpath` → `@loader_path` démontre que l'échec initial était résolu **pour ce témoin**, pas que `@rpath` est globalement défaillant dans D4rling.

Étape suivante : **inventaire de l'exécutable et des ressources de l'application SoundHack 0.896 réellement disponibles** sur le 10400 ; analyser son format (i386/PPC/Carbon) et ses dépendances **avant** de préparer un lancement applicatif isolé. Ne pas remplacer des binaires manquants, cloner de projet, ni publier un binaire propriétaire. L'absence de l'application doit être annoncée comme un blocage matériel de cette étape.
