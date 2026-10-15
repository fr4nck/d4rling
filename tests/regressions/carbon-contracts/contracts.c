/* SPDX-License-Identifier: GPL-3.0-or-later
 * Carbon public-header regression check, prepared with OpenAI Codex for fr4nck.
 */
#include <HIToolbox/MacWindows.h>
#include <HIToolbox/CarbonEventsCore.h>

#ifdef __cplusplus
#include <type_traits>
#define SAME_TYPE(a, b) static_assert(std::is_same<a, b>::value, "Carbon signature mismatch")
#else
#define SAME_TYPE(a, b) _Static_assert(__builtin_types_compatible_p(a, b), "Carbon signature mismatch")
#endif

typedef OSStatus (*ExpectedHandler)(EventHandlerCallRef, EventRef, void*);
typedef EventTargetRef (*ExpectedWindowTarget)(WindowRef);
SAME_TYPE(EventHandlerProcPtr, ExpectedHandler);
SAME_TYPE(EventHandlerUPP, ExpectedHandler);
#ifdef __cplusplus
SAME_TYPE(decltype(&GetWindowEventTarget), ExpectedWindowTarget);
#else
SAME_TYPE(__typeof__(&GetWindowEventTarget), ExpectedWindowTarget);
#endif

#ifdef REJECT_BAD_HANDLER
static void invalid_handler(void) {}
EventHandlerProcPtr rejected_handler = invalid_handler;
#endif

static OSStatus handler(EventHandlerCallRef call, EventRef event, void* data)
{
    (void)call;
    (void)event;
    ++*(int*)data;
    return 17;
}

int main(void)
{
    int calls = 0;
    EventHandlerProcPtr proc = handler;
    EventHandlerUPP upp = proc;
    ExpectedWindowTarget target = GetWindowEventTarget;
    if (upp(0, 0, &calls) != 17 || calls != 1)
        return 1;
    return target(0) == 0 ? 0 : 2;
}
