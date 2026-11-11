// SPDX-License-Identifier: GPL-3.0-or-later
// Narrow oracle for negative mutations of the real production getHandle path.
#define main i1_positive_contracts_not_run
#include "test.cpp"
#undef main
int main() {
    const auto original=makeFork();
    const auto path=makeFile(original);
    bool valid=false;
    {
        Resources res(path.c_str(),fsRdWrPerm,false);
        auto* resource=res.data().at(0x53545220).idMap.at(128);
        Handle h=resource->getHandle();
        if (h && *h && GetHandleSize(h)==3) {
            EmptyHandle(h);
            if (MemError()==noErr && !*h) {
                Handle recovered=resource->getHandle();
                if(recovered==h && *h && GetHandleSize(h)==3 && MemError()==noErr)
                    valid=std::memcmp(*h,"ABC",3)==0;
            }
        }
    }
    unlink(path.c_str());
    if (!valid) {
        std::fprintf(stderr,"I1_MUTANT_DETECTED: resource handle not rehydrated correctly\n");
        return 1;
    }
    std::puts("I1_REHYDRATE: PASS");
    return 0;
}
