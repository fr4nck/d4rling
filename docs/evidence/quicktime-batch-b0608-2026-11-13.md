# D4rling — B06–B08, jonction QuickTime → HAL B14 → FIFO privé (13 novembre 2026)

**Statut courant : `BATCH_B0608_BLOCKED` en `PHASE=SOURCE`.** Le résultat transmis vient du terminal Debian WSL2 sur le 5700X, sans reproduction sur GitHub. Ce n'est **pas** un résultat d'exécution CoreAudio.

## Contrat et précautions

- B06 : enregistrer un callback `AudioDeviceIOProc` réel auprès de la HAL B14 i386 ; convertir les données du MOV synthétique QuickTime C3 8 kHz / S16 big-endian mono vers Float32LE stéréo 44,1 kHz et fournir 16 callbacks × 1024 trames.
- B07 : utiliser le pont `libpulse-B14.dylib` et les FIFO **avec récepteur Python privé**, sans serveur PulseAudio, et mesurer 16 paquets de 8192 octets.
- B08 : oracle Python indépendant (flux 131072 octets, FNV64 `627f9a49f841751d` et SHA256 `553c73503849bc2a6e809ba7e61b011496f2a4a1dc4f5ab989d079b0832a0a5e`), fermeture de la HAL et du transport.
- C10 B14 et la cible du chantier audio AUD-C11-A1 ne doivent pas être modifiés. Toute écriture seulement dans un dossier de validation neuf ; aucune installation, suppression, réseau, écriture Git ni sortie sonore.

## Résultat du premier lancement

```text
LOCAL_HEAD=5b521087d79d4348ebe312e622a05f1f8b55c110
LOCAL_STATUS:
 m src/external/security
 M src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c
B0305_INPUT=PASS
C10_MOCK_SOURCE=FOUND
STOP=EXPECTED_SINGLE_MAIN
STATUS=BATCH_B0608_BLOCKED
PHASE=SOURCE COMPILE_EXIT=NOT_RUN LINK_EXIT=NOT_RUN GUEST_EXIT=NOT_RUN MOCK_EXIT=NOT_RUN
PROTECTED_INPUTS=UNCHANGED
```

Répertoire d'essai local conservé : `/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI/qt-batch-b0608.WdoeSyuV`, rapport `result.json`.

**Diagnostic confirmé par le texte du générateur et les sources du lot précédent :** le générateur B06 attend exactement `int main(void)\n{` dans `B03–B05/batch.c` alors que la fonction a été introduite comme `int main(void) {`. Le sélecteur de source est donc trop strict ; rien ne prouve un problème de compilation, de la HAL, de dyld ou de FIFO. La prochaine campagne doit sélectionner le seul `main` avec une expression régulière ancrée qui accepte les espaces/retours ligne, refuser toute ambiguïté, puis exécuter une **nouvelle** campagne isolée. Ne pas modifier le résultat bloqué.

**État de vérité :** B03–B05 R1 reste `PASS`. B06 `NOT_RUN` ; B07 `NOT_RUN` ; B08 `NOT_RUN`. `COREAUDIO_WITH_QUICKTIME=NOT_TESTED`, `PULSEAUDIO_SERVER=NOT_USED`, `AUDIO=NOT_TESTED`, `LOGIC8=NOT_TESTED`.

Le fait que le script avait prévu un hôte Python privé ne démontre pas la prise en charge réelle de l'ABI de transport : elle doit être testée séparément, notamment les réponses RPC, le chargement de CoreAudio-B14, le comportement du FIFO et la fermeture de flux.
