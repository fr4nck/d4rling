# D4rling — QuickTime E3-B2 C3

Date : 9 novembre 2026
Base canonique : `1172b80986dcde47a09485ca4f2dfd2135b62c40`
Statut : **PAUSE — EXPERIMENTAL PASS / PRODUCTION NO GO**

## Résultats

| Environnement | E3-B1 | C2 mémoire/PCM | C3 |
| --- | --- | --- | --- |
| Linux x64 natif, ASan/UBSan/LSan | 102/102 | 52/52 | 33/33 |
| Darwin Mach-O i386 sous D4rling | 102/102 | 52/52 | 33/33 |

Total : 187 contrôles réussis par environnement, soit 374.
Le témoin i386 termine avec rc=0 et processus inchangés.

## Acquis

- Lecture PCM bornée depuis un MOV déjà ouvert.
- Media associé à la bonne piste et au bon Movie.
- Gestion des Handle de taille logique exacte dans le candidat isolé.
- Agrandissement du Handle, y compris initialement vide.
- Conservation des données lors d'un échec de réallocation injecté.
- ABI hôte x64 et invité Darwin i386 distinguées.

## Limites et prochaines étapes

- Le Memory Manager C2 est une copie expérimentale instrumentée.
- CarbonCore n'est pas installé dans le préfixe i386 de référence.
- Les opérations PtrToHand, PtrToXHand, HandToHand,
  HandAndHand, PtrAndHand et ReallocateHandle restent à sécuriser (C4).
- La sortie SampleDescriptionHandle n'est pas implémentée.
- Limite expérimentale de 64 Kio PCM par appel.
- Pas de build CMake de production ni de test Logic Studio 8.
- Ne pas annoncer QuickTime complet ni le moteur audio validé.

## Sources conservées

- `quicktime-c3.patch` : candidat GetMediaSample et header.
- `macmemory-c2.patch` : candidat de gestion mémoire.
- `witness-c3.c` : témoin de qualification.
- `compat/` : adaptations réservées aux bancs.

Les correctifs sont archivés, **non appliqués** à la production.
Les binaires, installations, journaux complets et données locales
ne sont pas publiés.

## Empreintes des sources candidates

- QuickTime C3: `25c40f68f97375d7d8ed08b46f4c1528b6cb1713555cbb38d15c8b22327b5f03`
- QuickTime header C3: `935157d9f72a89844b6e7078b775b2e1725139ba5697695c72b10bf51340f0bc`
- MacMemory C2: `07ef5e8a987780ae03a0ff8d44aeee82403e30dff67bf967f8650cc90e081ecb`
- Witness C3: `0357d560800d384fd41c038c1d6b70d2c193bcb19ad0afa92ee4f0dc24fe06cc`

## Critère de reprise

Commencer par C4 et la liaison effective QuickTime–CarbonCore,
sans modifier les acquis C3 ni les autres chantiers.
