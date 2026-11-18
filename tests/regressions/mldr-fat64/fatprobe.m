/* FAT64 / issue #18 : témoin invité. Affiche l'architecture de la tranche que mldr a choisie. */
#include <stdio.h>
#include <unistd.h>
int main(void) {
#if defined(__x86_64__)
    const char *a = "x86_64";
#elif defined(__i386__)
    const char *a = "i386";
#else
    const char *a = "other";
#endif
    printf("FATPROBE arch=%s pointer_bits=%d pid_ok=%d\n", a, (int) (8 * sizeof(void *)), getpid() > 0);
    return 0;
}
