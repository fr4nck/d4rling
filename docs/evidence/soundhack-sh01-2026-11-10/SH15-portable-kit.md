# SoundHack SH15 — kit de reprise portable pour la liaison Darwin i386 (10400)

**10 novembre 2026. Qualification : KIT_HÔTE PASS, liaison i386 réelle NON EXÉCUTÉE.**
Cette note ne démontre ni `MH_DYLIB` liée, ni chargement Darwin i386, ni démarrage SoundHack, ni moteur audio ou Logic Studio 8.

## Évolution concrète depuis SH14

- Le dossier historique du i5-10400 contient désormais une **installation privée du socle D4rling qualifiée**, à ne pas confondre avec un lancement invité. Référence : [qualification 10400](../../qualification/10400-wsl2-core-i386-2026-11-10.md).
- Le code canonique `reproduction/build-carbon-probe.py` désigne explicitement le lieur potentiel à `build-core-i386/src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld`. Le chercheur SH13 examine déjà ce répertoire. **Sa présence exécutable sur le véritable 10400 n'a pas été constatée dans cette conversation.**
- SH14 obligeait à avoir un checkout `~/atelier/d4rling` sur `master` contenant SH13. Le 10400 utilise par ailleurs une reconstruction historique matérialisée depuis un ancien commit. Le kit SH15 supprime ce prérequis de synchronisation, **sans changer la branche ni écrire dans les checkouts**.

## Livrable

Le kit SH15 est un ZIP autonome, construit par `build_sh15_portable.py`, comprenant :
- `SH15-10400-portable.sh` : prévol, découverte et déclenchement de SH12 sans checkout récent ;
- les quatre scripts **byte-identiques** déjà publiés sur `master` : `sh12_cctools_replay.py` (blob Git `a4961c03b2c449a34e08f2d2736f36a599dfba6a`), `darwin_archive_gate.py` (`1c0229ccf6de6870add174a831837427e77a00b4`), `i386_link_gate.py` (`746855c0c9013aa0ee701035a2b1b5ffd7f8eac8`) et `macho_audit.py` (`0ac6e95301ed563bfb12cadabb444fda520f3c09`) ;
- l'archive originale SH10 (`d4rling-SH10-archive-i386.zip`, SHA-256 `2fb5c48ecc0ab879a2f60285574f275dd320bc076a1d3ad587a9584adc2d542b`), licence MIT incluse ;
- le texte GPL-3, un manifeste des sommes SHA-256 et une notice.

ZIP livré dans la conversation : **40 722 octets**, SHA-256 `1ae4ac3e3a2bfdfaf28bd327519519c20fe65bf494e5814502ae8466c58ef126`. Le ZIP n'est **pas** publié dans GitHub : seules les sources des outils, tests et preuves y sont enregistrées. Le générateur est déterministe à entrées identiques et refuse d'écraser un ZIP déjà présent.

## Comportement du script

Prévol en lecture seule : présence des outils Git/Python/Clang/LLVM, empreintes Git de chaque module, SHA-256 exact de SH10, `CMakeCache.txt` lié au `D4RLING-REPRODUCTION.json` historique (base `b7d0cb6a79fe196657deb9711647f8486bcc5e5e`), sous-module `cctools-port` à `d9456c221e1f462e17c0b3297748bc089d5a861e`.

Il recherche exactement **un** fichier ELF natif dans les emplacements bornés de SH12/SH13, puis réutilise SH12 et SH11 pour tenter le lien. Si le prévol échoue ou que le lieur est absent ou ambigu : **code 3**, aucun répertoire de sortie créé. Le dossier `~/atelier/d4rling-10400/validation/soundhack-sh15` n'est créé qu'après prévol validé. Une `libSoundHackFFT_i386.dylib` est conservée uniquement après vérification structurelle `LINK_STRUCTURE_PASS`, en création exclusive (pas d'écrasement).

L'absence de `LC_DYLD_INFO` décodé, la présence de faux ELF et le SHA d'un lieur ne suffisent **jamais** à prouver un chargement invité ou la provenance de la compilation.

## Tests réellement exécutés — Linux x86_64 isolé, pas le 10400

- **11/11 PASS, 0 FAIL, 0 SKIP** avec le paquet SH10 original disponible : identité des modules, ZIP, syntaxe Bash, refus des substitutions, absence de build/lieur, deux candidats ambigus, stabilité déterministe du ZIP, refus d'écraser, source altérée. Les faux ELF utilisés pour tester l'ambiguïté ne sont **jamais exécutés**.
- Sans ZIP SH10 : **2 PASS, 9 SKIP, 0 FAIL**. Les cas dépendants du ZIP sont explicitement ignorés, et non comptés comme succès.
- `python3 -m py_compile` sur le générateur et les tests, et `bash -n` sur le script : PASS.
- **Aucun véritable cctools `ld64` n'a été exécuté** : le conteneur est isolé et aucun chemin d'exécutable du 10400 n'y est accessible.

## Reproduction

Dans un checkout D4rling contenant les scripts SH15, avec le **vrai** ZIP SH10 séparément obtenu :

```sh
export SOUNDHACK_SH10_PACKAGE=/authorized/path/d4rling-SH10-archive-i386.zip
python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 -p 'test_sh15_portable.py' -v
python3 reproduction/fixtures/soundhack-i386/build_sh15_portable.py \
  --sh10-package "$SOUNDHACK_SH10_PACKAGE" \
  --output /authorized/new/d4rling-SH15-10400-portable.zip
```

Sur le **10400**, extraire le ZIP dans un dossier neuf et autorisé sous Debian WSL2 (sans remplacer des fichiers existants) puis, depuis ce dossier, lancer :

```sh
bash SH15-10400-portable.sh
```

Les chemins par défaut sont ceux du 10400 déjà documentés, sous `~/atelier/d4rling-10400`. Si nécessaire, définir `D4RLING_10400_ROOT` ou `D4RLING_BUILD_ROOT` sans modifier le script. Aucun réseau, installation système, mise à jour Git, `sudo`, suppression de fichiers existants, construction complète, démarrage invité ni audio ne sont déclenchés.

**Prochain résultat décisif à obtenir :** sortie JSON d'une véritable liaison SH12 sur le 10400 ; conserver la séparation entre un PASS structurel de dylib et un PASS d'exécution i386.
