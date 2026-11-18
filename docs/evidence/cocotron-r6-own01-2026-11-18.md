# Cocotron R6-OWN-01 — ownership des copies de `NSTextFieldCell` (18 novembre 2026)

**TEST invité i386/x86_64 sur le 5700X**, avec le runtime Darling réel et
l'image AppKit vérifiée dans chaque invité. Suite de
l'[issue #16](https://github.com/fr4nck/d4rling/issues/16) et de la
[qualification R6](cocotron-r6-convergence-2026-11-18.md).
Préparé avec l'assistance d'un agent IA (Claude Code) pour le mainteneur.

## Défaut

`-[NSTextFieldCell copyWithZone:]` duplique `_placeholder` et
`_allowedInputSourceLocales` sans en prendre la propriété :
- en i386, `NS_EXTRA_COPY` recopie le bloc d'extras par `memcpy` ;
- en x86_64, `NSCopyObject` partage les ivars.

Or `-dealloc` libère les deux champs dans chaque cellule. Libérer une cellule
puis sa copie libère donc deux fois les mêmes valeurs, et laisse la survivante
avec des pointeurs pendants. Le défaut existe déjà dans `deef9911` : ce n'est pas
une régression de R6.

## Correctif

Commit Cocotron
[`77219763`](https://github.com/fr4nck/darling-cocotron/commit/7721976389ad8481b8cf64a44283b231e0092b8d),
4ᵉ commit de la branche `d4rling/deef9911` au-dessus de `cfa659db`. Il ajoute
+5 lignes (+285 caractères) dans `AppKit/NSTextFieldCell.m` : la copie prend
ses propres copies des deux champs, avec la même sémantique `copy` que leurs
setters. C'est le changement minimal proposé dans l'issue, à la même ancre
(blob source `bc021462`, blob publié `ab5b1514`).

Les livrables privés OWN-01 décrits dans l'issue (patch `6453a2d4…`, témoin
`577132fa…`) **ne se trouvent pas** sur le 5700X. J'ai donc refait le patch à
partir du texte de l'issue (diff identique, +285 caractères) et écrit un témoin
équivalent selon le protocole demandé :
[`tests/regressions/cocotron/r6/own01.m`](../../tests/regressions/cocotron/r6/own01.m),
SHA-256 `09274b68…`.

## Méthode

- AppKit et X11 sont reconstruits avec les commandes de B13. La source de
  l'arbre `cfa659db` est montée en lecture seule.
  - Seul `NSTextFieldCell.m.o` change.
  - X11 a un code identique : `__text`, `__data` et chaînes égaux en i386 et
    x86_64.
  - AppKit ne diffère que par `__text`.
  - Le correctif n'ajoute aucun avertissement.
- Référence `cfa659db` : AppKit `75f88a30…`. Candidat : AppKit `02d3fc11…`,
  UUID i386 `215107e5…`, x86_64 `0811d790…`.
- Banc R5/R6 : namespaces privés, préfixe neuf, AppKit/X11 substitués par une
  couche overlay du namespace, empreinte de l'AppKit chargé relevée dans chaque
  invité.
- **Valeurs suivies** : une sous-classe de `NSString` qui compte ses propres
  références. À zéro, elle est marquée morte au lieu d'être libérée, et toute
  opération ultérieure est comptée. Une double libération est ainsi détectée de
  façon déterministe, sans corrompre le tas.
- **Valeurs réelles** : `NSString`/`NSArray` construites dynamiquement, sous
  `NSZombieEnabled=YES`.
- Un processus par cas, chaque cas exécuté deux fois.

## Résultats (48 exécutions de cas, plus un essai initial)

| Cas (i386 et x86_64, 2 ordres, ×2) | `cfa659db` | `77219763` |
| --- | --- | --- |
| `_placeholder` suivi | **FAIL 8/8** : objet partagé après copie, survivant mort, 2 opérations sur valeur détruite | **PASS 8/8** : 3 valeurs, chacune détruite une fois, 0 opération posthume |
| `_allowedInputSourceLocales` suivi | **FAIL 8/8** : objet partagé, 4 opérations sur valeur détruite | **PASS 8/8** |
| `NSString` + `NSArray` réels, `NSZombieEnabled` | **SIGTRAP 8/8** : `-[__NSCFString isKindOfClass:] message sent to deallocated instance` | **PASS 8/8** : valeurs de la survivante intactes |

**Canaris existants**, rejoués sur le candidat avec les arguments et
l'environnement de R6 (Xvfb privé) :
- layouts **137/137**, identiques à `cfa659db` en i386 et en x86_64 ;
- **ABI24 87/87**, 0 échec en i386 et en x86_64 ; en mode corrompu, 5 échecs,
  comme pour `cfa659db` ; sorties identiques hors UUID et adresses ;
- T3 (`NSCell`/`NSMenu`, identifiant chaîne sous diagnostics malloc et suivi) :
  8/8 lignes de résultat identiques à R6.

62 exécutions au total (49 OWN-01, 13 canaris), sans processus résiduel ni montage restant. B13, P09
et l'installation privée n'ont pas été modifiés.

## Limites

- La règle « aucune autre copie superficielle d'ivar objet non retenu » n'a pas
  été auditée dans toutes les classes d'AppKit. Ce lot ne traite que les deux
  champs de l'issue.
- Pas de rendu, d'événements, de Logic ni de SoundHack.
