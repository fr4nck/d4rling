# Cocotron ABI26 — contrat de correction de l'atomicite i386 (revue statique)

**18 novembre 2026. Statut : CONCEPTION, pas test execute ni patch integre.**
Suite du constat ABI25 publie dans [la revue](cocotron-abi25-port-review-2026-11-17.md) et de la provenance ABI25-R2 [archivee](cocotron-abi25-r2-source-recovery-2026-11-17.md). Aucune execution du 5700X ou modification du code source n'est revendiquee dans cette note.

## Preuve relue sur les sources amont epinglees

Source : `darlinghq/darling-cocotron@a99c14f972fdf4570652797a0cc0deff2db9edbc`,
`AppKit/include/AppKit/AppKitIvarLayout.h`, lignes 71–182 ;
`AppKit/include/AppKit/NSMenuItem.h`, propriete `@property(retain) NSView *view`.

Sur `!__OBJC2__` :

- `_NSExtraIvarsPointer` teste `*slot == NULL` puis effectue `*slot = calloc(...)`, sans synchronisation. Deux threads peuvent allouer deux blocs concurrents et perdre l'un.
- `_NSExtraIvarsSide` lit l'association, puis cree `NSMutableData` et l'installe avec `OBJC_ASSOCIATION_RETAIN_NONATOMIC`, sans primitive de synchronisation couvrant lecture/creation/conservation. Deux blocs peuvent etre publies successivement ; un pointeur `mutableBytes` obtenu peut ne pas rester valide pendant une ecriture concurrente de l'association.
- `NS_EXTRA_SYNTHESIZE_RETAIN` retourne le pointeur brut sans garantie de duree de vie a travers un setter concurrent ; celui-ci fait `retain(value)`, `release(old)`, puis affecte le champ sans verrou.
- `NS_EXTRA_SYNTHESIZE_COPY` a le meme probleme, avec copie avant liberation.
- `NS_EXTRA_SYNTHESIZE_ASSIGN`, `NS_EXTRA_FREE` et `NS_EXTRA_COPY` doivent etre examines sous le meme modele de concurrence ; le fait d'atomiciser uniquement les setters de `view` ne garantit pas la publication initiale du bloc.

L'atomicite d'une propriete Objective-C concerne **ses acces**. Elle ne rend pas les operations composites sur l'objet thread-safe et ne dispense pas de proteger dealloc, copie et acces directs aux extras au moment approprie.

## Contraintes pour un candidat prive ABI26

1. Inventorier les 26 occurrences de synthese du port, en classant chaque declaration source `atomic` ou `nonatomic` et la politique `assign / retain / copy`; ne pas changer les declarations publiques pour contourner le probleme.
2. Definir **une discipline de verrouillage coherente** par objet et par champ, couvrant l'allocation/publication des extras, le getter, l'echange du setter et les interactions avec copie/dealloc et association. Verifier notamment l'ordre des verrous, l'absence d'appels potentiellement reentrants vers du code utilisateur sous verrou et la semantique d'ownership (une valeur renvoyee doit rester vivante jusqu'a l'autorelease attendu).
3. Le backend peut s'appuyer sur les primitives runtime Objective-C **seulement apres preuve** qu'elles satisfont les contraintes de l'ABI fragile et que l'objet/offset utilise est valide. `objc_getProperty/objc_setProperty` sur un champ d'un bloc d'extras externe ne sont pas interchangeables avec un ivar de l'objet Objective-C.
4. Verification i386 et x86_64, sur fixture privee et vrai runtime : premieres allocations concurrentes, getter vs deux setters alternes, alias retain/copy, autorelease pool par thread, side-storage, copies, destruction apres arret des threads. Contraires : supprimer la synchronisation et s'assurer que le banc le detecte. TSAN peut completer mais non remplacer l'oracle de duree de vie.
5. Rejouer les **87 assertions positives ABI24** sur B13 x86_64 et sur les candidats i386/x86_64, ainsi que les cinq violations negatives attendues. La correction ne doit pas modifier le layout public des classes historiques, les exports/dylib IDs ou les UUID de reference sans justification. B13, source canonique, gitlink et caches restent inchanges.

## Barriere d'integration

**GATE=HOLD_FOR_IMPLEMENTATION_AND_DYNAMIC_ATOMICITY_TESTS.**
Ne pas publier de correction source, ne pas changer le gitlink et ne pas qualifier Logic ou le rendu GUI a partir de ce seul audit. Ce document est un protocole cible et une lecture de code, non une preuve que le correctif fonctionne.
