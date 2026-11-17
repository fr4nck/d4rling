# SoundHack SH25 — blocage du chargement __TEXT 0x1000 (5700X)

**17 novembre 2026 — bilan réel de l'opérateur, analyse hors réseau.**

SH24-R2 avait obtenu un **contrôle positif invité Mach-O i386 RC=0**,
puis une tentative de lancement de l'application officielle
SoundHack 0.896 **RC=1**.

Le lot SH25 a analysé les anciens journaux **sans nouvelle exécution
Darling**, puis rapporté :

`
EXIT_CODE=2
STATUS=SH25_OFFLINE_DIAG_PARTIAL
GATES=11/12_PASS
BLOCKED=DIRECT_FRAMEWORK_PRESENCE:AssertionError
CONTROL_RC=0
APP_RC=1
CAUSE_CLASS=RC1_PHASE_NOT_IDENTIFIED
RUNNER=GUEST_PREFLIGHT_REACHED
STDERR_BYTES=501
ERROR_IMPORT_MATCHES=0
ORIGINAL_SHA256=PASS
ERROR_HINT=Cannot mmap segment __TEXT at 0x1000: Operation not permitted
ERROR_HINT=See <url>
APP_MAIN=NOT_PROVEN GUI=NO AUDIO=NO
`

Rapport conservé :
`/home/Deniel/d4wrling-work/validation/soundhack-sh25.dVELQIxj/SH25-result.json`.
Journal :
`/home/Deniel/d4wrling-work/validation/soundhack-sh25.dVELQIxj/console.log`.

## Diagnostic RTFM

Le message `Cannot mmap segment __TEXT at 0x1000: Operation not permitted`
est **exactement celui documenté** dans
[Darling — Common Issues](https://docs.darlinghq.org/common-issues.html#cannot-mmap-segment-__text-at-0x1000-operation-not-permitted).
Darling attribue ce cas à la protection Linux `vm.mmap_min_addr`
lorsque l'exécutable veut mapper du code en dessous du seuil admis.

Le code D4rling `src/startup/mldr/loader.c` sur `master`
au 17 novembre 2026 possède déjà `mldr_explain_mmap_failure()` :
il lit `/proc/sys/vm/mmap_min_addr` en lecture seule et explique
l'échec `EPERM` d'une adresse basse. La branche de mapping
`__TEXT` emploie `compatible_mmap` en `MAP_FIXED_NOREPLACE`
pour le segment file-backed (ancienne présentation du code :
les erreurs et arguments de mapping doivent rester distingués
des adresses Mach-O sans journal de branche).

**Ce lot ne connaît pas encore la valeur réelle de
`vm.mmap_min_addr` du 5700X ni les flags `MH_PIE` et
`__TEXT.vmaddr` du témoin positif.** La restriction
`mmap_min_addr` est une explication primaire hautement probable,
**pas un test positif chiffré de SH25**.

Aucun symbole Carbon manquant ni défaut dyld n'est démontré
par les résultats disponibles. Ne pas créer de stubs.

## Douzième gate SH25 : erreur d'oracle indépendante

Le contrôle `DIRECT_FRAMEWORK_PRESENCE` lit les noms de bibliothèques
**uniquement parmi les 393 imports nlist** et impose
`len(libraries) == 7`. Or les sept commandes
`LC_LOAD_*_DYLIB` d'un exécutable n'impliquent pas
que chaque bibliothèque ait au moins un import direct
dans la table `nlist`. Une différence est donc possible
même si les sept fichiers existent. Le `AssertionError`
ne prouve pas une bibliothèque manquante.

Le prochain lot SH26 devra comparer séparément :
1. les **sept commandes de chargement** du binaire ;
2. les noms de bibliothèques réellement référencés par les imports ;
3. la présence des fichiers dans le préfixe privé.

Ne plus bloquer la vérification sur `len(set(imported_libraries))==7`.

## Suite SH26 (sans relancer SoundHack)

Un seul lot Shell autonome, sans réseau, installation, modification
de source/build/préfixe ni changement de `sysctl` :
relecture des journaux SH25, lecture du seuil
`/proc/sys/vm/mmap_min_addr`, comparaison des flags/segments i386
SoundHack et témoin positif, tests indépendants de mappings
**dans un processus temporaire, avec `MAP_FIXED_NOREPLACE`**
pour éviter tout écrasement, séparation de la présence
des sept dylibs de leurs imports, vérification d'intégrité et
bilan court auto-copié sur Windows.

**Sécurité : ne pas exécuter le `sudo sysctl` proposé
dans la documentation Darling sans décision explicite.**
Cette modification abaisserait une protection du noyau.
La préférence du projet est une solution privée/isolée,
sans dégradation de la sécurité générale.
