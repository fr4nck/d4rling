// Carbon windows backed by X11 windows (through the native libX11 wrapper,
// as Cocotron's X11 backend does). A WindowRef is a real opaque object owned
// by this file; it is never an X11 window id cast to a pointer.

#include <HIToolbox/MacWindows.h>
#include <CarbonCore/Resources.h>
#include <CarbonCore/MacMemory.h>
#include <CoreFoundation/CFString.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/Xutil.h>
#include <dlfcn.h>

// libX11 is loaded on first use, as AppKit loads its X11 backend: Carbon itself
// must still load on a host or in a process without X11.
static struct
{
	decltype(&::XOpenDisplay) OpenDisplay;
	decltype(&::XCloseDisplay) CloseDisplay;
	decltype(&::XFlush) Flush;
	decltype(&::XInternAtom) InternAtom;
	decltype(&::XUnmapWindow) UnmapWindow;
	decltype(&::XStoreName) StoreName;
	decltype(&::XSetWMNormalHints) SetWMNormalHints;
	decltype(&::XSetWindowBackground) SetWindowBackground;
	decltype(&::XSelectInput) SelectInput;
	decltype(&::XRestackWindows) RestackWindows;
	decltype(&::XMapWindow) MapWindow;
	decltype(&::XFree) Free;
	decltype(&::XDestroyWindow) DestroyWindow;
	decltype(&::XCreateSimpleWindow) CreateSimpleWindow;
	decltype(&::XClearWindow) ClearWindow;
	decltype(&::XChangeProperty) ChangeProperty;
	decltype(&::XAllocSizeHints) AllocSizeHints;
	decltype(&::XAllocColor) AllocColor;
} x11;

