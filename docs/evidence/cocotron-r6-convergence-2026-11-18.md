# Cocotron R6 — correctif unifié publié sur `fr4nck/darling-cocotron` (18 novembre 2026)

**TEST invité i386/x86_64 sur le 5700X, 58 essais neufs.** Mise en œuvre de la
[décision R6](../decisions/r6-cocotron-carbon-convergence-2026-11-18.md) et de
l'accord du mainteneur du 18/11 : création du fork Cocotron. Le gitlink de
production de D4rling n'est **pas** changé ; cette étape attend un accord
distinct. Les répertoires `tests/regressions/cocotron/abi26-r*` et les
espaces privés ABI26 n'ont été ni lus en écriture ni modifiés.
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur.

## Résultat intégrable

Dépôt [`fr4nck/darling-cocotron`](https://github.com/fr4nck/darling-cocotron),
fork de `darlinghq/darling-cocotron` (MIT, notices conservées).
- `master` reste le miroir de Cocotron officiel, pour suivre l'amont.
- L'étiquette `d4rling-base-deef9911` marque la base.
- La branche **`d4rling/deef9911`** porte trois commits au-dessus de `deef9911`,
  le gitlink actuel de D4rling :

| Commit | Contenu |
| --- | --- |
| [`086d75fb`](https://github.com/fr4nck/darling-cocotron/commit/086d75fbff2a87f1a41c8f4ebacc0411cb1eaf95) | R14 : `NSCell`/`NSMenu` `-copyWithZone:` copient `_identifier` (+2/+2) |
| [`a7ff43c2`](https://github.com/fr4nck/darling-cocotron/commit/a7ff43c22c3d9ad28c31a6ce933ab6893d4b9ec5) | Backport de darling-cocotron #256 (Luboš Doležel, notices conservées), patch `b35db80c…`, avec R14 reporté dans les extras (R22) ; 75 fichiers |
| [`cfa659db`](https://github.com/fr4nck/darling-cocotron/commit/cfa659db3161cef20070309e3864ea75233a1192) | Atomicité i386 unifiée (`AppKitIvarLayout.h`) |

**Contrôle d'identité.** L'arbre Git de `cfa659db` (`2ba973a4…`) est identique
à l'arbre local construit et testé (variante `uni`). R14 (`c534126e…`) est lui
aussi identique à la variante `r14` testée. Le commit intermédiaire `a7ff43c2`
n'est pas testé seul.

## Convergence R5 / ABI26-R1

Les deux candidats modifient **le même fichier de base** : l'en-tête du port
R5 est le blob amont `69bf9270…`, celui d'ABI26-R1. Différences réelles :

| Point | R5 | ABI26-R1 | Retenu |
| --- | --- | --- | --- |
| Accesseurs ASSIGN/RETAIN/COPY | `@synchronized(self)` ; getter retain sous verrou puis autorelease ; setter acquiert avant, libère après | identique | identique (R5) |
| Publication du bloc par pointeur | CAS acquire/release, sans verrou sur le chemin rapide | `@synchronized(object)` à **chaque** `NS_EXTRA()` | **CAS (R5)** |
| Stockage annexe | transaction sous verrou objet | identique, plus contrôle de nil | R5 + contrôle de nil |
| Échec d'allocation | non traité | NULL rendu | NULL rendu (ABI26) |

**Coût mesuré** (`r6-cost`, AppKit reconstruit, 1 million d'appels, ×2) :

| i386 | `-[NSMenuItem tag]` (lecture d'un champ d'extras) | setter `view` | getter `view` hors pool |
| --- | --- | --- | --- |
| port non atomique | 4,3 ns | 3,7 µs | 0,01 µs |
| **unifié** | **5,0 ns** | 7,5 µs | 7,9 µs |
| ABI26-R1 | **3 700 ns** | 7,6 µs | 8,0 µs |

Le verrou par accès d'ABI26-R1 rend toute lecture de champ d'extras environ
**800 fois plus lente** ; il est donc écarté. `@synchronized` ajoute environ
3,8 µs aux accesseurs atomiques, à iso-configuration. La valeur de 29 ns
mesurée en R5 portait sur des objets témoins à `retain` trivial. En x86_64,
le getter coûte 0,2 µs et la lecture de champ 2,4 ns, sans changement.

## Essais concurrents complétés (les manques de la décision R6)

Les témoins compilent l'en-tête testé directement (macros inline), avec les
vrais en-têtes Darwin (SDK de B13, `-F …/CoreServices.framework/Frameworks`
pour `AE/AE.h`). Ils s'exécutent dans le vrai runtime Objective-C de l'invité.

| Témoin | Port non atomique (négatif) | R5 | **unifié** | ABI26-R1 |
| --- | --- | --- | --- | --- |
| **ABI26-R2** (témoin de l'agent ABI26, tel quel : 2 setters et 3 getters sur les mêmes propriétés, assign/retain/copy) | **SIGSEGV ×2** | 8800/8800, 0 erreur ×2 | 8800/8800 ×2, et en x86_64 | 8800/8800 ×2 |
| `r6-extras first` : 2 000 objets neufs, 4 threads sur la première publication | pointeur : **4 940 valeurs perdues** ; annexe : **SIGSEGV** | PASS | **PASS** (pointeur, annexe, x86_64) | PASS |
| `r6-extras destroy` : valeur lue, conteneur détruit par un autre thread | **2 000/2 000 utilisations après libération** (pointeur et annexe) | PASS | **PASS** | PASS |
| `r6-extras copy` : copies `NS_EXTRA_COPY` + R22 pendant des lectures | PASS (non discriminant) | PASS | **PASS** | PASS |

**Arbre final unifié, avec AppKit/X11 reconstruits par les commandes de B13 :**
- layouts **137/137** conformes à l'oracle, identiques à ABI19 en i386 et x86_64 ;
- **ABI24 87/87** en i386 et x86_64, les 5 classes témoins venant de l'AppKit
  final, et 5 échecs en mode corrompu ;
- T3 sans double libération (`NSCell`, `NSMenu`, identifiant suivi ou
  `NSString` sous diagnostics malloc) ;
- course `NSMenuItem.view`/`NSCell.identifier` sans anomalie.

AppKit unifié : SHA-256 `75f88a30…`. UUID i386 `5cf40b45…`, x86_64 `e45c5bfc…`.

**Contrat et limites.**
- L'atomicité porte sur les **accesseurs** des propriétés, conformément au
  contrat Objective-C. Les accès directs à `NS_EXTRA` dans les autres méthodes
  d'AppKit ne sont pas synchronisés, comme pour un ivar ordinaire : AppKit
  n'est pas thread-safe hors de ces accesseurs.
- Copier un objet pendant qu'un autre thread le modifie, ou détruire un objet
  non retenu en concurrence, sort du contrat. Ces cas ne sont pas revendiqués.
- Pas de rendu, d'événements, de Logic ni de SoundHack.

**Pour le chantier ABI26.** Son témoin R2 est désormais exécuté dans un vrai
invité i386, avec les vrais en-têtes, contre son propre candidat R1 et contre
la version unifiée. Les pilotes R3/R4 de sélection de SDK ne sont plus
nécessaires pour cette question.

## Intégration dans D4rling — préparée, non appliquée

Changement unique proposé, après accord, en un commit sur `master` :
1. `.gitmodules`, section `src/external/cocotron` :
   `url = https://github.com/fr4nck/darling-cocotron.git`. Le fork contient
   tout l'historique amont, donc les anciennes révisions restent résolubles.
2. Gitlink `src/external/cocotron` : `deef9911…` → `cfa659db3161cef20070309e3864ea75233a1192`.
3. `CREDITS.md` : section de cette note.

Contrôles prévus à l'intégration :
- CI Darling complète (build-deb, build-dsc) ;
- relecture du diff du gitlink, limité aux 75 fichiers des trois commits (+4 965/−3 797) ;
- aucune écriture dans B13 ni dans les installations privées.

**Non encore exercé :** un build complet de D4rling avec ce gitlink. Seuls
AppKit et X11, les deux cibles dépendant de l'ABI selon le plan ABI14, ont été
reconstruits. La CI de l'intégration couvrira le reste.

## Reproduction

- Témoins : [`tests/regressions/cocotron/r6/`](../../tests/regressions/cocotron/r6/),
  et pour R5 [`abi25-r5/`](../../tests/regressions/cocotron/abi25-r5/).
- Méthode de build : `abi25-r5/build_appkit.sh`.
- Journaux et préfixes privés dans `validation/r5-recovery-20261118`.
