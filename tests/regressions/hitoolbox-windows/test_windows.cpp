#include <HIToolbox/MacWindows.h>
#include <cstdio>
#include <cstdint>

static int failures = 0;
static int assertions = 0;
static void check(bool expr, const char* what) {
    ++assertions;
    if (!expr) { ++failures; std::fprintf(stderr, "FAIL: %s\n", what); }
}

int main() {
    // Host check without a window backend (no X11 here): must not pretend a window exists.
    const Rect valid{10, 20, 200, 300};
    const Rect inverted{10, 300, 200, 20};
    auto sentinel = reinterpret_cast<WindowRef>(uintptr_t(0x1234));
    WindowRef window = sentinel;
    check(CreateNewWindow(0, 0, &valid, &window) == unimpErr,
          "CreateNewWindow reports backend unavailable");
    check(window == nullptr, "CreateNewWindow clears output handle");
    check(CreateNewWindow(0, 0, nullptr, &window) == paramErr,
          "CreateNewWindow rejects null rectangle");
    check(CreateNewWindow(0, 0, &valid, nullptr) == paramErr,
          "CreateNewWindow rejects null destination");
    window = sentinel;
    check(CreateNewWindow(0, 0, &inverted, &window) == paramErr,
          "CreateNewWindow rejects inverted rectangle");
    check(window == nullptr, "CreateNewWindow clears output on invalid rectangle");

    check(SelectWindow(nullptr) == errInvalidWindowRef, "SelectWindow rejects a null window");
    check(SetWindowContentColor(nullptr, nullptr) == errInvalidWindowRef, "SetWindowContentColor rejects a null window");
    check(SetWindowGroup(nullptr, 0) == unimpErr, "SetWindowGroup fails explicitly");
    check(SetWindowGroupLevel(0, 0) == unimpErr, "SetWindowGroupLevel fails explicitly");
    check(SetWindowTitleWithCFString(nullptr, nullptr) == errInvalidWindowRef, "SetWindowTitleWithCFString rejects a null window");
    check(TransitionWindowWithOptions(nullptr, 0, 0, nullptr, 0, nullptr) == unimpErr,
          "TransitionWindowWithOptions fails explicitly");
    check(GetWindowEventTarget(nullptr) == nullptr, "GetWindowEventTarget returns no target without backend");
    check(ReleaseWindow(nullptr) == errInvalidWindowRef, "ReleaseWindow rejects a null window");

    WindowGroupRef group = 999;
    check(CreateWindowGroup(0, &group) == unimpErr, "CreateWindowGroup fails explicitly");
    check(group == 0, "CreateWindowGroup clears output group");
    check(CreateWindowGroup(0, nullptr) == paramErr, "CreateWindowGroup rejects null output");

    Rect bounds{1,2,3,4};
    check(GetWindowBounds(nullptr, kWindowContentRgn, &bounds) == errInvalidWindowRef, "GetWindowBounds rejects a null window");
    check(bounds.top == 0 && bounds.left == 0 && bounds.bottom == 0 && bounds.right == 0,
          "GetWindowBounds clears output bounds");
    check(GetWindowBounds(nullptr, 0, nullptr) == paramErr, "GetWindowBounds rejects null output");

    SInt32 level = 999;
    check(GetWindowGroupLevel(0, &level) == unimpErr, "GetWindowGroupLevel fails explicitly");
    check(level == 0, "GetWindowGroupLevel clears output level");
    check(GetWindowGroupLevel(0, nullptr) == paramErr, "GetWindowGroupLevel rejects null output");

    check(!IsWindowVisible(nullptr), "IsWindowVisible is false without backend");
    check(!IsValidWindowPtr(nullptr), "IsValidWindowPtr is false without backend");

    // Window objects: unknown pointers are never treated as windows
    const Rect empty{10, 20, 10, 300};
    window = sentinel;
    check(CreateNewWindow(kDocumentWindowClass, 0, &empty, &window) == paramErr && window == nullptr,
          "CreateNewWindow rejects an empty rectangle");
    check(!IsValidWindowPtr(sentinel), "a foreign pointer is not a window");
    check(!IsWindowVisible(sentinel), "a foreign pointer is not visible");
    DisposeWindow(sentinel);
    ShowWindow(sentinel);
    HideWindow(sentinel);
    BringToFront(sentinel);
    SendBehind(sentinel, nullptr);
    check(RetainWindow(nullptr) == errInvalidWindowRef, "RetainWindow rejects a null window");
    WindowClass cls = 99;
    check(GetWindowClass(sentinel, &cls) == errInvalidWindowRef && cls == 99, "GetWindowClass rejects a foreign pointer");
    WindowAttributes attr = 99;
    check(GetWindowAttributes(nullptr, &attr) == errInvalidWindowRef, "GetWindowAttributes rejects a null window");
    RGBColor color{1, 2, 3};
    check(GetWindowContentColor(nullptr, &color) == errInvalidWindowRef, "GetWindowContentColor rejects a null window");
    CFStringRef title = reinterpret_cast<CFStringRef>(sentinel);
    check(CopyWindowTitleAsCFString(nullptr, &title) == errInvalidWindowRef, "CopyWindowTitleAsCFString rejects a null window");
    SetWRefCon(sentinel, (SRefCon) 42);
    check(GetWRefCon(sentinel) == 0, "refCon of a foreign pointer is 0");
    Str255 ptitle = {3, 'a', 'b', 'c'};
    GetWTitle(nullptr, ptitle);
    check(ptitle[0] == 0, "GetWTitle of a null window is empty");
    check(GetWindowPortBounds(nullptr, &bounds) == nullptr, "GetWindowPortBounds rejects a null window");
    check(GetWindowPort(nullptr) == nullptr, "no QuickDraw port is claimed");
    std::printf("Checks: %d | Failures: %d\n", assertions, failures);
    return failures ? 1 : 0;
}