static bool loadX11()
{
	static int state = 0; // 0 untried, 1 loaded, -1 unavailable
	if (state)
		return state > 0;
	state = -1;
	void* lib = dlopen("/usr/lib/native/libX11.dylib", RTLD_LAZY | RTLD_LOCAL);
	if (!lib)
	{
		fprintf(stderr, "Darling Carbon: cannot load libX11: %s\n", dlerror());
		return false;
	}
#define LOAD(name) if (!(x11.name = (decltype(x11.name)) dlsym(lib, "X" #name))) { \
		fprintf(stderr, "Darling Carbon: libX11 lacks X" #name "\n"); return false; }
	LOAD(OpenDisplay)
	LOAD(CloseDisplay)
	LOAD(Flush)
	LOAD(InternAtom)
	LOAD(UnmapWindow)
	LOAD(StoreName)
	LOAD(SetWMNormalHints)
	LOAD(SetWindowBackground)
	LOAD(SelectInput)
	LOAD(RestackWindows)
	LOAD(MapWindow)
	LOAD(Free)
	LOAD(DestroyWindow)
	LOAD(CreateSimpleWindow)
	LOAD(ClearWindow)
	LOAD(ChangeProperty)
	LOAD(AllocSizeHints)
	LOAD(AllocColor)
#undef LOAD
	state = 1;
	return true;
}

static int verbose = 0;

__attribute__((constructor))
static void initme(void) {
	verbose = getenv("STUB_VERBOSE") != NULL;
}

static Display* g_display = nullptr;
static bool g_displayFailed = false;
namespace Darling
{

namespace Carbon
{

// Returns NULL, once reported on stderr, when no X server can be reached:
// window creation then fails instead of aborting the process.
Display* getDisplay()
{
	if (g_display || g_displayFailed)
		return g_display;

	if (!loadX11())
	{
		g_displayFailed = true;
		return nullptr;
	}

	g_display = x11.OpenDisplay(nullptr);

	if (!g_display)
	{
		g_displayFailed = true;
		fprintf(stderr, "Darling Carbon: cannot open a connection to the X server%s\n",
			getenv("DISPLAY") ? "" : " (DISPLAY is not set)");
	}

	return g_display;
}

// Not a destructor: at process exit the dynamically loaded libX11 may already
// be finalized, and the connection closes with the process anyway.
void closeDisplay()
{
	if (g_display)
	{
		x11.CloseDisplay(g_display);
		g_display = nullptr;
	}
}

}
}

static const uint32_t kWindowMagic = 'CWin';

struct OpaqueWindowPtr
{
	uint32_t magic;
	int32_t refCount;
	Window xid;
	WindowClass windowClass;
	WindowAttributes attributes;
	Rect bounds;              // content rectangle, global coordinates
	CFStringRef title;
	Boolean visible;
	SRefCon refCon;
	RGBColor contentColor;
	struct OpaqueWindowPtr* next; // front-to-back window list
};

static OpaqueWindowPtr* g_windows = nullptr;   // frontmost first

static OpaqueWindowPtr* lookup(WindowRef window)
{
	for (OpaqueWindowPtr* w = g_windows; w; w = w->next)
	{
		if (w == window && w->magic == kWindowMagic)
			return w;
	}
	return nullptr;
}

static void unlinkWindow(OpaqueWindowPtr* window)
{
	for (OpaqueWindowPtr** p = &g_windows; *p; p = &(*p)->next)
	{
		if (*p == window)
		{
			*p = window->next;
			window->next = nullptr;
			return;
		}
	}
}

// Inserts at the front (behind == (WindowRef) -1), at the back (behind == NULL)
// or just behind another window
static void insertWindow(OpaqueWindowPtr* window, WindowRef behind)
{
	OpaqueWindowPtr* other = (behind && behind != (WindowRef) -1) ? lookup(behind) : nullptr;

	if (behind == (WindowRef) -1 || !g_windows || (behind && !other))
	{
		window->next = g_windows;
		g_windows = window;
		return;
	}
	if (other)
	{
		window->next = other->next;
		other->next = window;
		return;
	}
	OpaqueWindowPtr** p = &g_windows;
	while (*p)
		p = &(*p)->next;
	*p = window;
	window->next = nullptr;
}

// Applies the list order to the X11 stacking order
static void restack()
{
	Display* dpy = Darling::Carbon::getDisplay();
	if (!dpy)
		return;
	int count = 0;
	for (OpaqueWindowPtr* w = g_windows; w; w = w->next)
		count++;
	if (count == 0)
		return;
	Window* order = (Window*) malloc(sizeof(Window) * count);
	if (!order)
		return;
	int i = 0;
	for (OpaqueWindowPtr* w = g_windows; w; w = w->next)
		order[i++] = w->xid;
	x11.RestackWindows(dpy, order, count);
	x11.Flush(dpy);
	free(order);
}

static unsigned long pixelFor(Display* dpy, const RGBColor* color)
{
	XColor xc;
	xc.red = color->red;
	xc.green = color->green;
	xc.blue = color->blue;
	xc.flags = DoRed | DoGreen | DoBlue;
	if (x11.AllocColor(dpy, DefaultColormap(dpy, DefaultScreen(dpy)), &xc))
		return xc.pixel;
	return WhitePixel(dpy, DefaultScreen(dpy));
}

static void applyTitle(OpaqueWindowPtr* window)
{
	Display* dpy = Darling::Carbon::getDisplay();
	if (!dpy)
		return;

	const char* utf8 = "";
	char* buffer = nullptr;
	if (window->title)
	{
		CFIndex size = CFStringGetMaximumSizeForEncoding(CFStringGetLength(window->title), kCFStringEncodingUTF8) + 1;
		buffer = (char*) malloc(size);
		if (buffer && CFStringGetCString(window->title, buffer, size, kCFStringEncodingUTF8))
			utf8 = buffer;
	}

	Atom netName = x11.InternAtom(dpy, "_NET_WM_NAME", False);
	Atom utf8String = x11.InternAtom(dpy, "UTF8_STRING", False);
	x11.ChangeProperty(dpy, window->xid, netName, utf8String, 8, PropModeReplace,
		(const unsigned char*) utf8, (int) strlen(utf8));
	x11.StoreName(dpy, window->xid, utf8);
	x11.Flush(dpy);
	free(buffer);
}

OSStatus CreateNewWindow(WindowClass cls, WindowAttributes attr, const Rect* rect, WindowRef* newWindow)
{
	if (!newWindow || !rect)
		return paramErr;

	*newWindow = nullptr;

	if (rect->right <= rect->left || rect->bottom <= rect->top)
		return paramErr;

	Display* dpy = Darling::Carbon::getDisplay();
	if (!dpy)
		return unimpErr;

	OpaqueWindowPtr* window = (OpaqueWindowPtr*) calloc(1, sizeof(OpaqueWindowPtr));
	if (!window)
		return memFullErr;

	window->magic = kWindowMagic;
	window->refCount = 1;
	window->windowClass = cls;
	window->attributes = attr;
	window->bounds = *rect;
	window->contentColor.red = window->contentColor.green = window->contentColor.blue = 0xFFFF;

	int screen = DefaultScreen(dpy);
	window->xid = x11.CreateSimpleWindow(dpy, RootWindow(dpy, screen), rect->left, rect->top,
		rect->right - rect->left, rect->bottom - rect->top, 0,
		BlackPixel(dpy, screen), WhitePixel(dpy, screen));

	if (!window->xid)
	{
		free(window);
		return memFullErr;
	}

	// Carbon gives the content rectangle in global coordinates: ask for it
	XSizeHints* hints = x11.AllocSizeHints();
	if (hints)
	{
		hints->flags = USPosition | USSize | PPosition | PSize;
		hints->x = rect->left;
		hints->y = rect->top;
		hints->width = rect->right - rect->left;
		hints->height = rect->bottom - rect->top;
		if (!(attr & kWindowResizableAttribute))
		{
			hints->flags |= PMinSize | PMaxSize;
			hints->min_width = hints->max_width = hints->width;
			hints->min_height = hints->max_height = hints->height;
		}
		x11.SetWMNormalHints(dpy, window->xid, hints);
		x11.Free(hints);
	}

	x11.SelectInput(dpy, window->xid, ExposureMask | StructureNotifyMask);

	// New windows are created invisible and in front
	insertWindow(window, (WindowRef) -1);
	x11.Flush(dpy);

	*newWindow = window;
	return noErr;
}

// 'WIND' resource: Rect bounds, int16 procID, byte visible, filler,
// byte goAwayFlag, filler, int32 refCon, Pascal title, [align, int16 positioning]
static uint16_t be16(const unsigned char* p) { return (uint16_t) ((p[0] << 8) | p[1]); }
static uint32_t be32(const unsigned char* p) { return ((uint32_t) p[0] << 24) | ((uint32_t) p[1] << 16) | ((uint32_t) p[2] << 8) | p[3]; }

// Window definition procIDs of the standard WDEF 0 (Inside Macintosh: Toolbox Essentials)
static void classForProcID(short procID, Boolean goAway, WindowClass* cls, WindowAttributes* attr)
{
	*attr = goAway ? kWindowCloseBoxAttribute : 0;
	switch (procID & 0x0F)
	{
		case 1:  // dBoxProc
			*cls = kModalWindowClass;
			*attr = 0;
			break;
		case 2:  // plainDBox
			*cls = kPlainWindowClass;
			*attr = 0;
			break;
		case 3:  // altDBoxProc
			*cls = kAlertWindowClass;
			*attr = 0;
			break;
		case 5:  // movableDBoxProc
			*cls = kMovableModalWindowClass;
			break;
		case 4:  // noGrowDocProc
			*cls = kDocumentWindowClass;
			*attr |= kWindowCollapseBoxAttribute;
			break;
		case 8:  // zoomDocProc
			*cls = kDocumentWindowClass;
			*attr |= kWindowResizableAttribute | kWindowFullZoomAttribute | kWindowCollapseBoxAttribute;
			break;
		case 12: // zoomNoGrow
			*cls = kDocumentWindowClass;
			*attr |= kWindowFullZoomAttribute | kWindowCollapseBoxAttribute;
			break;
		default: // documentProc, rDocProc and the remaining variants
			*cls = kDocumentWindowClass;
			*attr |= kWindowResizableAttribute | kWindowCollapseBoxAttribute;
			break;
	}
}

// Content color of a 'wctb' resource (ColorTable: seed, flags, size, (size + 1) ColorSpec)
static bool contentColorFromWctb(Handle h, RGBColor* color)
{
	if (!h || !*h)
		return false;
	Size size = GetHandleSize(h);
	const unsigned char* p = (const unsigned char*) *h;
	if (size < 8)
		return false;
	int count = (int16_t) be16(p + 6) + 1;
	if (count <= 0 || size < 8 + (Size) count * 8)
		return false;
	for (int i = 0; i < count; i++)
	{
		const unsigned char* spec = p + 8 + i * 8;
		if (be16(spec) == 0) // wContentColor
		{
			color->red = be16(spec + 2);
			color->green = be16(spec + 4);
			color->blue = be16(spec + 6);
			return true;
		}
	}
	return false;
}

static WindowRef newWindowFromResource(short windowID, WindowRef behind)
{
	Handle h = GetResource('WIND', windowID);
	if (!h || !*h)
		return nullptr;

	Size size = GetHandleSize(h);
	const unsigned char* p = (const unsigned char*) *h;
	if (size < 19 || p[18] > size - 19)
		return nullptr;

	Rect bounds;
	bounds.top = (short) be16(p);
	bounds.left = (short) be16(p + 2);
	bounds.bottom = (short) be16(p + 4);
	bounds.right = (short) be16(p + 6);
	short procID = (short) be16(p + 8);
	Boolean visible = p[10] != 0;
	Boolean goAway = p[12] != 0;
	SRefCon refCon = (SRefCon) (uintptr_t) be32(p + 14);

	CFStringRef title = CFStringCreateWithPascalString(kCFAllocatorDefault, p + 18, kCFStringEncodingMacRoman);
	if (!title)
		return nullptr;

	WindowClass cls;
	WindowAttributes attr;
	classForProcID(procID, goAway, &cls, &attr);

	WindowRef window = nullptr;
	if (CreateNewWindow(cls, attr, &bounds, &window) != noErr || !window)
	{
		CFRelease(title);
		return nullptr;
	}

	window->title = title;
	window->refCon = refCon;
	applyTitle(window);

	RGBColor color;
	if (contentColorFromWctb(GetResource('wctb', windowID), &color))
		SetWindowContentColor(window, &color);

	if (behind != (WindowRef) -1)
		SendBehind(window, behind);

	if (visible)
		ShowWindow(window);

	return window;
}

WindowRef GetNewCWindow(short windowID, void* wStorage, WindowRef behind)
{
	// Carbon allocates window records itself; caller storage is not used.
	(void) wStorage;
	return newWindowFromResource(windowID, behind);
}

WindowRef GetNewWindow(short windowID, void* wStorage, WindowRef behind)
{
	(void) wStorage;
	return newWindowFromResource(windowID, behind);
}

static void destroyWindow(OpaqueWindowPtr* window)
{
	Display* dpy = Darling::Carbon::getDisplay();
	unlinkWindow(window);
	if (dpy)
	{
		x11.DestroyWindow(dpy, window->xid);
		x11.Flush(dpy);
	}
	if (window->title)
		CFRelease(window->title);
	window->magic = 0;
	free(window);
}

void DisposeWindow(WindowRef wnd)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (window)
		destroyWindow(window);
}

