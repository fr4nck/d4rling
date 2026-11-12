/*
This file is part of Darling.

Copyright (C) 2020 Lubos Dolezel

Darling is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Darling is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Darling.  If not, see <http://www.gnu.org/licenses/>.
*/
#include "ResourcesImpl.h"
#include <CarbonCore/MacErrors.h>
#include <stdexcept>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/xattr.h>
#include <memory>
#include <cstring>
#include <limits>
#include <cstdlib>
#include <cstdio>
#include <cerrno>
#include <algorithm>
#include <sys/stat.h>
#include <sys/types.h>

// Resource fork format: a 16-byte big-endian file header, a data section,
// and a resource map with type/reference/name lists. The type list starts
// with a 16-bit count; reference offsets are relative to the type-list start.
// See Inside Macintosh: More Macintosh Toolbox, Resource Manager, 1-123.
namespace {
bool inRange(size_t offset, size_t count, size_t length)
{
    return offset <= length && count <= length - offset;
}

uint16_t be16(const uint8_t* p)
{
    return (uint16_t(p[0]) << 8) | p[1];
}
uint32_t be24(const uint8_t* p)
{
    return (uint32_t(p[0]) << 16) | (uint32_t(p[1]) << 8) | p[2];
}
uint32_t be32(const uint8_t* p)
{
    return (uint32_t(p[0]) << 24) | (uint32_t(p[1]) << 16)
        | (uint32_t(p[2]) << 8) | p[3];
}
}

bool Resources::m_createHandles = true;

Resources::Resources(const char* file, SInt8 openMode, bool resourceFork)
: m_file(file), m_resourceFork(resourceFork), m_openMode(openMode), m_attributes(0)
{
    if (openMode != fsWrPerm)
        loadResources();
    else
        m_prefix.assign(256, 0);
}

void Resources::loadResources()
{
    if (!m_resourceFork)
    {
        int fd = ::open(m_file.c_str(), O_RDONLY);
        if (fd == -1)
            throw OSErr(fnfErr);
        off_t size = ::lseek(fd, 0, SEEK_END);
        if (size <= 0 || static_cast<uintmax_t>(size) > std::numeric_limits<size_t>::max())
        {
            ::close(fd);
            throw OSErr(eofErr);
        }
        void* map = mmap(nullptr, static_cast<size_t>(size), PROT_READ, MAP_PRIVATE, fd, 0);
        ::close(fd);
        if (map == MAP_FAILED)
            throw OSErr(fnfErr);
        try
        {
            loadResources(static_cast<const uint8_t*>(map), static_cast<size_t>(size));
            ::munmap(map, static_cast<size_t>(size));
        }
        catch (...)
        {
            ::munmap(map, static_cast<size_t>(size));
            throw;
        }
    }
    else
    {
        ssize_t size = ::getxattr(m_file.c_str(), "com.apple.ResourceFork", nullptr, 0, 0, 0);
        if (size <= 0)
            throw OSErr(eofErr);
        std::unique_ptr<uint8_t[]> bytes(new uint8_t[static_cast<size_t>(size)]);
        ssize_t actual = ::getxattr(m_file.c_str(), "com.apple.ResourceFork", bytes.get(), static_cast<size_t>(size), 0, 0);
        if (actual < 0)
            throw OSErr(eofErr);
        loadResources(bytes.get(), static_cast<size_t>(actual));
    }
}

Resources::ResourceData::ResourceData(ResourceData&& that)
{
    id = that.id;
    type = that.type;
    name = std::move(that.name);
    dataBacking = std::move(that.dataBacking);
    attributes = that.attributes;
    data = that.data;
    parent = that.parent;
    that.data = nullptr;
}

Resources::ResourceData::ResourceData(Handle inData)
{
    this->data = inData;
    dataChanged();
}

Resources::ResourceData::~ResourceData()
{
    if (data)
        DisposeHandle(data);
}

