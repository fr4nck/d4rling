#ifndef MACWINDOWS_H
#define MACWINDOWS_H
#include <CarbonCore/MacErrors.h>
#include "CoreServices/MacTypes.h"
#include <HIToolbox/CarbonEventsCore.h>
#include <stdint.h>
#include <QD/QD.h>

#pragma pack(2)

#ifdef __cplusplus
extern "C" {
#endif

typedef WindowRef HIWindowRef;
typedef int WindowGroupRef;
typedef uint32_t WindowClass;
typedef OptionBits WindowAttributes;
typedef OptionBits WindowGroupAttributes;
typedef uint16_t WindowRegionCode;
typedef Rect HIRect;
typedef void* TransitionWindowOptions;
typedef uint32_t WindowTransitionAction;
typedef uint32_t WindowTransitionEffect;

// Window classes, attributes and region codes (public MacWindows.h values)
enum {
	kAlertWindowClass = 1,
	kMovableAlertWindowClass = 2,
	kModalWindowClass = 3,
	kMovableModalWindowClass = 4,
	kFloatingWindowClass = 5,
	kDocumentWindowClass = 6,
	kUtilityWindowClass = 8,
	kHelpWindowClass = 10,
	kSheetWindowClass = 11,
	kToolbarWindowClass = 12,
	kPlainWindowClass = 13,
	kOverlayWindowClass = 14,
	kSheetAlertWindowClass = 15,
	kAltPlainWindowClass = 16,
	kSimpleWindowClass = 18,
	kDrawerWindowClass = 20,
	kAllWindowClasses = 0xFFFFFFFF
};

enum {
	kWindowNoAttributes = 0,
	kWindowCloseBoxAttribute = (1u << 0),
	kWindowHorizontalZoomAttribute = (1u << 1),
	kWindowVerticalZoomAttribute = (1u << 2),
	kWindowFullZoomAttribute = (kWindowVerticalZoomAttribute | kWindowHorizontalZoomAttribute),
	kWindowCollapseBoxAttribute = (1u << 3),
	kWindowResizableAttribute = (1u << 4),
	kWindowSideTitlebarAttribute = (1u << 5),
	kWindowNoUpdatesAttribute = (1u << 16),
	kWindowNoActivatesAttribute = (1u << 17),
	kWindowStandardDocumentAttributes = (kWindowCloseBoxAttribute | kWindowFullZoomAttribute | kWindowCollapseBoxAttribute | kWindowResizableAttribute)
};

enum {
	kWindowTitleBarRgn = 0,
	kWindowTitleTextRgn = 1,
	kWindowCloseBoxRgn = 2,
	kWindowZoomBoxRgn = 3,
	kWindowDragRgn = 5,
	kWindowGrowRgn = 6,
	kWindowCollapseBoxRgn = 7,
	kWindowTitleProxyIconRgn = 8,
	kWindowStructureRgn = 32,
	kWindowContentRgn = 33,
	kWindowUpdateRgn = 34,
	kWindowOpaqueRgn = 35,
	kWindowGlobalPortRgn = 40
};

OSStatus CreateNewWindow(WindowClass cls, WindowAttributes attr, const Rect* rect, WindowRef* newWindow);
WindowRef GetNewCWindow(short windowID, void* wStorage, WindowRef behind);
WindowRef GetNewWindow(short windowID, void* wStorage, WindowRef behind);
void DisposeWindow(WindowRef wnd);
void ShowWindow(WindowRef wnd);
void HideWindow(WindowRef wnd);
void ShowHide(WindowRef wnd, Boolean showFlag);
Boolean IsWindowVisible(WindowRef wnd);
OSStatus SelectWindow(WindowRef a);
void BringToFront(WindowRef wnd);
void SendBehind(WindowRef wnd, WindowRef behindWindow);
OSStatus SetWindowContentColor(WindowRef a, const RGBColor * b);
OSStatus GetWindowContentColor(WindowRef a, RGBColor * b);
OSStatus SetWindowGroup(WindowRef a, WindowGroupRef b);
OSStatus SetWindowGroupLevel(WindowGroupRef a, SInt32 b);
OSStatus SetWindowTitleWithCFString(WindowRef a, CFStringRef b);
OSStatus CopyWindowTitleAsCFString(WindowRef a, CFStringRef* b);
void SetWTitle(WindowRef wnd, ConstStr255Param title);
void GetWTitle(WindowRef wnd, Str255 title);
void SetWRefCon(WindowRef wnd, SRefCon data);
SRefCon GetWRefCon(WindowRef wnd);
OSStatus GetWindowClass(WindowRef wnd, WindowClass* outClass);
OSStatus GetWindowAttributes(WindowRef wnd, WindowAttributes* outAttributes);
OSStatus TransitionWindowWithOptions(WindowRef a, WindowTransitionEffect b, WindowTransitionAction c, const HIRect * d, Boolean e, TransitionWindowOptions * f);
OSStatus CreateWindowGroup(WindowGroupAttributes a, WindowGroupRef *b);
OSStatus GetWindowBounds(WindowRef a, WindowRegionCode b, Rect * c);
EventTargetRef GetWindowEventTarget(WindowRef a);
OSStatus GetWindowGroupLevel(WindowGroupRef a, SInt32 * b);
WindowGroupRef GetWindowGroupOfClass(WindowClass a);
CGrafPtr GetWindowPort(WindowRef a);
Rect* GetWindowPortBounds(WindowRef window, Rect * bounds);
Boolean IsValidWindowPtr(WindowRef a);
OSStatus ReleaseWindow(WindowRef a);
OSStatus RetainWindow(WindowRef a);

#ifdef __cplusplus
}
#endif

#pragma pack()

#endif
