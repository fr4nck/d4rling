# QuickTime C3-M3 — prévol du préfixe privé HIT-23R (13 novembre 2026)

**Statut :** `INVENTORY_COMPLETE`, *aucun test invité QuickTime*. Journal opérateur WSL2 sur 5700X ; dépôt historique `master@5b521087d79d4348ebe312e622a05f1f8b55c110`. Les modifications locales Security et HIToolbox restent protégées. Le rédacteur n'a pas exécuté ce test sur le PC.

## Faits observés

- `build-hitoolbox-i386/private-install/bin/darling` : exécutable présent.
- `build-hitoolbox-i386/hit07-production-guest/hit07-carbon-production-i386` : exécutable présent.
- Préfixe historique HIT-23R : **171 Mo**, volume de validation **860 Go libres**.
- Quatre candidats du lot C3-M3 R4 présents, empreintes SHA-256 conformes :
  - CarbonCore C4 : `0f221249af131f56b2930c0c425fcc9621646aa7e3d5b878e4faedda66fef126` (1 352 652 octets)
  - LaunchServices : `b686abb51ac03bc57a3fc35feb96637c3a2c83546efe13b3d6bd7e4545e43f9d` (151 084 octets)
  - CoreServices : `bf7aa2ab124fdfc64c6feabad4ebe53bc174a2c361a6ed4cee69ddb5a29f7dd2` (15 476 octets)
  - QuickTime : `55a7767c7088db4e331d84b014977177e45b9ace80a5d8673436b5f9125d3b03` (1 042 800 octets)
- Inventaire `os.walk(..., followlinks=False)` : aucun fichier nommé exactement CarbonCore, LaunchServices, CoreServices, QuickTime n'a été trouvé dans le préfixe. **Les liens symboliques de répertoires non parcourus et les versions alternatives n'ont pas été exclus**.
- Le prévol affichait `EXECUTABLE=MISSING` sur `reproduction/run-guest.sh` car il utilisait `test -x`. Le **fichier existe au commit historique GitHub exact**, blob `7b654180dae2184433b799e81ec06ff60146a180`. Lancé par `bash reproduction/run-guest.sh`, il n'a pas besoin du bit exécutable ; son existence/lisibilité sur 5700X restent à vérifier par `test -r` et `git hash-object`. Ne pas installer ou changer les permissions pour corriger un contrôle défectueux.
- `RUNTIME_PREFLIGHT=INVENTORY_COMPLETE`, `PROTECTED_INPUTS=UNCHANGED`, `DYLD_RUNTIME=NOT_TESTED`, `DARLING_GUEST=NOT_TESTED`.

## Suite autorisée

Faire un **inventaire en lecture seule** des vrais chemins du préfixe, des liens et versions sous `libexec/darling/System/Library/{Frameworks,PrivateFrameworks}`, et de la lisibilité du runner. Puis préparer une **copie entièrement distincte** du préfixe dans `quicktime-c3-m3/g2.0Tfg9onI` avec contrôle des empreintes des douze dylibs candidates. Ne pas écraser le préfixe HIT-23R, ne pas lancer Darling avant fermeture des dépendances. Aucun code de production ni x86_64/Cocoa concerné.

Voir [la liaison i386 R4 et l'analyse de rebase C4](quicktime-c3-m3-g2-prelink-2026-11-12.md) pour les preuves précédentes.

## Inspection détaillée du préfixe — opérateur 5700X, 13 novembre 2026

Prévol intégralement en lecture seule, `PREFIX_LAYOUT=INSPECTED`, `PROTECTED_INPUTS=UNCHANGED`. Fichier `reproduction/run-guest.sh` **présent et lisible**, `git ls-tree HEAD` = `100644 blob 7b654180dae2184433b799e81ec06ff60146a180` ; `git hash-object` local identique. Le premier diagnostic `EXECUTABLE=MISSING` était donc exclusivement une erreur de test `-x` au lieu de `-r`.

À **chacun des cinq chemins d'installation attendus** (`CarbonCore`, `LaunchServices`, `CoreServices`, `QuickTime`, `FMDB`), `ABSENT_AT_EXPECTED_PATH`. Une recherche `find -maxdepth 18` en fichiers ordinaires **et liens symboliques** de ces cinq noms confirme `TOTAL_MATCHES=0` dans tout le préfixe HIT-23R. Leur absence est établie, non seulement présumée.

La recherche de liens `Current` sous `System/Library` a trouvé **cinq liens historiques existants** : `CoreFoundation.framework/Versions/Current`, `Foundation.framework/Versions/Current`, `Carbon.framework/Versions/A/Frameworks/HIToolbox.framework/Versions/Current`, `Carbon.framework/Versions/Current`, `SystemConfiguration.framework/Versions/Current`. Ceux-ci ne doivent pas être écrasés.

**Décision de chantier :** conserver intact `build-hitoolbox-i386/private-install` (171 Mo) comme témoin HIT-23R. Les douze dylibs i386 authentifiées (CarbonCore C4 + 7 subframeworks + FMDB + LaunchServices + CoreServices + QuickTime) sont à préparer exclusivement sous un **nouveau préfixe privé**, avec prévol de leurs install-names et inventaire des dépendances après ajout, puis fermeture du graphe *avant* toute exécution invitée. Aucun GO runtime ni Logic 8 n'est déduit.
