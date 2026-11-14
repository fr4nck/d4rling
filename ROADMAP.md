# D4RLING — feuille de route multi-axes

**Version 0.2 — 9 novembre 2026.** Dépôt : `fr4nck/d4rling`, branche
d'intégration `master`. État public de référence avant actualisation :
[`d2318ea37f9edbdcd661408edfa8723b0289eb2e`](https://github.com/fr4nck/d4rling/commit/d2318ea37f9edbdcd661408edfa8723b0289eb2e).
La version 0.1 (8 novembre) demeure l'historique de cadrage ; les
actualisations datées ci-dessous prévalent lorsqu'elles couvrent le même
périmètre, sans effacer les preuves antérieures.
Cette publication est documentaire : aucun build, lancement applicatif, test
audio ou MIDI n'a été rejoué pour la rédiger.

**Repère musical évolutif : `01 — Shelter` (en cours).** Le titre et le
numéro de progression changent ensemble au passage à chaque nouveau jalon
musical ; pas de liste de 29 titres réservés à l'avance. Afficher seulement
le titre du morceau, sans nom d'artiste ni mention « feat. », et respecter
le plafond de trois morceaux par artiste. Ce repère éditorial ne vaut pas
validation technique : les critères R/U/A/M/QT/L/P et leurs statuts restent
indépendants.

## Intention et lecture

D4RLING développe un socle Darwin/macOS réutilisable sous Linux. **Logic
Studio 8 et son EXS24 authentique** sont une cible majeure de compatibilité.
**QuickTime/QTKit et QuickTime Player** constituent un jalon indépendant.
**Petite Victoire**, nom provisoire, est un prototype musical natif original
qui peut évoluer vers un DAW ; son utilité ne dépend pas du succès de Logic.
**Son développement et ses choix de produit restent réservés à fr4nck.**
Il doit servir de démonstrateur musical de référence pour vérifier D4RLING
sans posséder Logic Studio 8, avec une couverture fonctionnelle explicite.
Il n'existe pas encore de preuve de ces applications complètes sous D4RLING.

Lire [PROJECT_STATE.md](PROJECT_STATE.md), puis
[reproduction/README.md](reproduction/README.md),
[refs.lock.json](reproduction/refs.lock.json) et [AGENTS.md](AGENTS.md).
La feuille de route consolide les priorités ; elle ne remplace pas les
rapports datés ni les recettes épinglées. Une preuve récente ne remplace une
ancienne conclusion que pour **la même révision, architecture et chaîne**.

## I2-B — invalidation après SetResInfo (12 novembre 2026)

**Correctif ciblé :** `SetResInfo()` invalide désormais les caches
globaux après modification de l'identifiant ou du nom d'une ressource.
Les recherches par ID/nom d'un **même type** ne conservent plus les anciennes
correspondances après la modification.

**Qualification hôte d'extraits réels :** ancien code 13/20 PASS et 7 FAIL ;
correctif **20/20 PASS** en GCC/Clang `-O0/-O2`, ASan/UBSan ; 1/1 mutation
négative tuée par compilateur.
[Preuve I2-B](docs/evidence/carboncore-resource-i2-setresinfo-2026-11-12.md).

**Limites :** aucune compilation intégrale du framework, aucune intégration
des trois unités, aucun ABI Darwin i386, ni correction des collisions d'ID.
`ResError` et `SetResLoad` restent prioritaires.

## I2-A — caches globaux Resource Manager (12 novembre 2026)

Le sous-lot I2-A corrige dans `Resources.cpp` les caches de recherche par
type, identifiant et nom : leur contenu est remis à zéro lorsqu'on change
de type, et le cache de noms utilise son propre sélecteur.

**Qualification hôte bornée :** 21/21 contrôles des trois fonctions de cache
extraites du code de production, GCC 14.2 / Clang 17 en `-O0` et `-O2`,
ASan/UBSan ; 4/4 mutations négatives tuées par compilateur. L'ancien extrait
échoue sur 12/21 assertions dans les quatre configurations.

[Preuve I2-A](docs/evidence/carboncore-resource-i2-cache-2026-11-12.md).

**Toujours à faire :** compiler/lier les trois unités CarbonCore, qualifier
`SetResInfo`, `ResError`, `SetResLoad` et la persistance via l'API
publique. Aucune qualification Darwin Mach-O i386 ni application.
La suite QuickTime est indépendante et reste préservée.

## Actualisation CarbonCore — 11 novembre 2026 (I1)

**Périmètre borné :** les commits source G4, M1/M2 et R1/R2 sont publiés ;
I1 qualifie pour la première fois l'assemblage des **vraies unités**
`MacMemory.cpp` M2 + `ResourcesImpl.cpp` R2 sur un hôte Linux.
Consulter le [journal CarbonCore](docs/CHANGELOG-CARBONCORE.md) et la
[qualification I1](docs/evidence/carboncore-memory-resource-i1-2026-11-11.md).

| Porte | Acquis vérifié / statut | Suite nécessaire |
| --- | --- | --- |
| Gestalt G4 | Source publiée : `sysv` fondé sur version du produit ; `cbon` refusé honnêtement | Qualifier les capacités Carbon effectives avant toute annonce de version |
| Memory M1/M2 | Allocations/handles corrigés ; tests hôte archivés | ABI Mach-O i386 et gestion des zones mémoire historiques non qualifiées |
| Resources R1/R2 | Décodeur, sérialiseur et erreurs d'écriture effectifs ; bancs hôte archivés | Appels publics, ressources véritables et écritures xattr Darwin à qualifier |
| **I1 — Memory + Resources réels** | **54/54 PASS** sous GCC 14.2 et Clang 17, `-O0` et `-O2`, ASan/UBSan ; **2/2 mutations tuées par compilateur** | Lier les entrées publiques `Resources.cpp`, puis compiler/charger sur Darwin i386 |
| SoundHack / Logic Studio 8 | **NON QUALIFIÉS** | Vérification des imports, Carbon/HIToolbox/QuickTime et runtime i386 ; aucune extrapolation |

**Résultat I1 précis :** `EmptyHandle` conservait le master pointer
sans que `ResourceData::getHandle()` recharge ses données. Le correctif
appelle le vrai `ReallocateHandle` de M2, vérifie `MemError()` et recopie
les données ; les allocations forcées en échec restent vérifiables.
Aucun changement de CMake, des préfixes installés, du 5700X ou
de `x86_64/Cocoa`. **I1 reste un PASS hôte, pas un GO application.**

## Mise à jour ciblée Q — chaîne QuickTime i386 C3-M3 (12 novembre 2026)

**OBS opérateur 5700X / preuve de liaison réelle, sans recette invitée.** Le [checkpoint C3-M3 R4](docs/evidence/quicktime-c3-m3-g2-prelink-2026-11-12.md#essai-16--r4--trois-liaisons-darwin-i386-réussies-chaîne-c3-m3-statique-atteinte) contient les SHA-256 et le chemin du rapport local. Après 61 objets i386 compilés séparément et le portage du vrai Memory Manager C4 dans un objet CarbonCore, les bibliothèques LaunchServices, CoreServices et QuickTime C3 ont chacune `LINK_EXIT=0` et les identités Mach-O i386 attendues. CoreServices réexporte CarbonCore C4 ; QuickTime importe `GetHandleSize`, `SetHandleSize`, `MemError` via CoreServices et exporte `GetMediaSample` dans la table nlist. Verdict local **`C3_M3_STATIC_CHAIN_PASS`** ; état historique et sous-modules préservés.

**Portée strictement statique :** aucun chargement de cette chaîne par `dyld`, aucun témoin C4 contre ce trio réel, aucun test audio, aucune exécution de QuickTime Player ni de Logic 8. Les correspondances globales `-dylib_file` manquantes ne sont pas une fermeture de dépendances. **Q-C4-D production : NO GO ; Logic 8 : NON QUALIFIÉ.**

**Prochain jalon :** réutiliser le garde M2 déjà publié sur les trois dylibs réelles (sans reconstruire), puis qualifier le chargement invité sous préfixe neuf et les oracles C3/C4 sans modifier l'installation historique.

## Mise à jour ciblée Q — QuickTime C4-D (10 novembre 2026)

**Reprise du jalon C4-D, sans modifier les priorités globales ni les résultats historiques v0.2.** État Git consulté : `master` = `d50ca8afbe5e6cdbb7574e2e870180ce6a0c972b` ; dernier commit QuickTime C4-D = [`c897c0e7`](https://github.com/fr4nck/d4rling/commit/c897c0e78276c3c5b281e7cbf8d7ea66957ebc0d).

| Porte Q | État au 10/11 | Critère nécessaire pour avancer |
| --- | --- | --- |
| Q-C3 — témoin QuickTime isolé | **PASS rapporté : 187 Linux + 187 Darwin i386** | Garder les sources et bases d'essai exactes |
| Q-C4-A/B/C — Memory Manager et QuickTime isolés | **PASS rapporté localement, preuves non accessibles ici** | Vérifier le vrai candidat C4 et ses journaux sur 5700X, sans reconstruction |
| Q-C4-D — sélection ciblée et réexport CarbonCore | **PASS hôte borné ; patch proposé seulement** | Qualifier la variante [G2 conservant l'ordre CMake](docs/evidence/quicktime-c4d-2026-11-10/c4d-cmake-order-preserving.patch) dans un checkout d'essai i386 |
| Q-C4-D-M2-R2 — vérificateur Mach-O | **32/32 PASS, 0 SKIP rapportés sur Linux, données i386 synthétiques** | Trois vraies dylibs issues du **même build** ; vérifier import, export, réexport, tranche et install name |
| Q-C4-D production | **NO GO** | Compilation/lien/chargement Darwin i386, GetMediaSample + Memory Manager C4, négatifs et non-régression C3/C4 |
| Logic Studio 8 | **NON QUALIFIÉ** | Prérequis runtime, QuickTime, audio et Audio Units réels ; ne pas inférer du banc Q |

Le [checkpoint vérifiable](docs/evidence/quicktime-c4d-2026-11-10/README.md) et [M2-R2](docs/evidence/quicktime-c4d-2026-11-10/C4D-M2-R2-host-replay.md) sont la référence détaillée. **Aucun CMake ou framework de production n'a été promu dans ce lot.** Les tests synthétiques supplémentaires ne sont pas un substitut au premier vrai build C4-D i386 ; les suspendre jusqu'à preuve nouvelle. `x86_64/Cocoa` général reste reporté, et Petite Victoire demeure hors périmètre.

## Actualisation v0.2 — 9 novembre 2026

**Portée :** synchronisation de la feuille de route avec les commits publics
jusqu'à `d2318ea3` et les résultats privés rapportés les 8–9 novembre.
Cette mise à jour ne rejoue aucun test, ne modifie aucune source et ne confère
aucun PASS général à Logic, QuickTime, Cocoa ou CoreAudio. Les journaux privés
et l'observation humaine restent distingués des preuves reproductibles Git.

| Axe | Acquis ou constat récent | Limite toujours ouverte |
| --- | --- | --- |
| **R — Mach-O i386 / BSD** | Témoin Carbon i386 normal/bypass et négatif validés sur le canon `c17bd4f7` ; `mldr32` intégré au fork (`559f9911`) ; sur darling-xnu `fb8f932`, B15 rendu inutile par l'amont (BM4 32/32) et correctif `syscall()`/dispatcher/LDT qualifié en exécution i386 réelle, 46/46 ([rapport](docs/evidence/bsd-i386-xnu-fb8f932-syscall-2026-11-14.md)) | Correctif versionné en patch : gitlink XNU non avancé faute de dépôt darling-xnu publiable (fork ou contribution amont à décider) |
| **U — Carbon** | PR internes [#2](https://github.com/fr4nck/d4rling/pull/2) et [#3](https://github.com/fr4nck/d4rling/pull/3) fusionnées ; 246 contrôles hôte sur fixtures ; doublon `SetEventParameter` supprimé dans `6659e6b9` | CI packaging sur le correctif, CoreFoundation réelle et couverture globale de l'interface à qualifier |
| **A/P — audio et Petite Victoire** | **OBS humaine du 8 novembre :** fenêtre du témoin Mach-O i386 jugée correcte, sans scintillement perceptible en Play/Stop, et musique entendue intégralement ; C11-G1-L rapportait `LIVE_TECHNICAL=PASS` | Résultat limité au démonstrateur et aux conditions d'écoute ; pas de mesure acoustique de latence, de test 10 minutes ni de preuve du moteur audio Logic |
| **Q — QuickTime** | Au-delà des 7 fonctions Q-A2 : `NewMovieFromDataRef` et `GetMovieDuration`, parseur MOV borné, extraction de PCM pris en charge et conservation mémoire (`02418473`, `d2318ea3`) ; 4 600 exports préservés | `QuickTime` complet non construit via CMake/Ninja (`gui_stubs` bloqué) ; aucune lecture audio/vidéo, aucun Player qualifié |
| **M — MIDI / AU** | Inventaire et contrats historiques disponibles | Pas de chaîne MIDI → Audio Unit historique → rendu Logic validée |
| **L — Logic Studio 8** | Audit privé : 71 binaires i386 et 9 979 imports ; 154 symboles QuickTime distincts (147 stubs **au stade Q-A2**, nombre à recalculer après `QT-NEXT`) | Aucune exécution Logic/EXS24 ; résolution des dépendances, Cocoa i386, Audio Units et moteur audio à qualifier |

**Lecture des résultats :** l'observation d'écoute de Petite Victoire est
postérieure au cas C10 muet conservé dans la [synthèse historique
B14/C10](docs/REPRISE-AUDIO-MUSIQUE-2026-11-08.md) : ces essais ne sont pas
interchangeables. Les nombres B11/B15 sont des comptes rendus de qualification
locale, non une reconstruction intégrale de la pile par la roadmap.

**Prévol privé B15-A6-R2 (OBS, non publié dans Git) :** 890/890 objets
`libsystem_kernel` disponibles, 3/3 substitutions BSD, recettes Ninja et
archives statiques i386/x86_64 reconnues pour le lien `dyld`.
`PASS_PREVOL_LIAISONS_PRIVEES` **n'est pas** un PASS de compilation ou liaison :
aucune des deux liaisons n'a été exécutée. Étape proposée **B15-A7** :
liens privés contrôlés, vérification des slices/exports/ABI et tests différentiels
dans une installation isolée ; canon, anciens préfixes et Petite Victoire intacts.

### Priorités de convergence après v0.2

1. **Terminer B15** sans substitution de binaires dans une installation
   historique ; distinguer la correction du dispatcher BSD du traitement
   `errno` déjà introduit en amont par
   [darling-xnu #49](https://github.com/darlinghq/darling-xnu/pull/49)
   (fusionnée le 7 novembre). Le correctif `mldr32` provient déjà de
   [Darling #1864](https://github.com/darlinghq/darling/pull/1864) :
   ne pas le reproposer comme nouveauté.
2. **Stabiliser Carbon et la reproduction** : vérifier le packaging sur
   `6659e6b9` et comparer nos événements/queues à la
   [PR amont #1780](https://github.com/darlinghq/darling/pull/1780) WIP,
   avant toute proposition de correction.
3. **Consolider QuickTime utile** : construire la cible `gui_stubs` dans un
   espace isolé ; qualifier ABI i386, erreurs, médias synthétiques et traces
   d'appels. Ne pas confondre copie de PCM et restitution sonore.
4. **Approcher Logic 8 par étapes** : obtenir un premier chargement des
   frameworks privés/du programme, puis seulement une interface et un projet
   vide. **Cocoa i386** peut être nécessaire à son interface ;
   le chantier général **x86_64/Cocoa est reporté**.
5. **Préserver le moteur audio original de Logic** : D4RLING reproduit les
   services Darwin/CoreAudio/Audio Units attendus. Un éventuel décodeur
   auxiliaire (FFmpeg ou autre) ne remplace pas le mixage, les instruments ou
   les effets Logic ; aucun accès bloquant dans le callback audio, et tests
   de non-régression obligatoires.

### Contributions vers Darling officiel — candidats, pas de PR autorisée

| Candidat | Niveau de préparation / décision |
| --- | --- |
| `shellspawn` : garde de taille 16 bits ([`2d6ef337`](https://github.com/fr4nck/d4rling/commit/2d6ef3378da25e81ad5c41e74a94d102e979b855)) | Diff court ; ajout de test de borne, revue et comparaison amont nécessaires |
| Carbon événements et files (PR internes #2/#3) | Code et 246 tests hôte ; intégrer la vraie CF, l'ABI i386 et coordonner avec #1780 |
| QuickTime MOV / PCM ([`d2318ea3`](https://github.com/fr4nck/d4rling/commit/d2318ea37f9edbdcd661408edfa8723b0289eb2e)) | Fonctionnalités originales et essais i386 ciblés ; CMake/Ninja et tests d'intégration encore bloquants |
| BSD i386 : `syscall()`, borne de table, `.no_sys`, LDT ([patch](reproduction/patches/bsd-i386-syscall-dispatch-fb8f932.patch)) | Delta distinct de #49, qualifié sur `fb8f932` ; PR darling-xnu à ouvrir par un contributeur humain, avec mention de l'assistance IA |

Conformément à la [stratégie de contribution](docs/decisions/strategie-contributions-amont.md),
l'intérêt technique d'un correctif ne vaut **pas** autorisation de soumettre
une PR. Aucun nouveau chantier x86_64 ni aucune modification de
`experiments/petite-victoire/` n'est autorisé par cette actualisation.

## État documentaire et preuves disponibles

| Référence | Ce qui est attesté par le document consulté | Limite à conserver |
| --- | --- | --- |
| [Reproduction du 29 octobre](reproduction/validation.md) | 135 contrôles Carbon hôte, répétition ASan, contrats C11/C++17 ; build des quatre lanceurs/serveur ; témoin Carbon Mach-O i386 NORMAL/BYPASS et négatif sans dylib | Adaptateur CF pour les tests hôte ; dylibs système privées de référence pour le témoin ; pas de build intégral des frameworks ni d'application complète |
| [État historique](PROJECT_STATE.md) et [reprise BH–CE](docs/d4rling-reprise-2026-10-29.md) | Preuves distinctes de chargement, instructions i386 et appels Carbon/paramètres | `b7d0cb6` + neuf modifications et test ignoré diffère de `master` ; les compteurs d'audits statiques ne sont pas des tests applicatifs |
| [Audit dyld/ABI](docs/research/i386-dyld-abi-audit-2026-11.md) et [V3/candidat source](docs/research/bsd-i386-v3-source-2026-11-08.md) | V1-R3 statique clos ; V3 privé revérifié : références 6 erreurs, B7 0 ; dispatcher source testé deux fois à 82 659 contrôles sans échec | V3 limité aux appels identifiés ; source testée avec gestionnaires synthétiques ; libsystem_kernel reconstruit, cerror/TLS et dyld intégré à qualifier ; C2/PR #8 distincts |
| [Reprise audio B14/C10](docs/REPRISE-AUDIO-MUSIQUE-2026-11-08.md) | Compte rendu : 36/36 contrôles positifs, 16/16 pannes, Float32 stéréo 44,1 kHz ; stop 36,1 ms, erreur 497 ms | Journaux d'origine non rejoués ici ; C10 muet au dernier essai concerné ; délai de stop distinct de la latence acoustique |
| [Exigences audio et Logic](docs/decisions/logic8-exigences-audio-et-chantiers-2026-11-08.md) | Retour distinct du 7 novembre : 440 Hz entendu via trajet i386/CoreAudio/B13/PulseAudio/WSLg, avec microcoupures | Observation rapportée à relier aux artefacts exacts ; ne valide ni la mélodie C10 ni une sortie fiable |
| [AUDIO-01 natif](experiments/audio01-native/README.md) | Source conservée ; autotest publié : 55 125 frames, 220 500 octets, `SELF_TEST_PASS` | Python Linux natif ; ni Mach-O/CoreAudio, ni preuve acoustique sur la machine cible |
| [Petite Victoire v0.1](experiments/petite-victoire/v0.1/README.md) et [architecture](experiments/petite-victoire/v0.1/docs/architecture.md) | Sources C++17, exports WAV/MIDI, aperçu Web Audio ; tests rapportés pour le moteur portable | Adaptateur Carbon non compilé/non exécuté dans ce lot ; lots Q7–Q12 absents de cette livraison, donc non attestés |

Une synthèse locale du 4 novembre, consultée pour cette publication, rapporte
aussi des témoins Carbon/CF, pthread `$UNIX2003`, C++/RAII et
`@executable_path` passants en copies privées, avec des limites de lancement
(préfixe long, collision de pile EEXIST). Ses originaux ne sont pas publiés
ici : **OBS locale, sans rejeu**, à consolider avant promotion en TEST public.
Les anciens pthread et toute l'ABI C++ ne sont pas qualifiés par ces témoins.

L'[audit documentaire Logic](docs/audits/logic-studio-8/2026-11-08-synthese.md)
et la note d'exigences décrivent des instantanés différents. L'inventaire
statique privé rapporté le 4 novembre existe ; vérifier sa couverture avant
d'en refaire un. `exs24.res` repéré ne localise pas à lui seul le DSP d'EXS24.
Les mentions historiques « aucune publication » dans la livraison v0.1
décrivent sa création ; la présence actuelle des sources dans Git est vérifiée.

## Règles de qualification communes

- **SRC/DOC** : source ou contrat lu à une révision donnée. **OBS** : résultat
  rapporté, avec provenance et disponibilité des originaux. **TEST** : essai
  exécuté et reproductible, commande, entrées et sorties conservées.
  **INF/HYP/OPEN** : inférence, hypothèse ou point non résolu.
- **PASS** qualifie uniquement un critère nommé sur un environnement fixé.
  Exiger attendu, résultat mesuré, témoin positif et négatif pertinent,
  absence de régression dans le périmètre et preuve de conservation.
- **BLOCKED** signifie qu'un prérequis manque : nommer le manque, sa preuve,
  la condition de reprise et une tâche indépendante encore possible.
  Un essai exécuté qui échoue est **FAIL**, pas PASS après relances sélectives.
  **À FAIRE** signifie que le critère n'a pas encore été essayé.
- Pour les séries ci-dessous, les nombres/durées sont des **seuils proposés
  pour les prochains essais**, pas des performances obtenues. Conserver tous
  les échecs et le nombre total de tentatives.
- Un son Web Audio, un export WAV, un PCM reçu, un callback Darwin et un son
  entendu sont des preuves différentes. Toute confirmation acoustique indique
  opérateur, date, machine et route de sortie ; aucune écoute n'est inventée.

## Dépendances et ordre de convergence

| Travail | Dépendances pour le résultat intégré | Travail autonome possible dès maintenant |
| --- | --- | --- |
| R — runtime i386 | Fournisseurs cohérents, dyld, ABI, threads/horloges | Lecture V1, contrats, fixtures et contrôles négatifs |
| U — Carbon/Cocoa | R pour l'invité ; affichage et backend identifiés | Tests hôte d'événements, contrats UI, oracle sans display |
| A — CoreAudio/PulseAudio | R, ABI HAL et pont Mach-O/ELF approprié | Inventaire des preuves B13/B14/C10, oracle PCM, banc natif |
| M — CoreMIDI/AudioUnit | R ; A pour le rendu audible ; Carbon Component Manager historique | Contrats MIDI, paquets/horloges, composant original de test |
| Q — QuickTime/QTKit | R ; U pour le Player ; A pour l'audio ; décodeurs autorisés | Petit contrat QuickTime utile et médias synthétiques |
| L — Logic Studio 8/EXS24 | R + Cocoa U + A + M + sous-ensemble Q réellement requis et frameworks privés | Matrice des besoins et localisation statique du DSP, en privé |
| P — Petite Victoire | Aucune dépendance Logic/QuickTime pour le moteur natif ; R/U/A pour Carbon i386 ; M pour MIDI externe | Développement réservé à fr4nck ; agents : lecture, signalement de blocages et travail séparé sur le socle D4RLING |

L'échec de L ne bloque ni Q ni P. Q n'attend pas l'EXS24. Les tests sans
audio de U/M et les tests natifs de P n'attendent pas une chaîne i386 complète.
Les intégrations partagent des contrats : ne pas modifier simultanément
l'ABI HAL, Carbon, CoreMIDI et le backend pour faire passer un démonstrateur.

## R — runtime Mach-O / Darwin i386

**État : partiellement attesté ; stabilité et ABI complète non qualifiées.**
Les témoins Carbon i386 conservent leur valeur. C2 et H-CF n'établissent pas
une correction générale de dyld ou des erreurs Darwin.

**Actualisation R-A1/R-A2 — 8 novembre :** V1-R3 et V3 ciblé sont acquis ;
le [candidat source](docs/research/bsd-i386-v3-source-2026-11-08.md) est qualifié sur son témoin synthétique i386,
avec deux séries de 82 659 contrôles et un rejeu de la recette publique.
L'intégration système et le dyld restent À FAIRE ; aucun statut global
R1/R2/R3 n'est clos par ces seuls résultats. L'issue #11 reste ouverte.

| Jalon | Critère mesurable de PASS et preuves attendues | Dépendance / BLOCKED |
| --- | --- | --- |
| R1 — provenance et ABI | Identifier les slices et empreintes des binaires réellement utilisés ; désassemblage brut i386 validé de V1 ; séparer convention de retour, CF/errno et hypothèse H-CF | BLOCKED si tranche/outils/objets indisponibles ; aucune correction sur une étiquette d'analyseur |
| R2 — lancement déterministe | Même témoin terminant : 10/10 départs à préfixes frais, code 0 et marqueur exact ; négatif sans dylib échoue sans marqueur ; enregistrer stdin, pile et tous les essais | Dépend de R1 et des fournisseurs ; collision EEXIST ou timeout inexpliqué bloque la stabilité |
| R3 — contrats de liaison et langage | Positifs/négatifs pour `@loader_path`, `@executable_path`, `@rpath` ; pthread anciens, TLS, callbacks, exceptions/destructeurs sur témoins bornés | Les variantes UNIX2003 seules ne ferment pas les noms anciens ; C2 exige symlinks/normalisation/chemins restreints avant généralisation |

**Lot R-A1 :** V1 statique clos ; lire V3 et le candidat source ci-dessus
avant toute nouvelle inspection. **Lot R-A2 :** utiliser les fixtures publiées ;
la prochaine correction intégrée doit qualifier les vrais retours/errno,
puis dyld séparément, dans une nouvelle installation privée. Écritures : nouveaux rapports publics expurgés dans
`docs/research/`, nouvelles sources dédiées dans `reproduction/fixtures/`.
Chargeur, libSystem, sous-modules dyld/XNU et C2 restent hors écriture sans
mission de correction explicite. Aucun nouveau V3 runtime n'est autorisé
par cette seule roadmap.

## U — Carbon et Cocoa/AppKit

**État au 9 novembre :** contrats et événements Carbon testés sur un banc
hôte isolé ; interface du seul démonstrateur Petite Victoire observée
fonctionnelle en i386, sans validation de l'interface de Logic ni du backend
Carbon/Cocoa dans son ensemble. Voir l'actualisation v0.2. L'[audit UI](docs/carbon-ui-roadmap.md) est daté :
ses anciens constats de stubs d'événements doivent être lus avec les
[résultats de queue/dispatch](docs/carbon-queue-dispatch-2026-10-22.md).
Logic 8 requiert aussi Cocoa **i386** ; une fenêtre Carbon ne qualifie pas
son interface. L'axe x86_64/Cocoa générique reste volontairement différé.

| Jalon | Critère mesurable de PASS et preuves attendues | Dépendance / BLOCKED |
| --- | --- | --- |
| U1 — contrats | Rejouer les runners pertinents sur la source choisie ; ABI i386, callbacks, propriété mémoire et erreurs vérifiés ; cas sans affichage retourne une erreur réelle | Contrats hôte possibles sans R ; invité dépend de R |
| U2 — une fenêtre Carbon | Affichage/repaint, clic, clavier et fermeture vers le bon handler ; 20 cycles créer/fermer sans objet/handler résiduel ; fermeture d'une fenêtre distincte de quitter | BLOCKED si backend/display absent ou événement non livré ; capture seule insuffisante |
| U3 — un parcours Cocoa | Programme Cocoa i386 avec menu/contrôle, événements, fermeture propre ; qualifier séparément vue Carbon intégrée, nib et contrôles réellement nécessaires à la cible | Dépend de R et AppKit cohérent ; UI Logic reste BLOCKED tant que ses besoins réels manquent |

**Lot U-A1 :** étendre un contrat d'événement ou un oracle de fenêtre dans un
runner dédié. Écritures : `tests/regressions/carbon-*/` et note associée.
Une correction dans `src/frameworks/Carbon/` ou Cocotron exige une liste de
fichiers attribuée ; aucun remplacement global d'AppKit ni faux succès UI.

## A — CoreAudio / PulseAudio

**État au 9 novembre :** backend réel dans les sources ; écoute intégrale de
Petite Victoire confirmée humainement le 8 novembre sur la chaîne i386 ;
reproduction, stabilité prolongée et latence acoustique encore à qualifier.
Les comptes rendus audio antérieurs décrivent d'autres essais. Conserver PulseAudio,
l'ABI HAL et les acquis B11/B13/B14/C10. L'[audit historique
CA-01 à CA-12](docs/audits/coreaudio-i386-heritage.md) donne des oracles,
pas une liste de défauts encore ouverts sur toute révision.

**Qualification R0 / AUDIO-A1-T1 (9 novembre 2026) :** [premier signal i386 via CoreAudio-B14 entendu sur le socle canonique](docs/evidence/audio-r0-a1-t1-2026-11-09.md). Le test unique rapporte un PASS technique (786 432 octets/96 blocs, PulseAudio terminé, 38 bibliothèques système depuis R0) et une observation humaine distincte du signal de 440 Hz. CoreAudio-B14 reste externe au profil `core` ; la stabilité temps réel, les négatifs audio et le CoreAudio de `master` ne sont pas qualifiés. **A2 reste partiel.**

| Jalon | Critère mesurable de PASS et preuves attendues | Dépendance / BLOCKED |
| --- | --- | --- |
| A1 — réconcilier les preuves | Associer chaque lot à sources, SHA, architecture, installation, callback, format et sortie ; distinguer natif, mock et véritable invité ; localiser les originaux privés sans les publier | BLOCKED pour la promotion TEST si journaux/artefacts absents ; ne pas effacer les observations |
| A2 — premier trajet audible | Mach-O i386 → CoreAudio/HAL → pont qualifié → PulseAudio → sortie identifiée ; PCM synthétique vérifié et confirmation acoustique ; négatifs sans sortie et format refusé | Dépend de R ; ELF64 PulseAudio ne peut pas être appelé directement comme ELF32 |
| A3 — transport stable | Mélodie C10 réellement entendue ; 10 min de lecture, 20 Stop/reprises et boucle ; relever xruns, erreurs, CPU/RAM et timestamps ; zéro microcoupure constatée selon le protocole déclaré | BLOCKED tant que C10 muet ou microcoupures inexpliquées ; pannes propagées, jamais masquées |
| A4 — fichiers et mesures | WAV/AIFF synthétiques lus avec format/frames attendus ; mesurer séparément latence acoustique, acquittement de stop et détection d'erreur ; protocole et seuil d'usage annoncés avant essai | Pas de revendication « faible latence » sans mesure ; capture/full-duplex et JACK sont des qualifications ultérieures distinctes |

**Lot A-A1 :** registre de convergence et oracle format/propriétés/erreurs.
Écritures : `docs/evidence/` et sources d'un banc isolé sous `experiments/`.
`src/CoreAudio/`, le pont ELF/IPC et B11–C10 sont partagés : correction
uniquement sur fichiers attribués après comparaison des versions.
Aucun basculement de backend JACK/PipeWire dans ce lot.

## M — CoreMIDI et AudioUnit historique

**État : stubs historiques identifiés ; branches MIDI à comparer ; aucune
chaîne MIDI/AU générale démontrée.** Cibler les contrats 10.4/10.5 et le
Carbon Component Manager, sans supposer que l'API AudioComponent plus récente
suffit. Un synthétiseur natif n'est pas EXS24.

| Jalon | Critère mesurable de PASS et preuves attendues | Dépendance / BLOCKED |
| --- | --- | --- |
| M1 — contrat MIDI | Signatures/layouts i386, création/destruction clients/ports, bornes MIDIPacketList, callbacks/horloges ; négatifs paquet tronqué, tampon plein, endpoint invalide | Tests hôte autonomes ; transport invité dépend de R et d'un backend identifié |
| M2 — notes transmises | 1 000 paires Note On/Off sur endpoint virtuel ; ordre et timestamps contrôlés, zéro perte/duplication/note bloquée ; arrêt/déconnexion propres | Matériel optionnel séparé ; boucle virtuelle ne prouve pas un périphérique physique |
| M3 — composant AU | Découvrir, ouvrir, initialiser, rendre et fermer un composant i386 original de test par le chemin historique ; formats refusés et échecs réellement retournés | R + Component Manager ; A pour l'audibilité ; disponibilité propriétaire non requise pour le composant original |
| M4 — convergence musicale | Note MIDI → instrument de test → PCM audible ; paramètres/état restaurés ; graphe minimal et arrêt de 20 cycles sans note ni worker résiduel | Dépend de M2/M3/A ; ne qualifie pas tous les AU ou tout AUGraph |

**Lots M-A1 / M-A2 :** paquets MIDI et composant AU de test peuvent être
préparés séparément dans des sous-dossiers distincts de `tests/regressions/`.
`src/frameworks/CoreMIDI/` et `src/CoreAudio/` restent hors écriture
commune sans attribution. Préserver ABI publique, backend et durée de vie.

## Q — QuickTime / QTKit, jalon autonome

**État : audits de stubs disponibles ; aucun QuickTime Player fonctionnel
attesté.** Démonstrateur visé : **QuickTime Player exécuté sous D4RLING avec
lecture vidéo et audio réelle**. Son import set exact reste à établir depuis
une copie légitime disponible, sans téléchargement implicite.

**Historique Q-A2 (8 novembre) :** le [cycle de Movie vide](docs/evidence/quicktime-q-a2-empty-movie-2026-11-08.md)
implémente sept fonctions, d'abord qualifiées sur l'hôte Windows x64.
**État au 9 novembre :** Q-A3 a qualifié le sous-ensemble en Mach-O i386 ;
[QT-NEXT](tests/regressions/quicktime-mov-dataref/README.md) prend en charge
les MOV en mémoire via référence pointeur et leur durée (5 118 contrôles,
0 échec sur le témoin i386). [QT-MOV-02 R3](tests/regressions/quicktime-mov-pcm/README.md)
conserve certains échantillons PCM dans l'objet Movie (40 contrôles i386,
0 échec ; extracteur natif 20 149 contrôles, 0 échec). Ces fonctionnalités
ne restituent pas encore de son, ne couvrent pas les pistes publiques et ne
valident ni QTKit ni le Player ; construction de la cible `QuickTime`
par CMake/Ninja toujours BLOCKED.

| Jalon | Critère mesurable de PASS et preuves attendues | Dépendance / BLOCKED |
| --- | --- | --- |
| QT1 — runtime utile | Petite API réellement appelée : initialisation, ouverture/fermeture, erreurs et ressources ; 20 cycles et négatifs fichier absent/tronqué | R ; contrat ciblé possible avant le Player, sans nouveau catalogue de milliers de stubs |
| QT2 — vidéo | Ouvrir un .mov synthétique redistribuable ; frames identifiées, dimensions/cadence/durée attendues, play/pause/seek et image affichée | Décodeur autorisé + U ; export ou décodage seul distinct d'affichage |
| QT3 — audio | Extraire le PCM connu et le restituer via A ; frames/format/fin de flux et son confirmés | A ; le son d'un autre lecteur ne ferme pas ce jalon |
| QT4 — intégration et Player | Copie légitime du Player identifié ; ouvrir/fermer 5 fois ; lecture 5 min, contrôles interactifs, pas de fuite manifeste ; dérive A/V mesurée ≤ 80 ms avec média de test à repères | R/U/A ; préciser version et APIs QTKit réellement exercées ; Player absent = BLOCKED applicatif |
| QT5 — besoins Logic | Chaque appel QuickTime requis dans un scénario Logic borné a fournisseur, comportement et témoin ; erreurs propagées | Dépend des imports réels de L ; QT1–QT4 restent autonomes |

Le seuil de 80 ms est un objectif de banc initial, pas une mesure existante
ni une qualification professionnelle. QTKit doit avoir ses propres témoins :
un Player utilisant QuickTime ne prouve pas automatiquement tout QTKit.

**Lot Q-A1 :** média synthétique, oracle et une API utile, dans
`tests/regressions/quicktime-*/` et `docs/evidence/`.
`src/frameworks/QuickTime/` et `src/frameworks/QTKit/` sont les périmètres
candidats d'une correction attribuée. Ne pas incorporer de binaire Player,
codec propriétaire, SDK ou média commercial.

## L — Logic Studio 8 et EXS24 authentique

**État au 9 novembre :** audit statique privé des binaires i386 disponible,
avec matrice QuickTime datée Q-A2 (154 imports distincts dont 147 stubs à
cette date). Aucun chargement applicatif de Logic ni restitution EXS24
qualifiés. Ne pas utiliser cette matrice comme trace d'appels runtime. Les besoins
musicaux incluent édition MIDI/quantification non destructive, instruments,
Bitcrusher, Space Designer, compresseur et limiteur. Leur présence dans une
liste de dépendances ne démontre pas leur fonctionnement.

| Jalon | Critère mesurable de PASS et preuves attendues | Dépendance / BLOCKED |
| --- | --- | --- |
| L1 — besoin exact et faisabilité | Réutiliser l'audit privé : versions, tranches, imports/dépendances fortes-faibles/transitives, classes/sélecteurs et frameworks privés ; matrice requis/implémenté/stub/absent/non vérifié ; premier bloqueur et estimation argumentée GO/GO limité/NO-GO | BLOCKED sur entrées manquantes ; ne pas recopier les DVD ni refaire tout l'inventaire |
| L2 — démarrage puis projet vide | Après autorisation explicite d'essai propriétaire et prérequis bornés R/U/A/M/Q : démarrage, ouverture/fermeture et sauvegarde/réouverture d'un projet vide en copie privée | Cocoa, ProKit/ECore/XAudioUnits et dépendances exactes ; jamais un lancement prématuré pour compter les stubs |
| L3 — parcours musical | Projet original minimal : lecture audio/MIDI, édition, quantification réversible sans altérer les notes sources ; sauvegarde et rendu relus ; 10 min sans arrêt imprévu | L2 + A/M ; comparer à une référence légitime, noter les fonctions non exercées |
| L4 — EXS24 authentique | Localiser le DSP réel, charger l'instrument original et une banque légitimement détenue en privé ; notes/vélocités/polyphonie/arrêt/export comparés à la référence | `exs24.res` seul insuffisant ; aucun synthétiseur de remplacement ne ferme ce jalon |
| L5 — usage Studio | Qualifier séparément chaque instrument/effet visé, automation, rendu, fiabilité et ressources sur projets définis ; publier une matrice des scénarios passants/échoués | Aucun PASS global « Logic Studio compatible » fondé sur un projet ou un instrument |

**Lot L-A1 :** compléter une lacune de matrice en lecture seule et produire
une synthèse publique expurgée sous `docs/audits/logic-studio-8/`.
Originaux/DVD, banques, frameworks privés et rapports bruts restent privés,
sans écriture. Aucun patch binaire ni contournement de licence.

## P — Petite Victoire, prototype natif et DAW possible

**État au 9 novembre :** moteur et exports portables présents ; exécution
Carbon Mach-O i386 avec musique effectivement entendue et fenêtre correcte
**observées** par fr4nck le 8 novembre. C10/C11 et les mesures instrumentées
restent des preuves distinctes ; pas de qualification de Logic ni de stabilité
sur une session de production. Le nom peut changer. La trajectoire DAW reste une
orientation, sans promesse de calendrier ni assimilation à Logic.

**Rôle de validation :** permettre à une personne ne disposant pas de Logic
Studio 8 de composer et jouer un petit projet original, puis de vérifier
concrètement le socle musical D4RLING. Le parcours de référence doit fournir
sources redistribuables, séquence et médias originaux, commandes, résultats
attendus et rapport de couverture, sans binaire, banque ni ressource Logic.

| Fonction vérifiée avec Petite Victoire | Preuve attendue dans le mode concerné |
| --- | --- |
| Runtime i386 (R) | Le binaire invité identifié démarre et termine correctement ; le mode Linux natif reste une preuve distincte |
| Interface Carbon (U) | Fenêtre, édition, événements et fermeture réellement exercés ; aucune extrapolation à Cocoa non testé |
| Audio CoreAudio/PulseAudio (A) | Chemin d'appel identifié, mélodie entendue, format, boucle, Stop/reprise, erreurs et stabilité mesurés |
| MIDI / AudioUnit (M) | Lorsque intégrés : notes transmises, horodatages et rendu du composant de test original ; les exports MIDI seuls ne ferment pas ce critère |
| Usage musical et conservation (P) | Petit projet édité, sauvegardé/réouvert et exporté sans perte ni écrasement ; couverture et limites reproductibles sans Logic |

Ce rôle est un **objectif à qualifier**, sans nouveau résultat revendiqué.
Chaque rapport précise mode, révisions, matériel, contrôles PASS/FAIL/BLOCKED
et fonctions non exercées. QuickTime/QTKit et Logic/EXS24 conservent leurs
jalons applicatifs propres.

**Responsabilité : fr4nck.** Aucun lot P n'est proposé à la prise en charge
autonome par un agent. Toute intervention dans `experiments/petite-victoire/`
ou évolution du produit exige une demande explicite et ciblée de fr4nck.
Les agents peuvent lire, signaler les blocages et développer les couches
D4RLING dans leurs périmètres attribués avec des témoins séparés.

| Jalon | Critère mesurable de PASS et preuves attendues | Dépendance / BLOCKED |
| --- | --- | --- |
| P1 — base native reproductible | Rejouer CMake/CTest et, si Node déjà présent, le test web v0.1 ; contrôler MIDI type 1, WAV et absence d'écrasement ; rapprocher sources et livraison | Autonome Linux ; tests rapportés distincts des nouveaux essais ; droits/provenance à clarifier avant distribution élargie |
| P2 — expérience native sonore | Transport et édition fonctionnent ; mélodie audible via sortie Linux native, volume/pan/boucle/Stop ; exports explicites sans écrasement | A natif ; le navigateur reste un aperçu séparé, sans preuve Carbon |
| P3 — intégration D4RLING | Même séquence et commandes dans une fenêtre Carbon i386 avec CoreAudio ; UI/transport synchronisés ; arrêt propre et contrôle négatif sans backend | R/U/A ; ne pas remplacer B13/B14 pour contourner un défaut |
| P4 — outil musical original | Métronome : accents, subdivisions, ternaire, swing, rythmes asymétriques/polyrythmies et claves définis par exemples ; tests de positions/durées et écoute ; édition/quantification réversibles | M seulement pour MIDI externe ; lots Q7–Q12 à retrouver avant réimplémentation |
| P5 — décision DAW | Définir puis qualifier un petit scénario multipiste : audio/MIDI, enregistrement, automation, effet original, sauvegarde/réouverture sans perte et rendu ; budget CPU/RAM/latence mesuré | Décision produit après P2 ; compatibilité AU via M optionnelle et distincte d'EXS24 |

**Travaux réservés à fr4nck :** oracle musical/métronome, transport/exports
natifs et intégration du démonstrateur dans `experiments/petite-victoire/`.
Les anciens identifiants P-A1/P-A2 ne sont plus des lots autonomes pour agents.
L'archive source historique reste intacte ; la version suivante et son nom
relèvent de fr4nck. Toute aide d'un agent porte uniquement sur la tâche
explicitement déléguée. Ne pas importer les sons, DSP ou interface commerciale
de Logic ; préserver les exports à destination explicite.

## Organisation du travail autonome et sortie attendue

Un agent prend **un lot**, un objectif observable et une liste de fichiers.
Consulter [AGENTS.md](AGENTS.md) pour le prévol, le contrat d'écriture et
le format de preuve. La table des lots donne des périmètres candidats,
pas une autorisation de modifier tout un sous-système.

Priorité de convergence au 9 novembre : B15-A7 en isolation, vérification
CI Carbon, intégration QuickTime `gui_stubs`, puis chargement de composants
Logic sans toucher à son moteur audio. Rapprocher les preuves existantes R/A/P,
fermer les petits contrats bloquants, puis démontrer des parcours complets. L'audit
V1 et les oracles MIDI/QuickTime peuvent avancer indépendamment côté agents.
Petite Victoire progresse en parallèle sous la conduite de fr4nck, avec les
contrats du socle et ses propres preuves. Pas de fusion générale des branches.

Chaque livraison indique : lot, SHA de base et correctif éventuel, fichiers
touchés, commandes réellement exécutées, attendus/résultats, contrôles
négatifs, PASS/FAIL/BLOCKED, limites et prochain déblocage. Mettre à jour
l'état et la recette lorsque le résultat change une conclusion ; conserver
les anciens rapports datés. Aucun pourcentage global de compatibilité.

## Périmètres protégés et publication

- Préserver `b7d0cb6` et ses neuf modifications, `parameters.c` ignoré,
  builds, installations, préfixes actifs et preuves B11–C10/Carbon existantes.
  Aucun checkout/reset/clean/stash/pull dans la copie historique.
- Écrire uniquement dans les fichiers attribués et un espace neuf identifié ;
  aucune installation globale, modification sysctl ou arrêt de serveur historique.
- Pas de téléchargement/installation silencieux. Les lectures GitHub de
  documentation/source annoncées par une mission sont distinctes d'un clone,
  d'une récupération de sous-modules, de SDK ou de paquets.
- Dépôt public : uniquement documentation originale, sources redistribuables,
  métriques et preuves expurgées. Aucun binaire Logic/EXS24/Player propriétaire,
  DVD, banque commerciale, clé, trace privée ou archive de récupération.
- Commits documentaires en français, `[skip ci]` adapté aux changements
  strictement documentaires. Cette livraison vise directement `master`,
  sans branche ni PR, sans force-push. Les publications futures suivent
  l'autorisation de leur mission ; aucune contribution amont implicite.
- Respecter les auteurs/licences par fichier et [CREDITS.md](CREDITS.md),
  ainsi que la [stratégie amont](docs/decisions/strategie-contributions-amont.md).
