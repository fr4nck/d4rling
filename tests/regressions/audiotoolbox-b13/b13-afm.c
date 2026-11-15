/* SPDX-License-Identifier: GPL-3.0-or-later
 * B13 defect 3 (test only): AudioFileFormatManager reads the CFArrayRef properties of the
 * AudioFile components (UTIs, MIME types, extensions) with a size left at sizeof(UInt32).
 * Mach-O i386 and x86_64; one sub-command per process.
 *
 *   b13-afm component   the WAVE component itself, through the public AudioFileComponent API:
 *                       kAudioFileComponent_ExtensionsForType asked with size 4 and with
 *                       sizeof(CFArrayRef); FileTypeName as a positive control
 *   b13-afm tables      the AudioFile global tables built from the components:
 *                       ReadableTypes, ExtensionsForType/UTIsForType/MIMETypesForType(WAVE, AIFF),
 *                       AllExtensions/AllUTIs/AllMIMETypes
 *   b13-afm ext EXT     kAudioFileGlobalInfo_TypesForExtension(EXT)
 *   b13-afm open MEDIA  AudioFileOpenURL without a type hint, and with one, on demo-s16.aiff
 *                       and bad-garbage.wav (file format or error code)
 * Expectations are fixed before the runs in verify_b13_afm.py.
 */
#include <AudioToolbox/AudioToolbox.h>
#include <AudioToolbox/AudioFileComponent.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <string.h>

static void fourcc(UInt32 v, char out[16])
{
    char c[4] = { (char)(v >> 24), (char)(v >> 16), (char)(v >> 8), (char)v };
    bool ok = true;
    for (int i = 0; i < 4; ++i)
        ok &= c[i] >= 32 && c[i] < 127;
    if (ok)
        snprintf(out, 16, "%c%c%c%c", c[0], c[1], c[2], c[3]);
    else
        snprintf(out, 16, "%d", (int)v);
}

static void print_array(const char *key, OSStatus st, UInt32 size, CFArrayRef a)
{
    char s[16];
    fourcc((UInt32)st, s);
    printf("B13AFM %s status=%s size=%u count=%ld values=", key, st ? s : "0", (unsigned)size, a ? (long)CFArrayGetCount(a) : -1L);
    for (CFIndex i = 0; a && i < CFArrayGetCount(a); ++i) {
        char buf[128] = "";
        CFStringGetCString((CFStringRef)CFArrayGetValueAtIndex(a, i), buf, sizeof buf, kCFStringEncodingUTF8);
        printf("%s%s", i ? "," : "", buf);
    }
    printf("\n");
    fflush(stdout);
}

static int component(void)
{
    AudioComponentDescription d = {};
    d.componentType = 'afil';
    d.componentSubType = kAudioFileWAVEType;
    AudioComponent comp = AudioComponentFindNext(NULL, &d);
    printf("B13AFM component_found=%d\n", comp != NULL);
    if (!comp)
        return 3;
    AudioFileComponent inst = NULL;
    OSStatus st = AudioComponentInstanceNew(comp, &inst);
    printf("B13AFM instance_new=%d\n", (int)st);
    if (st)
        return 4;

    CFStringRef name = NULL;
    UInt32 size = sizeof name;
    st = AudioFileComponentGetGlobalInfo(inst, kAudioFileComponent_FileTypeName, 0, NULL, &size, &name);
    char buf[128] = "";
    if (name)
        CFStringGetCString(name, buf, sizeof buf, kCFStringEncodingUTF8);
    printf("B13AFM control_filetypename status=%d size=%u name=%s\n", (int)st, (unsigned)size, buf);

    /* the size AudioFileFormatManager passes (left at sizeof(UInt32) by CanRead/CanWrite) */
    CFArrayRef a = NULL;
    size = sizeof(UInt32);
    st = AudioFileComponentGetGlobalInfo(inst, kAudioFileComponent_ExtensionsForType, 0, NULL, &size, &a);
    print_array("component_extensions_size4", st, size, st ? NULL : a);
    /* the size of the property */
    a = NULL;
    size = sizeof(CFArrayRef);
    st = AudioFileComponentGetGlobalInfo(inst, kAudioFileComponent_ExtensionsForType, 0, NULL, &size, &a);
    print_array("component_extensions_sizeof_cfarrayref", st, size, st ? NULL : a);
    a = NULL;
    size = sizeof(CFArrayRef);
    st = AudioFileComponentGetGlobalInfo(inst, kAudioFileComponent_UTIsForType, 0, NULL, &size, &a);
    print_array("component_utis_sizeof_cfarrayref", st, size, st ? NULL : a);
    printf("B13AFM sizeof_cfarrayref=%zu\n", sizeof(CFArrayRef));
    AudioComponentInstanceDispose(inst);
    return 0;
}

