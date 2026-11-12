// SPDX-License-Identifier: GPL-3.0-or-later
// I2-C1 -- compile/link actual MacMemory.cpp + ResourcesImpl.cpp + Resources.cpp
// through the genuine public CarbonCore/Resources.h. No Resource API stubs.
#include <CarbonCore/Resources.h>
#include <CarbonCore/MacMemory.h>
#include <CarbonCore/MacErrors.h>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/xattr.h>
#include <unistd.h>

static int passed = 0, failed = 0;
#define CHECK(expr) do { if (expr) { ++passed; } else { ++failed; std::fprintf(stderr, "I2C_C1 FAIL line %d: %s\n", __LINE__, #expr); } } while (0)

// Host-only Darwin FSRef/fork-name adapters; real Resource Manager handles all work.
extern "C" OSErr FSRefMakePath(const FSRef* ref, UInt8* dst, UInt32 maxLen) {
    if (!ref || !dst || !maxLen) return paramErr;
    const size_t n = strnlen(ref->path, sizeof(ref->path));
    if (n == sizeof(ref->path) || n >= maxLen) return paramErr;
    std::memcpy(dst, ref->path, n + 1);
    return noErr;
}
extern "C" OSErr FSGetDataForkName(HFSUniStr255* n) {
    if (!n) return paramErr;
    n->length = 4;
    n->unicode[0] = 'd'; n->unicode[1] = 'a'; n->unicode[2] = 't'; n->unicode[3] = 'a';
    return noErr;
}
extern "C" OSErr FSGetResourceForkName(HFSUniStr255* n) {
    if (!n) return paramErr;
    n->length = 4;
    n->unicode[0] = 'r'; n->unicode[1] = 's'; n->unicode[2] = 'r'; n->unicode[3] = 'c';
    return noErr;
}
// Darwin six-argument xattr API is unavailable on Linux; mirror I1's host shims.
ssize_t getxattr(const char*, const char*, void*, size_t, unsigned int, int) { errno = ENODATA; return -1; }
int setxattr(const char*, const char*, const void*, size_t, unsigned int, int) { errno = ENOTSUP; return -1; }
ssize_t listxattr(const char*, char*, size_t, int) { return 0; }
static void put16(std::vector<UInt8>& f, size_t i, uint16_t v) { f.at(i) = v >> 8; f.at(i+1) = v; }
static void put32(std::vector<UInt8>& f, size_t i, uint32_t v) { f.at(i) = v >> 24; f.at(i+1) = v >> 16; f.at(i+2) = v >> 8; f.at(i+3) = v; }
static std::vector<UInt8> makeFork(ResType type, ResID id, const std::string& name, const std::string& body) {
    if (name.size() > 200 || body.size() > 100) throw std::runtime_error("fixture size");
    const size_t d = 256, m = 512, n = 51 + name.size();
    std::vector<UInt8> f(m + n, 0);
    put32(f, 0, d); put32(f, 4, m); put32(f, 8, 4 + body.size()); put32(f, 12, n);
    put32(f, d, body.size()); std::memcpy(f.data()+d+4, body.data(), body.size());
    put16(f, m+22, 0); put16(f, m+24, 28); put16(f, m+26, 50);
    put16(f, m+28, 0); put32(f, m+30, type); put16(f, m+34, 0); put16(f, m+36, 10);
    put16(f, m+38, id); put16(f, m+40, 0); f[m+42] = 0; // attributes
    f[m+50] = name.size(); std::memcpy(f.data()+m+51, name.data(), name.size());
    return f;
}
static std::string makeFile(const std::vector<UInt8>& b) {
    const std::string prefix = std::string(std::getenv("TMPDIR") ? std::getenv("TMPDIR") : "/tmp") + "/d4-i2c-XXXXXX";
    std::vector<char> name(prefix.begin(), prefix.end()); name.push_back(0);
    const int fd = mkstemp(name.data());
    if (fd < 0) throw std::runtime_error("mkstemp");
    size_t pos = 0;
    while (pos < b.size()) {
        const ssize_t n = write(fd, b.data() + pos, b.size() - pos);
        if (n <= 0) { close(fd); unlink(name.data()); throw std::runtime_error("fixture write"); }
        pos += n;
    }
    close(fd);
    return name.data();
}
static void setName(Str255& dest, const std::string& name) {
    std::memset(dest, 0, sizeof(dest)); dest[0] = name.size();
    std::memcpy(dest+1, name.data(), name.size());
}
static FSRef makeRef(const std::string& p) {
    FSRef r{};
    if (p.size() >= sizeof(r.path)) throw std::runtime_error("host path");
    std::memcpy(r.path, p.c_str(), p.size()+1);
    return r;
}
int main() {
    const ResType STR = 0x53545220U, ICON = 0x49434e20U, ABSENT = 0x5a5a5a5aU;
    const std::string p1 = makeFile(makeFork(STR, 128, "alpha", "ABC"));
    const std::string p2 = makeFile(makeFork(ICON, 128, "beta", "XYZ"));
    const FSRef f1 = makeRef(p1), f2 = makeRef(p2);
    ResFileRefNum r1 = kResFileNotOpened, r2 = kResFileNotOpened;
    CHECK(FSOpenResourceFile(&f1, 0, nullptr, fsRdWrPerm, &r1) == noErr && r1 != kResFileNotOpened);
    CHECK(FSOpenResourceFile(&f2, 0, nullptr, fsRdWrPerm, &r2) == noErr && r2 != kResFileNotOpened);
    UseResFile(r1); CHECK(CurResFile() == r1 && ResError() == noErr);
    CHECK(CountResources(STR) == 1 && CountResources(ICON) == 1);
    CHECK(Count1Resources(STR) == 1 && Count1Resources(ICON) == 0);
    Str255 alpha{}, beta{}, gamma{};
    setName(alpha, "alpha"); setName(beta, "beta"); setName(gamma, "gamma");
    Handle h1 = GetResource(STR, 128);
    CHECK(h1 && *h1 && GetHandleSize(h1) == 3 && std::memcmp(*h1,"ABC",3) == 0);
    CHECK(ResError() == noErr);
    Handle h2 = GetResource(ICON, 128);
    CHECK(h2 && *h2 && GetHandleSize(h2) == 3 && std::memcmp(*h2,"XYZ",3) == 0);
    CHECK(GetNamedResource(STR, alpha) == h1);
    CHECK(GetNamedResource(ICON, beta) == h2);
    CHECK(GetResource(STR, 128) == h1 && ResError() == noErr);
    CHECK(Get1Resource(STR, 128) == h1 && ResError() == noErr);
    CHECK(Get1NamedResource(STR, alpha) == h1 && ResError() == noErr);
    CHECK(GetIndResource(STR, 1) == h1 && ResError() == noErr);
    CHECK(GetResource(STR, 999) == nullptr && ResError() == resNotFound);
    CHECK(GetResource(STR, 128) == h1 && ResError() == noErr); // stale last error
    CHECK(GetResource(ABSENT, 999) == nullptr && ResError() == resNotFound); // missing type != missing ID
    CHECK(GetResource(STR, 999) == nullptr && ResError() == resNotFound);
    CHECK(CountResources(STR) == 1 && ResError() == noErr); // count succeeds
    CHECK(GetIndResource(STR, 0) == nullptr && ResError() == inputOutOfBounds);
    UseResFile(r2);
    CHECK(Get1Resource(STR, 128) == nullptr && ResError() == resNotFound);
    CHECK(Get1Resource(ICON, 128) == h2 && ResError() == noErr);
    UseResFile(r1);
    SetResInfo(h1, 129, gamma);
    CHECK(ResError() == noErr);
    CHECK(GetResource(STR, 129) == h1);
    CHECK(GetResource(STR, 128) == nullptr);
    CHECK(GetNamedResource(STR, gamma) == h1);
    CHECK(GetNamedResource(STR, alpha) == nullptr);
    ResID rid = 0; ResType rtype = 0; Str255 actual{};
    GetResInfo(h1, &rid, &rtype, actual);
    CHECK(ResError() == noErr && rid == 129 && rtype == STR && actual[0] == 5 && std::memcmp(actual+1,"gamma",5) == 0);
    CloseResFile(r2); CHECK(ResError() == noErr);
    CloseResFile(r1); CHECK(ResError() == noErr);
    unlink(p1.c_str()); unlink(p2.c_str());
    std::printf("I2C_C1_REAL_THREE_UNITS: %d PASS, %d FAIL\n", passed, failed);
    return failed ? 1 : 0;
}
