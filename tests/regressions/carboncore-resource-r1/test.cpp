// SPDX-License-Identifier: GPL-3.0-or-later
// Host contracts: real ResourcesImpl.cpp, a test-only MacMemory adapter.
#include "ResourcesImpl.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cerrno>
#include <map>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>
#include <fstream>
#include <unistd.h>

static int passed = 0, failed = 0;
#define CHECK(x) do { if (x) ++passed; else { ++failed; std::fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); } } while (0)
static std::map<Handle, size_t> live;
static bool failNextHandle = false;
extern "C" OSErr PtrToHand(const void* data, Handle* out, long length) {
    if (!out || length < 0 || (length && !data)) return -50;
    if (failNextHandle) { failNextHandle=false; return -108; }
    auto handle = static_cast<Handle>(std::malloc(sizeof(Ptr)));
    if (!handle) return -108;
    *handle = static_cast<Ptr>(std::malloc(length ? size_t(length) : 1));
    if (!*handle) { std::free(handle); return -108; }
    if (length) std::memcpy(*handle, data, length);
    *out = handle;
    live[handle] = size_t(length);
    return noErr;
}
extern "C" void DisposeHandle(Handle h) {
    if (!h) return;
    if (live.erase(h)) { std::free(*h); std::free(h); }
}
extern "C" long GetHandleSize(Handle h) {
    auto it = live.find(h);
    return it == live.end() ? -1 : long(it->second);
}

static void put16(std::vector<uint8_t>& f, size_t at, uint16_t v) {
    if (at+2 > f.size()) throw std::runtime_error("put16");
    f[at] = uint8_t(v>>8); f[at+1] = uint8_t(v);
}
static void put32(std::vector<uint8_t>& f, size_t at, uint32_t v) {
    if (at+4 > f.size()) throw std::runtime_error("put32");
    f[at] = uint8_t(v>>24); f[at+1] = uint8_t(v>>16);
    f[at+2] = uint8_t(v>>8); f[at+3] = uint8_t(v);
}
static std::vector<uint8_t> makeFork(size_t nameLength=4, bool emptyMap=false) {
    const size_t d=256, m=512;
    const size_t n=emptyMap ? 30 : 50+1+nameLength;
    std::vector<uint8_t> f(m+n, 0);
    put32(f,0,uint32_t(d)); put32(f,4,uint32_t(m));
    put32(f,8,7); put32(f,12,uint32_t(n));
    put32(f,d,3); f[d+4]='A'; f[d+5]='B'; f[d+6]='C';
    put16(f,m+22,0x0123); put16(f,m+24,28);
    put16(f,m+26,emptyMap ? 30 : 50);
    if (emptyMap) { put16(f,m+28,0xffff); return f; }
    put16(f,m+28,0); // one type
    put32(f,m+30,0x53545220); // STR<space>
    put16(f,m+34,0); // one resource
    put16(f,m+36,10); // reference list relative to type-list count
    put16(f,m+38,128); put16(f,m+40,0); // resource id and name offset
    f[m+42]=0x20; // resource attributes
    f[m+43]=0; f[m+44]=0; f[m+45]=0; // resource data offset 0
    f[m+50]=uint8_t(nameLength);
    for (size_t i=0; i<nameLength; ++i) f[m+51+i] = char('a'+i%26);
    return f;
}

// Two resources of the same type verify reference-list offsets, independent
// data offsets, and the resource map's first-match id/name indexes.
static std::vector<uint8_t> makeTwo() {
    auto f=makeFork();
    f.resize(512+74, 0);
    put32(f,8,15); put32(f,12,74);
    put32(f,256+7,4); f[256+11]='W'; f[256+12]='X';
    f[256+13]='Y'; f[256+14]='Z';
    put16(f,512+34,1); // two resources, same 'STR ' type
    put16(f,512+26,62); // names now follow two reference records
    put16(f,512+50,129); put16(f,512+52,5);
    f[512+54]=0x08;
    f[512+55]=0; f[512+56]=0; f[512+57]=7;
    f[512+62]=4;
    std::memcpy(f.data()+512+63, "abcd", 4);
    f[512+67]=6;
    std::memcpy(f.data()+512+68, "second", 6);
    return f;
}

