# AGENTS.md — travailler de façon autonome dans D4RLING

Ce guide s'applique au dépôt entier, sous réserve des consignes plus précises
d'un sous-dossier et de la mission explicite de l'utilisateur. Il encadre le
travail ; sa lecture ne déclenche ni expérimentation ni publication.
Objectif : livrer une amélioration bornée, prouvée et réutilisable sans
endommager les travaux existants ni annoncer une compatibilité non démontrée.

## Gouvernance transversale — PMSL-ARCH

La **source de règles transversales de développement** est le dépôt privé
[`fr4nck/PMSL-Arch`](https://github.com/fr4nck/PMSL-Arch), branche `main` :
[`AGENTS.md`](https://github.com/fr4nck/PMSL-Arch/blob/main/AGENTS.md) et
[`docs/GOUVERNANCE_AGENTS_OBJECTIFS.md`](https://github.com/fr4nck/PMSL-Arch/blob/main/docs/GOUVERNANCE_AGENTS_OBJECTIFS.md).
Avant tout chantier technique significatif, l'agent ayant accès à ce dépôt
consulte ces deux textes, en particulier **AGT-001 à AGT-014**, puis ce guide
local et les instructions du sous-système. L'accès au dépôt privé n'est pas
présumé pour un contributeur extérieur : ne jamais prétendre avoir consulté
une règle inaccessible. Dans ce cas, appliquer au minimum les garde-fous
autonomes ci-dessous et signaler toute règle non vérifiable dont dépend
l'autorisation ou la sûreté d'une opération. En cas de conflit ou
d'incertitude bloquante, **arrêter l'opération concernée et demander un
arbitrage**, sans contournement tacite.

**Contrat obligatoire avant création, développement, script ou délégation
à un agent :**

1. Identifier le **dépôt canonique**, l'état réel de `master`, les éventuels
   changements locaux, la source de vérité et les solutions déjà disponibles.
2. Réutiliser sources, builds, tests, dépendances et outils existants avant de
   créer une copie, un mécanisme ou un environnement parallèle ; justifier
   explicitement toute exception.
3. Conserver **une seule branche de développement : `master`**, un checkout
   canonique et un build/une installation de référence, avec traçabilité
   source → build → préfixe → essais. Les anciennes copies restent protégées
   jusqu'à décision explicite de migration ou de suppression.
4. Pour le travail pérenne sur le 5700X, viser **au plus trois zones
   permanentes** sous `/home/Deniel/d4wrling-work` :
   `canon/` (sources, build, installation), `validation/` (tests et sorties
   bornées) et `historique/` (preuves protégées). **C'est une cible
   d'organisation, pas une autorisation de créer ces dossiers, déplacer les
   copies actuelles ni nettoyer l'existant.** Utiliser l'espace autorisé par
   la mission ; ne pas multiplier les racines ou dossiers horodatés par
   défaut. Les essais temporaires ont un propriétaire, une limite et une
   politique de conservation.
5. Avant toute commande à effet, annoncer le **shell**, les chemins lus et
   écrits, le volume, les accès réseau, les changements Git et les risques.
   Aucune installation, copie volumineuse, écriture sur volume Windows ni
   téléchargement implicite. Un clone partiel peut déclencher un *lazy fetch*
   même en lecture ; le prévenir explicitement.
6. Aucune suppression, aucun déplacement, écrasement, force-push, reset
   destructif ou réécriture d'historique sans autorisation spécifique.
   Préserver `experiments/petite-victoire/`, ses preuves et les installations
   historiques selon les restrictions renforcées plus bas.
7. Une correction n'est **intégrée** que si elle est revue, testée au niveau
   pertinent et présente dans `master` ; un PASS synthétique, un commit
   publié et une recette réelle sont trois états distincts. Porter les
   corrections qualifiées par petits changements traçables, sans assembler
   arbitrairement des binaires issus de builds différents.
8. Définir le livrable demandé **maintenant**, la preuve attendue, les tests
   négatifs, un budget de travail et un **critère d'arrêt**. Ne pas étendre
   « go » à des chantiers implicites.
9. Les prompts destinés à un autre agent et les scripts livrés à l'utilisateur
   doivent être **complets et collables en une seule fois**, avec prévol du
   dépôt réel, bon répertoire, protections, lancement et bilan ; aucune
   retouche manuelle exigée.
10. Avant diagnostic ou correctif non trivial, lire **documentation officielle
    et code/version réels** (AGT-014). Si une précondition manque, signaler
    le blocage plutôt que multiplier des essais ou fabriquer des prérequis.

La mémoire conversationnelle ne remplace **jamais** ce prévol documentaire.
Les règles spécifiques D4rling ci-après renforcent ce contrat ; elles ne
l'annulent pas. Aucun changement des dossiers existants n'est autorisé par
ce document seul.

## Petite Victoire — développement réservé au responsable du projet

**Le responsable du projet garde la main sur le développement et les choix de produit de Petite
Victoire**, y compris son nom et son évolution éventuelle vers un DAW.
Les agents ne choisissent pas spontanément un lot de développement de ce
projet et n'écrivent pas dans `experiments/petite-victoire/` (code, tests,
interface, ressources, documentation du produit, versions ou archives).

Une intervention exige une **demande explicite et ciblée du responsable du projet**.
Une mission générale de développement autonome de D4RLING ne délègue pas
Petite Victoire. La lecture et le signalement de blocages restent possibles
dans le périmètre de la mission ; proposer une évolution ne vaut pas
autorisation de l'implémenter.

Petite Victoire doit devenir le démonstrateur musical de référence pour
vérifier les fonctions de D4RLING **sans posséder Logic Studio 8**.
Les agents peuvent préparer et qualifier le socle D4RLING avec leurs propres
témoins, puis documenter les contrats utilisables par le responsable du projet. La validation
par Petite Victoire porte sur les chemins réellement exercés et identifiés :
mode natif et mode invité i386 sont distingués, ainsi que les fonctions
encore absentes ou non testées. Les jalons Logic/EXS24 et QuickTime gardent
leurs preuves applicatives propres.

## 1. Lire avant d'agir

Lire dans cet ordre :

1. [PROJECT_STATE.md](PROJECT_STATE.md), état historique de reprise ;
2. [reproduction/README.md](reproduction/README.md) et
   [reproduction/refs.lock.json](reproduction/refs.lock.json) ;
3. [ROADMAP.md](ROADMAP.md), preuves récentes et lots indépendants ;
4. le README et les rapports datés du sous-système choisi ;
5. [CREDITS.md](CREDITS.md) avant toute réutilisation de code.

Le README racine renvoie à cet état pour les reprises depuis mobile.
Confronter les dates **et les révisions** : `master`, branches de travail,
snapshot historique et installation testée sont des états différents.
Ne pas transformer une vieille note « stub » en diagnostic actuel sans relire
le code ; ne pas transformer une nouvelle observation en qualification de
tous les anciens chemins.

Références de convergence : [audio B14/C10](docs/REPRISE-AUDIO-MUSIQUE-2026-11-08.md),
[dyld/ABI V0–V2](docs/research/i386-dyld-abi-audit-2026-11.md),
[exigences Logic](docs/decisions/logic8-exigences-audio-et-chantiers-2026-11-08.md),
[Petite Victoire v0.1](experiments/petite-victoire/v0.1/README.md).
Les recettes publiques indiquent le shell et la distribution attendus ;
ne pas exécuter une commande Bash comme une commande PowerShell.

## 2. Prévol sans mutation

- Identifier dépôt, branche, HEAD, statut, index, diff et sous-modules
  disponibles par des lectures bornées. Chercher d'abord avec `rg` /
  `rg --files`. Ne pas publier les sorties brutes si elles révèlent des
  données locales. Une copie sans `.git` est une copie de documents, pas
  un checkout : ne pas y inventer un état Git.
- Noter les fichiers modifiés/ignorés, leurs propriétaires de travail et les
  références nécessaires au lot. Préserver tout changement préexistant.
  Si la cible est déjà modifiée, lire le diff et choisir des fichiers neufs
  ou signaler le conflit ; ne pas écraser ni intégrer ce diff par défaut.
- Déterminer l'environnement réel : Linux/WSL2, architectures ELF/Mach-O,
  outils déjà présents, display, bibliothèques et route audio si nécessaires.
  Ne pas confondre le PC WSLg testé et un MacBook sous Linux.
- Choisir un espace de travail unique sous le dossier de projet autorisé,
  avec build, exports et rapports dédiés ; estimer volume et parallélisme.
  Ne pas dupliquer des builds/archives volumineux automatiquement.
- Aucun `fetch`, clone, récupération de sous-module ou paquet caché dans un
  prévol. Un clone partiel/promisor peut télécharger même pendant une
  lecture Git : vérifier la disponibilité locale, désactiver la récupération
  automatique selon l'outil, ou utiliser l'API GitHub pour les lectures
  distantes annoncées par la mission. Signaler un objet absent.

## Règles de l'amont Darling (synchronisation du 14 novembre 2026)

L'amont `darlinghq/darling` publie son propre `AGENTS.md`, conservé sans
modification dans [docs/upstream/darlinghq-AGENTS.md](docs/upstream/darlinghq-AGENTS.md).
Il ne remplace pas ce guide pour le travail dans D4rling, mais s'applique
intégralement à toute proposition destinée à l'amont (contrat public,
couches macOS, preuves admissibles, balises `QUIRK:`, aucune information
issue du désassemblage de binaires Apple), en complément de la
[stratégie amont](docs/decisions/strategie-contributions-amont.md).

## Coordination inter-conversations — journal Git partagé (10 novembre 2026)

Le dépôt GitHub `fr4nck/d4rling`, branche `master`, est le **point de
synchronisation commun** entre les conversations ChatGPT, agents locaux et
autres contributions. Une conversation, un rapport oral ou une session
terminale ne remplace pas les commits et documents publiés.

**Avant chaque nouveau lot, reprise ou changement de chantier :**

1. Lire le SHA courant de `master` **et les derniers commits** ; examiner
   les diffs qui touchent les fichiers, contrats, dépendances ou preuves du lot.
   Comparer avec le SHA de départ de la conversation ou du checkout local.
2. Lire le checkpoint publié le plus récent dans le périmètre concerné,
   puis vérifier l'état du checkout local, les modifications non commitées et
   les artefacts non publiés. Ne pas refaire un lot déjà qualifié ni ignorer
   un travail plus récent sous prétexte que la conversation est ancienne.
3. Définir un lot court et des fichiers attribués. Lorsque deux travaux
   risquent d'écrire les mêmes fichiers, coordonner la propriété avant
   modification ; réserver les fichiers partagés à un seul intégrateur.

**À chaque évolution et en fin de lot :**

- Publier un **commit séparé, traçable et de portée réduite** pour toute
  évolution **achevée et vérifiée** dans le périmètre autorisé : correction,
  test, documentation ou décision. Le commit mentionne le lot, l'état
  technique et renvoie vers les preuves utiles. Les tests pertinents doivent
  passer avant intégration d'une modification de production.
- Si un candidat, un résultat local ou une dépendance n'est pas encore
  qualifié ou accessible depuis GitHub, publier **uniquement un checkpoint
  documentaire honnête**, lorsque sa publication est autorisée :
  révision, provenance, résultats rapportés vs vérifiés, limitations,
  statut `PASS`/`FAIL`/`BLOCKED`, et prochaine action exacte.
  Ne pas publier du code non qualifié sous prétexte de le sauvegarder.
- À chaque checkpoint, distinguer les faits observés directement par
  l'agent des résultats **rapportés depuis un autre poste ou une autre
  conversation**. Ne jamais présenter ces derniers comme des tests rejoués.

**Juste avant chaque commit ou publication :** relire à nouveau `master`,
inspecter les nouveaux commits et les fichiers concernés. Si la tête a
changé, comparer et réconcilier avant toute écriture ; ne jamais écraser
silencieusement un travail concurrent. Publier uniquement en avance normale
avec vérification explicite de la tête attendue, sans force-push, reset ni
historique réécrit. Après publication, relire la tête et les fichiers,
puis communiquer SHA complet, URL, périmètre, preuves et prochain jalon.

Ces contrôles se font **à chaque session et à chaque publication** ; ils
ne constituent pas une surveillance continue en arrière-plan. Conserver
la règle de branche unique `master` et toutes les protections du présent
guide, notamment les exclusions de Petite Victoire, les installations
historiques et les données propriétaires.

## 3. Choisir et borner un lot

Prendre un seul identifiant de [ROADMAP.md](ROADMAP.md), par exemple R-A1,
A-A1, Q-A1 ou M-A1. Dans une mission autorisant le développement autonome,
choisir le plus petit lot utile dont les entrées sont disponibles ; annoncer
objectif, preuves et fichiers avant de modifier. Une mission documentaire
reste documentaire.

Fixer un contrat de tâche court :

```text
Lot / objectif observable :
Base : dépôt, branche, SHA, overlay éventuel, sous-modules concernés
Entrées disponibles / manquantes :
Écritures autorisées : liste exacte de fichiers et répertoire de sortie
Hors périmètre / fichiers partagés réservés :
Critère PASS : résultat attendu et méthode de mesure
Contrôles négatifs / erreurs / régressions :
Condition BLOCKED et tâche indépendante de repli :
Livraison : sources, preuve expurgée, commande de reproduction, limites
Publication autorisée : destination et mode explicitement demandés
```

L'autorisation explicite de la mission suffit pour ses actions nécessaires ;
ne pas redemander la même permission. Si une entrée ou une autorisation
nouvelle manque, avancer sur les parties indépendantes et poser une seule
question précise. **Ne pas élargir silencieusement le périmètre.**

Les lots ci-dessous sont parallélisables par leurs contrats, mais aucun guide
n'autorise à lancer d'autres agents sans mission le prévoyant. Si plusieurs
agents travaillent effectivement, attribuer des fichiers disjoints ; un seul
intégrateur écrit les contrats partagés et les fichiers racine. Relire l'état
courant avant chaque intégration, sans écraser le travail d'un autre agent.

## 4. Limites d'écriture par chantier

Les répertoires sont des **périmètres candidats**. Le contrat de tâche retient
une liste de fichiers précise ; leur mention ici n'autorise pas leur
modification collective.

| Lot | Écritures isolables | Limites / coordination nécessaire |
| --- | --- | --- |
| R-A1 / R-A2 | Note dédiée `docs/research/`, nouvelles fixtures `reproduction/fixtures/` | Lecture seule des binaires installés ; pas de modification mldr, dyld, libSystem/XNU, libgcc ou C2 sans mission de correction |
| U-A1 | Tests dédiés `tests/regressions/carbon-*/`, note datée | Production `src/frameworks/Carbon/`, interfaces publiques et Cocotron partagés ; attribution requise |
| A-A1 | Note `docs/evidence/`, nouveau banc isolé `experiments/` hors `experiments/petite-victoire/` | Préserver `src/CoreAudio/`, HAL, PulseAudio, pont ELF/IPC et acquis B11–C10 ; pas de nouveau backend implicite |
| M-A1 / M-A2 | Nouveaux tests MIDI et AU dans des sous-dossiers distincts de `tests/regressions/` | `src/frameworks/CoreMIDI/`, Component Manager et AudioUnit partagés ; contrôler ABI et durée de vie |
| Q-A1 | Témoin `tests/regressions/quicktime-*/`, média synthétique défini par source originale, note de preuve | Corrections attribuées seulement dans `src/frameworks/QuickTime/` / `QTKit/` ; aucun Player/codec propriétaire publié |
| L-A1 | Synthèse expurgée `docs/audits/logic-studio-8/` | DVD, Logic, banques et frameworks privés en lecture seule ; pas de lancement sans autorisation explicite |
| P — réservé au responsable du projet | Aucune écriture autonome dans `experiments/petite-victoire/` | Intervention uniquement sur demande explicite et ciblée du responsable du projet ; les agents travaillent sur le socle D4RLING et leurs témoins séparés |
| Intégration documentaire | `ROADMAP.md`, `AGENTS.md`, `PROJECT_STATE.md`, liens README | Un intégrateur ; actualiser les conclusions sans réécrire les anciens rapports |

Ne pas changer hors mission : CMake racine, CI, packaging, dépendances,
révisions de sous-modules, verrous de reproduction, snapshots et correctifs
historiques. Les snapshots conservent la source historique ; un correctif
nouveau reçoit sa propre provenance.

## 5. Protéger l'environnement et les travaux locaux

- Le checkout historique **`b7d0cb6a79fe196657deb9711647f8486bcc5e5e` avec
  neuf modifications locales et `parameters.c` ignoré est protégé**.
  Ne jamais y exécuter checkout/reset/clean/stash/pull, y appliquer les
  snapshots, ni modifier son build, installation ou préfixe.
- Ne pas supprimer, déplacer, écraser, « nettoyer » ou versionner les travaux
  d'autrui pour faciliter le lot. Pas de `git add .` / `git add -A` :
  sélectionner les seuls fichiers revus. Le motif historique `tests` de
  `.gitignore` peut masquer un nouveau test ; vérifier explicitement son
  inclusion, et ne forcer que la source précise après revue.
- Matérialiser les sources historiques uniquement dans une destination neuve
  avec les recettes documentées. Une récupération réseau reste soumise à
  l'autorisation de la mission ; préférer les entrées locales disponibles.
- Lancer uniquement dans installation copiée/cohérente, préfixe **neuf et
  court**, namespaces privés et timeout borné. Lire le runner avant usage.
  La présence d'une installation ne constitue pas l'autorisation de la lancer.
- Ne pas tuer de serveur historique, changer sysctl, démarrer un service
  global, installer dans `/usr/local` ou `/opt`, ni copier une dylib depuis
  un autre build pour masquer une dépendance.
- Après un essai, borner les seuls descendants/namespaces créés par le lot,
  attendre leur fin, vérifier l'absence de montage/processus résiduel et
  l'intégrité des fichiers protégés. Conserver les journaux privés.
- Aucun téléchargement/installation silencieux, SDK récupéré implicitement,
  fichier dispersé à la racine du disque ou extraction massive de DVD.
  Si une acquisition devient nécessaire hors autorisation, préciser source,
  volume, destination et raison avant de demander la décision.

## 6. Implémenter et tester le contrat utile

Avant tout correctif, lire source, tests, ABI publique, dépendances et
révisions de branches. Réutiliser les audits terminés ; rechercher la lacune
exacte au lieu de refaire un inventaire général. Respecter PulseAudio,
l'ABI CoreAudio, Carbon et CoreMIDI. Préserver auteurs/licences et enregistrer
les imports/adaptations dans CREDITS et le commit.

Pour une correction de comportement, établir un oracle indépendant :
même entrée avant/après, attendu défini, contrôle positif et négatif, panne
pertinente et régression ciblée. Ne pas coder un test qui reproduit seulement
l'implémentation. Un stub doit retourner une erreur honnête plutôt qu'un succès
sans objet ou effet demandé.

Choisir le niveau de vérification adapté :

| Niveau | Ce qu'il permet de conclure | Ce qu'il ne prouve pas |
| --- | --- | --- |
| Lecture SRC/DOC, audit de symboles | Contrat, présence de code/export ou dépendance à la révision lue | Comportement exécuté |
| Build / test hôte | Source compilable et assertions dans le banc décrit | ABI invité, vraie CF si adaptateur, application Mach-O |
| Chargement / marqueur Linux | Étape de chargement ou instructions exécutées | Appels Darwin si syscalls Linux directs |
| Témoin Darwin i386 | APIs et chemin explicitement exercés | Ensemble du framework, GUI/audio/Logic non exercés |
| PCM / écoute / application | Résultat du chemin et scénario mesurés | Toute la suite Logic, faible latence ou stabilité générale |

Pour les contrats Carbon hôte, les commandes sont dans
[le runner existant](tests/regressions/carbon-events/README.md) ; préciser
adaptateur CF, vrais en-têtes ou fixtures substituées. Si le responsable du projet délègue
explicitement un test de Petite Victoire, utiliser CMake/CTest et le test Node
déjà documentés, avec des sorties dédiées, sans installer un outil absent.
Pour Mach-O, vérifier tranches, ID, exports/réexports, conventions
d'appel, tailles/alignements, erreurs, callbacks et durées de vie.
Respecter le graphe `*_firstpass.dylib` ; un build `COMPONENTS=core`
ne qualifie pas les composants audio `gui`.

V1 i386 doit être clos sur désassemblage brut avant une conclusion H-CF.
La PR #8/C2 reste expérimentale ; aucune fusion ni nouveau V3 runtime n'est
autorisé par sa simple mention. Les lots Logic et essais propriétaires
restent des portes distinctes, comme l'indiquent leurs audits.

Pour l'audio : prouver le chemin natif ou invité réellement utilisé, format,
frames, callbacks, sortie, arrêt/reprise et erreurs. Aucune allocation,
opération disque/réseau ou verrou bloquant ajouté au callback de rendu.
Mesurer xruns, horloge, CPU/RAM et latence acoustique séparément des temps
d'acquittement. Une écoute doit être confirmée par une personne ou un
protocole de capture mesuré ; ne jamais l'inférer d'un compteur.

Une modification purement documentaire exige revue des faits, liens,
références et diff ; ne pas lancer un build intégral pour cette seule raison.

## 7. Preuves, statuts et arrêt

Une preuve livrable contient :

- date, lot, révisions/overlay, architecture, environnement et outils ;
- entrées identifiées par empreinte lorsque pertinent, sans secrets ;
- commande effectivement exécutée, attendu, résultat, retour, durée,
  marqueurs et artefacts utiles ; préciser ce qui n'a pas été exécuté ;
- contrôles négatifs, pannes, totalité des tentatives et limites ;
- état avant/après des seuls fichiers et processus concernés ;
- synthèse publique expurgée et emplacement **privé** des originaux conservés,
  sans exposer cet emplacement s'il contient des données personnelles.

Employer **PASS / FAIL / BLOCKED / À FAIRE** selon ROADMAP et qualifier
**SRC / DOC / OBS / TEST / INF / HYP / OPEN**. Une hypothèse peut guider un
test, jamais tenir lieu de résultat. Une sortie d'analyseur `INTEGRITY=PASS`
n'est pas une vérification indépendante.

Si une dépendance manque, arrêter le chemin qui en dépend, noter le premier
bloqueur reproductible et la condition exacte de reprise. Continuer un
contrat/test/note indépendant dans le périmètre autorisé. Ne pas relancer
jusqu'au succès, cacher un timeout ou appeler BLOCKED un essai ayant échoué.

Actualiser PROJECT_STATE, la commande de reproduction et les limites après
un jalon important ; ajouter une note datée et préserver le rapport antérieur.
La roadmap reçoit le résultat du seul critère prouvé, sans gonfler le statut
d'un axe entier.

## 8. Revue et publication

- Public : documentation originale, sources redistribuables, médias de test
  originaux et synthèses expurgées. **Jamais** de Logic/EXS24/QuickTime Player
  propriétaire, DVD, SDK non redistribuable, AU commercial, banque de sons,
  clé/numéro de série, préfixe, core dump, archive de récupération ou trace
  privée. Ne pas republier un élément sensible au motif qu'il existe déjà
  dans un ancien document. Examiner aussi captures et métadonnées.
- Une publication requiert l'autorisation de la mission. Pour la livraison
  de ces guides : `fr4nck/d4rling`, **`master` directement, sans créer de
  branche ni PR**. Les autres missions suivent leur destination autorisée.
  Pas de contribution amont sans décision distincte :
  [stratégie amont](docs/decisions/strategie-contributions-amont.md).
- Commits en français, portée étroite. Exemple documentaire :
  `docs: préciser les jalons QuickTime et leurs preuves [skip ci]`.
  Utiliser `[skip ci]` pour la documentation seule lorsque pertinent ;
  ne pas éviter les contrôles nécessaires à une modification de code.
- Relire le diff complet et la liste des fichiers du commit. Ne pas publier
  les changements locaux préexistants. Si le poste n'est pas un checkout
  propre, une publication documentaire via l'API GitHub peut préserver le
  poste, à partir de la tête distante relue.
- Relire `master` juste avant écriture ; utiliser une avance normale avec
  contrôle de la tête attendue. Si elle a changé, réexaminer les nouveaux
  commits et reconstruire le changement sur cette base. Aucun force-push,
  reset ou écrasement de modification concurrente.
- Après publication, relire la référence et les fichiers, comparer le contenu
  exact, confirmer les seuls chemins modifiés et fournir URLs + SHA complets.
  Un objet commit créé sans mise à jour de `master` n'est pas publié.

## 9. Compte rendu final d'un lot

Indiquer le résultat d'abord : objectif atteint ou premier bloqueur, puis
fichiers changés, preuve et commande de reproduction, ce qui reste non
qualifié, intégrité des travaux existants, et prochain lot utile.
Pour une publication, donner branche, URLs et SHA vérifiés.
Ne jamais annoncer QuickTime, JACK réel, Logic, EXS24 ou un DAW fonctionnels
sur la seule base d'un symbole, d'un build, d'un mock ou d'un autre banc.
