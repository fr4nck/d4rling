/* SPDX-License-Identifier: GPL-3.0-or-later
 * AUDIO-I386 control: inert ELF32 marker so that a private ld.so.cache differs from the
 * host cache only by this entry; proves which cache the bench namespace really reads.
 *   gcc -m32 -shared -fPIC -Wl,-soname,libd4rlingldcmarker.so.1 -o marker/libd4rlingldcmarker.so.1 ldc-marker.c
 *   printf '%s\ninclude /etc/ld.so.conf\n' "$PWD/marker" > ld.so.conf
 *   /sbin/ldconfig -X -i -C ld.so.cache -f ld.so.conf
 */
int d4rling_ldcache_marker(void) { return 42; }
