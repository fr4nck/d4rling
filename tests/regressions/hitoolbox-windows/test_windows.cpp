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
    // No actual GUI backend: must not pretend a window has been created.
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

    check(SelectWindow(nullptr) == unimpErr, "SelectWindow fails explicitly");
    check(SetWindowContentColor(nullptr, nullptr) == unimpErr, "SetWindowContentColor fails explicitly");
    check(SetWindowGroup(nullptr, 0) == unimpErr, "SetWindowGroup fails explicitly");
    check(SetWindowGroupLevel(0, 0) == unimpErr, "SetWindowGroupLevel fails explicitly");
    check(SetWindowTitleWithCFString(nullptr, nullptr) == unimpErr, "SetWindowTitleWithCFString fails explicitly");
    check(TransitionWindowWithOptions(nullptr, 0, 0, nullptr, 0, nullptr) == unimpErr,
          "TransitionWindowWithOptions fails explicitly");
    check(GetWindowEventTarget(nullptr) == nullptr, "GetWindowEventTarget returns no target without backend");
    check(ReleaseWindow(nullptr) == unimpErr, "ReleaseWindow fails explicitly");

    WindowGroupRef group = 999;
    check(CreateWindowGroup(0, &group) == unimpErr, "CreateWindowGroup fails explicitly");
    check(group == 0, "CreateWindowGroup clears output group");
    check(CreateWindowGroup(0, nullptr) == paramErr, "CreateWindowGroup rejects null output");

    Rect bounds{1,2,3,4};
    check(GetWindowBounds(nullptr, 0, &bounds) == unimpErr, "GetWindowBounds fails explicitly");
    check(bounds.top == 0 && bounds.left == 0 && bounds.bottom == 0 && bounds.right == 0,
          "GetWindowBounds clears output bounds");
    check(GetWindowBounds(nullptr, 0, nullptr) == paramErr, "GetWindowBounds rejects null output");

    SInt32 level = 999;
    check(GetWindowGroupLevel(0, &level) == unimpErr, "GetWindowGroupLevel fails explicitly");
    check(level == 0, "GetWindowGroupLevel clears output level");
    check(GetWindowGroupLevel(0, nullptr) == paramErr, "GetWindowGroupLevel rejects null output");

    check(!IsWindowVisible(nullptr), "IsWindowVisible is false without backend");
    check(!IsValidWindowPtr(nullptr), "IsValidWindowPtr is false without backend");
    std::printf("Checks: %d | Failures: %d\n", assertions, failures);
    return failures ? 1 : 0;
}
