# BSD i386 — qualification de contrat sur les vrais stubs XNU

**Date :** 10 novembre 2026. **Base amont :** darlinghq/darling-xnu `ba34c8ac576190d1bbacb6ee6b1903204a576114`.  
**Verdicts distincts :** `UPSTREAM_SOURCE_STATIC=22/22 PASS` ; `LOCAL_MUTATION_TESTS=21/21 PASS` ; `REAL_STUB_MACHO_BUILD=OPEN` ; `DARLING_GUEST_RUNTIME=OPEN`.

## Pourquoi ce contrôle ?

Le témoin I1 précédent reliait le véritable dispatcher assemblé à un **miroir** de conversion `-errno`/CF et à une variable factice d'errno. Cela ne démontrait pas le comportement des macros véritables de XNU. Cette étape lit **sept fichiers authentiques** de XNU et formalise les relations entre leurs différentes branches i386, sans reconstruire ni modifier XNU.

## Sources vérifiées en direct sur GitHub

Les Git blob SHA-1 sont épinglés dans `xnu_stub_contract.py` :

- `gen/bsdsyscalls/SYS.h` — `681a421262ccacce576ee6366a9b484ce73b3b3e`
- `libsyscall/custom/SYS.h` — `ba50e058a9c5dc621580c57522d1afb8bbd54c2a`
- `osfmk/mach/i386/syscall_sw.h` — `175b89252a44670f017ac1542347cb4088832ae2`
- `gen/bsdsyscalls/___lseek.S` — `0089abc6ad57d81593c99688b851056a2092b544`
- `libsyscall/custom/__lseek.S` — `490418f7929be4f132fb6f46089c2dbd2d2e4df8`
- `gen/bsdsyscalls/___sigreturn.S` — `62238b9eda4ffe5fb9d9e3aa4d85ed3b82dba779`
- `libsyscall/custom/__sigaltstack.S` — `7c4fceaf571c99c6ffaf5a666d288ecd32eed694`

**22/22 constats statiques PASS** lors d'une lecture directe des contenus GitHub et empreintes Git : blocs i386 des deux `SYS.h` identiques ; appels ordinaires via `__darling_bsd_syscall` ; conversion `cmpl/cmc/jnc/negl` ; cas `INT` utilisant le macro de piège qui, **sous DARLING**, est lui-même redirigé vers `__darling_bsd_syscall` ; chemins `ULOCK_RAW_SYSCALL` et `__SYSCALL_NOERROR` conservant le retour brut ; `lseek` 64 bits contrôlant `EDX:EAX` ; `sigreturn` et `sigaltstack` utilisant les variantes `INT`. Le `int 0x80` visible dans `syscall_sw.h` appartient **au cas non-Darling** : ne pas l'interpréter comme une régression Darling.

## Outil reproductible et contre-épreuves

- [`xnu_stub_contract.py`](../../reproduction/fixtures/bsd-i386-guard/xnu_stub_contract.py) lit exclusivement les objets Git existants par `git rev-parse` puis `git cat-file`, à la révision fixée. **Aucune modification de checkout ni réseau.** Toute révision ou empreinte absente provoque `BLOCKED_SOURCE` et un code de sortie 3 ; une divergence des règles génère `FAIL` code 10 ; seulement le succès produit `PASS_STATIC` code 0.
- [`test_xnu_stub_contract.py`](../../reproduction/fixtures/bsd-i386-guard/test_xnu_stub_contract.py) : **21/21 PASS**, cas positif et mutations indépendantes sur une fixture textuelle de contrat, dont suppressions `cmc`, changement de seuil, appels `INT` détournés, modification `lseek`, conversion interdite de `NOERROR` et `ULOCK`, et divergence des deux copies de `SYS.h`. Ces tests unitaires sont synthétiques : ils ne relisent pas à eux seuls les vrais fichiers XNU.

Pour réexécuter sur un clone local contenant **déjà** le commit amont exact (aucun téléchargement automatique) :

```bash
python3 -m unittest discover -s reproduction/fixtures/bsd-i386-guard -p 'test_xnu_stub_contract.py' -v
python3 reproduction/fixtures/bsd-i386-guard/xnu_stub_contract.py --xnu /chemin/xnu
```

**La qualification du script Python directement contre un checkout XNU à `ba34c8ac` n'a pas eu lieu dans cet environnement**, qui ne dispose pas des objets locaux de cette révision. La vérification directe amont `22/22` a été effectuée par inspection des fichiers GitHub et de leurs SHA dans cette conversation. Il n'y a eu ni compilation des vrais `SYS.h` et `__lseek.S`, ni lien de `libsystem_kernel.dylib`, ni exécution invitée. Il n'y a pas de nouveau PASS sur Logic 8, QuickTime, Carbon ou CoreAudio.

**Suite :** compiler les stubs i386 issus des sources épinglées avec un banc d'en-têtes minimal en espace privé, puis vérifier `cerror`/TLS et le retour `lseek` 64 bits dans une vraie chaîne Darling. Ne pas fusionner le garde BSD expérimental dans `master` à ce stade.
