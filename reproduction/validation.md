# Validation de la reprise — 29 octobre 2026

Contrôles exécutés sur Debian 13.5 amd64 / WSL2, avec Clang 19.1.7,
CMake 3.31.6, Ninja 1.12.1 et les paquets relevés. Une nouvelle copie de
travail et un nouveau build ont été utilisés. Aucune installation globale.

| Contrôle exécuté | Résultat |
| --- | --- |
| Matérialisation hors ligne depuis l'arbre de référence | Base b7d0cb6, neuf modifications reproduites, parameters.c restauré |
| Identité des sous-modules récursifs | **160/160** |
| Carbon hôte Clang | **54 événements + 81 paramètres = 135 PASS**, 0 échec |
| Mêmes suites sous AddressSanitizer | **135 PASS**, 0 échec ; répétition, pas 135 nouveaux comportements |
| Contrats C11 et C++17 | Deux exécutables PASS, callback incompatible rejeté |
| Configuration fraîche core-i386 | PASS ; nouvelle racine, sortie privée |
| Build darling, mldr, mldr32, darlingserver | **179/179 étapes**, code 0 |
| Formats des nouveaux binaires | darling/mldr/darlingserver ELF64 ; mldr32 ELF32 |
| Profil DEBIAN_PACKAGING=ON | Reconfiguration PASS ; hook shutdown-user retiré des règles d'installation |
| Reconstruction du témoin Carbon depuis les sources livrées | Mach-O i386 et dylib @loader_path liés |
| Nouveau témoin NORMAL | Code 0 et D4RLING-CARBON-EVENT-I386-OK |
| Nouveau témoin BYPASS | Code 0 et même marqueur |
| Contrôle négatif sans dylib | Code 1, marqueur absent, erreur Library not loaded explicite |
| Diagnostic des paquets | Signale libelf-dev absent, aucune dérive des autres versions relevées |
| Restauration d'une petite archive de contrôle | Texte et symlink retrouvés |
| Refus d'une archive contenant ../escape.txt | Échec avant création de la destination, aucun fichier externe créé |
| Archive privée principale | **615 224 entrées**, aucun manque ni écart par rapport au manifeste |
| Protection du checkout historique | HEAD, statut, index, diff et neuf contenus identiques |

Le témoin Carbon a été **recompilé**, puis exécuté avec l'installation privée
de référence existante. Ses dylibs système n'ont pas toutes été reconstruites
pour cette vérification. Les quatre binaires natifs ont, eux, été construits
dans le nouveau build ; ils n'ont pas remplacé les binaires installés.

La compilation émet les avertissements préexistants de pointeurs/formats dans
le chargeur et des avertissements XNU. Ils ne sont pas présentés comme corrigés.
L'absence de llvm-dsymutil empêche la production des fichiers de symboles debug
correspondants ; elle n'a pas bloqué ces cibles.

Ne sont pas revendiqués : un build intégral des frameworks sur un second poste,
une installation complète neuve testée, l'exécution du code QuickTime/Player 7,
un backend JACK réel, un test matériel audio/MIDI ou la disparition des RPC -111.
Le mode réseau de materialize.py est documenté ; le test réalisé ici utilise
la variante hors ligne pour conserver les sources déjà disponibles.

L'archive principale est complétée par le petit manifeste /opt à lecture
restreinte. Les fichiers spéciaux et core dumps sont exclus ; l'état mémoire
d'un processus n'est pas un fichier restaurable. Le paquet privé inclut les
preuves brutes et les exports de chats accessibles (14 caches, 10 pièces
jointes ; 5 éléments tronqués signalés). Il reste distinct des sources
publiques et n'est pas annoncé sur GitHub.
