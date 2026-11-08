# Protocole de retour BSD Darwin i386

Ce banc compile le dispatcher de `darling-xnu` avec des noms de symboles
dédiés, puis l'exécute dans un témoin Mach-O i386 avec une table et des
gestionnaires synthétiques. Il vérifie CF/EAX, EDX:EAX pour `lseek`, le
transfert des arguments, la pile et une concurrence limitée aux retours
scalaires. Son mini-stub `jnb`/errno ne remplace pas un test de `cerror`/TLS.

Le [correctif candidat](../../patches/bsd-i386-return-fa29287.patch) s'applique
à **darling-xnu `fa29287aa2f0115271e091f1031f53c9e024005d`**, pas à la racine
du dépôt D4RLING. Il n'est appliqué à aucun sous-module par cette publication.
Le [bilan daté](../../../docs/research/bsd-i386-v3-source-2026-11-08.md)
distingue V3 sur les vrais appels et ce banc du protocole.

## Préparer sans modifier le checkout existant

Shell : **Bash Debian amd64, WSL2 ou Linux x86_64**. Les outils et entrées
doivent déjà être présents : Python 3, Git, Clang/LLVM 19, cctools Darling,
SDK et installation privée cohérente contenant libSystem i386. Aucun SDK,
binaire ou installation n'est fourni ou téléchargé par le banc.

Depuis la racine de cette livraison, choisir une destination neuve et courte :

```bash
work=$(mktemp -d "$HOME/d4rl-bsd.XXXXXX")
python3 reproduction/fixtures/bsd-i386-return/prepare.py \
  --xnu /chemin/du/checkout-xnu-existant \
  --output "$work/source"
```

`prepare.py` lit seulement trois blobs Git locaux et vérifie leurs SHA-256.
Les objets manquants sont une erreur ; aucune récupération réseau implicite.
Le candidat et la référence sont des fichiers réguliers indépendants dans
`source/candidate` et `source/original`. Le patch est vérifié puis appliqué
à la seule copie candidate, et ses trois sorties sont vérifiées par SHA-256.

## Compiler et exécuter explicitement

Lire d'abord `run-tests.sh` et `run-private.sh`. Le point de montage
`/opt/d4rling-qt-i386` doit déjà exister ; le banc ne le crée pas. L'installation
fournie doit correspondre à cette racine interne. Elle est exposée en lecture
seule à cet emplacement dans des namespaces privés user/mount/PID/IPC/UTS/net.
Aucun montage de l'espace de noms de l'hôte n'est modifié.

```bash
BSD_SDK=/chemin/du/MacOSX.sdk \
BSD_LINKER=/chemin/du/x86_64-apple-darwin20-ld \
BSD_INSTALLATION=/chemin/de/installation-privee-coherente \
  bash "$work/source/candidate/tests/bsd-i386-return/run-tests.sh"
```

Chaque série crée ses résultats et des préfixes neufs. Leur longueur est
bornée pour les sockets Unix. Chaque lancement a un délai maximal de 75 s
puis 10 s de terminaison ; aucune élévation globale, aucun sysctl modifié.
Le lien utilise LC_MAIN (minimum 10.9) et une base `__TEXT` 0x10000000.
Les en-têtes restent compilés avec la cible i386 10.6 identifiée dans le
script ; ces choix sont ceux du banc, pas une qualification de tous les OS.

Attendre la dernière ligne **`SOURCE_RETURN_PROTOCOL=PASS`** et un code 0
du runner. `LAST_RESULTS.txt` indique le dossier conservant les journaux,
les quatre codes de sortie, les binaires privés et `validation.json`.
Les préfixes ne font pas partie des preuves publiques.

## Attendus et résultats conservés

| Variante | Code | Contrôles | Échecs attendus/observés |
| --- | ---: | ---: | ---: |
| Source originale, indices hors table omis | 10 | 82 641 | 36 863 |
| Candidat, exécution 1 | 0 | 82 659 | 0 |
| Contre-épreuve délibérément fautive « EAX seul » | 10 | 82 659 | 36 |
| Candidat, exécution 2 | 0 | 82 659 | 0 |

Chaque ligne inclut 8 000 appels sur quatre threads. Les états CF entrants
et les 4 095 erreurs sont couverts par la série, sans croisement exhaustif
de toutes les combinaisons. Les motifs 64 bits synthétiques ne prouvent pas
que toutes ces valeurs sont des succès réels de `lseek`.

`observed-validation.json` conserve le résultat de la campagne source
initiale. `publication-replay.json` conserve le rejeu après remplacement des
chemins personnels par les trois variables explicites ci-dessus ; ses
compteurs doivent être identiques. Le garde-fou de reproduction valide
également CPU Mach-O 7 et l'identité des objets x86_64 avant/après.

Le banc ne qualifie ni la bibliothèque système reconstruite, ni les vrais
retours `lseek`/psynch, `cerror`/TLS, le succès `getattrlist`, les hooks
activés dynamiquement ou le dyld intégré. La table épinglée n'a qu'une
déclaration C de retour 64 bits (`sys_lseek`, numéro 199) ; la classification
doit être réauditée si cette table évolue.

Sources de test originales préparées pour fr4nck avec OpenAI Codex,
GPL-3.0-or-later. Le patch reste soumis aux auteurs et licences du composant
Darling/XNU ; il ne change pas les mentions de licence de ses fichiers.
