/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-B12-B: run the R1-qualified extractor (qt_mov_pcm.c) natively on a MOV
 * and write the PCM it locates. Usage: extract-native IN.mov OUT.pcm */
#include "qt_mov_pcm.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv)
{
    FILE *f = argc == 3 ? fopen(argv[1], "rb") : NULL;
    long n; unsigned char *mov, *pcm; struct d4rl_qt_mov_pcm_info info; int st;
    if (!f || fseek(f, 0, SEEK_END) || (n = ftell(f)) <= 0 || fseek(f, 0, SEEK_SET)) return 2;
    mov = malloc((size_t)n); pcm = malloc((size_t)n);
    if (!mov || !pcm || fread(mov, 1, (size_t)n, f) != (size_t)n) return 3;
    fclose(f);
    st = d4rl_qt_mov_extract_pcm(mov, (size_t)n, pcm, (size_t)n, &info);
    printf("EXTRACT status=%d format=%08x rate=%u channels=%u bits=%u frames=%u bytes=%zu\n", st, info.format,
           info.sample_rate, info.channels, info.bits_per_sample, info.frame_count, st ? 0 : info.byte_count);
    if (st) return 4;
    f = fopen(argv[2], "wb");
    if (!f || fwrite(pcm, 1, info.byte_count, f) != info.byte_count || fclose(f)) return 5;
    free(mov); free(pcm);
    return 0;
}
