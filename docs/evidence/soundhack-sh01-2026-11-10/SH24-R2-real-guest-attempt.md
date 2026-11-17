# SoundHack SH24-R2 — contrôle invité i386 validé, app RC=1 (5700X)

**17 novembre 2026 — observation de terminal de l'opérateur**.
Le statut de fin du lot est `SH24R2_APP_ATTEMPT_RECORDED`
et le processus Shell a rendu `EXIT_CODE=0`. **Ce statut qualifie la
tentative, non le lancement réussi de SoundHack.**

## Résultat de la reprise sans réseau

Entrée : original `SoundHack.app` 0.896 déjà vérifié SHA-256 en SH20,
rapport SH23 réel `12/12 PASS`, installation Darling privée B13 et
cache ELF32 validé.

Le précédent SH24 a arrêté le lot en préparation : acquisition
des sources `SOURCE_PIN=BLOCKED`, sans aucun lancement invité.
SH24-R2 supprime le téléchargement du lanceur en intégrant un
contrôle i386 et le lanceur localement dans son stage. R2 consigne :

`
PRIOR_ERROR=SOURCE_ACQUISITION_BLOCKED_NOT_MAC_GUEST
PIN_SOUNDHACK_SH23=PASS
PIN_DARLING_PRIVATE=PASS
PIN_SOCKET_SHORT=PASS_LEN_82
RUNNER_EMBEDDED_OFFLINE=PASS
CACHE_ELF32=PIN_PASS
CONTROL_COMPILE=PASS
CONTROL_GUEST=PASS_REAL_I386_MAIN
SOUNDHACK_ATTEMPT=RECORDED_RC_1
FINAL_INTEGRITY=PASS
HOST_MOUNT_SERVER_COUNTS=UNCHANGED
FINAL_STATUS=SH24R2_APP_ATTEMPT_RECORDED
CONTROL_GUEST_RC=0
SOUNDHACK_GUEST_RC=1
GUI=NOT_QUALIFIED AUDIO=NOT_QUALIFIED
`

**Acquis :** avec un socket de 82 octets, l'environnement
d'exécution privé isolé lance réellement un petit témoin
Mach-O i386 et reçoit son marqueur `SH24R2_GUEST_I386_MAIN_PASS`,
`RC=0`. L'application originale a ensuite été transmise
au lanceur et son essai s'est terminé avec `RC=1`.
C'est la première **tentative de lancement de l'application originale**
sur ce banc ; cela ne démontre **pas** que son `main` a été atteint.

Les empreintes contrôlées à l'issue de R2 sont inchangées, et les
compteurs des montages et serveurs Darling hôtes sont inchangés
avant/après. Les préfixes et rapports privés sont conservés.

## Preuves privées à examiner

- `/home/Deniel/d4wrling-work/validation/soundhack-sh24r2.iH5unmDc/console.log`
- `/home/Deniel/d4wrling-work/validation/soundhack-sh24r2.iH5unmDc/events.txt`
- `/home/Deniel/d4wrling-work/validation/soundhack-sh24r2.iH5unmDc/runs/control/{rc,stdout.log,stderr.log}`
- `/home/Deniel/d4wrling-work/validation/soundhack-sh24r2.iH5unmDc/runs/soundhack/{rc,stdout.log,stderr.log}`

**Ces fichiers n'étaient pas consultables par l'agent rédigeant
ce document**. Il est impossible d'attribuer le code 1 à une erreur
`dyld`, un import Carbon, une initialisation applicative ou une
erreur du lanceur sans les lire. Ne pas inventer de cause.

## Prochain lot SH25

**Sans relancer SoundHack**, inspecter d'une seule commande Bash
les journaux invités bornés, la présence du contrôle positif,
le code retour, les erreurs dyld explicites, les fichiers
librairies d'origine si l'erreur donne un nom, le
recoupement des imports du rapport SH22/SH23 et les preuves
d'intégrité. Continuer les contrôles indépendants malgré un
blocage, puis produire un bilan court auto-copié sur Windows.

Aucune modification des sources/builds/préfixes, installation
ou Git local. `DYLD_BIND=NOT_QUALIFIED`,
`CARBON_GUI=NOT_TESTED`, `AUDIO=NOT_TESTED`.
