# D4RLING — état de référence pour reprendre le projet

Dernière consolidation : **29 octobre 2026**. Lire ce fichier avant de
proposer une suite de développement, y compris depuis mobile.

## Entrée unique

[Reproduire sur un autre poste](reproduction/README.md) donne les dépendances,
versions observées, références Git, sous-modules, correctif historique local,
test ignoré par Git, sondes sources et commandes exécutables.
[Historique JACK BH–CE](docs/d4rling-reprise-2026-10-29.md) conserve les détails
de ces campagnes. Ces documents décrivent des niveaux de preuve différents.

Le projet vise progressivement Logic Studio 8 / QuickTime 7 et le transport
CoreAudio/MIDI. **Aucune application complète ni chaîne audio réelle n'est
qualifiée.** Cela ne retire pas les preuves positives Carbon i386 ci-dessous.

## Ce qui est effectivement acquis

| Domaine | Résultat observé | Limite exacte |
| --- | --- | --- |
| Mach-O x86_64 | BK : sortie d'usage réelle de bitcode_strip, code 1 | Pas une application complète |
| ELF32 Linux | BM : 20/20 exécutions | Pas des appels Darwin |
| Chargement i386 diagnostique | BM et BN-R2 atteignent AY_AFTER_LOAD32 | Interception avant l'entrée |
| CB | 12 essais, 10 PASS / 2 INFO ; codes et marqueurs différentiels | Les payloads injectés utilisent les syscalls Linux i386 |
| Carbon dynamique i386, QT-1921/1980 | @loader_path fonctionnel, NORMAL/BYPASS, contrôle négatif sans dylib, **8/8 essais concurrents** | @rpath échoue ; bibliothèque de qualification séparée, pas tout Carbon/HIToolbox |
| Répétabilité Carbon, QT-1993 | TTY : 0/2 ; stdin=/dev/null : 2/2 | L'entrée standard influe sur le banc ; cause précise à isoler |
| QT-1994 | NORMAL et BYPASS : **2/2**, code 0 et marqueur | Conditions de lancement contrôlées |
| PR6H | Même invité Carbon avec mldr64/mldr32 corrigés : **2/2** | Ne prouve pas la correction des erreurs RPC -111 |
| PR6L-R2 et PR6N | Ancien bitmap échoue, corrigé passe ASan/UBSan ; 120 000 opérations pour le runner Python publié | Pas d'injection d'échec realloc ni preuve de toutes les RPC |
| CE | 100 observations sur 4 essais, 19 PASS / 81 INFO ; marqueur CB code 93 | Les dynamiques originaux expirent ; boucle EB FE présente ; dyld complet non qualifié |
| Audits QT-2161/2210, QT-2211/2410 et QT-2411/2710-reprise | Rapports statiques complets relus : 50, 200 et 300 observations | Ne pas les annoncer comme exécutions QuickTime |

**Correction d'un ancien bilan :** les rapports locaux QT-2211/2410 et
QT-2411/2710-reprise existent et sont complets comme audits statiques.
Les essais initiaux interrompus restent distincts. Leurs centaines
d'observations ne sont pas des tests runtime réussis.

La preuve Carbon dynamique est plus forte que le seul témoin CB : elle
appelle les fonctions événement/paramètres puis write via l'environnement
Darling. Elle ne qualifie toutefois ni tous les appels Darwin ni l'intégralité
de dyld. Ne pas revenir à « aucun code i386 exécuté » ; ne pas annoncer
« runtime Darwin entièrement opérationnel ».

## État du code et des sources

Le checkout qui a produit les essais historiques est **b7d0cb6 + neuf
modifications locales**, avec `parameters.c` ignoré par Git.
Il diffère du master et de la branche Carbon plus récente.
Le patch et le test sont maintenant sauvegardés dans
[reproduction/patches](reproduction/patches/carbon-local.patch) et
[reproduction/snapshots](reproduction/snapshots/parameters.c).
Ils sont applicables à la base historique dans une **nouvelle copie**.

