# D4RLING — note de reprise au 29 octobre 2026

> Cette note conserve le périmètre historique BH–CE. Pour l’ensemble du projet,
> les preuves Carbon dynamiques complémentaires et la reproduction sur un autre
> poste, lire [PROJECT_STATE.md](../PROJECT_STATE.md) et le
> [guide exécutable](../reproduction/README.md).

## Périmètre et provenance

Cette note conserve les résultats et décisions techniques importants de la
conversation « Ninja - Audit statique réussi », de JACK-01E12BH à BN-R2,
puis les qualifications intermédiaires jusqu'à CE. Elle complète la
documentation Carbon et les historiques audio/i386 déjà publiés.

La reprise a relu la conversation accessible, sa pièce jointe CE et **21
rapports JSON locaux existants**. Aucun essai Darling, build, installation ou
test audio n'a été relancé pour cette publication. Les conclusions sélectionnées et leurs limites sont dans
[le registre synthétique](evidence/jack01e12-bh-ce-2026-10-29.json).
L'inventaire détaillé avec chemins exacts et empreintes reste local.

**Publié ici :** cette synthèse et des extraits structurés anonymisés.
**Restent locaux :** les rapports originaux complets, journaux, timelines,
préfixes, exécutables et sources expérimentales. Un motif de chemin publié ne signifie pas que le fichier correspondant
est sur GitHub.
Cette publication ne sauvegarde pas le contenu des neuf modifications locales.

Les valeurs des rapports décrivent leurs campagnes historiques. Leur relecture
n'est pas une nouvelle qualification du runtime. PASS/INFO/REVIEW et les
verdicts d'origine sont conservés ; INFO ne signifie pas réussite fonctionnelle.

## État du dépôt vérifié avant publication

| Élément | Révision observée sur GitHub |
| --- | --- |
| Branche par défaut `master` | `f8e9b62e12247b827273ce42c277fbc4ee5b927c` |
| `work/carbon-event-contracts` | `8744f2deba4ae053f4a27fb07bdb975791344ab8` |
| `work/coreaudio-ninja-convergence` | `a37da006c8f4b31460a712209bac9358f5214cd4` |
| `work/macho-i386-loader-qualification` | `dfacf834551aa22127bd1ceef2943f3023f2de59` |
| Copie locale historique de qualification | `b7d0cb6a79fe196657deb9711647f8486bcc5e5e`, branche `work/carbon-event-contracts`, neuf fichiers modifiés non indexés |