OSStatus RetainWindow(WindowRef wnd)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window)
		return errInvalidWindowRef;
	window->refCount++;
	return noErr;
}

OSStatus ReleaseWindow(WindowRef wnd)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window)
		return errInvalidWindowRef;
	if (--window->refCount <= 0)
		destroyWindow(window);
	return noErr;
}

void ShowWindow(WindowRef wnd)
{
	OpaqueWindowPtr* window = lookup(wnd);
	Display* dpy = Darling::Carbon::getDisplay();
	if (!window || !dpy || window->visible)
		return;
	x11.MapWindow(dpy, window->xid);
	x11.Flush(dpy);
	window->visible = true;
	restack();
}

void HideWindow(WindowRef wnd)
{
	OpaqueWindowPtr* window = lookup(wnd);
	Display* dpy = Darling::Carbon::getDisplay();
	if (!window || !dpy || !window->visible)
		return;
	x11.UnmapWindow(dpy, window->xid);
	x11.Flush(dpy);
	window->visible = false;
}

void ShowHide(WindowRef wnd, Boolean showFlag)
{
	if (showFlag)
		ShowWindow(wnd);
	else
		HideWindow(wnd);
}

Boolean IsWindowVisible(WindowRef wnd)
{
	OpaqueWindowPtr* window = lookup(wnd);
	return window ? window->visible : false;
}

