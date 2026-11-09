/* SPDX-License-Identifier: GPL-3.0-or-later
 * Only platform macros required by the real MacTypes.h in this host test.
 * MSVC LLP64 long is 32 bits, so select the non-LP64 branch explicitly.
 */
#define __CONDITIONALMACROS__
#define PRAGMA_ONCE 0
#define TARGET_RT_BIG_ENDIAN 0
#define TYPE_LONGLONG 1
#define TARGET_RT_MAC_CFM 0
#define TARGET_CPU_68K 0
#define TARGET_CPU_PPC 0
#define OLDROUTINENAMES 0
#define CALLBACK_API_C(result, name) result (*name)
#define CALLBACK_API(result, name) result (*name)
#ifndef __DARWIN_NULL
#define __DARWIN_NULL ((void *)0)
#endif
