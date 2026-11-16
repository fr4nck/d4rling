# LOGIC-L3 — chargement AppKit i386 via GLU05 (16 novembre 2026)

**Jalon borné : `L3_APPKIT_I386_DLOPEN_PASS_RECOVERED`.** Journal d'exécution **transmis par l'opérateur depuis le 5700X**, puis relu en récupération locale, sans rejeu par l'agent publiant cette note. Un témoin Mach-O i386 original charge par `dlopen(RTLD_NOW | RTLD_LOCAL)` le **véritable** AppKit de Cocotron dans une installation privée de D4rling ; **Logic Pro 8 n'a pas été lancé**.

## Provenance et isolation

- Dépôt public relu avant publication : `fr4nck/d4rling`, `master@dd0e479e34e04aa55d8238df432b40f510f81f9b`. Les essais portent sur un **checkout de banc historique** `a007a5399d40868588d8cf7fbba97b726506ffa3` et l'installation **B13 privée** : ce résultat ne qualifie pas le build du `master` courant.
- AppKit de Cocotron, Mach-O FAT i386/x86_64, présent sous `<B13_PRIVATE_INSTALL>/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit` et identique au binaire de build ; SHA-256 : `3df8cd07012ca2392364f322fe97e34d5e487c69445dbab69aeb9db2937f6c93` ; UUID i386 : `c5cae6152a72390b81bd23ec46b0ed6f`. L'identité des artefacts est démontrée, **pas une reconstruction depuis les sources exactes** du sous-module.
- Cocoa réel disponible (non exécuté dans ce lot), SHA-256 : `cc411a1b682cf80b5e289cc0f4ebe08ef7e20489711cb599339624cdde002369`, UUID i386 : `2c33a71391163f84ad5dce241ec7e9fb`.
- Témoin i386 original `dlopen(AppKit)` : SHA-256 `0797644e378261cbbaf11eba97acf75a3d4f0f2a161e64b8c3d5cbf9f9d93d81`.
- Réutilisation du cache GL07 Carbon i386 qualifié (SHA-256 `9a6e38626d0cea271cca99ec37fee23281a8a30671fe9cfbcd4d92e5177e4d6d`). AppKit04 s'arrêtait en invité RC 134 sur `Cannot load libGLU.so.1 (ELF)`.
- GLU05 : fermeture Debian signée `libglu1-mesa:i386` **7 paquets dont 5 déjà disponibles**, seuls `libglu1-mesa` version `9.0.2-1.1+b3` et `libopengl0` version `1.7.0-1+b2` extraits en privé. Nouveau `libGLU.so.1` ELF32 SHA-256 `994ca3ad260bc3fa3f9b0eb4145764d6bb8a40f151fc26e2964cf27b0188e0a2` ; cache privé SHA-256 `9fb05674dc0b0a69b4eedda982f97748727ba70f0052ba854f30c466b544c99c`.
- Aucune installation globale, aucune écriture Git ni modification des préfixes B12/B13. Nouveau préfixe isolé avec UID/GID délégués et cache ELF32 privé lié en lecture seule dans le namespace invité.

## Observations GLU05 puis récupération

Le script GLU05 a **préparé la fermeture et effectivement exécuté le témoin**, mais sa construction du rapport final Python a levé `AttributeError: 'NoneType' object has no attribute 'get'` : la variable locale utilisée pour les métadonnées avait été écrasée. Cet incident de rapport ne doit pas être confondu avec le résultat du processus invité.

Un script de récupération **en lecture seule** a relu les journaux déjà présents, le code retour, les métadonnées du runner et les empreintes, sans relancer le témoin :

```text
PINNED_INPUTS=5/5
SOURCE_HEAD=a007a5399d40868588d8cf7fbba97b726506ffa3
RUN_DIRECTORIES=1
RUN_LABEL=ag05a6e95c
GUEST_RC=0
RUNNER_RECORDED_GUEST_RC=0
METRIC_HOST_MOUNTS_BEFORE=36
METRIC_HOST_MOUNTS_AFTER=36
METRIC_DARLINGSERVER_BEFORE=0
METRIC_DARLINGSERVER_AFTER=0
METRIC_RESIDUAL_PREFIX_PROCESSES=0
ACTIVE_PREFIX_PIDS=NONE
CLEANUP=PASS
INTEGRITY=PINNED_INPUTS_VERIFIED
NEXT_BLOCKER=NONE_OBSERVED
L3_APPKIT_PROBE pointer_size=4
APPKIT_LOAD_PASS /System/Library/Frameworks/AppKit.framework/Versions/C/AppKit
STATUS=L3_APPKIT_I386_DLOPEN_PASS_RECOVERED
EXIT_CODE=0
```

Les **5 entrées épinglées** sont revérifiées, mais ce contrôle de récupération n'est **pas** une requalification de tout le système ou de toutes les dépendances : ne pas extrapoler `PINNED_INPUTS_VERIFIED` en `INTEGRITY=UNCHANGED` global. Le nettoyage est confirmé par les métriques du banc et l'absence de PID utilisant le préfixe possédé.

Journaux privés conservés : `<L1_STAGE>/logic-l3-appkit04.ixO0LadJ/`, `<L1_STAGE>/logic-l3-glu05.ygbSODx9/runs/ag05a6e95c/` et les caches correspondants ; aucun binaire ni chemin personnel public.

## Limites et suite

**AppKit est chargé en i386**, mais aucune méthode `NSApplication`, fenêtre, événement Cocoa, affichage OpenGL, interaction souris/clavier, audio, MIDI ni logiciel Logic n'a été exécuté ou qualifié. Les défauts ABI `NSCell`/`NSMenu` étudiés parallèlement ne sont ni validés ni corrigés par un `dlopen`. Les sources Cocotron ne sont pas matérialisées dans le checkout L1 ; AppKit chargé est l'artefact B13, pas un stub, et ne démontre pas une reconstruction du `master` courant.

**Prochaine expérience :** `dlopen(Cocoa.framework/Versions/A/Cocoa)` avec le même runtime B13 et cache GLU05, via un témoin original i386 dans un préfixe neuf. Critère d'arrêt : code retour, marqueur de chargement, dépendances manquantes observées et nettoyage du namespace. Ne pas démarrer Logic.

[Précédent : Carbon GL07](2026-11-16-logic-l2-carbon-i386.md) · [Matrice de besoins Logic](2026-11-14-logic-l1.md).
