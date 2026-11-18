# Cocotron ABI25-R2 — recherche bornee des artefacts historiques

**17 novembre 2026.** Transcription de l'**observation de terminal fournie par l'operateur** du 5700X (Debian WSL2). Ce bilan n'a **pas** ete rejoue sur GitHub Actions ni par le connecteur GitHub. Il porte sur un seul snapshot prive ; le statut `SCRIPT_RC=0` indique que l'inventaire s'est termine, **pas** que le patch a ete retrouve ou que le port est integre.

## Perimetre exact de ABI25-R2

- Source inspectee : `/home/Deniel/d4wrling-work/validation/cocotron-abi-dyn-01-20261115/d2-abi15-source-r3.p7aJjo`.
- Revision Cocotron locale constatee : `c8d38d16a9f613d300157bebbab2b9501bc0c274` ; fichiers suivis propres (`TRACKED_SOURCE_CLEAN=True`).
- Snapshot : **1 966 fichiers reguliers** ; un `AppKitIvarLayout.h` et un oracle `tests/appkit-legacy-instance-sizes.m` identifies.
- Recherche SHA-256 exhaustive **pour les fichiers reguliers de ce snapshot** : 1 966/1 966 fichiers haches, 30,8 Mio lus, aucune erreur, aucun depassement de budget, aucune recherche partielle.
- `PATCH_SHA256_MATCH=False` ; `MANIFEST_SHA256_MATCH=False`. **Aucun artefact aux empreintes recherchees n'a ete retrouve dans ce perimetre uniquement.** Cette absence n'etablit ni la perte du patch, ni l'absence du manifeste dans un autre dossier de validation.
- `PATCH_PARSE=NOT_RUN`, `TARGET_REBASE_REQUIRED=True` dans la decision locale `PORTED_SOURCE_PRESENT_PATCH_RECOVERY_REQUIRED`.
- Aucune construction, installation, execution invitee, publication de correctif ou nouveau prefixe ; reseau, suppression et ecritures de source/Git interdits. `SCRIPT_RC=0`, `CLIPBOARD=PASS`.
- Bilan de reference conserve sous : `/home/Deniel/d4wrling-work/validation/cocotron-abi-dyn-01-20261115/ABI25-R2.hld9nQpy.txt`. Son contenu integral n'est pas depose ici ; l'observation est delimitee aux lignes du compte rendu transmises.

## Articulation avec la revue ABI25 ulterieure

**Ce checkpoint de recherche est anterieur et est depasse, pour la provenance du port, par la [revue ABI25](cocotron-abi25-port-review-2026-11-17.md)** publiee au commit `af00e2c20d96a3c22a259174fea2b5f05f6a3b13`. Cette revue plus large a qualifie le manifeste des **76 fichiers adaptes** (SHA-256 `fd5433ed4b1ded8606d6a9ead9ec8bf8bc5d4034f588fac6b17ee84a67d3effc`) et le **patch adapte** (SHA-256 `b35db80c2de0b1f0cbe2bcf766ac6e39906ccc30659dea206986cbc8b7c5a195`), ainsi que l'integrite du snapshot complet de **1 983 entrees**. Les 1 966 fichiers reguliers de R2 et les 1 983 entrees du snapshot de la revue n'etaient pas des perimetres identiques.

En consequence, **ne pas traiter `PATCH_SHA256_MATCH=False` de R2 comme un manque d'artefact encore ouvert** et ne pas reconstituer un patch de memoire. La decision technique a jour est differente : **`INTEGRATION=HOLD_FOR_ATOMIC_ACCESSORS_FIX`**.

La revue a demontre un ecart d'atomicite i386 sur `NSMenuItem.view` : les macros `NS_EXTRA_SYNTHESIZE_RETAIN` et `NS_EXTRA_SYNTHESIZE_COPY` utilisent des getters/setters directs alors que le contrat public de la propriete est atomique. Les verifications ABI24 positives (87 assertions par cas) restent qualifiees sur leurs cas sequentiels seulement ; elles ne valident pas la concurrence.

## Suite autorisee et limites

1. Partir de la revue ABI25 et du manifeste/patch qu'elle a epingles, **sans ecraser** les preuves ABI19-ABI24, le snapshot original, B13 ou le gitlink canonique.
2. En candidat **prive**, qualifier le stockage des extras i386, la publication initiale du bloc, le getter retenu et les setters retain/copy lorsque plusieurs threads accedent au meme objet. Ne pas rendre les proprietes nonatomic pour masquer la regression.
3. Concevoir des essais positifs et negatifs qui detectent concretement le retrait de la synchronisation, puis verifier a nouveau les ABI i386/x86_64 et les 87 assertions existantes.
4. Pas d'integration de production, nouveau build canonique ou affirmation de correction tant que ces preuves ne sont pas produites et relues.

**Cette publication est strictement documentaire.** Elle ajoute le jalon ABI25-R2, en preservant la conclusion plus recente d'ABI25 ; aucun test, correction ou changement de code n'est revendique.
