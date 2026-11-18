/* Host observer: top-level windows of an X display (title, geometry, map state, centre pixel). */
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    Display *d = XOpenDisplay(argc > 1 ? argv[1] : NULL);
    if (!d) { printf("XPROBE_NO_DISPLAY\n"); return 2; }
    Window root = DefaultRootWindow(d), r, p, *kids; unsigned n;
    Atom name = XInternAtom(d, "_NET_WM_NAME", False), utf8 = XInternAtom(d, "UTF8_STRING", False);
    XQueryTree(d, root, &r, &p, &kids, &n);
    for (unsigned i = 0; i < n; i++) {
        XWindowAttributes a; XGetWindowAttributes(d, kids[i], &a);
        Atom t; int f; unsigned long cnt, rem; unsigned char *v = NULL; char title[512] = "";
        if (XGetWindowProperty(d, kids[i], name, 0, 256, False, utf8, &t, &f, &cnt, &rem, &v) == Success && v) {
            snprintf(title, sizeof title, "%s", (char *) v); XFree(v);
        }
        if (!title[0]) continue;
        unsigned long px = 0; int havePx = 0;
        if (a.map_state == IsViewable) {
            XImage *img = XGetImage(d, kids[i], a.width / 2, a.height / 2, 1, 1, AllPlanes, ZPixmap);
            if (img) { px = XGetPixel(img, 0, 0); havePx = 1; XDestroyImage(img); }
        }
        printf("XPROBE_WINDOW stack=%u id=0x%lx title=\"%s\" x=%d y=%d w=%d h=%d viewable=%d pixel=%s%06lx\n",
               i, kids[i], title, a.x, a.y, a.width, a.height, a.map_state == IsViewable, havePx ? "0x" : "none:", px);
    }
    if (kids) XFree(kids);
    XCloseDisplay(d);
    return 0;
}
