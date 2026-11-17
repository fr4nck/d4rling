# SoundHack SH24-R4 — low mmap temporaire, progression jusqu'à RC=134 (5700X)

**17 novembre 2026 — observation opérateur, qualification bornée.**

Le lot SH24-R4 a poursuivi le chargement de l'application officielle
SoundHack 0.896 à partir de SH24-R2 et SH25 : contrôle invité
Mach-O i386 réel déjà PASS ; échec antérieur `Cannot mmap segment
__TEXT at 0x1000: Operation not permitted` avec `APP_RC=1`.

## Résultat recopié par l'opérateur

`
STATUS=SH24_R4_LOW_MAP_APP_ATTEMPT_RECORDED
PIN_GATE=PASS
PREVIOUS_GATE=PASS
RUNTIME_GATE=PASS
KERNEL_GATE=PASS
ORIGINAL_MMAP_MIN_ADDR=65536
CONSENT=YES
SYSCTL_CHANGE=PASS_TEMPORARY
SYSCTL_RESTORATION=PASS
FINAL_MMAP_MIN_ADDR=65536
APP_GATE=ATTEMPTED
RUNNER_RC=0
APP_RC=134
APP_CLASS=DYLD_DEPENDENCY_OR_SYMBOL_FAILURE
CLEAN=BOUNDED_PASS
INTEGRITY=PASS_BOUNDED
GUI=NOT_QUALIFIED
AUDIO=NOT_QUALIFIED
SOURCE_WRITE=NO GIT_WRITE=NO DELETE=NO
`

Rapport et journaux privés :
`/home/Deniel/d4wrling-work/validation/soundhack-sh24-r4.K5DVWwv6`,
dont `runs/s24low/stderr.log`, `runs/s24low/stdout.log`,
`runs/s24low/meta.txt`, `runner.log` et le bilan court.
Ces fichiers n'ont pas été directement lus par l'agent rédacteur.

## Portée et limites

La politique mémoire globale était à **65 536** avant et après
l'essai. Sous consentement explicite, le lot a temporairement
abaissé le seuil pour relancer le vrai SoundHack, puis l'a
restauré (selon rapport de l'opérateur).
**Ne pas reproduire automatiquement cette mutation système.**

SoundHack retourne désormais **134**, et le lanceur classe cet
arrêt comme `DYLD_DEPENDENCY_OR_SYMBOL_FAILURE`. En convention
Shell Unix, 134 est compatible avec `128 + SIGABRT(6)`,
mais la cause exacte et le symbol/dylib impliqué ne sont
pas établis par le bilan court.
`RUNNER_RC=0` signifie que le lanceur du banc a terminé ;
`APP_RC=134` n'est **pas** une preuve de lancement réussi.
Aucun `main`, interface Carbon, traitement FFT applicatif,
ni audio n'a été qualifié.

L'écart avec le `RC=1` précédent est une avancée :
le mapping bas n'est plus le blocage observé pour ce run.
La cause `dyld` doit être **confirmée dans la sortie stderr
d'origine**, plutôt qu'inférée des 206 imports statiquement
non retrouvés. Ne pas écrire de stubs Carbon spéculatifs.

## Prochain lot SH27

Lot autonome **100 % diagnostic hors ligne et lecture seule** :
contrôler la restauration actuelle de `vm.mmap_min_addr`,
le bilan R4, les codes de retour et les journaux limités en
taille, extraire le premier diagnostic concret `dyld`, corréler
les noms à la vraie table d'import `nlist`, comparer les dylibs
annoncées à leurs chemins dans le préfixe privé B13, et
préserver les empreintes. **Aucun `sysctl`, aucune exécution
invitée, aucune compilation, aucun téléchargement**.
La sortie longue reste locale ; ne copier sur le presse-papiers
Windows que le court bilan expurgé, même en cas d'échec.

**`SH24_R4_REAL_ATTEMPT_RECORDED`, `APP_RC=134`,
`DYLD_DETAILED_CAUSE=NOT_YET_VERIFIED`,
`GUI=NOT_QUALIFIED`, `AUDIO=NOT_QUALIFIED`.**
