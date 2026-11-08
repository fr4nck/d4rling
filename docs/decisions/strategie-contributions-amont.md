# Stratégie de contribution de D4rling vers Darling

**Décision de projet — 8 novembre 2026**

## Intention

D4rling est un espace de développement et de qualification de la compatibilité Darwin/macOS sous Linux, avec un objectif concret : faire fonctionner des applications musicales historiques, notamment Logic Studio 8 et EXS24.

Les travaux sur Mach-O i386, les ABI, Carbon, CoreAudio et les couches système doivent aussi pouvoir bénéficier au projet [Darling](https://github.com/darlinghq/darling) lorsqu'ils sont suffisamment génériques. L'objectif n'est pas de maintenir indéfiniment des corrections privées sans examiner leur réutilisation.

## Décision de publication

**Ne pas proposer de correctifs fragmentaires en amont au fil des expériences.**

1. Poursuivre les essais, les corrections et leur qualification dans le fork personnel D4rling.
2. Attendre un **jalon technique significatif et reproductible**, de préférence une chaîne audio vérifiée de bout en bout. Distinguer explicitement un son entendu, un flux PCM transféré, un callback CoreAudio exécuté et une application Mac réellement compatible : ces preuves ne sont pas interchangeables.
3. À ce jalon, figer un état de référence, consolider les résultats et vérifier quelles corrections sont générales plutôt que spécifiques à Logic ou à l'environnement expérimental.
4. Préparer ensuite des contributions ciblées vers Darling officiel, chacune compréhensible et vérifiable seule, mais accompagnée d'une documentation cohérente présentant l'ensemble du travail.
5. **Aucune PR vers Darling officiel n'est autorisée par cette note** ; toute publication en amont fait l'objet d'une décision distincte.

La légitimité d'une contribution doit reposer sur la qualité technique et la reproductibilité, non sur le statut professionnel de son auteur.

## Dossier de preuve attendu pour une correction candidate

- **Problème :** comportement attendu, anomalie observée, périmètre et références du code concerné.
- **Reproduction :** environnement, révisions et commandes minimales ; résultat initial et résultat après correction.
- **Correctif :** changement limité et explicable, justification des choix, provenance et compatibilité de licence.
- **Qualification :** tests positifs et négatifs, régressions, reproductibilité et limites connues.
- **Portabilité :** séparation de ce qui est propre à Linux, i386, une version de Darling ou une installation locale.
- **Bilan :** ce qui est prouvé, ce qui reste hypothétique et ce qui n'a pas été testé.

Les journaux expérimentaux, artefacts, chemins locaux ou données potentiellement sensibles ne sont pas publiés sans vérification explicite. Un compte rendu de conversation n'est pas une preuve d'exécution.

## Organisation pratique

Les chantiers audio Linux/PCM, chargement Mach-O i386, Carbon, CoreAudio et Logic/EXS24 peuvent avancer séparément. Leur convergence est évaluée au moment des jalons.

Cette note enregistre **une décision de méthode**, pas un résultat de test, un correctif de code ou un engagement de compatibilité. La synchronisation des travaux locaux B11/PCM et des artefacts associés doit être vérifiée séparément avant tout commit ou push.