Handle Resources::ResourceData::getHandle(bool loadData)
{
    if (dataBacking.size() > static_cast<size_t>(std::numeric_limits<long>::max()))
        return nullptr;
    if (!data)
    {
        Handle newHandle = nullptr;
        if (!loadData)
        {
            // SetResLoad(FALSE): retain a real master pointer but do not
            // populate its data until LoadResource or auto-loading is enabled.
            newHandle = NewEmptyHandle();
        }
        else if (PtrToHand(dataBacking.empty() ? nullptr : dataBacking.data(),
                           &newHandle, static_cast<long>(dataBacking.size())) != noErr)
        {
            return nullptr;
        }
        if (!newHandle)
            return nullptr;
        data = newHandle;
        parent->m_handleMap.insert({data, this});
    }
    else if (loadData && !*data)
    {
        // A purged resource keeps its master pointer. Rehydrate the same
        // Handle from its resource backing instead of returning an empty one.
        ReallocateHandle(data, static_cast<Size>(dataBacking.size()));
        if (MemError() != noErr || !*data)
            return nullptr;
        if (!dataBacking.empty())
            std::memcpy(*data, dataBacking.data(), dataBacking.size());
    }
    return data;
}

void Resources::ResourceData::releaseHandle(bool freeMemory)
{
    if (data)
    {
        if (freeMemory)
            DisposeHandle(data);
        parent->m_handleMap.erase(data);
        data = nullptr;
    }
}

bool Resources::ResourceData::snapshot(std::vector<uint8_t>& out) const
{
    if (!data || !*data) {
        out = dataBacking;
        return true;
    }
    const long count = GetHandleSize(data);
    if (count < 0 || MemError() != noErr)
        return false;
    if (!count) {
        out.clear();
        return true;
    }
    out.assign(reinterpret_cast<const uint8_t*>(*data),
               reinterpret_cast<const uint8_t*>(*data) + count);
    return true;
}

void Resources::ResourceData::dataChanged()
{
    if (!data || !*data)
        return;
    long size = GetHandleSize(data);
    if (size <= 0)
    {
        if (size == 0)
            dataBacking.clear();
        return;
    }
    dataBacking.assign(reinterpret_cast<const uint8_t*>(*data),
                       reinterpret_cast<const uint8_t*>(*data) + size);
}

void Resources::loadResources(const uint8_t* mem, size_t length)
{
    m_resourceTypes.clear();
    m_handleMap.clear();
    m_attributes = 0;
    if (!mem || !inRange(0, 16, length))
        throw OSErr(eofErr);

    const size_t dataOffset = be32(mem);
    const size_t mapOffset = be32(mem + 4);
    const size_t dataLength = be32(mem + 8);
    const size_t mapLength = be32(mem + 12);
    if (!inRange(dataOffset, dataLength, length) ||
        !inRange(mapOffset, mapLength, length) || mapLength < 30)
        throw OSErr(eofErr);

    if (dataOffset < 16)
        throw OSErr(eofErr);
    m_prefix.assign(mem, mem + dataOffset);

    const uint8_t* map = mem + mapOffset;
    m_attributes = static_cast<ResFileAttributes>(be16(map + 22));
    const size_t typeOffset = be16(map + 24);
    const size_t nameOffset = be16(map + 26);
    if (!inRange(typeOffset, 2, mapLength) || nameOffset > mapLength)
        throw OSErr(eofErr);

    const size_t numTypesField = be16(map + typeOffset);
    const size_t numTypes = numTypesField == 0xffff ? 0 : numTypesField + 1;
    if (numTypes > (mapLength - typeOffset - 2) / 8)
        throw OSErr(eofErr);

    for (size_t i = 0; i < numTypes; ++i)
    {
        const size_t typePos = typeOffset + 2 + i * 8;
        const uint32_t type = be32(map + typePos);
        const size_t count = static_cast<size_t>(be16(map + typePos + 4)) + 1;
        const size_t refOffset = be16(map + typePos + 6);
        if (refOffset > mapLength - typeOffset ||
            count > (mapLength - typeOffset - refOffset) / 12)
            throw OSErr(eofErr);

        ResourceTypeData typeData;
        typeData.type = type;
        for (size_t j = 0; j < count; ++j)
        {
            const uint8_t* reference = map + typeOffset + refOffset + j * 12;
            ResourceData res;
            res.id = static_cast<ResID>(be16(reference));
            const size_t nameRel = be16(reference + 2);
            res.attributes = static_cast<ResAttributes>(reference[4]);
            const size_t resourceOffset = be24(reference + 5);

            if (nameRel != 0xffff)
            {
                if (nameRel > mapLength - nameOffset ||
                    !inRange(nameOffset + nameRel, 1, mapLength))
                    throw OSErr(eofErr);
                const size_t namePos = nameOffset + nameRel;
                const size_t nameLength = map[namePos];
                if (!inRange(namePos + 1, nameLength, mapLength))
                    throw OSErr(eofErr);
                res.name.assign(reinterpret_cast<const char*>(map + namePos + 1), nameLength);
            }

            if (!inRange(resourceOffset, 4, dataLength))
                throw OSErr(eofErr);
            const size_t blockLength = be32(mem + dataOffset + resourceOffset);
            if (!inRange(resourceOffset + 4, blockLength, dataLength))
                throw OSErr(eofErr);
            const uint8_t* block = mem + dataOffset + resourceOffset + 4;
            res.dataBacking.assign(block, block + blockLength);
            res.type = type;
            res.parent = this;
            typeData.resources.emplace_back(std::make_unique<ResourceData>(std::move(res)));
            ResourceData* entry = typeData.resources.back().get();
            if (!typeData.idMap.emplace(entry->id, entry).second)
                throw OSErr(eofErr);
            typeData.nameMap.emplace(entry->name, entry);
            if (m_createHandles && !entry->getHandle())
                throw OSErr(eofErr);
        }
        if (!m_resourceTypes.emplace(type, std::move(typeData)).second)
            throw OSErr(eofErr);
    }
}

