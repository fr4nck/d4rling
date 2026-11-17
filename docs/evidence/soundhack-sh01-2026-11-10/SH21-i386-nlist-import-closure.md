# SH21 — fermeture statique préliminaire des imports i386 du vrai SoundHack 0.896

**17 novembre 2026 — outil développé et testé, validation réelle sur 5700X en attente.**

## Objectif, preuve initiale, contrat Mach-O

Le lot [SH20](SH20-official-portable-replay.md) a retrouvé, de façon
authentifiée sur le 5700X, le véritable `SoundHack.app` Universal Binary
PPC+i386 (SHA-256 exécutable :
`6fb11c708079ca3b8f91dc53ab0d8ae732fbb8be32f0e22e34114764b9be089c`).
SH20 a mesuré **393 imports nlist**, **sept dépendances Mach-O**
(Carbon, QuickTime, CoreAudio, AudioToolbox, AudioUnit, libgcc_s.1,
libSystem.B), avec zéro bibliothèque obligatoire absente de son chemin
littéral dans le sysroot privé B13. Aucun chargement d'application,
dyld, UI ou audio n'a été démontré.

La règle fondamentale du format Mach-O à deux niveaux est que l'octet
haut de `n_desc` d'un symbole nlist indéfini référence **une bibliothèque
par son ordinal** dans l'ordre des commandes `LC_LOAD_*_DYLIB`.
Sources primaires : [XNU Apple `mach-o/nlist.h`](https://github.com/apple-oss-distributions/xnu/blob/main/EXTERNAL_HEADERS/mach-o/nlist.h)
et [Apple Mach-O File Format Reference](https://leopard-adc.pepas.com/documentation/DeveloperTools/Conceptual/MachORuntime/Mach-O_File_Format.pdf).
Un symbole défini dans **une autre** bibliothèque ne prouve pas la
résolution d'un import lié à la première ; les chaînes de réexport,
le bind dyld, les imports faibles et le runtime Cocoa/Carbon imposent
d'autres contrôles.

## Livraison isolée

- `reproduction/fixtures/soundhack-i386/sh21_import_closure.py` :
  auditeur **lecture seule**, en Python standard. Il exige le rapport
  SH20 authentique, le SHA de l'application originale et le Git blob
  **`0ac6e95301ed563bfb12cadabb444fda520f3c09`** du parseur
  `macho_audit.py` déjà utilisé par SH19.
- Inspecte chaque bibliothèque **i386** directement à son chemin
  d'import dans le sysroot privé. Refuse les symlinks qui sortent
  du préfixe ; enregistre le `LC_ID_DYLIB`, le statut nlist,
  les réexports connus, les écarts d'identité et les empreintes.
- Produit des classifications prudentes : nom directement visible
  dans la bibliothèque attendue, visible dans une autre, absent
  du nlist direct, identité divergente, fournisseur absent,
  ordinal spécial ou référence non standard.
  **`NAME_NOT_IN_DIRECT_PROVIDER_NLIST` ne veut jamais dire que
  dyld échouera à charger ce symbole**, notamment à cause
  des reexports et autres mécanismes non parcourus.
- Le rapport JSON de taille bornée inclut les 393 noms, le
  groupe par bibliothèque et les preuves. Le terminal affiche
  une synthèse ; le shell de rejeu réalise la **copie automatique
  d'un bilan court** via `clip.exe`, même en cas d'échec.
- Aucun accès au réseau par l'outil lui-même, aucun fichier
  Apple/SoundHack dans GitHub, aucune exécution Mac, installation,
  compilation, écriture Git ou modification de préfixe.
  Le seul fichier produit par l'analyse est le rapport JSON
  **créé exclusivement dans un stage privé neuf**.

## Qualification exécutée

Le 17 novembre 2026 dans l'environnement de développement isolé :

- Compilation syntaxique des deux nouveaux scripts : **PASS**.
- `python3 -B -m unittest discover -s . -p test_sh21_import_closure.py -v` :
  **22/22 PASS**, dont une simulation complète à **393 imports /
  sept fournisseurs** ; autres essais négatifs : empreintes
  incorrectes, ancien rapport altéré, parseur différent,
  chemins symboliques sortants, bibliothèque absente ou non
  Mach-O, désaccord d'identité, import dans le mauvais fournisseur,
  ordinal inconnu, référence non standard, mauvaise architecture,
  doublons nlist et tentative d'écrasement.
- Les Mach-O de test et leurs exports sont **synthétiques et/ou
  simulés**. Le vrai exécutable et le sysroot du 5700X n'étaient
  pas disponibles dans l'environnement de développement.

**Statut publié : `SH21_HOST_TOOL_TEST_PASS_22`.**
**`SH21_REAL_5700X=NOT_RUN`**, `DYLD_BINDING=NOT_TESTED`,
`SH_LOAD=NOT_RUN`, `GUI=NOT_RUN`, `DSP=NOT_RUN`, `AUDIO=NOT_RUN`.

## Répétition ciblée sur le 5700X

Utiliser le bloc Bash autonome donné dans la conversation
(chemins vérifiés, PIN Git source et exécutable, tests synthétiques,
rapport privé exclusif, bilan court au presse-papiers). Origine
historique protégée :
`~/d4wrling-work/validation/soundhack-sh20.3OvPqBmm/replay/`,
sysroot privé B13 en lecture seule. Ne pas lancer dyld ni Darling
avant d'avoir vu la classification du vrai binaire. Identifier
ensuite le **premier groupe concret d'imports** demandant
un test dyld, avec témoin négatif, sans répéter une étude
encyclopédique des autres composants.
