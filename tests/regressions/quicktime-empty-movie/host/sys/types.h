/* SPDX-License-Identifier: GPL-3.0-or-later
 * The real MacTypes.h needs the Darwin null spelling only here.
 */
#ifndef __DARWIN_NULL
#ifdef __cplusplus
#define __DARWIN_NULL nullptr
#else
#define __DARWIN_NULL ((void *)0)
#endif
#endif
