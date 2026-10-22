/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef CARBON_TEST_ALLOCATOR_ADAPTER_H
#define CARBON_TEST_ALLOCATOR_ADAPTER_H
#include <CoreFoundation/CFBase.h>
CFAllocatorRef test_default_allocator(void);
CFAllocatorRef test_custom_allocator(void);
void test_set_default(CFAllocatorRef allocator);
void test_fail_next_allocation(void);
void test_fail_allocation_after(unsigned successes);
unsigned test_allocations(CFAllocatorRef allocator);
unsigned test_frees(CFAllocatorRef allocator);
unsigned test_references(CFAllocatorRef allocator);
#endif