void BringToFront(WindowRef wnd)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window)
		return;
	unlinkWindow(window);
	insertWindow(window, (WindowRef) -1);
	restack();
}

void SendBehind(WindowRef wnd, WindowRef behindWindow)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window || wnd == behindWindow)
		return;
	unlinkWindow(window);
	insertWindow(window, behindWindow ? behindWindow : nullptr);
	restack();
}

OSStatus SelectWindow(WindowRef wnd)
{
	if (!lookup(wnd))
		return errInvalidWindowRef;
	BringToFront(wnd);
	return noErr;
}

OSStatus SetWindowContentColor(WindowRef wnd, const RGBColor* color)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window)
		return errInvalidWindowRef;
	if (!color)
		return paramErr;
	window->contentColor = *color;
	Display* dpy = Darling::Carbon::getDisplay();
	if (dpy)
	{
		x11.SetWindowBackground(dpy, window->xid, pixelFor(dpy, color));
		x11.ClearWindow(dpy, window->xid);
		x11.Flush(dpy);
	}
	return noErr;
}

OSStatus GetWindowContentColor(WindowRef wnd, RGBColor* color)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window)
		return errInvalidWindowRef;
	if (!color)
		return paramErr;
	*color = window->contentColor;
	return noErr;
}

OSStatus SetWindowTitleWithCFString(WindowRef wnd, CFStringRef title)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window)
		return errInvalidWindowRef;
	CFStringRef copy = title ? CFStringCreateCopy(kCFAllocatorDefault, title) : nullptr;
	if (window->title)
		CFRelease(window->title);
	window->title = copy;
	applyTitle(window);
	return noErr;
}

