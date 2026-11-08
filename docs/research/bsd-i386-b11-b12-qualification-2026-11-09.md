# BSD Darwin i386 — qualification B11/B12

Date : 9 novembre 2026.

## Resultat fonctionnel

- B11-R5 : 40/40 executions invitees PASS.
- WIDE64 D : 20/20 PASS, 6 controles par execution.
- EXTRA D : 4/4 PASS, 13 controles par execution.
- BASIC/TLS/UNKNOWN D : 3/3 repetitions par famille.
- Collisions observees dans WIDE64 D : 0/20.
- Comparaison C/D : meme kernel et meme dyld ; mldr32 different.

## Provenance

- XNU de reference : `fa29287aa2f0115271e091f1031f53c9e024005d`.
- Dispatcher BSD : patch historique
  `reproduction/patches/bsd-i386-return-fa29287.patch`.
- Correction lseek : candidat B10 qualifie dans B11.
- Patch combine : `reproduction/patches/bsd-i386-return-lseek-fa29287.patch`.
- SHA-256 : `d2642690c6c15601261429fe807dca674dd06ada08e85ca554cd120655ec3d61`.

## Reproductibilite source

B12 a reconstruit exactement les quatre fichiers modifies
depuis les blobs Git du XNU epingle, verifie le patch avec
`git apply --check` et effectue un rejeu independant 4/4.

Les rapports et journaux complets sont conserves dans les
zones de validation locales B11 et B12, hors du depot Git.

## Portee et limites

Ce commit archive un **candidat source qualifie**, pas une
integration du correctif au build par defaut.

Le sous-module XNU reste au commit d'origine. Le patch
doit etre applique explicitement a une source XNU
**isolee**, jamais silencieusement au canon protege.

Une reconstruction independante du patch combine,
les controles x86_64 pertinents, ainsi que la provenance
du dyld effectivement charge restent a qualifier avant
de declarer l'integration complete.

La robustesse generale du chargeur mldr32 n'est pas
demontree par vingt demarrages sans collision.
