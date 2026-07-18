@echo off
setlocal

for %%I in ("%~dp0..") do set "SRC_WIN=%%~fI"

for /f "delims=" %%I in ('wsl wslpath "%SRC_WIN%"') do set "SRC_WSL=%%I"

set "DST_WSL=/home/eeli/pico/modules/VL53L7CX"
set "EXCLUDES=--exclude freeze --exclude cmake --exclude make"

if not defined SRC_WSL (
	echo Failed to resolve source path for WSL.
	pause
	exit /b 1
)

wsl bash -lc "mkdir -p \"%DST_WSL%\" && rsync -a --delete %EXCLUDES% \"%SRC_WSL%\"/ \"%DST_WSL%\"/"

if errorlevel 1 (
	echo Copy failed.
	pause
	exit /b 1
)

echo Copied %SRC_WIN% to %DST_WSL%/ with exclusions.
	pause
exit /b 0
