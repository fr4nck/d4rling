// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <CoreServices/MacTypes.h>
#include <CoreServices/FileManager.h>
using FSIORefNum = int;
enum { fsCurPerm = 0, fsRdPerm = 1, fsWrPerm = 2, fsRdWrPerm = 3 };
extern "C" OSErr FSGetDataForkName(HFSUniStr255*);
extern "C" OSErr FSGetResourceForkName(HFSUniStr255*);