OSStatus CopyWindowTitleAsCFString(WindowRef wnd, CFStringRef* title)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window)
		return errInvalidWindowRef;
	if (!title)
		return paramErr;
	*title = window->title ? (CFStringRef) CFRetain(window->title)
		: CFStringCreateWithPascalString(kCFAllocatorDefault, (ConstStr255Param) "", kCFStringEncodingMacRoman);
	return *title ? noErr : memFullErr;
}

void SetWTitle(WindowRef wnd, ConstStr255Param title)
{
	if (!title)
		return;
	CFStringRef string = CFStringCreateWithPascalString(kCFAllocatorDefault, title, kCFStringEncodingMacRoman);
	if (!string)
		return;
	SetWindowTitleWithCFString(wnd, string);
	CFRelease(string);
}

void GetWTitle(WindowRef wnd, Str255 title)
{
	if (!title)
		return;
	title[0] = 0;
	OpaqueWindowPtr* window = lookup(wnd);
	if (window && window->title && !CFStringGetPascalString(window->title, title, 256, kCFStringEncodingMacRoman))
		title[0] = 0;
}

void SetWRefCon(WindowRef wnd, SRefCon data)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (window)
		window->refCon = data;
}

SRefCon GetWRefCon(WindowRef wnd)
{
	OpaqueWindowPtr* window = lookup(wnd);
	return window ? window->refCon : 0;
}

OSStatus GetWindowClass(WindowRef wnd, WindowClass* outClass)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window)
		return errInvalidWindowRef;
	if (!outClass)
		return paramErr;
	*outClass = window->windowClass;
	return noErr;
}

OSStatus GetWindowAttributes(WindowRef wnd, WindowAttributes* outAttributes)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window)
		return errInvalidWindowRef;
	if (!outAttributes)
		return paramErr;
	*outAttributes = window->attributes;
	return noErr;
}

OSStatus GetWindowBounds(WindowRef wnd, WindowRegionCode region, Rect* bounds)
{
	if (!bounds)
		return paramErr;
	*bounds = Rect{};
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window)
		return errInvalidWindowRef;
	// No window frame is drawn by this backend: structure and content coincide
	if (region != kWindowContentRgn && region != kWindowStructureRgn && region != kWindowGlobalPortRgn)
		return errWindowRegionCodeInvalid;
	*bounds = window->bounds;
	return noErr;
}

Boolean IsValidWindowPtr(WindowRef wnd)
{
	return lookup(wnd) != nullptr;
}

OSStatus SetWindowGroup(WindowRef a, WindowGroupRef b)
{
	return unimpErr;
}

OSStatus SetWindowGroupLevel(WindowGroupRef a, SInt32 b)
{
	return unimpErr;
}

OSStatus TransitionWindowWithOptions(WindowRef a, WindowTransitionEffect b, WindowTransitionAction c, const HIRect * d, Boolean e, TransitionWindowOptions * f)
{
	return unimpErr;
}

OSStatus CreateWindowGroup(WindowGroupAttributes a, WindowGroupRef *b)
{
	if (!b)
		return paramErr;
	*b = 0;
	return unimpErr;
}

EventTargetRef GetWindowEventTarget(WindowRef a)
{
	// Window event targets are not implemented yet.
	return nullptr;
}

OSStatus GetWindowGroupLevel(WindowGroupRef a, SInt32 * b)
{
	if (!b)
		return paramErr;
	*b = 0;
	return unimpErr;
}

WindowGroupRef GetWindowGroupOfClass(WindowClass a)
{
	return (WindowGroupRef)0;
}

CGrafPtr GetWindowPort(WindowRef a)
{
	// No QuickDraw port exists for these windows yet.
	return (CGrafPtr)0;
}

Rect* GetWindowPortBounds(WindowRef wnd, Rect* bounds)
{
	OpaqueWindowPtr* window = lookup(wnd);
	if (!window || !bounds)
		return NULL;
	bounds->top = 0;
	bounds->left = 0;
	bounds->bottom = window->bounds.bottom - window->bounds.top;
	bounds->right = window->bounds.right - window->bounds.left;
	return bounds;
}
