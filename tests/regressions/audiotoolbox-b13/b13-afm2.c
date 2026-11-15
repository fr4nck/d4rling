/* SPDX-License-Identifier: GPL-3.0-or-later
 * ATB-FIX3 (positive oracle): format recognition by AudioToolbox once the AudioFile component
 * tables are read with the right property size. Mach-O i386 and x86_64; one sub-command per
 * process. The defect witness b13-afm.c is kept unchanged; expectations are fixed in
 * verify_b13_afm2.py before the candidate runs.
 *
 *   b13-afm2 tables          per type (WAVE, AIFF, AIFC, CAF): ExtensionsForType, UTIsForType,
 *                            MIMETypesForType; AllExtensions, AllUTIs, AllMIMETypes, ReadableTypes;
 *                            the WAVE component asked directly with sizeof(CFArrayRef) (control)
 *   b13-afm2 lookup          TypesForExtension / TypesForUTI / TypesForMIMEType, known and unknown keys
 *   b13-afm2 lookup_empty    TypesForExtension(""), information only (AudioFile.cpp passes the result of
 *                            CFStringGetCStringPtr, which may be NULL, to the manager)
 *   b13-afm2 open B13 FIX3   AudioFileOpenURL with and without a type hint on the B13 media and the
 *                            FIX3 media (AIFF-C, .aif, unknown extension): status, file format, packets
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

static const char *st_str(OSStatus st, char buf[16])
{
    if (!st)
        return "0";
    fourcc((UInt32)st, buf);
    return buf;
}

static void print_strings(const char *key, OSStatus st, CFArrayRef a)
{
    char s[16];
    printf("B13AFM2 %s status=%s count=%ld values=", key, st_str(st, s), (!st && a) ? (long)CFArrayGetCount(a) : -1L);
    for (CFIndex i = 0; !st && a && i < CFArrayGetCount(a); ++i) {
        char b[128] = "?";
        CFStringRef v = (CFStringRef)CFArrayGetValueAtIndex(a, i);
        if (v && CFGetTypeID(v) == CFStringGetTypeID())
            CFStringGetCString(v, b, sizeof b, kCFStringEncodingUTF8);
        printf("%s%s", i ? "," : "", b);
    }
    printf("\n");
}

static void print_types(const char *key, OSStatus st, UInt32 bytes, const UInt32 *t)
{
    char s[16];
    printf("B13AFM2 %s status=%s count=%u values=", key, st_str(st, s), st ? 0u : (unsigned)(bytes / 4));
    for (UInt32 i = 0; !st && i < bytes / 4; ++i) {
        char f[16];
        fourcc(t[i], f);
        printf("%s%s", i ? "," : "", f);
    }
    printf("\n");
}

static void array_for_type(const char *name, AudioFilePropertyID id, UInt32 type)
{
    CFArrayRef a = NULL;
    UInt32 size = sizeof a;
    OSStatus st = AudioFileGetGlobalInfo(id, sizeof type, &type, &size, &a);
    char f[16], key[64];
    fourcc(type, f);
    snprintf(key, sizeof key, "%s_for_%s", name, f);
    print_strings(key, st, a);
    if (a)
        CFRelease(a);
}

static void all_array(const char *key, AudioFilePropertyID id)
{
    CFArrayRef a = NULL;
    UInt32 size = sizeof a;
    OSStatus st = AudioFileGetGlobalInfo(id, 0, NULL, &size, &a);
    print_strings(key, st, a);
    if (a)
        CFRelease(a);
}

static int tables(void)
{
    const UInt32 types[] = { kAudioFileWAVEType, kAudioFileAIFFType, kAudioFileAIFCType, kAudioFileCAFType };
    for (unsigned i = 0; i < sizeof types / sizeof types[0]; ++i) {
        array_for_type("extensions", kAudioFileGlobalInfo_ExtensionsForType, types[i]);
        array_for_type("utis", kAudioFileGlobalInfo_UTIsForType, types[i]);
        array_for_type("mimes", kAudioFileGlobalInfo_MIMETypesForType, types[i]);
    }
    all_array("all_extensions", kAudioFileGlobalInfo_AllExtensions);
    all_array("all_utis", kAudioFileGlobalInfo_AllUTIs);
    all_array("all_mimes", kAudioFileGlobalInfo_AllMIMETypes);

    UInt32 n = 0, t[64];
    OSStatus st = AudioFileGetGlobalInfoSize(kAudioFileGlobalInfo_ReadableTypes, 0, NULL, &n);
    if (!st && n <= sizeof t)
        st = AudioFileGetGlobalInfo(kAudioFileGlobalInfo_ReadableTypes, 0, NULL, &n, t);
    print_types("readable_types", st, n, t);

    /* control: the WAVE component itself, with the right size */
    AudioComponentDescription d = { 'afil', kAudioFileWAVEType, 0, 0, 0 };
    AudioComponent comp = AudioComponentFindNext(NULL, &d);
    AudioComponentInstance inst = NULL;
    if (comp && AudioComponentInstanceNew(comp, &inst) == noErr) {
        CFArrayRef a = NULL;
        UInt32 size = sizeof a;
        st = AudioFileComponentGetGlobalInfo(inst, kAudioFileComponent_ExtensionsForType, 0, NULL, &size, &a);
        print_strings("component_wave_extensions", st, a);
        if (a)
            CFRelease(a);
        AudioComponentInstanceDispose(inst);
    } else
        printf("B13AFM2 component_wave_extensions status=nocomp count=-1 values=\n");
    return 0;
}

