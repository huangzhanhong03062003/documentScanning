@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PYTHON_EXE="
set "PY_LAUNCHER="

for %%I in (python.exe) do (
    for /f "delims=" %%P in ('where %%I 2^>nul') do (
        echo %%P | find /I "WindowsApps" >nul
        if errorlevel 1 if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
    )
)

for %%I in (py.exe) do (
    for /f "delims=" %%P in ('where %%I 2^>nul') do (
        echo %%P | find /I "WindowsApps" >nul
        if errorlevel 1 if not defined PY_LAUNCHER set "PY_LAUNCHER=%%P"
    )
)

if not defined PYTHON_EXE (
    for %%I in ("%LocalAppData%\Programs\Python\Python*\python.exe") do (
        if exist "%%~fI" if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
    )
)

if not defined PYTHON_EXE (
    for %%I in ("%ProgramFiles%\Python*\python.exe") do (
        if exist "%%~fI" if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
    )
)

if not defined PYTHON_EXE (
    for %%I in ("%ProgramFiles(x86)%\Python*\python.exe") do (
        if exist "%%~fI" if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
    )
)

if not defined PYTHON_EXE (
    echo Python was not found.
    if defined PY_LAUNCHER (
        echo A Python launcher was found:
        echo %PY_LAUNCHER%
        echo.
        echo You can also try launching from that installation manually.
        echo.
    )
    echo Please install Python and select "Add python.exe to PATH" during setup.
    echo Download: https://www.python.org/downloads/windows/
    pause
    exit /b 1
)

echo Using Python:
echo %PYTHON_EXE%
echo.
"%PYTHON_EXE%" --version
echo.
echo Launching CLI scanner...
echo.

"%PYTHON_EXE%" "%~dp0file_scanner_cli.py"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo The CLI scanner exited with code %EXIT_CODE%.
) else (
    echo The CLI scanner finished successfully.
)
pause

endlocal
exit /b %EXIT_CODE%
