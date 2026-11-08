# CLAUDE.md — D4RLING

**Avant toute action**, lire intégralement [`AGENTS.md`](AGENTS.md), qui
contient les règles locales, les zones protégées, le prévol et les limites
d'écriture, puis la documentation de reprise qu'il désigne.

**Gouvernance transversale :** le référentiel est le dépôt **privé**
[`fr4nck/PMSL-Arch`](https://github.com/fr4nck/PMSL-Arch), branche
`main`, fichiers `AGENTS.md` et
`docs/GOUVERNANCE_AGENTS_OBJECTIFS.md` (AGT-001 à AGT-014).
Le consulter avant toute mission technique significative si les permissions
le permettent. Ne pas supposer cet accès et ne pas inventer les règles
inaccessibles ; appliquer dans tous les cas les garde-fous autonomes de
`AGENTS.md`. Arrêter une opération en cas de règle indispensable non
vérifiable ou de conflit non résolu.

**Contrat D4RLING :** branche unique `master` ; réutilisation prioritaire
de la source, des builds et des témoins existants ; un seul checkout
canonique et un seul build/une installation de référence à terme ; au plus
trois zones permanentes ciblées (`canon/`, `validation/`,
`historique/`) sous `/home/Deniel/d4wrling-work`, **sans migration
automatique**. Identifier les chemins et autorisations du lot avant
d'écrire. Aucun dossier parallèle, transfert réseau, installation,
suppression ni modification d'un ancien témoin sans autorisation explicite.

**Protection majeure :** `experiments/petite-victoire/` et l'installation
musicale historique ne sont pas des espaces de travail généraux. Leur
consultation ne vaut pas autorisation de modification.

**Livraison :** un objectif borné, un prévol Git réel, des scripts et
prompts directement exécutables, les preuves et régressions pertinentes,
un critère d'arrêt ; intégration de petites corrections qualifiées
directement à `master` seulement lorsque la mission l'autorise.

Ce document ne remplace pas `AGENTS.md` : ses protections plus détaillées
restent obligatoires.
