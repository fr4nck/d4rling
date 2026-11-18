# Carbon windows from `'WIND'` resources — guest witness (2026-11-18)

Report: [docs/evidence/carbon-getnewcwindow-2026-11-18.md](../../../docs/evidence/carbon-getnewcwindow-2026-11-18.md).

| File | Role |
| --- | --- |
| `carbon-window.c` | Mach-O i386/x86_64 C program. It writes a classic resource file (data fork) with `'WIND'` 128 (visible document window, MacRoman title, refCon), `'wctb'` 128 (content colour), `'WIND'` 129 (invisible, `noGrowDocProc`) and `'WIND'` 130 (title longer than the resource). It opens the file with `FSOpenResFile` and checks `GetNewCWindow`, titles, refCon, bounds, class and attributes, content colour, show/hide, stacking, NULL for malformed and missing resources, and invalidation by `DisposeWindow` (19 checks, `CW_RESULT`). `carbon-window HOLD_SECONDS` keeps the windows for an observer. |
| `xprobe.c` | Host X client run against the witness's display: lists top-level windows with their `_NET_WM_NAME`, geometry, map state and the colour of the centre pixel (`XGetImage`). |

The witness was linked with the candidate HIToolbox (`-dylib_file` on its
install name) and run in the Darling guest with an overlay. It used a private
Xvfb in its own user/mount/net namespace (socket in the validation space, no
TCP) and the private ELF32 `ld.so.cache` that holds the i386 X11 libraries.
License: GPL-3.0-or-later, like the other regression witnesses.
Prepared with the help of an AI assistant for the D4rling maintainer.
