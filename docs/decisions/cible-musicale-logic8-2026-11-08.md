# D4RLING — objectif musical de référence : Logic Studio 8

**Date :** 8 novembre 2026  
**Statut :** orientation produit, sans validation technique nouvelle

## Finalité

Retrouver les qualités musicales et l'efficacité de Logic Studio 8 sous Linux. L'objectif n'est pas de réécrire une station audionumérique complète par principe : il est de choisir la voie qui préserve au mieux les fonctions recherchées, avec un coût de développement et de fonctionnement raisonnable.

## Trois exigences prioritaires

1. **Instruments et effets historiques, à commencer par EXS24 mkII.** La cible est l'instrument lui-même (édition des zones et groupes, filtres, enveloppes, modulation et rendu), **pas uniquement la lecture ou la conversion de ses banques**. Les autres instruments et effets de Logic Studio — notamment ES2, Sculpture, Ultrabeat, Space Designer et les traitements natifs — comptent également dans la valeur de la suite. Leur compatibilité n'est pas acquise.
2. **Quantification MIDI avancée et non destructive.** Préserver le jeu d'origine ; prendre en compte Q-Strength, Q-Swing, Q-Range, les modèles de groove, les décalages de type Q-Flam et, après vérification des comportements historiques, les paramètres de longueur et vélocité. L'enjeu est le traitement d'événements MIDI, **pas** le recalage temporel d'enregistrements audio.
3. **Sobriété mémoire et réactivité.** Logic Studio 8 reste la référence d'ergonomie et de frugalité : démarrage rapide, surcharge logicielle limitée, chargement d'échantillons proportionné et lecture en streaming quand elle est pertinente. Les valeurs de RAM historiques et les objectifs chiffrés doivent être établis par des mesures comparables ; aucune consommation réelle n'a été mesurée dans cette note.

## Voies techniques à comparer, sans choix prématuré

- **Exécuter l'original** : poursuivre les qualifications D4RLING (Mach-O i386, Cocoa/Carbon, CoreAudio, Audio Units, CoreMIDI) pour Logic 8 et ses instruments. Examiner séparément, comme hypothèses, les versions ultérieures x86-64 et l'environnement historique Windows/Wine. Le passage en 64 bits facilite certains éléments d'infrastructure, mais ne rend pas Logic 8 i386 automatiquement compatible.
- **Réimplémentation ciblée** : envisager Python/PySide6/Qt pour l'interface et l'édition MIDI, avec un moteur natif C/C++ pour le rendu audio temps réel, et JACK/PipeWire selon l'environnement. Cette voie créerait un nouvel instrument inspiré des fonctionnalités recherchées, **pas l'EXS24 original** ; la fidélité sonore devrait être étudiée et testée séparément.

## Critères pour décider

Comparer, sur des prototypes reproductibles : ouverture et édition d'un instrument, jeu MIDI, rendu audio réellement audible, stabilité et latence, quantification non destructive, consommation mémoire, temps de démarrage, charge CPU et effort de maintenance. Distinguer mesures, preuves de fonctionnement et simples possibilités documentées.

**Aucune décision d'abandonner D4RLING, aucun choix définitif d'architecture et aucun résultat de compatibilité EXS24/Logic ne découlent de cette note.**

## Documents complémentaires

- [État général et limites des preuves](../../PROJECT_STATE.md)
- [Reprise audio et musique du 8 novembre](../REPRISE-AUDIO-MUSIQUE-2026-11-08.md)
- [Audit documentaire Logic Studio 8](../audits/logic-studio-8/2026-11-08-synthese.md)
