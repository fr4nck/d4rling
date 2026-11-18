/* R6 — Carbon windows from 'WIND' resources (Mach-O i386/x86_64, C).
 *
 * Writes a classic resource file (data fork) holding 'WIND' 128 (visible document window, MacRoman
 * title, refCon), 'wctb' 128 (content colour), 'WIND' 129 (invisible), 'WIND' 130 (title longer than
 * the resource), opens it with FSOpenResFile and calls GetNewCWindow as the Window Manager reference
 * describes it: a real WindowRef built from the resource, or NULL when it cannot be read.
 *   carbon-window [HOLD_SECONDS]   prints CW_CHECK lines, CW_HOLD while the windows exist, CW_RESULT
 */
#include <CoreServices/CoreServices.h>
#include <HIToolbox/MacWindows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int checks, failures;
#define CHECK(cond, what) do { checks++; if (cond) printf("CW_CHECK PASS %s\n", what); \
    else { failures++; printf("CW_CHECK FAIL %s (line %d)\n", what, __LINE__); } } while (0)

static void be16(unsigned char *p, unsigned v) { p[0] = v >> 8; p[1] = v; }
static void be32(unsigned char *p, unsigned long v) { p[0] = v >> 24; p[1] = v >> 16; p[2] = v >> 8; p[3] = v; }

struct res { unsigned long type; short id; const unsigned char *data; unsigned len; };

/* Classic resource file: header, data area at 256, map after the data */
static int writeResourceFile(const char *path, const struct res *r, int n) {
    unsigned char buf[4096];
    memset(buf, 0, sizeof buf);
    unsigned dataOff = 256, pos = dataOff, offs[16];
    for (int i = 0; i < n; i++) {
        offs[i] = pos - dataOff;
        be32(buf + pos, r[i].len);
        memcpy(buf + pos + 4, r[i].data, r[i].len);
        pos += 4 + r[i].len;
    }
    unsigned dataLen = pos - dataOff, mapOff = pos;
    /* distinct types in order of appearance */
    unsigned long types[8]; int ntypes = 0;
    for (int i = 0; i < n; i++) {
        int seen = 0;
        for (int t = 0; t < ntypes; t++) if (types[t] == r[i].type) seen = 1;
        if (!seen) types[ntypes++] = r[i].type;
    }
    unsigned typeListOff = 28, m = mapOff + typeListOff;
    be16(buf + m, ntypes - 1);
    unsigned refList = 2 + ntypes * 8;      /* relative to the type list */
    for (int t = 0; t < ntypes; t++) {
        int count = 0;
        for (int i = 0; i < n; i++) if (r[i].type == types[t]) count++;
        unsigned char *e = buf + m + 2 + t * 8;
        be32(e, types[t]);
        be16(e + 4, count - 1);
        be16(e + 6, refList);
        for (int i = 0; i < n; i++) {
            if (r[i].type != types[t]) continue;
            unsigned char *ref = buf + m + refList;
            be16(ref, (unsigned short) r[i].id);
            be16(ref + 2, 0xFFFF);              /* no name */
            ref[4] = 0;                          /* attributes */
            ref[5] = offs[i] >> 16; ref[6] = offs[i] >> 8; ref[7] = offs[i];
            refList += 12;
        }
    }
    unsigned mapLen = typeListOff + refList;
    unsigned char hdr[16];
    be32(hdr, dataOff); be32(hdr + 4, mapOff); be32(hdr + 8, dataLen); be32(hdr + 12, mapLen);
    memcpy(buf, hdr, 16);
    memcpy(buf + mapOff, hdr, 16);           /* copy of the header at the start of the map */
    be16(buf + mapOff + 24, typeListOff);    /* offset to type list */
    be16(buf + mapOff + 26, mapLen);         /* offset to name list (empty) */
    FILE *f = fopen(path, "wb");
    if (!f) return -1;
    size_t total = mapOff + mapLen;
    int ok = fwrite(buf, 1, total, f) == total;
    fclose(f);
    return ok ? 0 : -1;
}

static void windRes(unsigned char *w, unsigned *len, short top, short left, short bottom, short right,
                    short procID, int visible, int goAway, unsigned long refCon, const char *title, int titleLenOverride) {
    be16(w, top); be16(w + 2, left); be16(w + 4, bottom); be16(w + 6, right);
    be16(w + 8, procID);
    w[10] = visible; w[11] = 0; w[12] = goAway; w[13] = 0;
    be32(w + 14, refCon);
    size_t t = strlen(title);
    w[18] = titleLenOverride >= 0 ? titleLenOverride : (unsigned char) t;
    memcpy(w + 19, title, t);
    *len = 19 + t;
    if (*len & 1) w[(*len)++] = 0;           /* align */
    be16(w + *len, 0); *len += 2;            /* positioning: none */
}

