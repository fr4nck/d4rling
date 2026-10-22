/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <HIToolbox/CarbonEventsCore.h>
#include <stdio.h>
int main(void) {
    EventRef e = NULL, out = NULL;
    unsigned failures = 0;
    if (CreateEvent(NULL, 1, 2, 1.0, 0, &e) || !e) return 2;
    EventQueueRef q = GetMainEventQueue();
    failures += q == NULL;
    failures += PostEventToQueue(q, e, 1) != 0;
    failures += GetEventRetainCount(e) != 2;
    failures += ReceiveNextEvent(0, NULL, 0, 1, &out) != 0 || out != e;
    if (out) ReleaseEvent(out);
    ReleaseEvent(e);
    printf("Queue behavior probe: 4 checks, %u failures\n", failures);
    return failures != 0;
}
