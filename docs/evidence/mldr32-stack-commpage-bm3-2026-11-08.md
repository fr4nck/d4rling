# mldr32 i386 — collision stack/commpage (BIG MAMA 3, 8 novembre 2026)

## Provenance

- Base du portage : D4RLING `master` `c17bd4f7262360ab0a2ef1316d56e73266bddfeb`.
- Source amont : [Darling PR #1864](https://github.com/darlinghq/darling/pull/1864), auteur Lubos Dolezel (`LubosD`), fusionnee le 7 novembre 2026 ; commit de fusion `331c65d63b3b4aace9ad442ad9cc19f59d20be96`.
- Portage limite a `src/startup/mldr/mldr.c`, `commpage.c` et `commpage.h`, sans fusion globale de l'amont.
- Adaptations locales : validation stricte du compteur (`strtol`) et interruption de la relance si `setenv()` echoue, contre-test R7.
- `O_CLOEXEC` est deliberement exclu : changement independant non qualifie par cet incident.
- Licence et notices d'origine conservees.

## Reproduction et resultats (preuves locales privees)

- Trois fichiers de depart identiques entre le commit Carbon de qualification et le canon : 3/3. Patch verifie sur copie : application 3/3.
- R7 : fonction extraite et appels systeme simules, 11/12 cas pour la variante sans garde ; **12/12** pour la variante avec garde ; negatif `setenv()` discriminant.
- BIG MAMA 3 : compilation et liaison ELF32 de `mldr32` reference, candidat et candidat FD, ainsi que deux binaires `mldr` ELF64 ; 4/4 smoke ELF.
- Temoins **Mach-O i386 reels**, dans installations/namespaces prives : ASLR normal, 5/5 reference et 5/5 candidat ; ASLR desactive, 1/2 reference et 2/2 candidat.
- Le second lancement de reference avec ASLR desactive echoue avec `Failed to allocate stack of 65536 bytes: 17 (File exists)` ; le lancement candidat associe atteint `BM3-I386-CONTRACT-PASS`.
- Arguments et variable d'environnement verifies par le temoin sur les demarrages reussis ; sources protegees controlees inchangees.

## Limites / interpretation

- Les essais A/B emploient des processus et prefixes differents : ils montrent une correction fonctionnelle et la collision de la reference, **pas** une preuve que l'adresse conflictuelle etait identique dans les deux essais.
- Les relancements `execv()` du candidat n'ont pas ete comptes ; la disparition generale de toutes les collisions n'est pas demontree.
- Deux essais par variante sans ASLR ne constituent pas une estimation fiable de taux d'echec.
- Le chargement ELF64 a ete reconstruit et lance en smoke, sans regression applicative x86_64 exhaustive.
- L'integration en source n'est pas un remplacement de l'installation de reference : un nouveau build installe et qualifie reste distinct.

## Empreintes des preuves (non publiees)

- Patch d'integration SHA-256 : `2bcf4faf22ca5ee0014511edee0c3e0adabf715e3af4b79c435e469140894c84`.
- Resultat local BIG MAMA 3 SHA-256 : `b9a06bd04ebfd3b6131480cd6ad4539ef09527a4c4289f1a65026fe450564ab5`.
- Correctif R7 SHA-256 : `429dce2c82570f91e818152ae07b37fa69dd6af169eede4b7ac9d3fb96435292`.

Les journaux bruts, chemins locaux, processus et prefixes restent hors Git.