static int tables(void)
{
    UInt32 size = 0;
    OSStatus st = AudioFileGetGlobalInfoSize(kAudioFileGlobalInfo_ReadableTypes, 0, NULL, &size);
    UInt32 types[256];
    UInt32 n = sizeof types;
    if (!st)
        st = AudioFileGetGlobalInfo(kAudioFileGlobalInfo_ReadableTypes, 0, NULL, &n, types);
    printf("B13AFM readable_types status=%d count=%u values=", (int)st, st ? 0u : (unsigned)(n / 4));
    for (UInt32 i = 0; !st && i < n / 4; ++i) {
        char s[16];
        fourcc(types[i], s);
        printf("%s%s", i ? "," : "", s);
    }
    printf("\n");
    static const struct { UInt32 id; const char *key; } per[] = {
        { kAudioFileGlobalInfo_ExtensionsForType, "extensions" },
        { kAudioFileGlobalInfo_UTIsForType, "utis" },
        { kAudioFileGlobalInfo_MIMETypesForType, "mimes" },
    };
    static const struct { UInt32 type; const char *name; } ft[] = { { kAudioFileWAVEType, "WAVE" }, { kAudioFileAIFFType, "AIFF" } };
    for (unsigned t = 0; t < 2; ++t)
        for (unsigned p = 0; p < 3; ++p) {
            CFArrayRef a = NULL;
            UInt32 type = ft[t].type, sz = sizeof a;
            st = AudioFileGetGlobalInfo(per[p].id, sizeof type, &type, &sz, &a);
            char key[64];
            snprintf(key, sizeof key, "%s_for_%s", per[p].key, ft[t].name);
            print_array(key, st, sz, st ? NULL : a);
        }
    static const struct { UInt32 id; const char *key; } all[] = {
        { kAudioFileGlobalInfo_AllExtensions, "all_extensions" },
        { kAudioFileGlobalInfo_AllUTIs, "all_utis" },
        { kAudioFileGlobalInfo_AllMIMETypes, "all_mimes" },
    };
    for (unsigned p = 0; p < 3; ++p) {
        CFArrayRef a = NULL;
        UInt32 sz = sizeof a;
        st = AudioFileGetGlobalInfo(all[p].id, 0, NULL, &sz, &a);
        print_array(all[p].key, st, sz, st ? NULL : a);
    }
    return 0;
}

static int ext(const char *e)
{
    CFStringRef s = CFStringCreateWithCString(NULL, e, kCFStringEncodingUTF8);
    UInt32 types[64], n = sizeof types;
    /* the specifier is the CFStringRef itself, of size sizeof(CFStringRef) (public contract) */
    OSStatus st = AudioFileGetGlobalInfo(kAudioFileGlobalInfo_TypesForExtension, sizeof s, (void *)s, &n, types);
    printf("B13AFM types_for_extension ext=%s status=%d count=%u values=", e, (int)st, st ? 0u : (unsigned)(n / 4));
    for (UInt32 i = 0; !st && i < n / 4; ++i) {
        char c[16];
        fourcc(types[i], c);
        printf("%s%s", i ? "," : "", c);
    }
    printf("\n");
    CFRelease(s);
    return 0;
}

static void open1(const char *media, const char *file, AudioFileTypeID hint, const char *key)
{
    char path[4096];
    snprintf(path, sizeof path, "%s/%s", media, file);
    CFURLRef u = CFURLCreateFromFileSystemRepresentation(NULL, (const UInt8 *)path, (CFIndex)strlen(path), false);
    AudioFileID af = NULL;
    OSStatus st = AudioFileOpenURL(u, kAudioFileReadPermission, hint, &af);
    CFRelease(u);
    UInt32 fmt = 0, sz = sizeof fmt;
    if (!st)
        AudioFileGetProperty(af, kAudioFilePropertyFileFormat, &sz, &fmt);
    char s[16], f[16];
    fourcc((UInt32)st, s);
    fourcc(fmt, f);
    printf("B13AFM open %s status=%s file_format=%s\n", key, st ? s : "0", st ? "-" : f);
    if (af)
        AudioFileClose(af);
    fflush(stdout);
}

int main(int argc, char **argv)
{
    printf("B13AFM_ABI pointer_bits=%zu\n", sizeof(void *) * 8);
    fflush(stdout);
    if (argc == 2 && !strcmp(argv[1], "component"))
        return component();
    if (argc == 2 && !strcmp(argv[1], "tables"))
        return tables();
    if (argc == 3 && !strcmp(argv[1], "ext"))
        return ext(argv[2]);
    if (argc == 3 && !strcmp(argv[1], "open")) {
        open1(argv[2], "demo-s16.aiff", 0, "aiff_nohint");
        open1(argv[2], "demo-s16.aiff", kAudioFileAIFFType, "aiff_hint_AIFF");
        open1(argv[2], "demo-s16.wav", 0, "wav_nohint");
        open1(argv[2], "bad-garbage.wav", 0, "garbage_wav_nohint");
        open1(argv[2], "bad-garbage.wav", kAudioFileWAVEType, "garbage_wav_hint_WAVE");
        return 0;
    }
    fprintf(stderr, "usage: b13-afm component|tables|ext EXT|open MEDIA\n");
    return 2;
}
