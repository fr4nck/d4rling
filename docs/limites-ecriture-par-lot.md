# Limites d'écriture par chantier

Annexe de [AGENTS.md](../../AGENTS.md) (§3). Ces répertoires sont des
**périmètres candidats** : le contrat de tâche retient une liste de fichiers
précise, et leur mention ici n'autorise pas leur modification collective.

| Lot | Écritures isolables | Limites / coordination nécessaire |
| --- | --- | --- |
| R-A1 / R-A2 | Note dédiée `docs/research/`, nouvelles fixtures `reproduction/fixtures/` | Lecture seule des binaires installés ; pas de modification mldr, dyld, libSystem/XNU, libgcc ou C2 sans mission de correction |
| U-A1 | Tests dédiés `tests/regressions/carbon-*/`, note datée | Production `src/frameworks/Carbon/`, interfaces publiques et Cocotron partagés ; attribution requise |
| A-A1 | Note `docs/evidence/`, nouveau banc isolé `experiments/` hors `experiments/petite-victoire/` | Préserver `src/CoreAudio/`, HAL, PulseAudio, pont ELF/IPC et acquis B11–C10 ; pas de nouveau backend implicite |
| M-A1 / M-A2 | Nouveaux tests MIDI et AU dans des sous-dossiers distincts de `tests/regressions/` | `src/frameworks/CoreMIDI/`, Component Manager et AudioUnit partagés ; contrôler ABI et durée de vie |
| Q-A1 | Témoin `tests/regressions/quicktime-*/`, média synthétique défini par source originale, note de preuve | Corrections attribuées seulement dans `src/frameworks/QuickTime/` / `QTKit/` ; aucun Player/codec propriétaire publié |
| L-A1 | Synthèse expurgée `docs/audits/logic-studio-8/` | DVD, Logic, banques et frameworks privés en lecture seule ; **pas de lancement sans autorisation explicite** (voir « Priorité courante » dans AGENTS.md) |
| P — réservé au responsable du projet | Aucune écriture autonome dans `experiments/petite-victoire/` | Intervention uniquement sur demande explicite et ciblée du responsable ; les agents travaillent sur le socle D4RLING et leurs témoins séparés |
| Intégration documentaire | `ROADMAP.md`, `AGENTS.md`, `PROJECT_STATE.md`, liens README | Un intégrateur ; actualiser les conclusions sans réécrire les anciens rapports |

Ne pas changer hors mission : CMake racine, CI, packaging, dépendances,
révisions de sous-modules, verrous de reproduction, snapshots et correctifs
historiques. Les snapshots conservent la source historique ; un correctif
nouveau reçoit sa propre provenance.
