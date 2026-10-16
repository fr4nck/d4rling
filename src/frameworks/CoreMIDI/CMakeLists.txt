project(CoreMIDI)

remove_sdk_framework(CoreMIDI)

set(DYLIB_COMPAT_VERSION "1.0.0")
set(DYLIB_CURRENT_VERSION "69.0.0")

set(FRAMEWORK_VERSION "A")

option(DARLING_COREMIDI_ENABLE_ALSA "Experimental CoreMIDI ALSA sequencer output bridge" OFF)
if(DARLING_COREMIDI_ENABLE_ALSA)
    find_package(ALSA REQUIRED)
    include(wrap_elf)
    include_directories(${ALSA_INCLUDE_DIRS})
    wrap_elf(asound libasound.so)
endif()

generate_sdk_framework(CoreMIDI
    VERSION ${FRAMEWORK_VERSION}
    HEADER "include/CoreMIDI"
)

add_framework(CoreMIDI
    FAT
    CURRENT_VERSION
    VERSION ${FRAMEWORK_VERSION}

    SOURCES
        src/CoreMIDI.m
        src/MIDIVirtual.c
        src/MIDIAlsaBridge.c
        src/MIDICIProfile.m
        src/MIDICIProfileState.m
        src/MIDICISession.m
        src/BLEMIDIAccessor.m
        src/MIDINetworkSession.m
        src/MIDINetworkHost.m
        src/MIDINetworkConnection.m
        src/MIDIServices.m

    DEPENDENCIES
        system
        objc
        Foundation
)

if(DARLING_COREMIDI_ENABLE_ALSA)
    target_compile_definitions(CoreMIDI PRIVATE DARLING_COREMIDI_WITH_ALSA=1)
    target_link_libraries(CoreMIDI PRIVATE asound)
endif()