La copie locale et la branche distante n'ont donc pas le même HEAD.
Le commit local [b7d0cb6](https://github.com/fr4nck/d4rling/commit/b7d0cb6a79fe196657deb9711647f8486bcc5e5e)
existe bien sur GitHub ; cela ne publie pas les modifications locales ultérieures.
Les documents de `master` relus décrivaient principalement Carbon jusqu'au
22 octobre. Les notes audio de la branche dédiée atteignaient JACK-01E12G ;
le README i386 conservait notamment QT-106 à QT-113. Les références sont
épinglées ci-dessous afin de ne pas confondre branches et résultats.

La présente reprise est documentaire, issue du `master` vérifié, sur une
branche de publication séparée. Elle n'importe aucune branche de développement
ni aucun changement de production depuis la copie locale protégée.

## Résultat actuel et frontières de preuve

| Domaine | Acquis | Limite à conserver |
| --- | --- | --- |
| Mach-O x86_64 | BK observe une sortie propre à un exécutable installé, repris par BL | Ni tous les exécutables ni toutes les applications ne sont testés |
| Linux i386 | BM exécute 20/20 ELF32 | Ce n'est pas du Darwin |
| Chargement Mach-O i386 | BM puis BN-R2 atteignent le retour diagnostique AY | Interception avant le point d'entrée ; pas d'exécution Darwin dans ces lots |
| Instructions du point d'entrée Mach-O i386 | CB apporte des contrôles différentiels positifs, CE reproduit le marqueur du témoin | Payloads injectés utilisant `int 0x80` et la convention Linux i386 |
| Chaîne dynamique privée | CE voit `mldr32`, `dyld` et la région d'entrée du programme dans le même processus | Initialisation complète de `dyld`, transfert exact et appels Darwin non qualifiés |
| Qt / témoin `qt56-original` | Échec rapide code 1 ; variante instrumentée CB code 97 avec marqueur | Ni application Qt complète ni QuickTime 7 qualifiés ; ne pas déduire le sens de « Qt » du seul nom du témoin |
| Carbon | Contrats et régressions hôte publiés séparément | Pas de preuve d'interface graphique ni de compatibilité applicative globale |
| CoreAudio / JACK / CoreMIDI | Inventaires, graphes, symboles et IPC Linux documentés | Pas de HAL audio opérationnel, route JACK réelle ou compatibilité Logic Studio 8 démontrés |

L'affirmation historique « aucun point d'entrée i386 exécuté » est correcte
pour BM/BN-R2, mais est dépassée par les contrôles CB. Réciproquement, CB
ne permet pas d'annoncer « dyld i386 pleinement opérationnel ».

## Chronologie BH à BN-R2

| Lot | Résultat conservé | Décision / portée |
| --- | --- | --- |
| BH | Un serveur, un shellspawn, cinq zombies observés ; aucun bash Darwin trouvé dans l'inventaire borné | `SUSPECT_MISSING_DARWIN_BASH` ; aucune commande Darling exécutée |
| BI | `/bin/bash` absent ou inaccessible avec ENOENT dans l'installation, l'upper et la vue overlay active ; shellspawn contient ce chemin par défaut | `MISSING_BASH_IN_ACTIVE_OVERLAY` ; ne pas réparer à l'aveugle ni arrêter le serveur |
| BJ-R2 | 100 observations : 69 PASS, 12 CONFIRMED, 17 INFO, 1 REVIEW, 1 VERDICT | `MISSING_BASH_SEARCH_INCOMPLETE` : recherche SOURCE tronquée à 25 001 entrées ; zéro candidat ne prouve pas une absence globale |
| BK | 38 exécutables Mach-O installés vérifiés ; lancement direct de `bitcode_strip`, code 1, message d'usage attendu (« one of -r, -m or -l »), sans timeout | `DIRECT_MACHO_OUTPUT_OBSERVED` : exécution réelle x86_64 malgré un code d'usage non nul ; serveur et Git préservés |
| BL | 100 observations : 83 PASS, 14 INFO, 2 CONFIRMED, 1 VERDICT ; 38 exécutables x86_64 vérifiés | `X64_RUNTIME_PROVEN_I386_STAGING_REQUIRED` ; mldr32 construit mais non installé sous la forme ELF32 attendue ; dyld historique avec i386 |
| BM | 100 observations : 95 PASS, 2 INFO, 2 REVIEW, 1 VERDICT ; ELF32 20/20, chargements diagnostiques Mach-O32 20/20, troncatures rejetées 19/20 | `I386_NEGATIVE_BOUNDS_NEED_REVIEW` ; exception à 192 octets ; aucun point d'entrée Darwin exécuté |
| BN initial | Arrêt `STOP_AY_DIAGNOSTIC_IDENTITY` au prévol | Aucun des 100 cas lancé ; exigence erronée d'un seul candidat AY |
| BN-R2 | 100 fichiers distincts : 53 LOAD_RETURNED, 46 REJECTED, 1 CRASHED ; deux copies AY de même SHA-256 | `REVIEW_BOUNDARY_CASES` ; doublons identiques permis, aucun autre hash accepté |

BL observe libSystem, libsystem_kernel et CoreFoundation aux chemins
inspectés ; Foundation, Carbon, CoreAudio, AudioToolbox, CoreMIDI, QuickTime
et AppKit y sont absents. Cet inventaire est daté et limité aux racines
inspectées ; il ne décrit pas tous les builds ou préfixes privés ultérieurs.

AY est un chargeur privé instrumenté : gardes `AY_AFTER_LOAD32`,
`AY_AFTER_LOAD64`, `_exit(90)` et `D4RL_DIAG_ONLY`.
Son identité a été vérifiée localement par empreinte.
Les deux exemplaires O0/native sont identiques. Le retour 90 avec
`AY_AFTER_LOAD32` prouve le retour du chargement diagnostique, pas la
validation intégrale des segments, le transfert à dyld ou l'exécution de l'EIP.

BN-R2 classe 30 rejets de fichiers trop courts, 19 troncatures acceptées,
11 images complètes acceptées, 16 mutations rejetées, 23 mutations acceptées
et un cas REVIEW. Les 19 images incomplètes acceptées commencent à 192 octets
(jusqu'à 4095 dans les cas testés), pour une image de référence de 4096 octets.
Les mutations d'EIP nul ou hors segment atteignent également le retour AY ;
l'interception précède justement leur exécution.

**BN063** conserve une structure Mach-O32 et annonce `cputype=x86_64`.
Le rapport détaillé relu donne `returncode=-6` (SIGABRT selon la convention
POSIX de subprocess), et non un signal encore inconnu.
L'identité de la fixture est conservée dans l'inventaire local détaillé.
Un crash de robustesse est observé ; cause précise, portée exploitable et
correctif ne sont pas établis. Le serveur, Git, dyld, binaire AY et sources AY
sont déclarés inchangés par le contrôle d'intégrité BN-R2.

## Étapes intermédiaires et correction des sondes

| Lot | Résultat conservé | Ce que cela autorise à conclure |
| --- | --- | --- |
| BP | 461 fichiers, 207 implémentations, 7 fichiers PulseAudio, 41 API critiques ; 35 candidats de définition | Audit heuristique des sources ; aucun fournisseur CoreAudio/AudioToolbox qualifié dans le runtime inspecté |
| BQ | 41 API HAL, 7 fichiers PulseAudio, 429 cellules d'évidence | Cellules d'audit, pas 429 tests ; liaison i386, CoreAudio runtime et route JACK non qualifiés |
| BR reprise | 41 API, aucun P0 manquant selon l'analyse ; PulseAudio ELF64/pkg-config natif présent, ELF32/pkg-config i386 absent ; socket WSLg observé | `PREBUILD_ABI_REVIEW_REQUIRED` ; présence de fonctions/socket ne prouve ni serveur audio accessible ni sortie sonore |
| BT | 50 observations : 17 PASS, 31 INFO, 2 FAIL | FAIL 36/37 = chargeurs build/install différents ou manquants ; conserver ces échecs, ne pas les relabeller succès |
| BU | 60 observations : 8 PASS, 52 INFO | Confirme la divergence des identités de chargeurs ; rejette la modification sysctl ; prépare un témoin privé à adresse haute |
| BW | Inventaires attendu/observé des neuf chemins égaux, aucun manque/extra, 25 contrôles enregistrés | Prévol compatible avec la campagne BV prévue ; pas une exécution BV |
| BX | 100 observations : 84 PASS, 16 INFO ; `runtime_executed=false` | Inspection des sondes et adresses, pas qualification de production |
| BZ | Prévol d'identité et de protection enregistré ; `by_executed=false` | Ne pas annoncer BY exécuté |
| CA | Témoin relocalisé code 0 ; variante exit42 code 42 | Indice positif, mais le rapport conserve `entry_execution_proven=false` ; CB apporte ensuite les contrôles décisifs |

Les sondes originales non PIE placent `__TEXT` à `0x1000`, sous
`mmap_min_addr=65536` (`0x10000`). Le conflit d'adresses est une
observation statique sur ces fixtures ; il ne suffit pas à expliquer tout
échec du runtime. La stratégie retenue conserve la protection du noyau et
modifie seulement des copies expérimentales : décalage de `0x10000`,
`__TEXT=0x11000`, correction des segments et de l'entrée.
Par exemple CA passe d'une entrée 8096 à 73632.
Une relocalisation manuelle de sonde ne constitue pas un correctif général
de chargeur, de relocations dynamiques ou d'application.

Les dossiers initiaux BQ et BR peuvent contenir des sorties partielles.
La synthèse utilise BQ terminé et BR-reprise, avec leurs chemins exacts.
Aucun résultat exécuté n'est attribué ici aux propositions BO, BS, BV,
BY ou CF ; leur proposition ou un dossier de prévol ne prouve pas leur
réalisation.

## CB : preuve différentielle d'exécution i386

CB enregistre 12 essais : **10 PASS, 2 INFO**.
Les sorties suivent les variantes injectées, plutôt qu'un code constant
du lanceur.

| Témoin CB | Retour observé | Marqueur / observation |
| --- | ---: | --- |
| 01-static-original | 0 | Témoin relocalisé |
| 02-static-exit17 | 17 | Retour attendu |
| 03-static-exit73 | 73 | Retour attendu |
| 04-static-write42 | 42 | `D4RL_CB_STDOUT_ALPHA` sur stdout |
| 05-static-no-write42 | 42 | Même marqueur absent ; contrôle négatif |
| 06-static-stderr57 | 57 | `D4RL_CB_STDERR_BRAVO` sur stderr |
| 07-static-stdout83 | 83 | `D4RL_CB_STDOUT_CHARLIE` sur stdout |
| 08-dynamic-original | 124 | Timeout à 18 s, INFO |
| 09-dynamic-exit91 | 91 | Retour attendu |
| 10-dynamic-write93 | 93 | `D4RL_CB_DYNAMIC_MARKER` sur stdout |
| 11-qt56-original | 1 | Échec rapide, INFO |
| 12-qt56-write97 | 97 | `D4RL_CB_QT56_MARKER` sur stdout |

Le contrôle négatif 04/05 ne diffère qu'aux offsets 4042 et 4043 :
`CD 80` devient `90 90` pour neutraliser l'écriture ; la sortie 42
reste identique. Les identités des 12 fixtures ont été revérifiées localement, de même
que les deux seuls offsets modifiés du contrôle négatif. Leurs empreintes
et entrées détaillées restent dans l'inventaire local. Une inspection des octets pendant la publication confirme
la convention Linux i386 (eax/ebx/ecx/edx, `int 0x80`, write/exit).
Ces payloads ne valident ni les appels système Darwin ni libSystem i386.
Les noms « dynamic » et « qt56 » désignent les fixtures sources/variantes ;
le marqueur d'un programme modifié ne qualifie pas l'application originale.

Le rapport conserve `strong_i386_entry_proof=true`, mais
`dynamic_loader_fully_qualified=false`, `darwin_syscalls_qualified=false`,
`quicktime_qualified=false` et `coreaudio_qualified=false`.

## CC, CD et CE : observer la chaîne sans surinterpréter les timeouts

CC : 100 observations sur cinq essais, 42 PASS / 58 INFO.
CD : deux rapports distincts, chacun 100 métriques sur huit essais,
7 PASS / 93 INFO. Les deux chemins sont conservés ; ne pas les additionner
en « 200 programmes fonctionnels ». CD note des erreurs RPC avant la fin
du processus observé, ainsi que dans les logs finaux, mais les dates par
rapport à l'échéance du timeout restent déterminantes.

**CE : 100 observations sur quatre essais, 19 PASS / 81 INFO / 0 FAIL.**
Ce bilan ne représente pas 100 exécutions applicatives réussies.

| Essai CE | Retour | Durée | Observation déterminante |
| --- | ---: | ---: | --- |
| marker-control | 93 | 1,422 s | Marqueur CB présent ; aucun mldr32 capturé dans les échantillons |
| qt56-original | 1 | 1,330 s | Pas de marqueur ni mldr32 capturé |
| dynamic-6s | 124 | 6,038 s | mldr32 vu à 1,419 s, dyld et région d'entrée mappés, état R |
| dynamic-10s | 124 | 10,055 s | Même visibilité de mldr32, dyld et entrée ; état R |

Le succès du témoin rapide malgré l'absence de mldr32 dans les échantillons
montre pourquoi « non observé » ne signifie pas « jamais démarré ».
Pour les deux essais longs, CE cible les mappings **dans mldr32 lui-même** ;
les lectures /proc indiquent `R (running)`, syscall `running` et wchan 0.
Cela ne donne pas la valeur du registre EIP.

L'entrée du dynamique original (adresse 73552, offset fichier 3920) commence
par `E8 0B 00 00 00 EB FE` : appel vers une fonction à +16, puis
saut sur lui-même au retour. **Hypothèse :** cette boucle volontaire peut
expliquer les timeouts. Elle n'est pas une preuve que l'EIP l'a atteinte ;
un blocage préalable dans dyld reste à départager.
Le témoin Qt original commence par `CC EB FE` ; son code 1 ne suffit pas
à établir le chemin exact de traitement du trap.

CE classe les messages `mach_msg_overwrite ... -111` et
`dserver_rpc_interrupt_enter ... -111` :

- à 6 s : visibles seulement dans la sortie finale ou à la terminaison ;
- à 10 s : première observation à 10,010 s, catégorie `TIMEOUT_BOUNDARY`.

Une erreur observée avant la sortie finale peut déjà suivre l'échéance du
timeout. La chronologie ne permet donc pas d'en faire la cause initiale du
blocage, ni d'annoncer CA-12/RPC résolu. Les avertissements de limite FD
observés dans les journaux ne suffisent pas non plus à expliquer les échecs.
CE conserve `dyld_operational=false`, `quicktime_qualified=false` et
l'intégrité de Git/binaires/serveur historique.

## CoreAudio, JACK, QuickTime et choix d'architecture

BP/BQ/BR restent des audits de sources, de dépendances et d'ABI.
Les appels PulseAudio repérés (connexion du contexte, playback, écriture,
capture, déconnexion) n'établissent pas leur fonctionnement. Les 35 candidats
de BP et l'absence de P0 manquant de BR proviennent d'analyses différentes ;
ils ne forment pas un score fonctionnel comparable.
Les outils et bibliothèques natifs visibles ne qualifient pas leurs variantes
ELF32 ni la passerelle entre Mach-O et ELF. JACK/PipeWire-JACK n'est pas
disponible/qualifié dans l'environnement inspecté par ces rapports.

Conserver les décisions de l'historique audio :

- garder un seul contrat public CoreAudio HAL/AudioObject/AudioDevice et le
  backend PulseAudio existant ; JACK reste une option candidate ;
- préserver Carbon et CoreMIDI/ALSA ; ne pas porter JackRouter directement
  comme s'il constituait une implémentation HAL compatible Darling ;
- séparer transport PCM et contrat API ; les IPC Linux ELF32/ELF64 déjà validés
  ne valident pas le passage de descripteurs/mmap depuis un invité Darwin ;
- examiner durée de vie des callbacks, erreurs, formats, horloges et
  contraintes temps réel avant de lancer un callback CoreAudio sur un
  thread JACK ;
- respecter le graphe circulaire CMake/Ninja `*_firstpass.dylib`,
  distinguer artifacts build/install et architectures effectives ; ne pas
  copier des binaires entre arbres pour masquer une dépendance manquante.

La clôture statique i386 38/38 déjà publiée (1 umbrella libSystem, 33
dépendances directes distinctes, 4 supplémentaires ; 317 références non
uniques) concerne des candidats du build. Elle ne garantit pas une
installation cohérente ou un runtime dynamique.
QuickTime 7, applications Qt, AudioUnit, audio/MIDI matériel, ALSA depuis
l'invité, route JACK réelle et Logic Studio 8 restent non qualifiés.

## Environnement de reprise PMSL-ARCH / AGT-013

Conventions attestées par les blocs de campagne ; cette note ne prétend pas
reconstituer un règlement AGT-013 externe absent des sources consultées.

- Hôte de qualification : Windows 11 Pro N x64 ; Debian GNU/Linux 13 sous
  WSL2 ; scripts à lancer dans **Bash /bin/bash**.
- Les blocs Bash historiques ne doivent pas être collés dans PowerShell,
  CMD ou une console Python. Le compte WSL, son UID et la machine doivent
  être vérifiés localement avant de reprendre un lanceur existant.
- Publier les chemins avec `$D4RL_HOME`, alias du répertoire personnel WSL
  de qualification. Aucun nom de compte, nom de machine, adresse privée ou
  identifiant de connexion n'est nécessaire pour reprendre la logique.
- Distinguer le terminal utilisé pour documenter depuis Windows du terminal
  Debian/Bash requis par les campagnes. Vérifier branche, HEAD et état local,
  sans imposer une bascule de branche ; BN-R2 accepte un HEAD détaché.
- Toute nouvelle campagne produit un nouveau répertoire privé, permissions
  restrictives (`umask 077`), sans écraser les anciens rapports.

| Rôle | Chemin historique normalisé |
| --- | --- |
| Sources protégées | `$D4RL_HOME/d4rling-ui/d4rling-carbon-qualif` |
| Build i386 | `$D4RL_HOME/d4rling-core/d4rling-build-i386` |
| Installation historique | `/usr/local/libexec/darling` |
| Préfixe historique protégé | `$D4RL_HOME/d4rling-prefix-runtime-01` |
| Racine dyld historique | `$D4RL_HOME/d4rling-audio/jack01e12m-*/private-root` |
| Chargeur AY vérifié | `$D4RL_HOME/d4rling-jack01e12ay-r1-*/bin/O0/mldr32` ; copie `bin/native/mldr32` |
| Paire de chargeurs BM | `$D4RL_HOME/d4rling-jack01e12bm-*/private-loader-pair/` |
| Installation privée utilisée en CE | `$D4RL_HOME/d4rling-qt432-438-*/installation/` |
| Darling privé CE | sous cette installation : `bin/darling` |
| mldr32 et dyld privés CE | `libexec/darling/usr/libexec/darling/mldr32` et `libexec/darling/usr/lib/dyld` |
| Ancienne zone de qualification audio | `$D4RL_HOME/d4rling-audio/qualif/` |

## Préservation, sécurité et confidentialité

Les neuf changements locaux restent protégés :
```text
CREDITS.md
src/frameworks/Carbon/HIToolbox/include/HIToolbox/CarbonEventsCore.h
src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c
src/shellspawn/shellspawn.c
tests/regressions/carbon-contracts/run.sh
tests/regressions/carbon-events/README.md
tests/regressions/carbon-events/allocator-adapter.c
tests/regressions/carbon-events/allocator-adapter.h
tests/regressions/carbon-events/run.sh
```

Le contrôle de publication a confirmé les neuf contenus, leur statut, le HEAD,
la branche, l'index et le diff local inchangés par comparaison d'empreintes.
La publication conserve leurs chemins de dépôt et le bilan de préservation ;
les empreintes détaillées restent locales. Elle ne les indexe, ne les commit et ne les pousse
pas. Aucune opération checkout/switch/reset/pull/rebase/stash/clean n'est
requise dans cette copie locale. Ne pas mettre à jour automatiquement le
checkout au HEAD distant ni changer la source du build existant.

Le serveur historique de référence des campagnes est `darlingserver` ;
un PID seul n'est jamais une identité suffisante pour agir.
Vérifier propriétaire, exécutable, préfixe et identité de processus avant
toute intervention. Ne pas arrêter le serveur historique, modifier son
préfixe, les sources/builds, les installations ou le dyld de référence.
Les essais CB–CE créent leurs propres préfixes ; leurs observations ne
donnent pas licence d'utiliser un préfixe en cours d'utilisation.

Conserver `mmap_min_addr` et les protections du système ; pas de sudo,
sysctl, montage, téléchargement, installation, compilation ou relance de
daemon dans une simple reprise documentaire. Les interdictions historiques
commit/push concernent les campagnes de qualification ; la demande actuelle
autorise la publication documentaire distante sur une branche séparée.

Pour de futurs essais, borner durée et sorties, désactiver les core dumps
si prévu par le banc, et ne signaler/nettoyer que les processus expérimentaux
dont l'appartenance au nouveau banc est vérifiée. Aucune exploitation de
BN063 n'est démontrée. Relire et filtrer tout journal avant une publication :
ne pas téléverser environnements, identifiants, tokens, archives privées
ou binaires tiers. Les chemins personnels sont normalisés ici, sans lien
public fictif vers un fichier local.

## Prochaines étapes avec critères d'acceptation

1. **Témoin dynamique i386 terminant (CF proposé, pas exécuté).** Remplacer
   la boucle de la fixture privée par une fin observable et déterministe,
   garder un contrôle négatif, relever marqueur et code attendus. Pour
   qualifier dyld → programme, documenter le chemin et l'EIP/les registres
   d'entrée, pas seulement les mappings.
2. **Échec Qt original.** Exploiter stderr complet, chronologie, code 1,
   séquence trap et comparaison avec la variante CB code 97. Distinguer
   fin rapide et absence d'échantillon mldr32 ; ne pas conclure sans preuve
   qu'aucun processus 32 bits n'a démarré.
3. **RPC et timeout.** Horodater les premiers messages avant/après l'échéance,
   distinguer cause primaire et arrêt imposé. Ne corriger le serveur
   qu'après une reproduction indépendante du mécanisme de terminaison.
4. **Robustesse BN063 et bornes.** Analyser d'abord le routage architecture
   et le rejet attendu d'un CPU incohérent, en conservant fixture/hash et
   `-6`. Revoir les 19 troncatures AY acceptées ; demander un rejet
   contrôlé des entrées invalides avant toute prétention de sécurité.
5. **ABI Darwin i386.** Construire/qualifier séparément un programme minimal
   via une pile libSystem/dyld cohérente et des API Darwin. Les témoins Linux
   directs ne satisfont pas ce jalon.
6. **Audio après les prérequis ABI/runtime.** Vérifier dépendances Mach-O/ELF32,
   exports et providers, puis cycle HAL start/stop/callback/erreurs, puis
   buffers PCM, capture/playback et routage JACK mesuré. Qualifier ensuite
   applications, AudioUnit, QuickTime et Logic ; aucun audit statique ne
   remplace ces essais.

Ces critères décrivent le travail restant et n'autorisent pas implicitement
une nouvelle installation, une modification du runtime protégé ou un build
concurrent. Ne pas répéter de grandes séries statiques identiques si elles
ne départagent pas une hypothèse technique.

## Registre des rapports locaux

Les motifs ci-dessous sont relatifs à `$D4RL_HOME`. Le caractère `*`
représente le suffixe propre à chaque campagne. Les noms personnels et
localisateurs exacts restent dans l'inventaire local détaillé de cette
reprise. Résoudre les motifs en lecture seule et vérifier le schéma/lot
du JSON ; plusieurs reprises peuvent correspondre au même motif.
Les deux rapports CD sont conservés séparément localement.

| Rapport | Motif de chemin local relatif |
| --- | --- |
| JACK-01E12BH | `d4rling-jack01e12bh-*/summary.json` |
| JACK-01E12BI | `d4rling-jack01e12bi-*/summary.json` |
| JACK-01E12BJ-R2 | `d4rling-jack01e12bj-r2-*/summary.json` |
| JACK-01E12BK | `d4rling-jack01e12bk-*/summary.json` |
| JACK-01E12BL | `d4rling-jack01e12bl-*/summary.json` |
| JACK-01E12BM | `d4rling-jack01e12bm-*/summary.json` |
| JACK-01E12BN-R2 | `d4rling-jack01e12bn-r2-*/summary.json` |
| JACK-01E12BP | `d4rling-jack01e12bp-*/summary.json` |
| JACK-01E12BQ | `d4rling-jack01e12bq-*/summary.json` |
| JACK-01E12BR-REPRISE | `d4rling-jack01e12br-reprise-*/summary.json` |
| JACK-01E12BT | `d4rling-jack01e12bt-*/report.json` |
| JACK-01E12BU | `d4rling-jack01e12bu-*/report.json` |
| JACK-01E12BW | `d4rling-jack01e12bw-*/report.json` |
| JACK-01E12BX | `d4rling-jack01e12bx-*/report.json` |
| JACK-01E12BZ | `d4rling-jack01e12bz-*/report.json` |
| JACK-01E12CA | `d4rling-jack01e12ca-*/report.json` |
| JACK-01E12CB | `d4rling-jack01e12cb-*/report.json` |
| JACK-01E12CC | `d4rling-jack01e12cc-*/report.json` |
| JACK-01E12CD (rapport 1) | `d4rling-jack01e12cd-*/report.json` |
| JACK-01E12CD (rapport 2) | `d4rling-jack01e12cd-*/report.json` |
| JACK-01E12CE | `d4rling-jack01e12ce-*/report.json` |

À conserver également localement : `lots.json`/TSV des campagnes,
`results.json`/TSV et `ay-identity.json` de BN-R2, fixtures CB,
stdout/stderr, timelines CC/CD/CE, et `entry-disassembly.txt` de CE.
Le prévol BN interrompu est dans `d4rling-jack01e12bn-*` ;
le premier dossier BK n'a qu'un `first-run.log`, distinct du résultat BK
complet retenu. Une absence de résumé ne doit pas être convertie en réussite.

## Références GitHub déjà publiées

- [Suivi Carbon / Logic sur la base master relue](https://github.com/fr4nck/d4rling/blob/f8e9b62e12247b827273ce42c277fbc4ee5b927c/docs/logic8-progress.md)
  et [portée des régressions du 22 octobre](https://github.com/fr4nck/d4rling/blob/f8e9b62e12247b827273ce42c277fbc4ee5b927c/docs/carbon-queue-dispatch-2026-10-22.md).
- [Historique CoreAudio/JACK jusqu'à JACK-01E12G](https://github.com/fr4nck/d4rling/blob/a37da006c8f4b31460a712209bac9358f5214cd4/docs/audio/COREAUDIO_JACK_CONVERGENCE.md)
  et [reprise Ninja/firstpass](https://github.com/fr4nck/d4rling/blob/a37da006c8f4b31460a712209bac9358f5214cd4/docs/audio/NINJA_FIRSTPASS_HANDOFF_2026-10-27.md).
- [Qualification du générateur Mach-O i386 et historique QT](https://github.com/fr4nck/d4rling/blob/dfacf834551aa22127bd1ceef2943f3023f2de59/tests/regressions/macho-i386/README.md).
  Les tests hôte/CI du générateur et des sources épinglées restent distincts
  d'une exécution de l'invité sur la machine de qualification.
- [Identité du commit historique de qualification](https://github.com/fr4nck/d4rling/commit/b7d0cb6a79fe196657deb9711647f8486bcc5e5e).

Une reprise à partir de GitHub peut maintenant retrouver conclusions,
frontières de preuve, anomalies, décisions et emplacements locaux. Elle
doit toujours obtenir les originaux locaux pour une réanalyse complète ;
l'archivage du chat ne constitue pas leur sauvegarde.