void Resources::setCreateHandles(bool create)
{
    m_createHandles = create;
}

void Resources::add(ResType type, ResID id, const char* name, Handle data)
{
    auto itType = m_resourceTypes.find(type);
    if (itType == m_resourceTypes.end())
    {
        ResourceTypeData newType{};
        newType.type = type;
        itType = m_resourceTypes.emplace(type, std::move(newType)).first;
    }
    ResourceData rd(data);
    rd.id = id;
    rd.type = type;
    rd.name = name;
    rd.attributes = 0;
    rd.parent = this;
    itType->second.resources.push_back(std::make_unique<ResourceData>(std::move(rd)));
    ResourceData* added = itType->second.resources.back().get();
    itType->second.idMap.insert({id, added});
    itType->second.nameMap.insert({name, added});
    m_handleMap.insert({data, added});
}

void Resources::remove(Handle data)
{
    auto it = m_handleMap.find(data);
    if (it == m_handleMap.end())
        return;
    ResourceData* target = it->second;
    auto itType = m_resourceTypes.find(target->type);
    if (itType == m_resourceTypes.end())
        return;
    itType->second.idMap.erase(target->id);
    itType->second.nameMap.erase(target->name);
    // RemoveResource only removes the map entry. The caller still owns its
    // handle and must DisposeHandle explicitly (Apple Resource Manager).
    target->releaseHandle(false);
    auto& resources = itType->second.resources;
    for (size_t i = 0; i < resources.size(); ++i)
    {
        if (resources[i].get() == target)
        {
            resources.erase(resources.begin() + i);
            break;
        }
    }
}

Resources::ResourceData* Resources::dataByHandle(Handle h)
{
    auto it = m_handleMap.find(h);
    return it == m_handleMap.end() ? nullptr : it->second;
}

