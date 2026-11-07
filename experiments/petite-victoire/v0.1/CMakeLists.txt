cmake_minimum_required(VERSION 3.16)
project(PetiteVictoire VERSION 0.1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(pv_music STATIC src/music.cpp)
target_include_directories(pv_music PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/src")
if (CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(pv_music PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(petite-victoire src/main.cpp)
target_link_libraries(petite-victoire PRIVATE pv_music)

include(CTest)
if (BUILD_TESTING)
    add_executable(pv_tests tests/test_music.cpp)
    target_link_libraries(pv_tests PRIVATE pv_music)
    add_test(NAME pv_tests COMMAND pv_tests)
endif()

# Carbon only exists as a 32-bit macOS framework. In Darling's cross build,
# enable this option explicitly and supply the correct SDK, sysroot and Mach-O linker.
option(PV_BUILD_CARBON "Build experimental 32-bit Carbon frontend" OFF)
if (PV_BUILD_CARBON)
    if (NOT APPLE AND NOT PV_CROSS_DARWIN)
        message(FATAL_ERROR "Carbon requires a macOS i386 SDK / Darling cross toolchain")
    endif()
    add_executable(petite-victoire-carbon mac/CarbonApp.cpp)
    target_link_libraries(petite-victoire-carbon PRIVATE pv_music "-framework Carbon" "-framework CoreAudio")
    target_compile_definitions(petite-victoire-carbon PRIVATE PV_CARBON_EXPERIMENTAL=1)
endif()
