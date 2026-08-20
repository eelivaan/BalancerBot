@echo off
setlocal

set "ROOT=%~dp0"

rem Source directories to copy
set "SRC_SOUND=%ROOT%sound-api"
set "SRC_VL53=%ROOT%VL53L7CX-api"

rem Destination in the WSL Pico modules folder
set "DST_WSL=/home/eeli/pico/modules"

for %%I in ("%ROOT%.") do set "ROOT_WIN=%%~fI"
for /f "delims=" %%I in ('wsl wslpath "%ROOT_WIN%"') do set "ROOT_WSL=%%I"

if not defined ROOT_WSL (
    echo  Failed to resolve workspace path for WSL.
    exit /b 1
)

if not exist "%SRC_SOUND%" (
    echo  Missing source folder: %SRC_SOUND%
    exit /b 1
)

if not exist "%SRC_VL53%" (
    echo  Missing source folder: %SRC_VL53%
    exit /b 1
)

echo  Copying native modules to %DST_WSL%...

wsl bash -lc "mkdir -p \"%DST_WSL%\" && rsync -a --delete \"%ROOT_WSL%/sound-api\"/ \"%DST_WSL%/sound\"/ && rsync -a --delete --exclude freeze --exclude cmake --exclude make \"%ROOT_WSL%/VL53L7CX-api\"/ \"%DST_WSL%/VL53L7CX\"/"

if errorlevel 1 (
    echo  Copy failed.
    exit /b 1
)

echo  Copied native modules from
echo         %ROOT_WIN%
echo  to
echo         %DST_WSL%/
exit /b 0