int main(int argc, char **argv) {
    int hold = argc > 1 ? atoi(argv[1]) : 0;
    setvbuf(stdout, NULL, _IONBF, 0);
    /* MacRoman 0xA5 is U+2022 BULLET */
    static const char title128[] = "SoundHack R6 \xA5 WIND 128";
    unsigned char w128[300], w129[300], w130[300];
    unsigned l128, l129, l130;
    windRes(w128, &l128, 60, 80, 260, 400, 0 /* documentProc */, 1, 1, 0x52364F4BUL, title128, -1);
    windRes(w129, &l129, 100, 120, 220, 360, 4 /* noGrowDocProc */, 0, 0, 7, "Invisible 129", -1);
    windRes(w130, &l130, 10, 10, 50, 50, 0, 1, 1, 0, "short", 200);   /* title runs past the resource */
    l130 = 19 + 5;
    static const unsigned char wctb128[] = { 0,0,0,0, 0,0, 0,0, /* seed, flags, size 0 -> 1 entry */
        0,0, 0x20,0x00, 0x80,0x00, 0xC0,0x00 };                    /* wContentColor */
    struct res r[] = {
        { 'WIND', 128, w128, l128 }, { 'wctb', 128, wctb128, sizeof wctb128 },
        { 'WIND', 129, w129, l129 }, { 'WIND', 130, w130, l130 },
    };
    const char *path = "/tmp/r6-carbon-window.rsrc";
    if (writeResourceFile(path, r, 4) != 0) { printf("CW_FATAL cannot write %s\n", path); return 3; }

    FSRef ref;
    OSStatus st = FSPathMakeRef((const UInt8 *) path, &ref, NULL);
    ResFileRefNum rf = st == noErr ? FSOpenResFile(&ref, fsRdPerm) : -1;
    CHECK(st == noErr && rf > 0, "resource file opened");
    if (rf <= 0) { printf("CW_RESULT checks=%d failures=%d\n", checks, failures + 1); return 1; }
    UseResFile(rf);

    WindowRef w = GetNewCWindow(128, NULL, (WindowRef) -1);
    CHECK(w != NULL, "GetNewCWindow(128) returns a window");
    if (!w) { printf("CW_RESULT checks=%d failures=%d\n", checks, failures); return 1; }
    CHECK(IsValidWindowPtr(w), "WindowRef is valid");
    CHECK(IsWindowVisible(w), "visible flag of 'WIND' 128 honoured");
    Str255 t; GetWTitle(w, t);
    CHECK(t[0] == strlen(title128) && memcmp(t + 1, title128, t[0]) == 0, "GetWTitle returns the MacRoman title");
    CFStringRef cf = NULL;
    CHECK(CopyWindowTitleAsCFString(w, &cf) == noErr && cf && CFStringFind(cf, CFSTR("•"), 0).location == 13,
          "CFString title decodes MacRoman 0xA5 as U+2022");
    if (cf) CFRelease(cf);
    CHECK((unsigned long) GetWRefCon(w) == 0x52364F4BUL, "refCon from the resource");
    Rect b; CHECK(GetWindowBounds(w, kWindowContentRgn, &b) == noErr && b.top == 60 && b.left == 80
          && b.bottom == 260 && b.right == 400, "content bounds from the resource");
    WindowClass c = 0; WindowAttributes a = 0;
    CHECK(GetWindowClass(w, &c) == noErr && c == kDocumentWindowClass, "documentProc gives a document window");
    CHECK(GetWindowAttributes(w, &a) == noErr && (a & kWindowCloseBoxAttribute), "goAwayFlag gives a close box");
    RGBColor col; CHECK(GetWindowContentColor(w, &col) == noErr && col.red == 0x2000 && col.green == 0x8000
          && col.blue == 0xC000, "'wctb' content colour applied");

    WindowRef w2 = GetNewCWindow(129, NULL, NULL);
    CHECK(w2 != NULL && !IsWindowVisible(w2), "GetNewCWindow(129) creates an invisible window");
    CHECK(GetWindowClass(w2, &c) == noErr && c == kDocumentWindowClass && GetWindowAttributes(w2, &a) == noErr
          && !(a & kWindowCloseBoxAttribute) && !(a & kWindowResizableAttribute), "noGrowDocProc without close box");
    SetWTitle(w2, (ConstStr255Param) "\x0eRenamed window");
    GetWTitle(w2, t);
    CHECK(t[0] == 14 && memcmp(t + 1, "Renamed window", 14) == 0, "SetWTitle / GetWTitle round trip");
    ShowWindow(w2);
    CHECK(IsWindowVisible(w2), "ShowWindow maps the window");

    CHECK(GetNewCWindow(130, NULL, (WindowRef) -1) == NULL, "malformed 'WIND' 130 gives NULL");
    CHECK(GetNewCWindow(131, NULL, (WindowRef) -1) == NULL, "missing 'WIND' 131 gives NULL");
    CHECK(!IsValidWindowPtr((WindowRef) &b), "a foreign pointer is not a window");

    printf("CW_HOLD seconds=%d\n", hold);
    if (hold > 0) sleep(hold);

    DisposeWindow(w2);
    CHECK(!IsValidWindowPtr(w2), "DisposeWindow invalidates the WindowRef");
    DisposeWindow(w);
    CloseResFile(rf);
    unlink(path);
    printf("CW_RESULT checks=%d failures=%d\n", checks, failures);
    return failures ? 1 : 0;
}