static std::string makeFile(const std::vector<uint8_t>& f) {
    const char* tmp = std::getenv("TMPDIR");
    if (!tmp) tmp = "/tmp";
    std::string pattern=std::string(tmp)+"/d4rl-rsrc-r1-XXXXXX";
    std::vector<char> name(pattern.begin(), pattern.end());
    name.push_back('\0');
    int fd = mkstemp(name.data());
    if (fd < 0) throw std::runtime_error("mkstemp");
    size_t written = 0;
    while (written < f.size()) {
        ssize_t n = ::write(fd, f.data()+written, f.size()-written);
        if (n <= 0) { close(fd); unlink(name.data()); throw std::runtime_error("write"); }
        written += size_t(n);
    }
    close(fd);
    return name.data();
}
static bool rejects(const std::vector<uint8_t>& bytes) {
    std::string path=makeFile(bytes);
    try { Resources resource(path.c_str(), 1, false); unlink(path.c_str()); return false; }
    catch (OSErr e) { unlink(path.c_str()); return e==eofErr; }
    catch (...) { unlink(path.c_str()); throw; }
}

int main() {
    auto fork=makeFork();
    const size_t baselineLive=live.size();
    {
        std::string path=makeFile(fork);
        Resources res(path.c_str(),1,false);
        unlink(path.c_str());
        CHECK(res.attributes()==0x0123);
        CHECK(res.data().size()==1);
        auto it = res.data().find(0x53545220);
        CHECK(it!=res.data().end());
        if (it!=res.data().end()) {
            CHECK(it->second.resources.size()==1);
            auto* entry=it->second.resources.front().get();
            CHECK(entry->id==128);
            CHECK(entry->name=="abcd");
            CHECK(entry->attributes==0x20);
            CHECK(entry->dataBacking==std::vector<uint8_t>({'A','B','C'}));
            Handle h=entry->getHandle();
            CHECK(h && *h);
            CHECK(h && GetHandleSize(h)==3);
            CHECK(h && std::memcmp(*h,"ABC",3)==0);
            CHECK(res.dataByHandle(h)==entry);
            res.remove(h);
            CHECK(res.dataByHandle(h)==nullptr);
            CHECK(it->second.resources.empty());
            CHECK(GetHandleSize(h)==3);  // detached, still owned by caller
            if (GetHandleSize(h)==3)
                CHECK(std::memcmp(*h,"ABC",3)==0);
            else
                CHECK(false);  // guard intentionally avoids deref of dead handle
            DisposeHandle(h);
        }
    }
    CHECK(live.size()==baselineLive);
    // Read two real resources with distinct IDs, names, data blocks and sizes.
    auto a = makeTwo();
    {
        std::string path=makeFile(a);
        Resources res(path.c_str(),1,false);
        unlink(path.c_str());
        auto& group=res.data().at(0x53545220);
        CHECK(group.resources.size()==2);
        CHECK(group.idMap.size()==2);
        CHECK(group.nameMap.size()==2);
        auto* second=group.idMap.at(129);
        CHECK(second->name=="second" && second->attributes==0x08);
        CHECK(second->dataBacking==std::vector<uint8_t>({'W','X','Y','Z'}));
        CHECK(second->getHandle() && GetHandleSize(second->getHandle())==4);
        CHECK(std::memcmp(*second->getHandle(),"WXYZ",4)==0);
        CHECK(group.nameMap.at("second")==second);
    }
    CHECK(live.size()==baselineLive);
    a=makeTwo(); put16(a,512+50,128); CHECK(rejects(a));  // duplicate resource ID
    a=makeTwo(); a[512+57]=100; CHECK(rejects(a)); // second data offset OOB
    a=makeTwo(); put32(a,12,61); CHECK(rejects(a)); // truncated second list/name
    a=makeFork(); put16(a,512+38,0xffff);
    {
        std::string path=makeFile(a);
        Resources res(path.c_str(),1,false);
        unlink(path.c_str());
        CHECK(res.data().at(0x53545220).resources.front()->id==-1);
    }
    a=makeFork(); put32(a,256,0); put32(a,8,4);
    {
        std::string path=makeFile(a);
        Resources res(path.c_str(),1,false);
        unlink(path.c_str());
        auto* entry=res.data().at(0x53545220).resources.front().get();
        CHECK(entry->dataBacking.empty());
        CHECK(entry->getHandle() && GetHandleSize(entry->getHandle())==0);
    }
    a=makeFork();
    Resources::setCreateHandles(false);
    {
        std::string path=makeFile(a);
        Resources res(path.c_str(),1,false);
        unlink(path.c_str());
        CHECK(res.handleMap().empty());
        auto* entry=res.data().at(0x53545220).resources.front().get();
        CHECK(entry->getHandle() && GetHandleSize(entry->getHandle())==3);
        CHECK(res.dataByHandle(entry->getHandle())==entry);
    }
    Resources::setCreateHandles(true);
    // Handle allocation failure must leave lookup/cache intact and permit retry.
    Resources::setCreateHandles(false);
    {
        std::string path=makeFile(a);
        Resources res(path.c_str(),1,false);
        unlink(path.c_str());
        auto* entry=res.data().at(0x53545220).resources.front().get();
        failNextHandle=true;
        CHECK(entry->getHandle()==nullptr);
        CHECK(res.handleMap().empty());
        Handle recovered=entry->getHandle();
        CHECK(recovered!=nullptr && res.dataByHandle(recovered)==entry);
        (*recovered)[0]='Z';
        entry->dataChanged();
        CHECK(entry->dataBacking[0]=='Z');
    }
    Resources::setCreateHandles(true);
    CHECK(live.size()==baselineLive);
    CHECK(rejects({}));
    CHECK(rejects(std::vector<uint8_t>(15,0)));
    a=fork; put32(a,4,0xffffffff); CHECK(rejects(a));
    a=fork; put32(a,12,0xffffffff); CHECK(rejects(a));
    a=fork; put32(a,0,0xffffffff); CHECK(rejects(a));
    a=fork; put32(a,8,0xffffffff); CHECK(rejects(a));
    a=fork; put32(a,12,29); CHECK(rejects(a));
    a=fork; put16(a,512+24,0xffff); CHECK(rejects(a));
    a=fork; put16(a,512+26,0xffff); CHECK(rejects(a));
    a=fork; put16(a,512+28,0xfffe); CHECK(rejects(a));
    a=fork; put16(a,512+36,0xffff); CHECK(rejects(a));
    a=fork; put16(a,512+34,0xffff); CHECK(rejects(a));
    a=fork; put16(a,512+40,0xfffe); CHECK(rejects(a));
    a=fork; put16(a,512+40,4); CHECK(rejects(a));
    a=fork; a[512+50]=250; CHECK(rejects(a));
    a=fork; a[512+43]=0xff; a[512+44]=0xff; a[512+45]=0xff; CHECK(rejects(a));
    a=fork; put32(a,256,0xffffffff); CHECK(rejects(a));
    a=fork; put32(a,8,3); CHECK(rejects(a));
    a=fork; put16(a,512+24,27); CHECK(rejects(a));
    a=fork; put32(a,4,540); CHECK(rejects(a));
    a=makeFork(200);
    {
        std::string path=makeFile(a);
        Resources res(path.c_str(),1,false);
        unlink(path.c_str());
        auto* entry=res.data().at(0x53545220).resources.front().get();
        CHECK(entry->name.size()==200);
        CHECK(entry->name[199]=='r');
    }
    a=makeFork(0);
    {
        std::string path=makeFile(a);
        Resources res(path.c_str(),1,false);
        unlink(path.c_str());
        CHECK(res.data().at(0x53545220).resources.front()->name.empty());
    }
    a=makeFork(4,true);
    {
        std::string path=makeFile(a);
        Resources res(path.c_str(),1,false);
        unlink(path.c_str());
        CHECK(res.data().empty());
        CHECK(res.attributes()==0x0123);
    }
    // Unnamed resource has 0xffff name-list offset (no extra bytes accessed).
    a=makeFork(); put16(a,512+40,0xffff);
    {
        std::string path=makeFile(a);
        Resources res(path.c_str(),1,false);
        unlink(path.c_str());
        CHECK(res.data().at(0x53545220).resources.front()->name.empty());
    }
    CHECK(live.empty());
    try { Resources missing("/d4rl-rsrc-r1-does-not-exist-ephemeral-xyz",1,false); CHECK(false); }
    catch (OSErr e) { CHECK(e==fnfErr); }
    std::printf("CARBONCORE_RESOURCE_R1_HOST: %d PASS, %d FAIL\n",passed,failed);
    return failed?1:0;
}
