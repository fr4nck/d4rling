/* R4-D: isolated host smoke for the opt-in loader diagnostic macro.
 * Compile three modes with -std=c11 -Wall -Wextra -Werror:
 *   gcc -std=c11 -Wall -Wextra -Werror -DGEN_32BIT -DD4RLING_MLDR_I386_MMAP_DIAG reproduction/fixtures/bsd-i386-r4-d-mmap-diag-smoke.c -o /tmp/r4d-on
 *   gcc -std=c11 -Wall -Wextra -Werror -DGEN_32BIT reproduction/fixtures/bsd-i386-r4-d-mmap-diag-smoke.c -o /tmp/r4d-off
 *   gcc -std=c11 -Wall -Wextra -Werror -DD4RLING_MLDR_I386_MMAP_DIAG reproduction/fixtures/bsd-i386-r4-d-mmap-diag-smoke.c -o /tmp/r4d-noni386
 * No guest execution. Macro copied from src/startup/mldr/loader.c;
 * this is NOT a full loader build. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
struct synthetic_segment { char segname[16]; unsigned long vmaddr; };
#if defined(GEN_32BIT) && defined(D4RLING_MLDR_I386_MMAP_DIAG)
#define MLDR_MMAP_DIAG(branch, seg, address, length, slide, flags) do { int mldr_diag_saved_errno = errno; fprintf(stderr, "MLDR_I386_MMAP_DIAG branch=%s segment=%.16s requested=%p length=%zu slide=0x%lx vmaddr=0x%lx flags=0x%x errno=%d\n", branch, (seg)->segname, (void*)(uintptr_t)(address), (size_t)(length), (unsigned long)(slide), (unsigned long)(seg)->vmaddr, (unsigned int)(flags), mldr_diag_saved_errno); errno = mldr_diag_saved_errno; } while (0)
#else
#define MLDR_MMAP_DIAG(branch, seg, address, length, slide, flags) ((void)0)
#endif
int main(void) {
  struct synthetic_segment seg = {"__TEXT", 0x1000};
  errno = 13;
  MLDR_MMAP_DIAG("file-backed", &seg, 0x401000UL, 4096UL, 0x400000UL, 0x12);
  return seg.vmaddr != 0x1000 || errno != 13;
}
