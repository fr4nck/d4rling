#pragma once
// Minimal standalone ABI-compatible types for contract tests. NOT the Darling SDK.
#include <stdint.h>
#include <stddef.h>
typedef int32_t OSStatus;
typedef uint8_t Boolean;
typedef int32_t SInt32;
typedef struct OpaqueWindow* WindowRef;
typedef void* CGrafPtr;
typedef const void* CFStringRef;
typedef uint32_t WindowClass;
typedef uint32_t WindowAttributes;
typedef uint32_t WindowGroupAttributes;
typedef int WindowGroupRef;
typedef uint32_t WindowRegionCode;
typedef uint32_t WindowTransitionEffect;
typedef uint32_t WindowTransitionAction;
typedef struct { int16_t top, left, bottom, right; } Rect;
typedef Rect HIRect;
typedef struct { uint16_t red, green, blue; } RGBColor;
typedef void* TransitionWindowOptions;
static const OSStatus noErr = 0;
static const OSStatus paramErr = -50;
static const OSStatus unimpErr = -4;

OSStatus CreateNewWindow(WindowClass, WindowAttributes, const Rect*, WindowRef*);
void DisposeWindow(WindowRef);
void ShowWindow(WindowRef);
void HideWindow(WindowRef);
void ShowHide(WindowRef, Boolean);
Boolean IsWindowVisible(WindowRef);
OSStatus SelectWindow(WindowRef);
OSStatus SetWindowContentColor(WindowRef, const RGBColor*);
OSStatus SetWindowGroup(WindowRef, WindowGroupRef);
OSStatus SetWindowGroupLevel(WindowGroupRef, SInt32);
OSStatus SetWindowTitleWithCFString(WindowRef, CFStringRef);
OSStatus TransitionWindowWithOptions(WindowRef, WindowTransitionEffect, WindowTransitionAction, const HIRect*, Boolean, TransitionWindowOptions*);
OSStatus CreateWindowGroup(WindowGroupAttributes, WindowGroupRef*);
OSStatus GetWindowBounds(WindowRef, WindowRegionCode, Rect*);
OSStatus GetWindowEventTarget(WindowRef);
OSStatus GetWindowGroupLevel(WindowGroupRef, SInt32*);
WindowGroupRef GetWindowGroupOfClass(WindowClass);
CGrafPtr GetWindowPort(WindowRef);
Rect* GetWindowPortBounds(WindowRef, Rect*);
Boolean IsValidWindowPtr(WindowRef);
OSStatus ReleaseWindow(WindowRef);
