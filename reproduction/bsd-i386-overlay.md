# BSD i386 - build OverlayFS reproductible (R12)

Patch : `reproduction/patches/bsd-i386-return-lseek-fa29287.patch`.
XNU epingle : `fa29287aa2f0115271e091f1031f53c9e024005d`.

Le lanceur integre le worker valide en R11.
Verification sans compilation :
`bash reproduction/build-bsd-i386-overlay.sh --check`

Build explicite dans un dossier neuf WSL ext4 :
`bash reproduction/build-bsd-i386-overlay.sh --build /home/Deniel/d4wrling-work/C13-gQ93QvMc/BM4-tvUnbSa8/r12`

Sorties : exports/libsystem_kernel.dylib, exports/dyld,
exports/SHA256SUMS et journaux prives.

R11 : PASS borne.
R12 --check : controle statique, pas validation du build.
R12 --build : PASS borne (reconstruction isolee).
R12 invite Mach-O i386 : PASS borne, 32 controles BSD et 400 appels multithreads.
Preuves locales : BM4/r12/build.log, guest-r12.log et exports/SHA256SUMS.
Les changements de maintenance R13 ne sont pas encore rejoues en mode --build.
Aucun remplacement du build ou de l'installation de reference.
La non-regression fonctionnelle x86_64 reste non prouvee.

## Provenance des exports R12

- libsystem_kernel.dylib SHA-256 : `e90c29306497de664d59c37e841c6ab2c73dd800319741e02d68570c27115a1d`
- dyld SHA-256 : `55abc10dea803b66dbf24380b437f89825c7e07a73d230fa16d2b03228900b60`
- Source canonique : `d2318ea37f9edbdcd661408edfa8723b0289eb2e`
- Aucun test fonctionnel x86_64 revendique.

## Portabilite

La racine de travail est deduite de l'emplacement du depot.
La variable `D4RLING_BSD_OUTPUT_ROOT` permet de choisir une
autre racine de sortie, obligatoirement situee dans le meme
espace de travail WSL. Le dossier de sortie doit etre neuf.
