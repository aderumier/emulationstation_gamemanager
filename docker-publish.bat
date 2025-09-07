@echo off
REM GameManager Docker Publishing Script for Windows
REM This script helps publish the GameManager Docker image to DockerHub

setlocal enabledelayedexpansion

REM Configuration
set IMAGE_NAME=gamemanager
set VERSION=1.6-1
set DOCKERHUB_USERNAME=

REM Function to print colored output (Windows doesn't support colors in batch, so we'll use echo)
echo [INFO] GameManager Docker Publishing Script
echo [INFO] Version: %VERSION%
echo.

REM Check if Docker is running
echo [INFO] Checking Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running or not accessible
    echo [INFO] Please start Docker Desktop and try again
    pause
    exit /b 1
)
echo [SUCCESS] Docker is running
echo.

REM Get DockerHub username if not provided
if "%DOCKERHUB_USERNAME%"=="" (
    set /p DOCKERHUB_USERNAME="Enter your DockerHub username: "
    if "!DOCKERHUB_USERNAME!"=="" (
        echo [ERROR] DockerHub username is required
        pause
        exit /b 1
    )
)

REM Check command line arguments
set BUILD_ONLY=false
set PUSH_ONLY=false

:parse_args
if "%1"=="-u" (
    set DOCKERHUB_USERNAME=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--username" (
    set DOCKERHUB_USERNAME=%2
    shift
    shift
    goto parse_args
)
if "%1"=="-v" (
    set VERSION=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--version" (
    set VERSION=%2
    shift
    shift
    goto parse_args
)
if "%1"=="-b" (
    set BUILD_ONLY=true
    shift
    goto parse_args
)
if "%1"=="--build-only" (
    set BUILD_ONLY=true
    shift
    goto parse_args
)
if "%1"=="-p" (
    set PUSH_ONLY=true
    shift
    goto parse_args
)
if "%1"=="--push-only" (
    set PUSH_ONLY=true
    shift
    goto parse_args
)
if "%1"=="-h" (
    goto show_help
)
if "%1"=="--help" (
    goto show_help
)
if "%1"=="" (
    goto main
)
echo [ERROR] Unknown option: %1
goto show_help

:show_help
echo Usage: %0 [OPTIONS]
echo.
echo Options:
echo   -u, --username USERNAME    DockerHub username
echo   -v, --version VERSION      Image version (default: 1.6-1)
echo   -b, --build-only          Only build the image, don't push
echo   -p, --push-only           Only push existing images, don't build
echo   -h, --help                Show this help message
echo.
echo Examples:
echo   %0 -u myusername                    # Build and push with username
echo   %0 -u myusername -v 1.7.0          # Build and push specific version
echo   %0 -u myusername -b                 # Only build, don't push
echo   %0 -u myusername -p                 # Only push existing images
pause
exit /b 0

:main
if "%PUSH_ONLY%"=="false" (
    REM Build image
    echo [INFO] Building Docker image: %IMAGE_NAME%:%VERSION%
    docker build -t %IMAGE_NAME%:%VERSION% .
    if errorlevel 1 (
        echo [ERROR] Failed to build image
        pause
        exit /b 1
    )
    echo [SUCCESS] Image built successfully
    echo.
)

if "%BUILD_ONLY%"=="false" (
    REM Login to DockerHub
    echo [INFO] Logging into DockerHub...
    docker login
    if errorlevel 1 (
        echo [ERROR] Failed to login to DockerHub
        pause
        exit /b 1
    )
    echo [SUCCESS] Successfully logged into DockerHub
    echo.
    
    REM Tag images
    echo [INFO] Tagging images...
    docker tag %IMAGE_NAME%:%VERSION% %DOCKERHUB_USERNAME%/%IMAGE_NAME%:%VERSION%
    docker tag %IMAGE_NAME%:%VERSION% %DOCKERHUB_USERNAME%/%IMAGE_NAME%:latest
    echo [SUCCESS] Images tagged successfully
    echo.
    
    REM Push images
    echo [INFO] Pushing images to DockerHub...
    echo [INFO] Pushing %DOCKERHUB_USERNAME%/%IMAGE_NAME%:%VERSION%...
    docker push %DOCKERHUB_USERNAME%/%IMAGE_NAME%:%VERSION%
    if errorlevel 1 (
        echo [ERROR] Failed to push versioned image
        pause
        exit /b 1
    )
    echo [SUCCESS] Versioned image pushed successfully
    
    echo [INFO] Pushing %DOCKERHUB_USERNAME%/%IMAGE_NAME%:latest...
    docker push %DOCKERHUB_USERNAME%/%IMAGE_NAME%:latest
    if errorlevel 1 (
        echo [ERROR] Failed to push latest image
        pause
        exit /b 1
    )
    echo [SUCCESS] Latest image pushed successfully
    echo.
    
    echo [SUCCESS] All done! Your images are now available on DockerHub:
    echo [INFO]   %DOCKERHUB_USERNAME%/%IMAGE_NAME%:%VERSION%
    echo [INFO]   %DOCKERHUB_USERNAME%/%IMAGE_NAME%:latest
    echo.
    echo [INFO] Users can now pull your image with:
    echo [INFO]   docker pull %DOCKERHUB_USERNAME%/%IMAGE_NAME%:latest
) else (
    echo [SUCCESS] Build completed. Image: %IMAGE_NAME%:%VERSION%
)

echo.
pause


