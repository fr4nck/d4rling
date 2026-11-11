// SPDX-License-Identifier: GPL-3.0-or-later
// Reuse the unchanged R1 tests and their original synthetic resource fixtures.
#define main r1_contracts
#include "../carboncore-resource-r1/test.cpp"
#undef main
#include <sys/stat.h>
#include <atomic>
#include <algorithm>
#include <unordered_map>
#include <sys/xattr.h>
#include <glob.h>

// Host-only Apple-style six-argument xattr adapter. Production still calls
// the real Darwin API; these maps never get linked into Darling.
static std::map<std::string, std::vector<uint8_t>> simulatedForks;
static bool denyXattr = false;
static bool simulatedExtraXattr = false;
ssize_t getxattr(const char* path, const char* key, void* bytes,
                 size_t size, unsigned int, int) {
    if (std::strcmp(key,"com.apple.ResourceFork")) { errno=ENODATA; return -1; }
    auto it=simulatedForks.find(path);
    if(it==simulatedForks.end()) { errno=ENODATA; return -1; }
    if(!bytes) return static_cast<ssize_t>(it->second.size());
    if(size < it->second.size()) { errno=ERANGE; return -1; }
    std::memcpy(bytes,it->second.data(),it->second.size());
    return static_cast<ssize_t>(it->second.size());
}
int setxattr(const char* path, const char* key, const void* bytes,
             size_t size, unsigned int, int) {
    if(denyXattr) { errno=ENOSPC; return -1; }
    if(std::strcmp(key,"com.apple.ResourceFork")) { errno=ENOTSUP; return -1; }
    simulatedForks[path]=std::vector<uint8_t>(static_cast<const uint8_t*>(bytes),
                                               static_cast<const uint8_t*>(bytes)+size);
    return 0;
}
ssize_t listxattr(const char*, char*, size_t, int) { return simulatedExtraXattr ? 9 : 0; }
extern "C" OSErr MemError(void) { return noErr; }

static int denyWrite=0, denyRename=0, denySync=0;
static bool shortenNextWrite=false;
extern "C" ssize_t __real_write(int,const void*,size_t);
extern "C" int __real_rename(const char*,const char*);
extern "C" int __real_fsync(int);
extern "C" ssize_t __wrap_write(int fd,const void* bytes,size_t count) {
    if(denyWrite && --denyWrite==0) { errno=ENOSPC; return -1; }
    if (shortenNextWrite && count > 1) { shortenNextWrite=false; return __real_write(fd,bytes,count/2); }
    return __real_write(fd,bytes,count);
}
extern "C" int __wrap_rename(const char* src,const char* dest) {
    if(denyRename && --denyRename==0) { errno=EACCES; return -1; }
    return __real_rename(src,dest);
}
extern "C" int __wrap_fsync(int fd) {
    if(denySync && --denySync==0) { errno=EIO; return -1; }
    return __real_fsync(fd);
}
static std::vector<uint8_t> readBytes(const std::string& file) {
    std::ifstream input(file, std::ios::binary);
    if(!input.good()) throw std::runtime_error("open readBytes");
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(input),std::istreambuf_iterator<char>());
}
static uint32_t load32(const std::vector<uint8_t>& b,size_t pos) {
    return (uint32_t(b.at(pos))<<24)|(uint32_t(b.at(pos+1))<<16)|
           (uint32_t(b.at(pos+2))<<8)|b.at(pos+3);
}

static bool noTemporaryFiles(const std::string& path) {
    glob_t found{};
    const int result=::glob((path+".d4rling-r2-*").c_str(),0,nullptr,&found);
    const bool clean=(result==GLOB_NOMATCH);
    ::globfree(&found);
    return clean;
}

