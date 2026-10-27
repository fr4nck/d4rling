#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic, host-only source contract tests. No SDK or Darling runtime."""

from pathlib import Path
import tempfile
import unittest

import source_contract as source

KERNEL_CMAKE = '''
add_circular(system_kernel FAT
 OBJECTS
  $<IF:$<BOOL:${BUILD_TARGET_32BIT}>,$<TARGET_OBJECTS:libsyscall_32>,>
  $<TARGET_OBJECTS:libsyscall>
  $<TARGET_OBJECTS:libsyscall_dynamic>
  $<TARGET_OBJECTS:emulation>
 SIBLINGS
  system_c compiler_rt system_dyld
 DEPENDENCIES
  libsimple_darling
)
add_library(system_kernel_static32 STATIC
 $<TARGET_OBJECTS:libsyscall_32>
 $<TARGET_OBJECTS:libsyscall>
 $<TARGET_OBJECTS:emulation_dyld>
)
'''
SYSCALL_CMAKE = '''
set(syscall_dynamic_sources
 wrappers/_libc_funcptr.c
 wrappers/_libkernel_init.c)
set(syscall_sources
 mach/mach_traps.S
 # wrappers/_libkernel_init.c deliberately excluded
 wrappers/carbon_delete.c)
add_darling_object_library(libsyscall_dynamic ${syscall_dynamic_sources})
'''
KERNEL_INIT = '''
_libkernel_functions_t _libkernel_functions;
void __libkernel_init(_libkernel_functions_t fns) { _libkernel_functions = fns; }
'''
MALLOC_CMAKE = '''
set(libmalloc_sources src/magazine_malloc.c src/malloc.c src/other.c)
add_circular(system_malloc FAT
 SOURCES ${libmalloc_sources}
 SIBLINGS system_kernel platform system_dyld compiler_rt
 UPWARD system_c)
'''
MALLOC_SOURCE = '''
void *
malloc(size_t size)
{
 return 0;
}
void
free(void *ptr)
{
}
'''
SYSTEM_CMAKE = '''
add_circular(system FAT SOURCES ${libsystem_sources} SIBLINGS system_malloc)
libsystem_reexport(
 system_malloc src/external/libmalloc/libsystem_malloc.dylib
 system_c src/external/libc/libsystem_c.dylib
 system_kernel src/external/xnu/darling/src/libsystem_kernel/libsystem_kernel.dylib
)
'''

FILES = {
    'src/external/xnu/darling/src/libsystem_kernel/CMakeLists.txt': KERNEL_CMAKE,
    'src/external/xnu/libsyscall/CMakeLists.txt': SYSCALL_CMAKE,
    'src/external/xnu/libsyscall/wrappers/_libkernel_init.c': KERNEL_INIT,
    'src/external/libmalloc/CMakeLists.txt': MALLOC_CMAKE,
    'src/external/libmalloc/src/malloc.c': MALLOC_SOURCE,
    'src/external/libsystem/CMakeLists.txt': SYSTEM_CMAKE,
}


class CmakeParserTests(unittest.TestCase):
    def test_reads_multiple_commands(self):
        self.assertEqual(len(source.cmake_calls('set(x a)\nset(y b)\n', 'set')), 2)

    def test_ignores_comment_fake_target(self):
        self.assertEqual(source.cmake_calls('# add_library(fake STATIC)\n', 'add_library'), [])

    def test_removes_comment_inside_call(self):
        call = source.find_call('set(x a # ignored\n b)\n', 'set', 'x')
        self.assertEqual(call, ['x', 'a', 'b'])

    def test_quoted_comment_is_not_removed(self):
        call = source.find_call('set(x "a#b" c)\n', 'set', 'x')
        self.assertEqual(call, ['x', '"a#b"', 'c'])

    def test_parser_rejects_incomplete_command(self):
        with self.assertRaises(source.ContractError):
            source.cmake_calls('set(x a\n', 'set')

    def test_parser_rejects_duplicate_target(self):
        with self.assertRaises(source.ContractError):
            source.find_call('set(x 1)\nset(x 2)\n', 'set', 'x')

    def test_extracts_nested_object_targets(self):
        call = source.find_call(KERNEL_CMAKE, 'add_circular', 'system_kernel')
        self.assertIn('libsyscall_32', source.object_targets(call))
        self.assertIn('libsyscall_dynamic', source.object_targets(call))

    def test_group_finder_stops_at_next_section(self):
        call = source.find_call(KERNEL_CMAKE, 'add_circular', 'system_kernel')
        self.assertEqual(source.values_after(call, 'SIBLINGS', {'DEPENDENCIES'}),
                         ['system_c', 'compiler_rt', 'system_dyld'])


class SourceContractTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        for relative, contents in FILES.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)

    def _replace(self, relative, old, new):
        path = self.root / relative
        content = path.read_text()
        assert old in content
        path.write_text(content.replace(old, new))

    def test_complete_pinned_style_contract(self):
        data = source.inspect_checkout(self.root)
        self.assertTrue(data['all_checks_pass'], data['checks'])
        self.assertEqual(len(data['checks']), 9)
        self.assertEqual(data['kind'], 'source_contract_only')

    def test_static_archive_does_not_contain_dynamic_initializers(self):
        data = source.inspect_checkout(self.root)
        self.assertNotIn('libsyscall_dynamic', data['static32_object_targets'])
        self.assertIn('libsyscall_dynamic', data['dynamic_kernel_object_targets'])

    def test_detects_static_archive_with_dynamic_initializers(self):
        path = 'src/external/xnu/darling/src/libsystem_kernel/CMakeLists.txt'
        self._replace(path, '$<TARGET_OBJECTS:emulation_dyld>\n)',
                      '$<TARGET_OBJECTS:emulation_dyld>\n $<TARGET_OBJECTS:libsyscall_dynamic>\n)')
        self.assertFalse(source.inspect_checkout(self.root)['checks']['static32_omits_dynamic_init_objects'])

    def test_detects_missing_dynamic_initializers(self):
        path = 'src/external/xnu/darling/src/libsystem_kernel/CMakeLists.txt'
        self._replace(path, '$<TARGET_OBJECTS:libsyscall_dynamic>\n', '')
        self.assertFalse(source.inspect_checkout(self.root)['checks']['dynamic_kernel_has_init_objects'])

    def test_detects_missing_libmalloc_source(self):
        self._replace('src/external/libmalloc/CMakeLists.txt', 'src/malloc.c', 'src/other-malloc.c')
        self.assertFalse(source.inspect_checkout(self.root)['checks']['malloc_source_in_dynamic_malloc_target'])

    def test_detects_broken_libsystem_reexport(self):
        self._replace('src/external/libsystem/CMakeLists.txt', 'system_malloc src/', 'not_malloc src/')
        self.assertFalse(source.inspect_checkout(self.root)['checks']['libsystem_dynamically_reexports_malloc_and_kernel'])

    def test_detects_missing_data_symbol(self):
        self._replace('src/external/xnu/libsyscall/wrappers/_libkernel_init.c',
                      '_libkernel_functions_t _libkernel_functions;', 'void init(void);')
        self.assertFalse(source.inspect_checkout(self.root)['checks']['libkernel_functions_declared_in_kernel_init'])

    def test_uninitialized_submodule_refused(self):
        (self.root / 'src/external/libmalloc/CMakeLists.txt').unlink()
        with self.assertRaises(source.ContractError):
            source.inspect_checkout(self.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
