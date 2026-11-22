# AGENTS.md — travailler de façon autonome dans D4RLING

Ce guide s'applique au dépôt entier, sous réserve des consignes plus précises
d'un sous-dossier et de la mission explicite de l'utilisateur. Il encadre le
travail ; sa lecture ne déclenche ni expérimentation ni publication.
Objectif : livrer une amélioration bornée, prouvée et réutilisable sans
endommager les travaux existants ni annoncer une compatibilité non démontrée.

Révision : 18 novembre 2026. Les tableaux et procédures de référence sont dans
`docs/agents/` : [limites d'écriture par lot](docs/agents/limites-ecriture-par-lot.md)
et [niveaux de vérification et qualification](docs/agents/niveaux-de-verification.md).

## Essentiel (lire d'abord ; le reste du fichier est la référence)

- **Priorité courante :** voir la section suivante. Tout lot doit s'y rattacher.
- **Commandes :** un seul bloc copiable avec prévol, bilan copié au presse-papiers et code de retour préservé (règle permanente plus bas).
- **Jamais :** force-push, reset, clean, `git add -A`, toucher au checkout `b7d0cb6`, écrire dans `experiments/petite-victoire/` sans demande explicite du responsable.
- **Preuve :** PASS seulement avec une sortie observée ; distinguer résultat observé et résultat rapporté.
- **Revue :** une correction n'est intégrée qu'après relecture par quelqu'un d'autre que son auteur.
- **Arrêt :** annoncer un critère d'arrêt avant de commencer ; au premier bloqueur reproductible, s'arrêter et le documenter.
- **Publication :** `master`, avance normale, relire la tête avant et après.

## Priorité courante (à mettre à jour à chaque jalon)

**Objectif de la période :** amener Logic Studio 8 (i386) jusqu'à son prochain obstacle exécuté, puis le lever, et recommencer.

**Dernier obstacle connu :** `dyld` échoue sur `_kWSMethodInvocationResult`, demandé par DotMacKit à CoreServices, **avant le point d'entrée de Logic 8** (18 novembre 2026, banc privé sur 5700X, rapport Claude Code non rejoué sur `master`). Le chargement des 164 images i386 est atteint dans ce banc, avec une libcrypto 0.9.8 candidate et ProKit provenant du média original. Les 99 autres absences préalables et 613 ultérieures proviennent d'un diagnostic statique privé, non de 99 échecs `dyld` observés. `0x1000` est franchi dans un banc temporairement privilégié, pas par un correctif général rootless.

**Limite de provenance :** les erreurs `dyld` observées à l'exécution peuvent guider un diagnostic ; les tableaux tirés des imports de frameworks Apple, les binaires Logic/ProKit/DotMacKit et leur analyse interne restent privés. Pour l'amont, privilégier contrats publics, sources licites et tests autonomes. Ne pas fabriquer les valeurs prétendument observées de constantes. Tout quirk de sécurité/crypto doit obtenir l'accord explicite d'un mainteneur. Ne pas détourner l'activation ou une protection.

**Boucle de travail :** lancer → classer le premier obstacle exécuté → corriger le plus petit élément qui le lève → relancer. Ne pas qualifier un sous-système que Logic n'appelle pas encore.

**Autorisation de lancer Logic ou son témoin d'import :** **ACCORDÉE LE 18 NOVEMBRE 2026 POUR LA MISSION PRIVÉE CIBLÉE SUR LE 5700X**, visant le franchissement isolé de `0x1000`, puis la qualification de `libcrypto` et une nouvelle tentative de Logic seulement si elle passe. Périmètre : installation historique inchangée, banc et préfixe isolés, espaces de noms privés, temps d'exécution borné, retrait des privilèges comme dans le banc qualifié, aucun réglage global, installation système ou téléchargement sans accord, aucun processus/montage d'autrui perturbé. **Cette autorisation ne vaut pas permission générale pour tout agent, poste, préfixe ou lot futur.** Toute nouvelle exécution hors de la mission autorisée suit le contrat L-A1 et le §4 et demande un périmètre explicite.

**Règle de sélection des lots**, dans cet ordre :
1. le lot qui lève le premier obstacle exécuté de Logic ;
2. à défaut, un prérequis direct de cet obstacle (dépendance ELF32, symbole, API appelée) ;
3. à défaut, la maintenance (synchronisation amont, durcissement des tests), à raison d'un lot sur trois au plus ;
4. tout autre lot (nouvel audit, témoin synthétique, inventaire) exige une phrase de justification : quel obstacle de la priorité courante il débloque. Sans elle, ne pas le faire.

**Arrêt :** trois tentatives consécutives qui ne changent pas le premier obstacle déclenchent un arrêt et une demande d'arbitrage, pas une quatrième variante.

## Pérennité des bancs et preuves — AGT-015 (22 novembre 2026)

**Règle transversale immédiate :** appliquer l'[AGT-015 de PMSL-Arch](https://github.com/fr4nck/PMSL-Arch/blob/main/docs/GOUVERNANCE_AGENTS_OBJECTIFS.md) à tout développement D4rling. Un jalon qualifié doit rester reproductible après coupure de courant, redémarrage WSL ou fin de session. `/tmp`, `tmpfs` et les espaces de travail temporaires ne servent qu'à des ressources jetables.

- Avant de déclarer un jalon durable, vérifier que recettes, versions, binaires qualifiés non trivialement reproductibles, entrées autorisées et preuves nécessaires à sa reprise sont dans des **emplacements Linux persistants déjà autorisés**, avec empreintes et provenance. Les éléments reconstruisibles de façon démontrée peuvent n'exiger qu'une recette et des entrées durables.
- Conserver la chaîne source → build → installation → banc et les chemins réels de reprise ; tester sans dépendre de l'ancien `/tmp` par un contrôle ciblé **non destructif**. Consigner `REPRISE=PASS` ou `REPRISE=BLOCKED` avec sa cause, distinct du résultat des tests fonctionnels.
- Réutiliser `validation/` et `historique/` selon les propriétaires de lot ; ne pas dupliquer ni déplacer automatiquement les installations ou preuves existantes. Aucun `rm /tmp`, redémarrage imposé, copie de média propriétaire dans Git, écriture Windows ou acquisition implicite.

**Motif :** le banc Logic du 18 novembre a perdu des composants indispensables après redémarrage WSL. Sa remise en état exige un lot autorisé et la vérification de sa durabilité avant clôture. Voir `PROJECT_STATE.md`.

## Remise des commandes — règle permanente, indépendante de l'appareil

**Consigne explicite et permanente du responsable (16 novembre 2026) :** ces préférences s'appliquent quel que soit l'appareil utilisé. Ne pas les conditionner à un téléphone, à un contexte mobile ou à un changement d'appareil ; ne pas présumer l'appareil courant. Adapter les commandes au shell et à la machine cible réellement identifiés.

- **Commandes intégrales dans le chat :** fournir toute commande Bash/Shell (dont `sh`) ou PowerShell dans **un bloc unique, autonome et directement copiable**, avec prévol, chemins, limites d'écriture, accès réseau, protections, exécution et bilan. Aucune retouche ni composition manuelle ne doit être exigée.
- **Jamais de scripts à télécharger, sauf demande explicite :** ne fournir ni fichier `.sh`/`.ps1`, ni archive, pièce jointe ou lien de téléchargement/sandbox pour remettre un script à l'utilisateur sans cette demande.
- **Copie automatique pour CHAQUE commande ou script Bash/Shell :** incorporer dans le même bloc la collecte du bilan/journal utile et sa copie dans le presse-papiers **à la fin de l'exécution, y compris en cas d'échec**, sans demander une seconde commande ni une étape manuelle supplémentaire. Le résultat doit être prêt à coller dans la conversation.
- **Finalisation et code de retour :** installer la finalisation avant les prévols et opérations susceptibles d'échouer (`trap EXIT` en Bash, mécanisme équivalent compatible avec le shell employé). Capturer immédiatement le véritable code de retour de l'exécution, joindre au bilan le diagnostic et ce code, puis préserver ce même code après journalisation, copie et nettoyage. Une erreur du presse-papiers ne doit ni masquer l'échec initial ni transformer une exécution réussie en échec.
- **Presse-papiers disponible :** privilégier `clip.exe` sous WSL2, `pbcopy` sous macOS, puis `wl-copy` ou `xclip` sous Linux selon les outils et la session disponibles. Vérifier la disponibilité et le succès réel de la copie ; ne pas installer d'outil implicitement.
- **Protection des secrets :** ne collecter que les informations utiles et non sensibles ; expurger avant affichage, enregistrement ou copie les mots de passe, jetons, clés, données personnelles et chemins sensibles. Ne pas activer de trace de commandes ni copier un inventaire brut de l'environnement susceptible de révéler des secrets.
- **Rapport préservé si la copie est impossible :** afficher un avertissement explicite, garder le bilan expurgé lisible dans le terminal et conserver tout rapport déjà enregistré dans son emplacement autorisé à accès restreint, sans le supprimer ni l'écraser lors du nettoyage. L'absence ou l'échec du presse-papiers ne doit jamais faire perdre le rapport ni altérer le code de retour initial.
- **Un bloc collé n'est pas une preuve d'exécution.** Seule une sortie de terminal, un rapport ou l'action effective d'un outil permet d'affirmer qu'une commande a été exécutée ou qu'un résultat est observé.
- Ne pas confondre l'appareil de conversation et la machine cible (5700X/WSL2, 10400, etc.), ni présumer un accès à celle-ci. Si l'agent ne peut pas y exécuter les commandes, le dire et remettre le bloc directement exploitable.
- Cette règle concerne **la forme de livraison à l'utilisateur** ; les agents peuvent créer leurs propres fichiers de travail uniquement dans les emplacements et limites autorisés par leur mission.

Voir aussi la consigne transversale du dépôt `PMSL-Arch/AGENTS.md`.

## Gouvernance transversale — PMSL-ARCH

La **source de règles transversales de développement** est le dépôt privé
[`fr4nck/PMSL-Arch`](https://github.com/fr4nck/PMSL-Arch), branche `main` :
[`AGENTS.md`](https://github.com/fr4nck/PMSL-Arch/blob/main/AGENTS.md) et
[`docs/GOUVERNANCE_AGENTS_OBJECTIFS.md`](https://github.com/fr4nck/PMSL-Arch/blob/main/docs/GOUVERNANCE_AGENTS_OBJECTIFS.md).
Avant tout chantier technique significatif, l'agent ayant accès à ce dépôt
consulte ces deux textes, en particulier **AGT-001 à AGT-014**, puis ce guide
local et les instructions du sous-système. L'accès au dépôt privé n'est pas
présumé pour un contributeur extérieur : ne jamais prétendre avoir consulté
une règle inaccessible ; appliquer au minimum les garde-fous de ce guide et
signaler toute règle non vérifiable dont dépend l'autorisation ou la sûreté
d'une opération. En cas de conflit ou d'incertitude bloquante, **arrêter
l'opération concernée et demander un arbitrage**, sans contournement tacite.

**Contrat obligatoire avant création, développement, script ou délégation
à un agent :**

1. Identifier le **dépôt canonique**, l'état réel de `master`, les éventuels changements locaux, la source de vérité et les solutions déjà disponibles.
2. Réutiliser sources, builds, tests, dépendances et outils existants avant de créer une copie, un mécanisme ou un environnement parallèle ; justifier explicitement toute exception.
3. Conserver **une seule branche de développement : `master`**, un checkout canonique et un build/une installation de référence, avec traçabilité source → build → préfixe → essais. Les anciennes copies restent protégées jusqu'à décision explicite de migration ou de suppression.
4. Pour le travail pérenne sur le 5700X, viser **au plus trois zones permanentes** sous `$D4RL_HOME/d4wrling-work` : `canon/` (sources, build, installation), `validation/` (tests et sorties bornées) et `historique/` (preuves protégées). **C'est une cible d'organisation, pas une autorisation de créer ces dossiers, déplacer les copies actuelles ni nettoyer l'existant.** Les essais temporaires ont un propriétaire, une limite et une politique de conservation.
5. Avant toute commande à effet, annoncer le **shell**, les chemins lus et écrits, le volume, les accès réseau, les changements Git et les risques. Aucune installation, copie volumineuse, écriture sur volume Windows ni téléchargement implicite. Un clone partiel peut déclencher un *lazy fetch* même en lecture ; le prévenir explicitement.
6. Aucune suppression, aucun déplacement, écrasement, force-push, reset destructif ou réécriture d'historique sans autorisation spécifique. Préserver `experiments/petite-victoire/`, ses preuves et les installations historiques.
7. Une correction n'est **intégrée** que si elle est testée au niveau pertinent, **relue par une personne ou un agent différent de son auteur**, et présente dans `master`. Un PASS synthétique, un commit publié et une recette réelle sont trois états distincts. Porter les corrections qualifiées par petits changements traçables, sans assembler arbitrairement des binaires issus de builds différents. (Détail de la relecture au §7.)
8. Définir le livrable demandé **maintenant**, la preuve attendue, les tests négatifs, un budget de travail et un **critère d'arrêt**. Ne pas étendre « go » à des chantiers implicites.
9. Les prompts destinés à un autre agent et les scripts livrés à l'utilisateur doivent être **complets et collables en une seule fois**, avec prévol du dépôt réel, bon répertoire, protections, lancement et bilan ; aucune retouche manuelle exigée.
10. Avant diagnostic ou correctif non trivial, lire **documentation officielle et code/version réels** (AGT-014). Si une précondition manque, signaler le blocage plutôt que multiplier des essais ou fabriquer des prérequis.

La mémoire conversationnelle ne remplace **jamais** ce prévol documentaire.
Les règles spécifiques D4rling ci-après renforcent ce contrat ; elles ne
l'annulent pas.

## Petite Victoire — développement réservé au responsable du projet

**Le responsable du projet garde la main sur le développement et les choix de
produit de Petite Victoire**, y compris son nom et son évolution éventuelle
vers un DAW. Les agents ne choisissent pas spontanément un lot de ce projet et
n'écrivent pas dans `experiments/petite-victoire/` (code, tests, interface,
ressources, documentation du produit, versions ou archives).

Une intervention exige une **demande explicite et ciblée du responsable du
projet**. Une mission générale de développement autonome de D4RLING ne délègue
pas Petite Victoire. La lecture et le signalement de blocages restent possibles
dans le périmètre de la mission ; proposer une évolution ne vaut pas
autorisation de l'implémenter.

Petite Victoire doit devenir le démonstrateur musical de référence pour
vérifier les fonctions de D4RLING **sans posséder Logic Studio 8**. Les agents
peuvent préparer et qualifier le socle D4RLING avec leurs propres témoins, puis
documenter les contrats utilisables par le responsable. La validation par
Petite Victoire porte sur les chemins réellement exercés et identifiés : mode
natif et mode invité i386 sont distingués, ainsi que les fonctions encore
absentes ou non testées. Les jalons Logic/EXS24 et QuickTime gardent leurs
preuves applicatives propres.

## 1. Lire avant d'agir

Lire dans cet ordre : [PROJECT_STATE.md](PROJECT_STATE.md) ;
[reproduction/README.md](reproduction/README.md) et
[reproduction/refs.lock.json](reproduction/refs.lock.json) ;
[ROADMAP.md](ROADMAP.md) ; le README et les rapports datés du sous-système
choisi ; [CREDITS.md](CREDITS.md) avant toute réutilisation de code.

Confronter les dates **et les révisions** : `master`, branches de travail,
snapshot historique et installation testée sont des états différents. Ne pas
transformer une vieille note « stub » en diagnostic actuel sans relire le code ;
ne pas transformer une nouvelle observation en qualification de tous les
anciens chemins. Les recettes publiques indiquent le shell et la distribution
attendus : ne pas exécuter une commande Bash comme une commande PowerShell.

Références de convergence : [audio B14/C10](docs/REPRISE-AUDIO-MUSIQUE-2026-11-08.md),
[dyld/ABI V0–V2](docs/research/i386-dyld-abi-audit-2026-11.md),
[exigences Logic](docs/decisions/logic8-exigences-audio-et-chantiers-2026-11-08.md),
[Petite Victoire v0.1](experiments/petite-victoire/v0.1/README.md).

## 2. Prévol sans mutation

- Identifier dépôt, branche, HEAD, statut, index, diff et sous-modules par des lectures bornées. Chercher d'abord avec `rg` / `rg --files`. Ne pas publier les sorties brutes si elles révèlent des données locales. Une copie sans `.git` est une copie de documents, pas un checkout : ne pas y inventer un état Git.
- Noter les fichiers modifiés/ignorés et leurs propriétaires de travail ; préserver tout changement préexistant. Si la cible est déjà modifiée, lire le diff et choisir des fichiers neufs ou signaler le conflit ; ne pas écraser ni intégrer ce diff par défaut.
- Déterminer l'environnement réel : Linux/WSL2, architectures ELF/Mach-O, outils présents, display, bibliothèques et route audio si nécessaires. Ne pas confondre le PC WSLg testé et un MacBook sous Linux.
- Choisir un espace de travail unique sous le dossier de projet autorisé, avec build, exports et rapports dédiés ; estimer volume et parallélisme. Ne pas dupliquer automatiquement des builds ou archives volumineux.
- Aucun `fetch`, clone, récupération de sous-module ou paquet caché dans un prévol. Un clone partiel/promisor peut télécharger même pendant une lecture Git : vérifier la disponibilité locale, désactiver la récupération automatique selon l'outil, ou utiliser l'API GitHub pour les lectures distantes annoncées par la mission. Signaler un objet absent.

## 3. Choisir et borner un lot

Appliquer la **règle de sélection** de la « Priorité courante ». Prendre un seul
identifiant de [ROADMAP.md](ROADMAP.md) (R-A1, A-A1, Q-A1, M-A1…), annoncer
objectif, preuves et fichiers avant de modifier. Une mission documentaire
reste documentaire.

Fixer un contrat de tâche court :

```text
Lot / objectif observable :
Obstacle de la priorité courante que ce lot lève :
Base : dépôt, branche, SHA, overlay éventuel, sous-modules concernés
Entrées disponibles / manquantes :
Écritures autorisées : liste exacte de fichiers et répertoire de sortie
Hors périmètre / fichiers partagés réservés :
Critère PASS : résultat attendu et méthode de mesure
Contrôles négatifs / erreurs / régressions :
Condition BLOCKED et tâche indépendante de repli :
Critère d'arrêt (budget, nombre de tentatives) :
Livraison : sources, preuve expurgée, commande de reproduction, limites
Publication autorisée : destination et mode explicitement demandés
```

L'autorisation explicite de la mission suffit pour ses actions nécessaires ; ne
pas redemander la même permission. Si une entrée ou une autorisation nouvelle
manque, avancer sur les parties indépendantes et poser une seule question
précise. **Ne pas élargir silencieusement le périmètre.**

Si plusieurs agents travaillent effectivement, attribuer des fichiers
disjoints ; un seul intégrateur écrit les contrats partagés et les fichiers
racine. Aucun guide n'autorise à lancer d'autres agents sans mission le
prévoyant. Les répertoires candidats par chantier sont dans
[limites d'écriture par lot](docs/agents/limites-ecriture-par-lot.md) : leur
mention n'autorise pas leur modification collective.

## 4. Protéger l'environnement et les travaux locaux

- Le checkout historique **`b7d0cb6a79fe196657deb9711647f8486bcc5e5e` avec neuf modifications locales et `parameters.c` ignoré est protégé.** Ne jamais y exécuter checkout/reset/clean/stash/pull, y appliquer les snapshots, ni modifier son build, installation ou préfixe.
- Ne pas supprimer, déplacer, écraser, « nettoyer » ou versionner les travaux d'autrui. Pas de `git add .` / `git add -A` : sélectionner les seuls fichiers revus. Le motif historique `tests` de `.gitignore` peut masquer un nouveau test ; vérifier explicitement son inclusion et ne forcer que la source précise après revue.
- Matérialiser les sources historiques uniquement dans une destination neuve avec les recettes documentées ; préférer les entrées locales disponibles.
- Lancer uniquement dans une installation copiée/cohérente, un préfixe **neuf et court**, des namespaces privés et un timeout borné. Lire le runner avant usage. **La présence d'une installation ne constitue pas l'autorisation de la lancer** ; le lancement de Logic suit l'autorisation de la « Priorité courante ».
- Ne pas tuer de serveur historique, changer sysctl, démarrer un service global, installer dans `/usr/local` ou `/opt`, ni copier une dylib depuis un autre build pour masquer une dépendance.
- Après un essai, borner les seuls descendants/namespaces créés par le lot, attendre leur fin, vérifier l'absence de montage/processus résiduel et l'intégrité des fichiers protégés. Conserver les journaux privés.
- Aucun téléchargement/installation silencieux, SDK récupéré implicitement, fichier dispersé à la racine du disque ou extraction massive de DVD. Si une acquisition devient nécessaire, préciser source, volume, destination et raison avant de demander la décision.
- Ne pas changer hors mission : CMake racine, CI, packaging, dépendances, révisions de sous-modules, verrous de reproduction, snapshots et correctifs historiques.

## 5. Implémenter et tester le contrat utile

Avant tout correctif, lire source, tests, ABI publique, dépendances et
révisions de branches. Réutiliser les audits terminés ; chercher la lacune
exacte au lieu de refaire un inventaire général. Respecter PulseAudio, l'ABI
CoreAudio, Carbon et CoreMIDI. Préserver auteurs/licences et enregistrer les
imports/adaptations dans CREDITS et le commit.

- **Oracle indépendant :** même entrée avant/après, attendu défini, contrôle positif et négatif, panne pertinente, régression ciblée. Ne pas coder un test qui reproduit seulement l'implémentation.
- **Stub honnête :** un stub retourne une erreur plutôt qu'un succès sans objet ou effet demandé.
- **Niveau de preuve adapté :** lecture de source, test hôte, chargement Linux, témoin Darwin i386 et application ne prouvent pas la même chose ; voir le [tableau des niveaux](docs/agents/niveaux-de-verification.md), qui détaille aussi les contrôles Carbon, Mach-O, GUI et la frontière hôte/invité.
- **Audio :** prouver le chemin natif ou invité réellement utilisé ; aucune allocation, opération disque/réseau ou verrou bloquant dans le callback de rendu ; une écoute est confirmée par une personne ou une capture mesurée, jamais inférée d'un compteur.
- **Application :** classer le **premier obstacle exécuté** avant les lacunes secondaires ; les tables Mach-O seules ne démontrent ni chargement ni fonctionnement. Réutiliser l'audit existant avant tout nouveau scan. **Ne jamais désassembler de code Apple.** Pour Logic, rester au niveau du comportement observé (symbole absent, plantage, erreur) : c'est ce niveau de preuve que l'amont accepte.
- Une modification purement documentaire exige revue des faits, liens, références et diff ; pas de build intégral pour cette seule raison.

## 6. Preuves, statuts et arrêt

Une preuve livrable contient :

- date, lot, révisions/overlay, architecture, environnement et outils ;
- entrées identifiées par empreinte lorsque pertinent, sans secrets ;
- commande effectivement exécutée, attendu, résultat, retour, durée, marqueurs et artefacts utiles ; préciser ce qui n'a pas été exécuté ;
- contrôles négatifs, pannes, totalité des tentatives et limites ;
- état avant/après des seuls fichiers et processus concernés ;
- synthèse publique expurgée et emplacement **privé** des originaux conservés, sans exposer cet emplacement s'il contient des données personnelles.

Employer **PASS / FAIL / BLOCKED / À FAIRE** selon ROADMAP et qualifier
**SRC / DOC / OBS / TEST / INF / HYP / OPEN**. Une hypothèse peut guider un
test, jamais tenir lieu de résultat. Une sortie d'analyseur `INTEGRITY=PASS`
n'est pas une vérification indépendante.

Distinguer à chaque checkpoint les faits **observés directement** par l'agent
et les résultats **rapportés** depuis un autre poste ou une autre
conversation ; ne jamais présenter ces derniers comme rejoués.

Si une dépendance manque, arrêter le chemin qui en dépend, noter le premier
bloqueur reproductible et la condition exacte de reprise, puis continuer un
contrat/test/note indépendant. Ne pas relancer jusqu'au succès, cacher un
timeout ou appeler BLOCKED un essai ayant échoué. Appliquer la règle d'arrêt
(trois tentatives sans changement du premier obstacle).

Actualiser PROJECT_STATE, la commande de reproduction et les limites après un
jalon important ; ajouter une note datée et préserver le rapport antérieur. La
roadmap reçoit le résultat du seul critère prouvé, sans gonfler le statut d'un
axe entier.

## 7. Publication, coordination et revue

`master` est le **point de synchronisation commun** entre conversations,
agents locaux et contributions : une conversation, un rapport oral ou une
session terminale ne remplace pas les commits et documents publiés.

**Avant chaque lot, reprise ou changement de chantier :**
1. Lire le SHA courant de `master` **et les derniers commits** ; examiner les diffs qui touchent les fichiers, contrats, dépendances ou preuves du lot ; comparer avec le SHA de départ.
2. Lire le checkpoint publié le plus récent du périmètre, puis l'état du checkout local, les modifications non commitées et les artefacts non publiés. Ne pas refaire un lot déjà qualifié ni ignorer un travail plus récent.
3. Si deux travaux risquent d'écrire les mêmes fichiers, coordonner la propriété avant modification ; réserver les fichiers partagés à un seul intégrateur.

**Contenu public :** documentation originale, sources redistribuables, médias
de test originaux et synthèses expurgées. **Jamais** de Logic/EXS24/QuickTime
Player propriétaire, DVD, SDK non redistribuable, AU commercial, banque de
sons, clé/numéro de série, préfixe, core dump, archive de récupération ou
trace privée ; examiner aussi captures et métadonnées. Ne pas republier un
élément sensible au motif qu'il existe déjà dans un ancien document.

**Commits :** en français, portée étroite, un commit séparé par évolution
**achevée et vérifiée**. Exemple documentaire :
`docs: préciser les jalons QuickTime et leurs preuves [skip ci]`. Utiliser
`[skip ci]` pour la documentation seule, jamais pour éviter les contrôles d'une
modification de code. Si un candidat ou un résultat n'est pas qualifié ou pas
accessible depuis GitHub, publier **uniquement un checkpoint documentaire
honnête** (révision, provenance, rapporté vs vérifié, limites, statut, prochaine
action exacte) ; ne pas publier du code non qualifié sous prétexte de le
sauvegarder.

**Revue :** toute modification de production (`src/`, tests, CMake, CI) est
relue sur son diff exact par une personne ou un agent **différent de son
auteur**. Le message de commit porte `Revue: <qui>, <date>, <verdict>` (accepté,
accepté avec réserves, refusé). Un auteur ne relit pas son propre diff.
Exception : la documentation seule et les checkpoints documentaires.

**Publication :** requiert l'autorisation de la mission. Pour la livraison de ce
guide et de la documentation : `fr4nck/d4rling`, **`master` directement, sans
branche ni PR**. Relire `master` juste avant écriture ; avance normale avec
contrôle de la tête attendue. Si elle a changé, réexaminer les nouveaux commits
et reconstruire le changement sur cette base. Aucun force-push, reset ou
écrasement d'un travail concurrent. Relire le diff complet et la liste des
fichiers ; ne pas publier les changements locaux préexistants (si le poste
n'est pas un checkout propre, une publication documentaire via l'API GitHub
préserve le poste). Après publication : relire la référence et les fichiers,
comparer le contenu exact, confirmer les seuls chemins modifiés, fournir URLs
et SHA complets. Un objet commit sans mise à jour de `master` n'est pas publié.

Ces contrôles se font **à chaque session et à chaque publication** ; ils ne
constituent pas une surveillance continue en arrière-plan.

## 8. Amont Darling et dette de synchronisation

L'amont `darlinghq/darling` publie son propre `AGENTS.md`, conservé sans
modification dans [docs/upstream/darlinghq-AGENTS.md](docs/upstream/darlinghq-AGENTS.md)
(texte de l'amont au commit `91d6dacd`, 14 novembre 2026). Il permet
d'inspecter, **pour diagnostic seulement**, le code propre d'une application
tierce non Apple (SoundHack par exemple) ; Logic Studio et tout framework Apple
embarqué restent exclus, et rien de ce code ne peut être reproduit dans
Darling. Il ne remplace pas ce guide pour le travail dans D4rling, mais
s'applique intégralement à toute proposition destinée à l'amont (contrat public,
couches macOS, preuves admissibles, balises `QUIRK:`, aucune information issue
du désassemblage de binaires Apple), avec la
[stratégie amont](docs/decisions/strategie-contributions-amont.md). Pas de
contribution amont sans décision distincte.

- **Symboles privés :** ne pas ajouter un symbole privé ou non documenté à la surface publique du simple fait qu'une application l'importe ; seulement si le comportement d'une couche publique l'exige, s'il est général, et avec l'accord d'un mainteneur (amont §7).

**Dette de synchronisation.** À chaque jalon, relever le retard de `master` sur
`darlinghq/darling` (en commits) et lister les conflits prévisibles avec les
travaux en cours (exemple connu : cibles d'événements Carbon, amont `e808ce94`).
**Seuil : 300 commits** *(valeur proposée, à valider par le responsable ; jusque-là
indicative)*. Au-delà, ou si un lot touche un fichier déjà modifié par l'amont,
un lot de synchronisation passe avant tout nouveau lot sur ce périmètre. Les
correctifs qualifiés de petite portée sont proposés à l'amont, en priorité ceux
qui réduisent les conflits à venir.

## 9. Compte rendu final d'un lot

Indiquer le résultat d'abord : objectif atteint ou premier bloqueur, puis
fichiers changés, preuve et commande de reproduction, ce qui reste non
qualifié, intégrité des travaux existants, et prochain lot utile. Pour une
publication, donner branche, URLs et SHA vérifiés. Ne jamais annoncer
QuickTime, JACK réel, Logic, EXS24 ou un DAW fonctionnels sur la seule base
d'un symbole, d'un build, d'un mock ou d'un autre banc.
