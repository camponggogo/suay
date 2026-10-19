@echo off
setlocal
cd /d "%~dp0"
docker build -t petals-client .
if errorlevel 1 exit /b 1
docker run --rm -it --network host -v petals-client-cache:/cache petals-client %*
