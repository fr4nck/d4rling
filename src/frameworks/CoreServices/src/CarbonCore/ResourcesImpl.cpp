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
#include <stdexcept>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/xattr.h>
#include <memory>
#include <cstring>
#include <limits>

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

Handle Resources::ResourceData::getHandle()
{
    if (!data)
    {
        Handle newHandle = nullptr;
        if (dataBacking.size() > static_cast<size_t>(std::numeric_limits<long>::max()))
            return nullptr;
        if (PtrToHand(dataBacking.empty() ? nullptr : dataBacking.data(),
                      &newHandle, static_cast<long>(dataBacking.size())) != noErr || !newHandle)
            return nullptr;
        data = newHandle;
        parent->m_handleMap.insert({data, this});
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

void Resources::save()
{
    // Disk serialization is not implemented in this isolated reader lot.
    // Callers must not infer that a successful in-memory edit was persisted.
}
