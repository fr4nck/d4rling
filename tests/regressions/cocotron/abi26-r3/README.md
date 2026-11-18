# Cocotron ABI26-R3 — convergence sur le SDK Darwin reel

**18 novembre 2026. Statut : PILOTE PREPARE, execution sur le 5700X non encore obtenue.**

## Point d'entree

[R2, bilan 7/9 observe sur le 5700X](../../../../docs/evidence/cocotron-abi26-r2-codegen-5700x-2026-11-18.md) qualifie les objets Mach-O de la fixture dans les deux architectures et les exports `objc_sync_enter/exit`, mais ne qualifie ni compilation aux vrais en-tetes i386 ni liaison invitée. L'examen du pilote R2 montre que `REAL_HEADERS_I386=NOT_QUALIFIED` provient de la **selection du SDK** : seules deux racines etaient testees, exigeant un chemin `Foundation.framework/Headers/Foundation.h` deja resolu. La compilation reelle n'a pas ete tentee.

## ABI26-R3 : banc autonome (pas un autre inventaire)

Le pilote local `cocotron_abi26_r3.sh` a ete prepare pour le 5700X avec SHA-256 :
`d0293402e0fd4b2ff5200512adf61f724ad7a8dd8ee59e0cebdb12429581dfc4`.

Il comporte 10 etapes independantes, avec etat PASS/REVIEW/BLOCKED et affichage de l'activite en temps reel :

1. Pins des sources historiques, du candidat R1 et de la fixture R2 **sans les recreer ni recompilier les temoins synthetiques**.
2. Resolution bornee des SDK a partir des sources connues `upstream-sync`, `security-s4`, `L1-CANON`, de B13 et des metadonnees ABI16/ABI19 ; examen des liens Foundation et, uniquement si des en-tetes source reels sont trouves, creation d'un lien d'overlay dans le nouveau repertoire prive.
3. Sonde Objective-C fragile i386 avec de **vrais en-tetes** ; echec capture avec diagnostic.
4. Compilation du vrai objet Mach-O i386 sous le SDK selectionne.
5. Contre-epreuve SDK : compile la fixture avec les macros historiques, verifie que seuls les nouveaux accesseurs font apparaitre `objc_sync_enter/exit`.
6. Empreintes et exports des fournisseurs libobjc/Foundation B13.
7. Tentative de liaison Darwin i386 **en prive**, sans installation.
8. Verification seulement d'un lanceur historique en lecture seule (pas de relance invitée sans prefixe prouve).
9. Controle d'integrite des sources, B13 et `vm.mmap_min_addr`.
10. Budget des sorties et rapport JSON + bilan copie automatiquement par `clip.exe`.

Toutes les sorties sont dans un nouveau `~/d4wrling-work/validation/cocotron-abi26-r3.*`. Aucun acces reseau, installation, suppression, ecriture Git, modification du sysctl, ecriture en source ou en B13.

La syntaxe Bash et celle du Python embarque ont ete controlees ; le parcours de rapport a ete teste en environnement local avec donnees synthetiques. **Aucune execution 5700X, compilation avec SDK reel, liaison reussie ou guest execute n'est encore revendiquee.**

## Garde d'integration

`INTEGRATION=HOLD`. Un lien reussi n'est pas une preuve d'atomicite en concurrence. Une fois le bon SDK identifie, lancer une qualification invitee reelle avec identite du runtime charge, puis tester les cycles de vie `NS_EXTRA_COPY` et `NS_EXTRA_FREE`. Il faudra ensuite reconstruire AppKit de maniere coherente et rejouer les temoins ABI24 avant d'envisager toute mise a jour du sous-module.