Ces snapshots conservent leurs anciens commentaires « proposed/not executed » :
ces commentaires sont historiques. Les nouveaux constats de validation doivent
être datés séparément. Ils ne sont pas intégrés automatiquement aux fichiers
de production du master.

Les [références épinglées](reproduction/refs.lock.json) identifient aussi
les travaux Carbon, CoreAudio/CoreMIDI, générateur i386 et bitmap RPC.
Le manifeste relève **160 sous-modules initialisés récursivement**.
Une branche portant un correctif ne signifie pas que celui-ci est fusionné.

## Blocages et décisions actuelles

- **BN063 :** structure Mach-O32 annonçant CPU x86_64, abort `-6`.
  Les 19 troncatures AY acceptées ne prouvent pas une validation de sécurité.
- **dyld / banc dynamique :** `E8 ... EB FE` contient une boucle volontaire.
  Les mappings et l'état running ne donnent pas EIP. Les erreurs RPC
  observées à la limite du timeout peuvent être secondaires.
- **Chargement des dylibs :** préserver le témoin `@loader_path` qui fonctionne
  et son contrôle négatif ; comparer `@rpath` sur ce même contrat.
- **CoreAudio :** une configuration `COMPONENTS=core` n'inclut pas le chantier
  audio gui. La bibliothèque PulseAudio observée est ELF64. Un processus i386
  ne peut pas l'appeler directement comme bibliothèque ELF32.
- **Architecture audio :** conserver PulseAudio et l'ABI HAL ; examiner d'abord
  le pont ELF existant. Un service Linux64 par IPC est une option à qualifier,
  pas un backend déjà livré. Les IPC Linux32/64 ne prouvent pas l'IPC invité Darwin.
- **JACK :** ni bibliothèques/outils JACK ni route audio réelle qualifiés sur
  l'environnement relevé. Claude Code et Ruby ne sont pas des dépendances
  obligatoires du projet ; aucune installation Claude n'est démontrée.
- **QuickTime/QTKit :** les audits trouvent environ 4 600 symboles de stubs
  explicites QuickTime ; des sources et références ne constituent pas un
  lecteur multimédia. Player 7 et plusieurs frameworks sont absents aux
  emplacements examinés. Aucun import set réel du Player n'a été fourni.
- **Build :** respecter les dépendances circulaires `*_firstpass.dylib`,
  les slices i386 et les ID Mach-O. Ne pas copier des artifacts entre arbres
  pour faire disparaître des dépendances non résolues.

## Suite utile, avec critère de réussite

1. Reconstituer la source historique et passer les contrôles hôte documentés.
   Vérifier ensuite le build et l'exécution du témoin Carbon portable.
2. Qualifier un témoin dynamique qui termine et son transfert d'entrée ;
   horodater RPC par rapport au timeout avant toute correction serveur.
3. Corriger/qualifier `@rpath` par comparaison au témoin `@loader_path`,
   puis la stabilité de lancement et les cas d'entrée standard.
4. Fermer l'ABI et les fournisseurs audio, construire en privé les composants
   gui nécessaires, qualifier HAL/callbacks/start-stop/PCM avant JACK réel.
5. Pour QuickTime, choisir une petite fonction réellement utile et testable
   à partir d'un appel applicatif identifié ; éviter une nouvelle série
   d'inventaires de stubs sans gain fonctionnel.

Aucune de ces propositions n'est un résultat exécuté. Une nouvelle contribution
doit mettre à jour cet état, les commandes de reproduction et les limites.

## Conservation et reprise privée

Une archive privée de transfert conserve les sources locales complètes,
rapports, sondes, builds et installations ; son inventaire est vérifié fichier
par fichier. Elle complète les sources reproductibles publiques. Elle ne doit
pas être annoncée comme disponible sur GitHub.

Les fichiers sensibles, préfixes, logs bruts, identifiants locaux et core dumps
ne doivent pas être publiés pour alimenter une suggestion. Les processus en
mémoire et les sockets ne sont pas des artifacts restaurables.
Les neuf fichiers du checkout protégé restent intacts ; aucun checkout/reset
n'est à effectuer dans cette copie.