// Serializes a complete Macintosh resource fork. All offsets are checked
// before any file is opened for writing, and the output is deterministic.
namespace {
void append32(std::vector<uint8_t>& out, uint32_t v) {
    out.push_back(static_cast<uint8_t>(v >> 24));
    out.push_back(static_cast<uint8_t>(v >> 16));
    out.push_back(static_cast<uint8_t>(v >> 8));
    out.push_back(static_cast<uint8_t>(v));
}
void store16(std::vector<uint8_t>& out, size_t at, uint16_t v) {
    out[at] = static_cast<uint8_t>(v >> 8);
    out[at + 1] = static_cast<uint8_t>(v);
}
void store32(std::vector<uint8_t>& out, size_t at, uint32_t v) {
    out[at] = static_cast<uint8_t>(v >> 24);
    out[at + 1] = static_cast<uint8_t>(v >> 16);
    out[at + 2] = static_cast<uint8_t>(v >> 8);
    out[at + 3] = static_cast<uint8_t>(v);
}
OSErr ioCode(int e) {
    if (e == ENOSPC || e == EDQUOT || e == EFBIG)
        return dskFulErr;
    if (e == EACCES || e == EPERM || e == EROFS)
        return wPrErr;
    return ioErr;
}
// A regular data fork is written to a private file in the same directory,
// fsynced and atomically renamed over the old inode. We reject hard links,
// symlinks and foreign ownership rather than silently discard their semantics.
OSErr writeDataFork(const std::string& path, const std::vector<uint8_t>& bytes) {
    const int in = ::open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (in < 0) return ioCode(errno);
    struct stat oldStat{};
    const int st = ::fstat(in, &oldStat);
    const int savedErrno = errno;
    ::close(in);
    if (st < 0) return ioCode(savedErrno);
    if (!S_ISREG(oldStat.st_mode) || oldStat.st_nlink != 1 ||
        oldStat.st_uid != geteuid() || !(oldStat.st_mode & 0222)) return wPrErr;
    // Atomic replacement changes the inode. Never silently lose extended
    // attributes (Finder metadata, other forks, quarantine, etc.). Supporting
    // their preservation is a separate, higher-level filesystem contract.
    const ssize_t attributes = ::listxattr(path.c_str(), nullptr, 0, 0);
    if (attributes > 0) return wPrErr;
    if (attributes < 0 && errno != ENOTSUP && errno != EOPNOTSUPP)
        return ioCode(errno);

    std::string temporary = path + ".d4rling-r2-XXXXXX";
    std::vector<char> tempName(temporary.begin(), temporary.end());
    tempName.push_back('\0');
    const int fd = ::mkstemp(tempName.data());
    if (fd < 0) return ioCode(errno);
    OSErr outcome = noErr;
    if (::fchown(fd, static_cast<uid_t>(-1), oldStat.st_gid) != 0 ||
        ::fchmod(fd, oldStat.st_mode & 07777) != 0)
        outcome = ioCode(errno);
    size_t cursor = 0;
    while (outcome == noErr && cursor < bytes.size()) {
        const ssize_t got = ::write(fd, bytes.data() + cursor, bytes.size() - cursor);
        if (got < 0 && errno == EINTR) continue;
        if (got <= 0) { outcome = got == 0 ? ioErr : ioCode(errno); break; }
        cursor += static_cast<size_t>(got);
    }
    if (outcome == noErr && ::fsync(fd) != 0) outcome = ioCode(errno);
    if (::close(fd) != 0 && outcome == noErr) outcome = ioCode(errno);

    // Abort if the filename was replaced while we prepared the temp file.
    struct stat now{};
    if (outcome == noErr && (::lstat(path.c_str(), &now) != 0 ||
        now.st_ino != oldStat.st_ino || now.st_dev != oldStat.st_dev ||
        !S_ISREG(now.st_mode))) outcome = ioErr;
    if (outcome == noErr && ::rename(tempName.data(), path.c_str()) != 0)
        outcome = ioCode(errno);
    if (outcome != noErr) { ::unlink(tempName.data()); return outcome; }

    const size_t slash = path.find_last_of('/');
    const std::string directory = slash == std::string::npos ? "." :
        (slash == 0 ? "/" : path.substr(0, slash));
    const int dirfd = ::open(directory.c_str(), O_RDONLY | O_CLOEXEC | O_DIRECTORY);
    if (dirfd < 0) return ioCode(errno); // Rename succeeded, durability unverified.
    const int ok = ::fsync(dirfd);
    const int dirErrno = errno;
    ::close(dirfd);
    return ok == 0 ? noErr : ioCode(dirErrno);
}
}

