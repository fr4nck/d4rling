# Cocotron ABI26-R2 — témoin de runtime concurrent i386

**18 novembre 2026 — protocole expérimental ; exécution invitée réelle non effectuée.**

## Acquis

- Le candidat [ABI26-R1](../abi26-r1/AppKitIvarLayout.candidate.h) est conservé dans `tests/regressions`, sans modification du gitlink Cocotron canonique.
- Le bilan réel 5700X de [R1](../../../../docs/evidence/cocotron-abi26-r1-codegen-5700x-2026-11-18.md) a validé 10/10 portes de compilation et IR, et aucun essai multithread dans l'invité.
- Le [témoin R2](atomic-accessors-runtime.m), blob Git `cdc0a697b891d2ed8c7ba911835a6115a4b4c62a`, est une nouvelle preuve *à exécuter*, et **non** la preuve d'un correctif dynamique.

## Contrat du témoin

Le programme définit une classe Objective-C avec les trois macros d'accesseurs `assign`, `retain` et `copy` du candidat, ainsi qu'une valeur `NSCopying` ayant des compteurs de création et de destruction.

Il lance deux écrivains et trois lecteurs, à **2 200 itérations par thread**, avec démarrage synchronisé par primitives atomiques, pools d'autorelease propres aux threads, et vérification des objets lus après remplacement concurrent. Les écrivains produisent **4 400 valeurs originales** et les setters `copy` produisent **4 400 copies** ; le témoin attend donc **8 800 créations et 8 800 destructions** après libération de l'objet principal, zéro valeur invalide et zéro échec de création de thread.

Sortie positive attendue **uniquement après exécution sous un véritable runtime** :

```text
ABI26_GUEST_WORKERS=5/5
ABI26_GUEST_CREATED=8800
ABI26_GUEST_DEALLOCATED=8800
ABI26_GUEST_BAD_READS=0
ABI26_GUEST_RETAIN_COPY_STRESS=PASS
ABI26_CONCURRENT_COPY_DEALLOC=NOT_QUALIFIED
```

**Attention :** même si ce résultat est obtenu, il ne qualifie pas l'exécution simultanée de `NS_EXTRA_COPY` ou `NS_EXTRA_FREE` avec des appels concurrents. Le témoin libère le contenant seulement après la réunion de tous les threads ; il ne valide pas l'intégration d'AppKit ni les 87 assertions ABI24.

## Qualification du pilote privé préparé

Le pilote `cocotron_abi26_r2.sh`, SHA-256 `0993c4cf0a5a8925d2fcba75c2c641ca9be96cd711fa1825b853c5e3c115da00`, est remis séparément dans le chat. Il contrôle les empreintes privées R1, conserve la fixture dans un nouveau répertoire de validation, compile des objets Mach-O i386 et x86_64 avec des en-têtes synthétiques, puis tente **en lecture seule** d'utiliser les vrais en-têtes Darwin et fournisseurs Objective-C de B13 et de produire un binaire invité privé.

Avant remise, un environnement synthétique distinct (sans le 5700X) a validé la **syntaxe Bash, les deux compilations Objective-C et les deux objets Mach-O** ; les portes dépendant de la présence des SDK et des fournisseurs B13 réels y sont restées en REVIEW. Ce n'est **pas** un résultat de runtime du 5700X.

Le pilote ne lance **pas automatiquement** de programme invité, car le lanceur privé, le préfixe et les bibliothèques chargées doivent être identifiés et vérifiés explicitement afin de ne pas écrire ailleurs. Aucun `vm.mmap_min_addr`, préfixe historique, dossier B13, gitlink, source canonique ou dépôt n'est modifié. Répertoire d'écriture : uniquement un nouveau `~/d4wrling-work/validation/cocotron-abi26-r2.*`. Rapport final copié via `clip.exe`.

## Garde d'intégration

`INTEGRATION=HOLD_FOR_DYNAMIC_I386_GUEST_AND_LIFECYCLE_REVIEW`.
Conserver le candidat expérimental ; ne pas assimiler les sorties de compilation, d'IR ou de simulation à une preuve d'atomicité dynamique complète. Une exécution réelle sous le runtime i386 avec identité des bibliothèques vérifiée et une qualification dédiée des chemins `NS_EXTRA_COPY`/`NS_EXTRA_FREE` précèdent toute proposition d'intégration.