int main() {
    const int r1=r1_contracts();
    CHECK(r1==0);
    const int r1Count=passed;
    auto f=makeFork();
    for(size_t i=16;i<256;i++) f[i]=static_cast<uint8_t>(i^0x5a);
    auto path=makeFile(f);
    struct stat start{}; CHECK(::stat(path.c_str(),&start)==0);
    {
        Resources res(path.c_str(),fsRdWrPerm,false);
        auto* entry=res.data().at(0x53545220).resources.front().get();
        CHECK(entry->getHandle() != nullptr);
        (*entry->getHandle())[0]='R';
        entry->name="renamed";
        entry->id=299;
        entry->attributes=0x24;
        res.setAttributes(0x2345);
        CHECK(res.save()==noErr);
        CHECK(entry->dataBacking==std::vector<uint8_t>({'R','B','C'}));
        auto bytes=readBytes(path);
        CHECK(load32(bytes,0)==256);
        CHECK(load32(bytes,4)==256+7);
        CHECK(load32(bytes,8)==7);
        CHECK(load32(bytes,12)==30+8+12+1+7);
        CHECK(std::equal(bytes.begin()+16,bytes.begin()+256,f.begin()+16));
        CHECK(std::equal(bytes.begin(),bytes.begin()+16,bytes.begin()+load32(bytes,4)));
        CHECK(bytes.size()==load32(bytes,4)+load32(bytes,12));
        auto first=bytes;
        CHECK(res.save()==noErr);
        CHECK(readBytes(path)==first);
        struct stat after{}; CHECK(::stat(path.c_str(),&after)==0);
        CHECK((after.st_mode&07777)==(start.st_mode&07777));
        CHECK(after.st_uid==start.st_uid && after.st_gid==start.st_gid);
    }
    {
        Resources reopened(path.c_str(),fsRdPerm,false);
        CHECK(reopened.attributes()==0x2345);
        auto* entry=reopened.data().at(0x53545220).resources.front().get();
        CHECK(entry->id==299 && entry->name=="renamed");
        CHECK(entry->attributes==0x24);
        CHECK(entry->dataBacking==std::vector<uint8_t>({'R','B','C'}));
        CHECK(reopened.save()==wPrErr);
    }
    // Multiple types, a zero-byte resource and a 255-byte Pascal name.
    {
        Resources res(path.c_str(),fsRdWrPerm,false);
        auto* item=res.data().at(0x53545220).resources.front().get();
        item->name=std::string(255,'z');
        Handle emptyHandle=nullptr;
        CHECK(PtrToHand(nullptr,&emptyHandle,0)==noErr);
        res.add(0x4d454e55,101,"",emptyHandle); // 'MENU'
        CHECK(res.save()==noErr);
    }
    {
        Resources res(path.c_str(),fsRdPerm,false);
        CHECK(res.data().size()==2);
        CHECK(res.data().at(0x4d454e55).resources.front()->dataBacking.empty());
        CHECK(res.data().at(0x4d454e55).resources.front()->name.empty());
        CHECK(res.data().at(0x53545220).resources.front()->name.size()==255);
    }
    // Refusal before any filesystem mutation on structurally invalid data.
    auto before=readBytes(path);
    {
        Resources res(path.c_str(),fsRdWrPerm,false);
        res.data().at(0x53545220).resources.front()->name=std::string(256,'x');
        CHECK(res.save()==mapReadErr);
    }
    CHECK(readBytes(path)==before);
    {
        Resources res(path.c_str(),fsRdWrPerm,false);
        res.data().at(0x53545220).resources.front()->attributes=0x100;
        CHECK(res.save()==mapReadErr);
    }
    CHECK(readBytes(path)==before);
    // No corrupt/partial replacement on write/fsync/rename failures.
    {
        Resources res(path.c_str(),fsRdWrPerm,false);
        auto* entry=res.data().at(0x53545220).resources.front().get();
        (*entry->getHandle())[0]='!';
        denyWrite=1;
        CHECK(res.save()==dskFulErr);
        CHECK(readBytes(path)==before);
        CHECK(noTemporaryFiles(path));
        denySync=1;
        CHECK(res.save()==ioErr);
        CHECK(readBytes(path)==before);
        CHECK(noTemporaryFiles(path));
        denyRename=1;
        CHECK(res.save()==wPrErr);
        CHECK(readBytes(path)==before);
        CHECK(noTemporaryFiles(path));
        shortenNextWrite=true;
        CHECK(res.save()==noErr);
        CHECK(!shortenNextWrite);
        CHECK(readBytes(path)!=before);
        CHECK(noTemporaryFiles(path));
    }
    before=readBytes(path);
    // A directory fsync error is *after* successful rename. Report failure;
    // bytes may already have changed. Do not falsely promise rollback.
    {
        Resources res(path.c_str(),fsRdWrPerm,false);
        (*res.data().at(0x53545220).resources.front()->getHandle())[0]='~';
        denySync=2;
        CHECK(res.save()==ioErr);
        CHECK(readBytes(path)!=before);
        CHECK(noTemporaryFiles(path));
    }
    before=readBytes(path);
    simulatedExtraXattr=true;
    {
        Resources res(path.c_str(), fsRdWrPerm, false);
        CHECK(res.save()==wPrErr);
        CHECK(readBytes(path)==before);
    }
    simulatedExtraXattr=false;
    // The data fork writer may not overwrite through a symlink/hard link.
    const std::string linkPath=path+".hardlink";
    CHECK(::link(path.c_str(),linkPath.c_str())==0);
    {
        Resources res(path.c_str(),fsRdWrPerm,false);
        CHECK(res.save()==wPrErr);
        CHECK(readBytes(path)==before);
    }
    unlink(linkPath.c_str());
    const std::string symPath=path+".symlink";
    CHECK(::symlink(path.c_str(),symPath.c_str())==0);
    {
        Resources res(symPath.c_str(),fsRdWrPerm,false);
        CHECK(res.save()!=noErr);
        CHECK(readBytes(path)==before);
    }
    unlink(symPath.c_str());
    CHECK(::chmod(path.c_str(),0444)==0);
    {
        Resources res(path.c_str(),fsRdWrPerm,false);
        CHECK(res.save()==wPrErr);
    }
    CHECK(::chmod(path.c_str(),start.st_mode&07777)==0);
    CHECK(readBytes(path)==before);
    // On a newly-created resource file, a writable-only instance has no input.
    const std::string newPath=path+".new";
    { std::ofstream out(newPath,std::ios::binary); }
    {
        Resources fresh(newPath.c_str(),fsWrPerm,false);
        CHECK(fresh.save()==noErr);
    }
    {
        Resources check(newPath.c_str(),fsRdPerm,false);
        CHECK(check.data().empty());
        CHECK(check.attributes()==0);
    }
    unlink(newPath.c_str());
    // Resource-fork path must modify only its named xattr and must propagate
    // failure; data fork bytes are preserved byte-for-byte.
    auto xPath=makeFile(makeFork());
    simulatedForks[xPath]=makeFork();
    const auto dataForkBefore=readBytes(xPath);
    const auto xattrBefore=simulatedForks.at(xPath);
    {
        Resources res(xPath.c_str(),fsRdWrPerm,true);
        auto* entry=res.data().at(0x53545220).resources.front().get();
        (*entry->getHandle())[1]='?';
        denyXattr=true;
        CHECK(res.save()==dskFulErr);
        CHECK(simulatedForks.at(xPath)==xattrBefore);
        denyXattr=false;
        CHECK(res.save()==noErr);
        CHECK(simulatedForks.at(xPath)!=xattrBefore);
        CHECK(readBytes(xPath)==dataForkBefore);
    }
    {
        Resources reopened(xPath.c_str(),fsRdPerm,true);
        auto* entry=reopened.data().at(0x53545220).resources.front().get();
        CHECK(entry->dataBacking==std::vector<uint8_t>({'A','?','C'}));
    }
    unlink(xPath.c_str());
    simulatedForks.clear();
    // TB40: partial write changes the disk, not the loaded handle; read
    // partial must consult the disk, not the in-memory handle.
    const auto partialPath=makeFile(makeFork());
    {
        Resources res(partialPath.c_str(),fsRdWrPerm,false);
        Handle h=res.data().at(0x53545220).resources.front()->getHandle();
        CHECK(h!=nullptr && std::memcmp(*h,"ABC",3)==0);
        CHECK(res.writePartial(h,1,"Z",1)==noErr);
        CHECK(std::memcmp(*h,"ABC",3)==0);
        char value='!';
        CHECK(res.readPartial(h,1,&value,1)==noErr && value=='Z');
        CHECK(res.writePartial(h,3,"Q",1)==paramErr);
        CHECK(res.writePartial(h,-1,"Q",1)==paramErr);
        CHECK(res.writePartial(h,0,nullptr,1)==paramErr);
        CHECK(res.readPartial(h,3,&value,1)==paramErr);
        CHECK(res.readPartial(h,0,nullptr,1)==paramErr);
        CHECK(res.readPartial(nullptr,0,&value,1)==resNotFound);
        CHECK(res.writePartial(nullptr,0,"x",1)==resNotFound);
        CHECK(res.readPartial(h,0,&value,0)==noErr);
        CHECK(res.writePartial(h,0,"",0)==noErr);
    }
    {
        Resources verify(partialPath.c_str(),fsRdPerm,false);
        auto* r=verify.data().at(0x53545220).resources.front().get();
        CHECK(r->dataBacking==std::vector<uint8_t>({'A','Z','C'}));
        CHECK(verify.writePartial(r->getHandle(),0,"Q",1)==wPrErr);
    }
    unlink(partialPath.c_str());

    unlink(path.c_str());
    CHECK(live.empty());
    std::printf("CARBONCORE_RESOURCE_R2_HOST: %d PASS, %d FAIL (%d R1 retained)\n",
                passed,failed,r1Count);
    return failed?1:0;
}