OSErr Resources::save(bool snapshotHandles)
{
    if (m_openMode == fsRdPerm) return wPrErr;
    if (m_openMode != fsWrPerm && m_openMode != fsRdWrPerm)
        return paramErr;
    try {
        if (m_prefix.size() < 16 || m_prefix.size() > UINT32_MAX)
            return mapReadErr;
        struct Entry {
            ResourceData* resource;
            std::vector<uint8_t> data;
            uint32_t dataOffset;
            uint16_t nameOffset;
        };
        struct Group { ResType type; std::vector<Entry> entries; };
        std::vector<Group> groups;
        groups.reserve(m_resourceTypes.size());
        if (m_resourceTypes.size() > 65536) return mapReadErr;
        size_t count = 0;
        for (auto& pair : m_resourceTypes) {
            Group group{};
            group.type = pair.first;
            for (auto& item : pair.second.resources) {
                ResourceData* resource = item.get();
                if (!resource || resource->name.size() > 255 ||
                    resource->attributes < 0 || resource->attributes > 255)
                    return mapReadErr;
                Entry entry{};
                entry.resource = resource;
                if (snapshotHandles) {
                    if (!resource->snapshot(entry.data)) return mapReadErr;
                } else entry.data = resource->dataBacking;
                group.entries.push_back(std::move(entry));
            }
            if (group.entries.empty()) continue;
            if (group.entries.size() > 65536) return mapReadErr;
            count += group.entries.size();
            std::sort(group.entries.begin(), group.entries.end(), [](const Entry& a, const Entry& b) {
                return a.resource->id < b.resource->id;
            });
            for (size_t i = 1; i < group.entries.size(); ++i)
                if (group.entries[i - 1].resource->id == group.entries[i].resource->id)
                    return mapReadErr;
            groups.push_back(std::move(group));
        }
        std::sort(groups.begin(), groups.end(), [](const Group& a, const Group& b) {
            return a.type < b.type;
        });
        if (groups.size() > 65536 || count > (SIZE_MAX - 30 - 8 * groups.size()) / 12)
            return mapReadErr;
        const size_t nameStart = 30 + groups.size() * 8 + count * 12;
        if (nameStart > 65535) return mapReadErr;

        std::vector<uint8_t> bytes = m_prefix;
        const size_t dataStart = bytes.size();
        for (auto& group : groups) {
            for (auto& entry : group.entries) {
                if (bytes.size() - dataStart > 0xffffff ||
                    entry.data.size() > UINT32_MAX ||
                    entry.data.size() > UINT32_MAX - 4 - (bytes.size() - dataStart))
                    return mapReadErr;
                entry.dataOffset = static_cast<uint32_t>(bytes.size() - dataStart);
                append32(bytes, static_cast<uint32_t>(entry.data.size()));
                bytes.insert(bytes.end(), entry.data.begin(), entry.data.end());
            }
        }
        const size_t dataLength = bytes.size() - dataStart;
        const size_t mapStart = bytes.size();
        if (mapStart > UINT32_MAX) return mapReadErr;
        std::vector<uint8_t> map(nameStart, 0);
        store16(map, 22, static_cast<uint16_t>(m_attributes));
        store16(map, 24, 28);
        store16(map, 26, static_cast<uint16_t>(nameStart));
        store16(map, 28, groups.empty() ? 0xffff : static_cast<uint16_t>(groups.size() - 1));
        size_t typePos = 30;
        size_t refPos = 30 + 8 * groups.size();
        for (auto& group : groups) {
            store32(map, typePos, static_cast<uint32_t>(group.type));
            store16(map, typePos + 4, static_cast<uint16_t>(group.entries.size() - 1));
            const size_t relativeRef = refPos - 28;
            if (relativeRef > 65535) return mapReadErr;
            store16(map, typePos + 6, static_cast<uint16_t>(relativeRef));
            typePos += 8;
            for (auto& entry : group.entries) {
                store16(map, refPos, static_cast<uint16_t>(entry.resource->id));
                if (!entry.resource->name.empty()) {
                    const size_t offset = map.size() - nameStart;
                    if (offset >= 0xffff) return mapReadErr;
                    entry.nameOffset = static_cast<uint16_t>(offset);
                    map.push_back(static_cast<uint8_t>(entry.resource->name.size()));
                    map.insert(map.end(), entry.resource->name.begin(), entry.resource->name.end());
                } else entry.nameOffset = 0xffff;
                store16(map, refPos + 2, entry.nameOffset);
                map[refPos + 4] = static_cast<uint8_t>(entry.resource->attributes);
                map[refPos + 5] = static_cast<uint8_t>(entry.dataOffset >> 16);
                map[refPos + 6] = static_cast<uint8_t>(entry.dataOffset >> 8);
                map[refPos + 7] = static_cast<uint8_t>(entry.dataOffset);
                refPos += 12;
            }
        }
        if (map.size() > UINT32_MAX) return mapReadErr;
        store32(bytes, 0, static_cast<uint32_t>(dataStart));
        store32(bytes, 4, static_cast<uint32_t>(mapStart));
        store32(bytes, 8, static_cast<uint32_t>(dataLength));
        store32(bytes, 12, static_cast<uint32_t>(map.size()));
        // A copied resource header is required in the resource map itself.
        std::copy(bytes.begin(), bytes.begin() + 16, map.begin());
        bytes.insert(bytes.end(), map.begin(), map.end());

        OSErr err = noErr;
        if (m_resourceFork) {
            struct stat current{};
            if (::lstat(m_file.c_str(), &current) != 0)
                err = ioCode(errno);
            else if (!S_ISREG(current.st_mode) || !(current.st_mode & 0222))
                err = wPrErr;
            else if (::setxattr(m_file.c_str(), "com.apple.ResourceFork", bytes.data(),
                                bytes.size(), 0, 0) != 0)
                err = ioCode(errno);
        } else {
            err = writeDataFork(m_file, bytes);
        }
        if (err != noErr) return err;
        for (auto& group : groups)
            for (auto& entry : group.entries)
                entry.resource->dataBacking.swap(entry.data);
        return noErr;
    } catch (const std::bad_alloc&) {
        return memFullErr;
    } catch (const std::length_error&) {
        return mapReadErr;
    }
}

