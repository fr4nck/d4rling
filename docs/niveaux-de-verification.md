# Niveaux de vérification et méthodes de qualification

Annexe de [AGENTS.md](../../AGENTS.md) (§5). Ces méthodes s'appliquent
**lorsque le lot les exige** ; elles ne créent aucun chantier, outil ou
prérequis obligatoire supplémentaire.

## Niveaux de preuve

| Niveau | Ce qu'il permet de conclure | Ce qu'il ne prouve pas |
| --- | --- | --- |
| Lecture SRC/DOC, audit de symboles | Contrat, présence de code/export ou dépendance à la révision lue | Comportement exécuté |
| Build / test hôte | Source compilable et assertions dans le banc décrit | ABI invité, vraie CF si adaptateur, application Mach-O |
| Chargement / marqueur Linux | Étape de chargement ou instructions exécutées | Appels Darwin si syscalls Linux directs |
| Témoin Darwin i386 | APIs et chemin explicitement exercés | Ensemble du framework, GUI/audio/Logic non exercés |
| PCM / écoute / application | Résultat du chemin et scénario mesurés | Toute la suite Logic, faible latence ou stabilité générale |

## Carbon, Mach-O et build

- Pour les contrats Carbon hôte, les commandes sont dans [le runner existant](../../tests/regressions/carbon-events/README.md) ; préciser adaptateur CF, vrais en-têtes ou fixtures substituées.
- Pour Mach-O, vérifier tranches, ID, exports/réexports, conventions d'appel, tailles/alignements, erreurs, callbacks et durées de vie.
- Respecter le graphe `*_firstpass.dylib` ; un build `COMPONENTS=core` ne qualifie pas les composants audio `gui`.
- V1 i386 doit être clos sur désassemblage brut avant une conclusion H-CF (il s'agit des bibliothèques du build D4RLING, jamais de code Apple). La PR #8/C2 reste expérimentale ; aucune fusion ni nouveau V3 runtime n'est autorisé par sa simple mention.
- Si le responsable délègue explicitement un test de Petite Victoire, utiliser CMake/CTest et le test Node déjà documentés, avec des sorties dédiées, sans installer un outil absent.

## Audio

Prouver le chemin natif ou invité réellement utilisé, format, frames,
callbacks, sortie, arrêt/reprise et erreurs. Aucune allocation, opération
disque/réseau ou verrou bloquant ajouté au callback de rendu. Mesurer xruns,
horloge, CPU/RAM et latence acoustique séparément des temps d'acquittement.
Une écoute doit être confirmée par une personne ou un protocole de capture
mesuré ; ne jamais l'inférer d'un compteur.

## GUI X11/Wayland

- Utiliser un serveur d'affichage et un gestionnaire de fenêtres **isolés du bureau et des autres bancs** (Xvfb pour X11, compositeur headless pour Wayland, seulement s'ils sont déjà disponibles).
- Vérifier le backend effectivement sélectionné : un repli Wayland vers X11 ne vaut jamais PASS Wayland.
- Contrôler fenêtres, focus, dimensions, rendu et événements par des observations/API vérifiables ; toute injection clavier/souris exige son oracle côté application.
- Rejouer les régressions X11 après une modification d'une couche graphique partagée.

## Frontière hôte/invité

Distinguer chemins Mach-O vus via `/Volumes/SystemRoot`, chemins natifs Linux
utilisés par les bibliothèques ELF chargées par `wrap_elf`, sockets et
variables effectivement transmises au processus invité. Une écriture de
l'hôte dans un préfixe overlay actif n'est pas présumée visible dans l'invité.
Rediriger les journaux du shell invité vers un fichier, fermer son entrée
standard, borner les attentes et ne terminer que les processus/namespaces
appartenant au lot.

## Triage d'une application

Partir de l'architecture réellement visée (i386 pour Logic 8), distinguer
imports forts/faibles, réexports, bibliothèques chargées dès le démarrage ou
seulement par des plugins, symboles absents et comportements d'API
défaillants. Classer le **premier obstacle exécuté** avant les lacunes
secondaires ; les tables Mach-O seules ne démontrent ni chargement, ni
fonctionnement. Réutiliser l'audit existant avant tout nouveau scan et ne
jamais désassembler de code Apple.

Référence comparative : [méthodes Darling de test invité et de diagnostic
applicatif](https://github.com/darlinghq/darling-skills) (14 novembre 2026).
Aucun script, installation partagée, relance globale ni dépendance de ce dépôt
n'est adopté par la présente annexe.
