/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-B12: host-side PulseAudio observer (Linux x86-64, host libpulse), used
 * because pactl is not installed. It never plays anything.
 *   pa-tool info                     server name/version, default sink
 *   pa-tool inputs                   one line per sink input (playback stream)
 *   pa-tool record SECONDS OUT.raw   capture @DEFAULT_MONITOR@ (what the sink
 *                                    plays), S16LE stereo 44100 Hz
 */
#include <pulse/pulseaudio.h>
#include <pulse/simple.h>
#include <pulse/error.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static pa_mainloop *ml;
static int pending, inputs;

static void server_cb(pa_context *c, const pa_server_info *i, void *u)
{
    (void)c; (void)u;
    printf("PA_SERVER name=%s version=%s default_sink=%s rate=%u channels=%u\n", i->server_name,
           i->server_version, i->default_sink_name, i->sample_spec.rate, i->sample_spec.channels);
    --pending;
}

static void input_cb(pa_context *c, const pa_sink_input_info *i, int eol, void *u)
{
    (void)c; (void)u;
    if (eol) { --pending; return; }
    ++inputs;
    printf("PA_INPUT index=%u client=%s media=%s format=%s rate=%u channels=%u corked=%d\n", i->index,
           pa_proplist_gets(i->proplist, PA_PROP_APPLICATION_NAME) ? pa_proplist_gets(i->proplist, PA_PROP_APPLICATION_NAME) : "?",
           i->name ? i->name : "?", pa_sample_format_to_string(i->sample_spec.format), i->sample_spec.rate,
           i->sample_spec.channels, i->corked);
}

static void state_cb(pa_context *c, void *u)
{
    const char *what = u;
    switch (pa_context_get_state(c)) {
    case PA_CONTEXT_READY:
        if (!strcmp(what, "info"))
            pa_operation_unref(pa_context_get_server_info(c, server_cb, NULL));
        else
            pa_operation_unref(pa_context_get_sink_input_info_list(c, input_cb, NULL));
        break;
    case PA_CONTEXT_FAILED:
    case PA_CONTEXT_TERMINATED:
        pending = -100;
        break;
    default:
        break;
    }
}

static int query(const char *what)
{
    pa_context *c;
    int ret = 0;
    ml = pa_mainloop_new();
    c = pa_context_new(pa_mainloop_get_api(ml), "d4rling-b12-observer");
    pa_context_set_state_callback(c, state_cb, (void *)what);
    if (pa_context_connect(c, NULL, PA_CONTEXT_NOFLAGS, NULL) < 0) {
        printf("PA_CONNECT_FAIL %s\n", pa_strerror(pa_context_errno(c)));
        return 3;
    }
    pending = 1;
    while (pending > 0)
        if (pa_mainloop_iterate(ml, 1, &ret) < 0)
            break;
    if (pending < 0)
        printf("PA_CONNECT_FAIL %s\n", pa_strerror(pa_context_errno(c)));
    else if (!strcmp(what, "inputs"))
        printf("PA_INPUTS count=%d\n", inputs);
    ret = pending < 0 ? 3 : 0; /* before disconnect: its state callback sets pending */
    pa_context_disconnect(c);
    pa_context_unref(c);
    pa_mainloop_free(ml);
    return ret;
}

static int record(double seconds, const char *path)
{
    static const pa_sample_spec ss = { PA_SAMPLE_S16LE, 44100, 2 };
    pa_buffer_attr attr = { (uint32_t)-1, (uint32_t)-1, (uint32_t)-1, (uint32_t)-1, 4410 * 4 };
    int err = 0;
    size_t total = (size_t)(seconds * 44100) * 4, done = 0;
    unsigned char buf[4410 * 4];
    FILE *f = fopen(path, "wb");
    pa_simple *s = f ? pa_simple_new(NULL, "d4rling-b12-observer", PA_STREAM_RECORD, "@DEFAULT_MONITOR@",
                                     "b12-monitor", &ss, NULL, &attr, &err) : NULL;
    if (!s) {
        printf("PA_RECORD_FAIL %s\n", pa_strerror(err));
        return 4;
    }
    while (done < total) {
        size_t n = total - done < sizeof buf ? total - done : sizeof buf;
        if (pa_simple_read(s, buf, n, &err) < 0) {
            printf("PA_RECORD_FAIL %s\n", pa_strerror(err));
            break;
        }
        fwrite(buf, 1, n, f);
        done += n;
    }
    pa_simple_free(s);
    fclose(f);
    printf("PA_RECORDED bytes=%zu\n", done);
    return done == total ? 0 : 5;
}

int main(int argc, char **argv)
{
    if (argc == 2 && (!strcmp(argv[1], "info") || !strcmp(argv[1], "inputs")))
        return query(argv[1]);
    if (argc == 4 && !strcmp(argv[1], "record"))
        return record(atof(argv[2]), argv[3]);
    fprintf(stderr, "usage: pa-tool info|inputs|record SECONDS OUT.raw\n");
    return 2;
}
