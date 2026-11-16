# LOGIC-L2 / GL07 — Carbon i386 chargé avec ses dépendances ELF32 (16 novembre 2026)

**Statut borné : `L2_CARBON_I386_LOAD_PASS`.** Résultat de la campagne GL07 **transmis par l'opérateur depuis le 5700X** ; le témoin et les binaires n'ont pas été rejoués par l'agent publiant cette note.

## Objet et frontière

Le banc LOGIC-L1 s'arrêtait sur FreeType puis Fontconfig, ensuite JPEG et GIF ELF32. GL07 fournit au **vrai témoin Mach-O Darwin i386** un cache Linux ELF32 privé complété par la fermeture Debian de `libgl1:i386`, et charge le véritable `Carbon.framework/Versions/A/Carbon` par `dlopen`, sans supprimer de dépendances ni modifier Carbon ou les wrappers `wrap_elf`.

- **Dépôt public relu avant publication :** `fr4nck/d4rling` branche unique `master@c1e842eafd908bfff2ea377666961e337c1d4cfb`.
- **Checkout historique réellement utilisé par le témoin :** `a007a5399d40868588d8cf7fbba97b726506ffa3`, distinct du `master` public. Pas de rebuild de `master` ni de Logic.
- **Provenance :** banc privé `<L1_STAGE>`, cache `<B13_PRIVATE_FFMPEG>` et couche `<GIF06_STAGE>`, sous `validation/` sur le 5700X ; chemin local du rapport `<L1_STAGE>/logic-l2-gl07.dCekdL5r/result.json`. Les archives Debian sont sélectionnées depuis les index `InRelease` authentifiés, leurs empreintes SHA-256 et métadonnées vérifiées, puis extraites en privé par `dpkg-deb --extract`.
- Aucun `apt install`, changement de `/etc`, architecture étrangère système, écriture dans les préfixes historiques ni modification de B12/B13. Le `ld.so.cache` privé est monté pour la seule exécution dans le namespace isolé.

## Résultat réellement observé

```text
PREFLIGHT=PASS L1_HEAD=a007a5399d40868588d8cf7fbba97b726506ffa3
GL_CLOSURE=47 PACKAGES
REUSED_PACKAGES=22 B13 + 0 biarch
DOWNLOAD_PLAN=25 archives 51398300 bytes
DOWNLOADED=25 HTTPS_DEBIAN_ARCHIVES
GL_ELF32=VERIFIED SHA256=04919c97da536dc4b536f8a20787a722de202d4873ac6ef3b602fc3b1c64946a
PRIVATE_CACHE=VERIFIED SHA256=9a6e38626d0cea271cca99ec37fee23281a8a30671fe9cfbcd4d92e5177e4d6d
RUNNER_RC=0 GUEST_RC=0
NEXT_MISSING_ELF=NONE_OBSERVED
LOGIC_L1_PROBE pointer_size=4
DEPENDENCY_LOAD_PASS /System/Library/Frameworks/Carbon.framework/Versions/A/Carbon
STATUS=L2_CARBON_I386_LOAD_PASS
CLEANUP=PASS INTEGRITY=UNCHANGED
EXIT_CODE=0
```

**25 archives nouvelles :** `libdrm-amdgpu1`, `libdrm-intel1`, `libedit2`, `libelf1t64`, `libgbm1`, `libgl1`, `libgl1-mesa-dri`, `libglvnd0`, `libglx-mesa0`, `libglx0`, `libllvm19`, `libpciaccess0`, `libsensors5`, `libtinfo6`, `libvulkan1`, `libwayland-server0`, `libxcb-glx0`, `libxcb-present0`, `libxcb-randr0`, `libxcb-sync1`, `libxcb-xfixes0`, `libxshmfence1`, `libxxf86vm1`, `libz3-4`, `mesa-libgallium`.

Le témoin est revenu à `0` et a annoncé `DEPENDENCY_LOAD_PASS` sur Carbon. Les contrôles de nettoyage et d'intégrité sont `PASS` / `UNCHANGED`. L'échec antérieur GIF06 est conservé sous `<GIF06_STAGE>`, avec `GUEST_RC=134` et manque `libGL.so.1` ; il s'agit d'une référence négative **historique**, sans rejeu lors de GL07.

## Ce que cette qualification ne démontre pas

- **Aucun lancement de Logic Pro 8**, chargement de son binaire principal, de ses plug-ins, de ses ressources privées, ni de projet audio.
- Le seul `dlopen` Carbon ne qualifie **ni AppKit/Cocoa**, ni `NSApplication`, ni la création d'une fenêtre, ni le rendu OpenGL, ni l'utilisation de CoreAudio, AudioToolbox, MIDI ou Audio Units.
- Un préfixe L1 d'origine historique et le cache B13 privé ne constituent **pas un build intégré de `master` actuel**. Tout test sur Logic devra refaire le prévol source/build/préfixe et respecter les limites de droits et de ressources.
- Le graphe inventorié de Logic Pro 8.0 build 800B237 comprend **40 images directes** (39 fortes, 1 faible), environ 2 398 imports et une surface Cocoa importante : cf. [inventaire L1](2026-11-14-logic-l1.md). Le bundle complet et les fournitures Cocoa restent non qualifiés.

## Décision : passage au prochain obstacle utile

**Clore le sous-objectif « chargement Carbon i386 »**. La suite ne consiste pas à poursuivre les téléchargements ELF32 sans trace d'erreur : faire le prévol ciblé du **chargement Cocoa/AppKit** et des images fortes du graphe Logic, dans le banc privé, sans exécuter encore l'application originale. Vérifier les sources et l'installation réellement présentes avant toute préparation. Aucun correctif QuickTime, CoreAudio, PulseAudio, GL ou Carbon n'est justifié par GL07.

[Précédent L1 / FreeType et Fontconfig](2026-11-14-logic-l1-elf32.md). Les journaux complets, l'installation privée, les archives Debian et les éventuels fichiers propriétaires ne sont pas publiés. Cette note est une transcription synthétique de résultats opérateur, pas une exécution indépendante par GitHub.
