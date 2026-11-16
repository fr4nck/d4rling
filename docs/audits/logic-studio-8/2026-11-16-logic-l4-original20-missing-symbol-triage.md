# LOGIC-L4 / ORIGINAL20 — triage statique de 511 imports non retrouvés (16 novembre 2026)

**Verdict borné : `L4_ORIGINAL20_MISSING_SYMBOL_TRIAGE_PASS`.** Journal du terminal communiqué par le responsable sur le 5700X ; non rejoué par l'agent rédacteur. **Ce verdict ne signifie pas que les APIs manquantes sont qualifiées à l'exécution.** Aucun binaire propriétaire ou liste brute d'imports de Logic n'a été publié.

## Sources et périmètre

- ORIGINAL19 : 511 instances d'imports requis sur 23 bibliothèques B13 non retrouvées dans la table statique du fournisseur attendu, après recoupement des réexports.
- ORIGINAL20 a relu **93 images Mach-O i386** de l'installation B13 privée : les 23 fournisseurs directs de Logic et les images du sous-graphe ORIGINAL17 (76 images, chevauchement entre ensembles). 139 020 096 octets lus dans le lot, aucune anomalie de lecture ou modification observée.
- Lecteur d'audit L1 `macho_reader.py` épinglé par SHA-256 ; 21/21 graines de ORIGINAL17 retrouvent leur empreinte.
- Rapport privé détaillé : `<L1_STAGE>/logic-l4-original20.a5Ad4Nbu/result.json`. Les 511 noms complets restent uniquement sur le poste local.

## Bilan transmis

```text
PREFLIGHT=PASS
READER_PIN=PASS
MISSING_INPUT=511
MISSING_UNIQUE_NAMES=511
SOURCE_IMAGE_CANDIDATES=93
SOURCE_IMAGES_PARSED=93
SOURCE_BYTES_READ=139020096
SOURCE_R17_SEED_MATCH=21/21
MISSING_OBJC_CLASS=4
MISSING_OBJC_OTHER=0
MISSING_CPP_EH=31
MISSING_C_OTHER=476
ALTERNATE_IN_DIRECT_B13=2
ALTERNATE_IN_SUBGRAPH_B13=13
NO_MATCH_IN_SCANNED_B13=496
CONTRADICTION_OWN_EXPORT=0
INTEGRITY=UNCHANGED
STATUS=L4_ORIGINAL20_MISSING_SYMBOL_TRIAGE_PASS
NEXT_GATE=SELECT_TARGETED_NATIVE_LOOKUP
EXIT_CODE=0
```

La classification de 511 imports dans l'ensemble analysé est **disjointe** : 2 noms ont un export statique dans un autre fournisseur direct de Logic, 13 dans le sous-graphe supplémentaire, **496 noms n'ont aucun export statique retrouvé** dans ces 93 images. **La présence d'un nom dans une autre image ne démontre pas sa résolution par le `dyld` de Logic (two-level namespace).**

### Concentration des écarts

| Fournisseur direct de Logic | Instances non trouvées au fournisseur | Alternative B13 | Toujours non retrouvé |
|---|---:|---:|---:|
| Carbon | 219 | 0 | 219 |
| CoreServices | 140 | 0 | 140 |
| DiscRecording | 69 | 0 | 69 |
| AddressBook | 12 | 12 dans le sous-graphe | 0 |
| Tous les autres | 71 | 3 | 68 |
| **Total** | **511** | **15** | **496** |

`MISSING_UNIQUE_NAMES=511` : chaque instance manquante de ORIGINAL19 possède dans ce lot un nom distinct. Familles comptées dans l'ensemble : **476 C/autres**, **31 C++/gestion des exceptions**, **4 noms de classes Objective-C**. La classification ne tranche pas les anciens alias ObjC, les symboles à double préfixe C/C++ ni les dépendances natives ELF32.

## Implications et prochaine expérience

Le triage concentre le chantier sur **trois bibliothèques** : Carbon, CoreServices et DiscRecording totalisent 428 des 496 absences dans l'ensemble de 93 images. Avant d'écrire des stubs ou corriger des symboles, qualifier sur le runtime Darling i386 en namespace privé :
1. un **témoin positif** de `dlopen` / `dlsym` sur CoreFoundation et, si possible, un symbole déjà présent dans chaque bibliothèque cible ;
2. un **témoin négatif** de nom inexistant ;
3. le résultat `dlopen` de Carbon, CoreServices et DiscRecording, puis `dlsym` d'une petite sélection de leurs noms manquants.
4. les codes invités, empreintes, montages/résidus et l'usage du cache ELF32 privé déjà qualifié ; aucune exécution du logiciel Logic ni de frameworks originaux Apple.

Le texte principal L1 documente que `_Unwind_Resume` était statiquement absent mais résolu lors d'un essai natif ; cela interdit d'inférer un défaut à partir de la seule table statique. Un `dlsym` positif dans une bibliothèque donnée **ne prouve pas** à lui seul la résolution des imports directs de Logic ou la compatibilité de leurs signatures.

[ORIGINAL19](2026-11-16-logic-l4-original19-b13-export-inventory.md) · [ORIGINAL18](2026-11-16-logic-l4-original18-direct-provenance.md).
