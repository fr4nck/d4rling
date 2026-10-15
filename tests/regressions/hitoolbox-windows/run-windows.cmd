@echo off
setlocal
where cl >nul 2>&1
if errorlevel 1 (
  echo Run from a Visual Studio x64 Native Tools command prompt.
  exit /b 2
)
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /EHsc /W3 /FI"%~dp0msvc-attributes.h" /Iinclude ..\..\..\src\frameworks\Carbon\HIToolbox\src\MacWindows.cpp test_windows.cpp /Fobuild\ /Febuild\hitoolbox_contract_test.exe
if errorlevel 1 (
  popd
  exit /b 3
)
build\hitoolbox_contract_test.exe
set result=%errorlevel%
popd
exit /b %result%