// The partial-resource APIs operate on the on-disk resource, not on an
// application-modified Handle. Reopen the resource fork so reads do not use
// stale memory; report an error instead of silently extending a resource.
OSErr Resources::readPartial(Handle resource, long offset, void* buffer, long count)
{
    auto local = m_handleMap.find(resource);
    if (local == m_handleMap.end()) return resNotFound;
    if (offset < 0 || count < 0 || (count > 0 && !buffer)) return paramErr;
    try {
        Resources disk(m_file.c_str(), fsRdPerm, m_resourceFork);
        auto kind = disk.data().find(local->second->type);
        if (kind == disk.data().end()) return resNotFound;
        auto record = kind->second.idMap.find(local->second->id);
        if (record == kind->second.idMap.end()) return resNotFound;
        const auto& bytes = record->second->dataBacking;
        if (static_cast<size_t>(offset) > bytes.size() ||
            static_cast<size_t>(count) > bytes.size() - static_cast<size_t>(offset))
            return paramErr;
        if (count > 0)
            std::memcpy(buffer, bytes.data() + offset, static_cast<size_t>(count));
        return noErr;
    } catch (OSErr e) { return e; }
      catch (const std::bad_alloc&) { return memFullErr; }
      catch (const std::length_error&) { return mapReadErr; }
}

OSErr Resources::writePartial(Handle resource, long offset, const void* buffer, long count)
{
    auto local = m_handleMap.find(resource);
    if (local == m_handleMap.end()) return resNotFound;
    if (offset < 0 || count < 0 || (count > 0 && !buffer)) return paramErr;
    if (m_openMode == fsRdPerm) return wPrErr;
    try {
        Resources disk(m_file.c_str(), fsRdWrPerm, m_resourceFork);
        auto kind = disk.data().find(local->second->type);
        if (kind == disk.data().end()) return resNotFound;
        auto record = kind->second.idMap.find(local->second->id);
        if (record == kind->second.idMap.end()) return resNotFound;
        auto& bytes = record->second->dataBacking;
        if (static_cast<size_t>(offset) > bytes.size() ||
            static_cast<size_t>(count) > bytes.size() - static_cast<size_t>(offset))
            return paramErr;
        if (count > 0)
            std::memcpy(bytes.data() + offset, buffer, static_cast<size_t>(count));
        // No snapshot from the in-memory Handle: it intentionally remains
        // stale, as specified by Apple Technical Note TB40.
        return disk.save(false);
    } catch (OSErr e) { return e; }
      catch (const std::bad_alloc&) { return memFullErr; }
      catch (const std::length_error&) { return mapReadErr; }
}
