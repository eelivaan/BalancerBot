@echo off
setlocal

echo  Resolving source path...
for %%I in ("%~dp0..") do set "SRC_WIN=%%~fI"

for /f "delims=" %%I in ('wsl wslpath "%SRC_WIN%"') do set "SRC_WSL=%%I"

set "DST_WSL=/home/eeli/pico/modules/VL53L7CX"
set "EXCLUDES=--exclude freeze --exclude cmake --exclude make"

if not defined SRC_WSL (
	echo  Failed to resolve source path for WSL.
	exit /b 1
)

echo  Copying module...
wsl bash -lc "mkdir -p \"%DST_WSL%\" && rsync -a --delete %EXCLUDES% \"%SRC_WSL%\"/ \"%DST_WSL%\"/"

if errorlevel 1 (
	echo  Copy failed.
	exit /b 1
)

echo  Copied %SRC_WIN% to
echo         %DST_WSL%/
exit /b 0
