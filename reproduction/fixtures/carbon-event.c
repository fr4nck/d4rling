typedef void *EventRef;
typedef unsigned int UInt32;
typedef int OSStatus;

extern OSStatus CreateEvent(
    const void *, UInt32, UInt32, double,
    UInt32, EventRef *
);

extern OSStatus SetEventParameter(
    EventRef, UInt32, UInt32, UInt32, const void *
);

extern OSStatus GetEventParameter(
    EventRef, UInt32, UInt32, UInt32 *,
    UInt32, UInt32 *, void *
);

extern void ReleaseEvent(EventRef);
extern long write(int, const void *, unsigned long);

static void say(const char *s)
{
    unsigned long n = 0;
    while (s[n]) ++n;
    (void)write(1, s, n);
    (void)write(1, "\n", 1);
}

int main(void)
{
    EventRef event = 0;
    UInt32 value = 0x12345678U;
    UInt32 recovered = 0;
    UInt32 actual_type = 0;
    UInt32 actual_size = 0;

    OSStatus status = CreateEvent(
        0, 0x4434524cU, 1, 0.0, 0, &event
    );

    if (status != 0 || !event)
        return 11;

    status = SetEventParameter(
        event, 0x74657374U, 0x6c6f6e67U,
        sizeof(value), &value
    );

    if (status != 0) {
        ReleaseEvent(event);
        return 12;
    }

    status = GetEventParameter(
        event, 0x74657374U, 0x6c6f6e67U,
        &actual_type, sizeof(recovered),
        &actual_size, &recovered
    );

    if (status != 0 ||
        actual_type != 0x6c6f6e67U ||
        actual_size != sizeof(recovered) ||
        recovered != value) {
        ReleaseEvent(event);
        return 13;
    }

    ReleaseEvent(event);
    say("D4RLING-CARBON-EVENT-I386-OK");
    return 0;
}
