# Cocotron ABI26-R1 — candidat prive des accesseurs i386

**18 novembre 2026 — CANDIDAT NON INTEGRE, RUNTIME NON QUALIFIE.**

Source de reference : `darlinghq/darling-cocotron@a99c14f972fdf4570652797a0cc0deff2db9edbc`,
blob `AppKit/include/AppKit/AppKitIvarLayout.h` = `69bf92700c0bd0d6003e67b31dacdc6462c56528`.

Le fichier [`AppKitIvarLayout.candidate.h`](AppKitIvarLayout.candidate.h)
est conserve **dans les tests**, hors du sous-module de production.
Il conserve les declarations et layouts de l'ABI historique, sans nouveau champ.
Il remplace la publication non synchronisee des blocs d'extras et les accesseurs
`NS_EXTRA_SYNTHESIZE_ASSIGN/RETAIN/COPY` par des acces sous `@synchronized(self)`.
Le getter d'objet retient la valeur sous le verrou, puis autorelease apres le
verrou ; le setter retient/copie avant l'echange et libere l'ancienne valeur
apres le verrou.

## Nature de la verification

Un pilote **externe** `cocotron_abi26_r1.sh`, SHA-256
`2c7b572c6b0d40e1c949994d6aad136a54f1c0e4d0ab3a6e8ad4eec67a1f98dd`,
est prepare pour etre execute sur le 5700X. Il valide l'empreinte de
l'en-tete historique local ; cree un dossier prive sous
`~/d4wrling-work/validation/cocotron-abi26-r1.*` ; produit une copie
candidate et un patch ; compile des temoins Objective-C sous le compilateur
existant, en fragile i386 et non-fragile x86_64 ; controle six methodes
i386 synchronisees contre la base non synchronisee ; confronte l'IR x86_64 ;
verifie que les sources et le noyau restent inchanges ; copie le bilan dans
le presse-papiers Windows.

**Les controles d'assemblage ont ete verifies seulement sur un en-tete
synthetique de developpement** avec en-tetes factices Objective-C, pas sur un
build complet AppKit du 5700X. Aucun resultat reel du pilote 5700X n'est
encore revendique ici.

## Barriere technique

Le passage a l'execution de tests multithreads avec le **vrai runtime
Objective-C Darwin i386** reste requis. Les points ouverts comprennent :
initialisation concurrente des blocs, effets des acces directs a
`NS_EXTRA`, comportement des associations et de `NS_EXTRA_COPY`,
`NS_EXTRA_FREE`, autorelease pools, cycle de vie de l'objet, securite
du verrou en reentrance, dependances `objc_sync_enter/exit`, validation
du build FAT et des **87 assertions ABI24** existantes.

Le candidat n'est pas un correctif de production et ne justifie **aucun
changement du gitlink Cocotron ni de B13**. Ne pas traiter sa seule
compilation comme une preuve d'atomicite effective, de stabilite
multithread, de GUI ou de Logic.

References :
[ABI25, defaut observe](../../../../docs/evidence/cocotron-abi25-port-review-2026-11-17.md)
et [contrat ABI26](../../../../docs/evidence/cocotron-abi26-i386-atomicity-contract-2026-11-18.md).