static void types_for(const char *kind, AudioFilePropertyID id, const char *value)
{
    CFStringRef s = CFStringCreateWithCString(NULL, value, kCFStringEncodingUTF8);
    UInt32 n = 0, t[64];
    /* the specifier is the CFStringRef itself, of size sizeof(CFStringRef) (public contract) */
    OSStatus st = AudioFileGetGlobalInfoSize(id, sizeof s, (void *)s, &n);
    if (!st && n <= sizeof t)
        st = AudioFileGetGlobalInfo(id, sizeof s, (void *)s, &n, t);
    char key[160];
    snprintf(key, sizeof key, "types_for_%s:%s", kind, *value ? value : "(empty)");
    print_types(key, st, n, t);
    CFRelease(s);
}

static int lookup(void)
{
    const char *ext[] = { "wav", "wave", "aif", "aiff", "aifc", "caf", "zzzq" };
    for (unsigned i = 0; i < sizeof ext / sizeof ext[0]; ++i)
        types_for("extension", kAudioFileGlobalInfo_TypesForExtension, ext[i]);
    const char *uti[] = { "com.microsoft.waveform-audio", "public.aiff-audio", "public.aifc-audio", "org.example.none" };
    for (unsigned i = 0; i < sizeof uti / sizeof uti[0]; ++i)
        types_for("uti", kAudioFileGlobalInfo_TypesForUTI, uti[i]);
    const char *mime[] = { "audio/x-wav", "audio/aiff", "audio/x-none" };
    for (unsigned i = 0; i < sizeof mime / sizeof mime[0]; ++i)
        types_for("mime", kAudioFileGlobalInfo_TypesForMIMEType, mime[i]);
    return 0;
}

static void open1(const char *dir, const char *file, UInt32 hint, const char *key)
{
    char path[1024], s[16], f[16] = "-";
    snprintf(path, sizeof path, "%s/%s", dir, file);
    CFURLRef u = CFURLCreateFromFileSystemRepresentation(NULL, (const UInt8 *)path, strlen(path), false);
    AudioFileID af = NULL;
    OSStatus st = AudioFileOpenURL(u, kAudioFileReadPermission, hint, &af);
    CFRelease(u);
    long long packets = -1;
    if (!st && af) {
        UInt32 type = 0, sz = sizeof type;
        if (AudioFileGetProperty(af, kAudioFilePropertyFileFormat, &sz, &type) == noErr)
            fourcc(type, f);
        UInt64 p = 0;
        sz = sizeof p;
        if (AudioFileGetProperty(af, kAudioFilePropertyAudioDataPacketCount, &sz, &p) == noErr)
            packets = (long long)p;
        AudioFileClose(af);
    }
    printf("B13AFM2 open %s status=%s file_format=%s packets=%lld handle=%s\n", key, st_str(st, s), f, packets, af ? "set" : "null");
}

static int openall(const char *b13, const char *fix3)
{
    open1(b13, "demo-s16.wav", 0, "wav_nohint");
    open1(b13, "demo-s16.wav", kAudioFileWAVEType, "wav_hint_WAVE");
    open1(b13, "demo-s16.wav", kAudioFileAIFFType, "wav_hint_AIFF");
    open1(b13, "demo-s16.aiff", 0, "aiff_nohint");
    open1(b13, "demo-s16.aiff", kAudioFileAIFFType, "aiff_hint_AIFF");
    open1(b13, "demo-s16.aiff", kAudioFileAIFCType, "aiff_hint_AIFC");
    open1(fix3, "demo-s16.aif", 0, "aif_nohint");
    open1(fix3, "demo-s16.aifc", 0, "aifc_nohint");
    open1(fix3, "demo-s16.aifc", kAudioFileAIFCType, "aifc_hint_AIFC");
    open1(fix3, "demo-s16.aifc", kAudioFileAIFFType, "aifc_hint_AIFF");
    open1(b13, "bad-garbage.wav", 0, "garbage_wav_nohint");
    open1(b13, "bad-garbage.wav", kAudioFileWAVEType, "garbage_wav_hint_WAVE");
    open1(b13, "bad-empty.wav", 0, "empty_wav_nohint");
    open1(b13, "bad-trunc.wav", 0, "trunc_wav_nohint");
    open1(fix3, "bad-garbage.zzzq", 0, "garbage_zzzq_nohint");
    open1(fix3, "bad-empty.zzzq", 0, "empty_zzzq_nohint");
    return 0;
}

int main(int argc, char **argv)
{
    printf("B13AFM2_ABI pointer_bits=%zu\n", sizeof(void *) * 8);
    fflush(stdout);
    if (argc == 2 && !strcmp(argv[1], "tables"))
        return tables();
    if (argc == 2 && !strcmp(argv[1], "lookup"))
        return lookup();
    if (argc == 2 && !strcmp(argv[1], "lookup_empty")) {   /* information only, outside the verdict */
        types_for("extension", kAudioFileGlobalInfo_TypesForExtension, "");
        return 0;
    }
    if (argc == 4 && !strcmp(argv[1], "open"))
        return openall(argv[2], argv[3]);
    fprintf(stderr, "usage: b13-afm2 tables | lookup | lookup_empty | open B13_MEDIA FIX3_MEDIA\n");
    return 2;
}
