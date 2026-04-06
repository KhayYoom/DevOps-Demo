@echo off
REM =============================================================================
REM  DOCKER & DEPLOYMENT PIPELINE SIMULATOR (Windows)
REM =============================================================================
REM
REM  This script simulates what happens in Labs 7 & 8:
REM  building a Docker image, running the container, and testing it.
REM
REM  The Pipeline Stages:
REM
REM   [1.CHECK] --> [2.DEPS] --> [3.UNIT] --> [4.DOCKER] -->
REM   [5.BUILD] --> [6.RUN]  --> [7.HEALTH] --> [8.CLEANUP]
REM
REM  Usage: scripts\run-pipeline.bat  (from the lab-docker-deploy folder)
REM
REM =============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo.
echo ============================================================
echo      DOCKER ^& DEPLOYMENT PIPELINE - Starting...
echo ============================================================
echo.
echo   Project:   %CD%
echo   Timestamp: %DATE% %TIME%
python --version 2>nul
echo.

REM ===========================================================================
REM STAGE 1: CHECK FILES
REM ===========================================================================

echo.
echo ----------------------------------------------------------
echo   STAGE 1/8 - CHECK (Verify Project Structure)
echo ----------------------------------------------------------
echo.
echo   Checking that all required files exist...

set "ALL_FOUND=1"

if exist "app\__init__.py"                (echo     [OK] app\__init__.py) else (echo     [MISSING] app\__init__.py & set "ALL_FOUND=0")
if exist "app\inventory.py"              (echo     [OK] app\inventory.py) else (echo     [MISSING] app\inventory.py & set "ALL_FOUND=0")
if exist "app\database.py"              (echo     [OK] app\database.py) else (echo     [MISSING] app\database.py & set "ALL_FOUND=0")
if exist "app\cache.py"                 (echo     [OK] app\cache.py) else (echo     [MISSING] app\cache.py & set "ALL_FOUND=0")
if exist "app\api.py"                   (echo     [OK] app\api.py) else (echo     [MISSING] app\api.py & set "ALL_FOUND=0")
if exist "tests\unit\test_inventory.py" (echo     [OK] tests\unit\test_inventory.py) else (echo     [MISSING] tests\unit\test_inventory.py & set "ALL_FOUND=0")
if exist "tests\integration\test_api.py" (echo     [OK] tests\integration\test_api.py) else (echo     [MISSING] tests\integration\test_api.py & set "ALL_FOUND=0")
if exist "Dockerfile"                   (echo     [OK] Dockerfile) else (echo     [MISSING] Dockerfile & set "ALL_FOUND=0")
if exist "requirements.txt"             (echo     [OK] requirements.txt) else (echo     [MISSING] requirements.txt & set "ALL_FOUND=0")

if "%ALL_FOUND%"=="0" (
    echo.
    echo   [FAILED] Missing required files!
    echo   PIPELINE STOPPED at stage: CHECK
    exit /b 1
)

echo.
echo   [PASSED] All source files present
echo.

REM ===========================================================================
REM STAGE 2: INSTALL DEPENDENCIES
REM ===========================================================================

echo.
echo ----------------------------------------------------------
echo   STAGE 2/8 - DEPS (Install Dependencies)
echo ----------------------------------------------------------
echo.
echo   Installing Python dependencies from requirements.txt...
echo.

python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo   [FAILED] Could not install dependencies!
    echo   PIPELINE STOPPED at stage: DEPS
    exit /b 1
)

echo.
echo   [PASSED] Dependencies installed successfully
echo.

REM ===========================================================================
REM STAGE 3: UNIT TESTS
REM ===========================================================================

echo.
echo ----------------------------------------------------------
echo   STAGE 3/8 - UNIT TESTS (fast, no services needed)
echo ----------------------------------------------------------
echo.
echo   Running unit tests against inventory.py...
echo.

python -m pytest tests/unit/ -v --tb=short
if errorlevel 1 (
    echo.
    echo   [FAILED] Unit tests failed!
    echo   Hint: Look at the FAILED line above.
    echo   PIPELINE STOPPED at stage: UNIT TESTS
    exit /b 1
)

echo.
echo   [PASSED] Unit tests passed
echo.

REM ===========================================================================
REM STAGE 4: CHECK DOCKER
REM ===========================================================================

echo.
echo ----------------------------------------------------------
echo   STAGE 4/8 - DOCKER CHECK (Is Docker installed?)
echo ----------------------------------------------------------
echo.

docker --version >nul 2>&1
if errorlevel 1 (
    echo     [WARNING] Docker is NOT installed or not in PATH
    echo     Install Docker Desktop to run stages 5-8
    echo     https://docs.docker.com/get-docker/
    echo.
    echo   Skipping Docker stages. Unit tests passed!
    echo.
    echo ============================================================
    echo     PIPELINE PASSED (Docker stages skipped)
    echo ============================================================
    exit /b 0
)

echo     [OK] Docker found
docker info >nul 2>&1
if errorlevel 1 (
    echo     [WARNING] Docker daemon is not running
    echo     Start Docker Desktop and try again
    echo.
    echo   Skipping Docker stages. Unit tests passed!
    echo.
    echo ============================================================
    echo     PIPELINE PASSED (Docker stages skipped)
    echo ============================================================
    exit /b 0
)

echo     [OK] Docker daemon is running
echo.
echo   [PASSED] Docker is available
echo.

REM ===========================================================================
REM STAGE 5: BUILD DOCKER IMAGE
REM ===========================================================================

echo.
echo ----------------------------------------------------------
echo   STAGE 5/8 - BUILD (Build Docker Image)
echo ----------------------------------------------------------
echo.
echo   Building Docker image: inventory-api:local ...
echo.

docker build -t inventory-api:local .
if errorlevel 1 (
    echo.
    echo   [FAILED] Docker build failed!
    echo   PIPELINE STOPPED at stage: BUILD
    exit /b 1
)

echo.
echo   [PASSED] Docker image built successfully
echo.

REM ===========================================================================
REM STAGE 6: RUN CONTAINER
REM ===========================================================================

echo.
echo ----------------------------------------------------------
echo   STAGE 6/8 - RUN (Start Container)
echo ----------------------------------------------------------
echo.
echo   Starting container on port 8080...

docker rm -f inventory-api-test >nul 2>&1
docker run -d --name inventory-api-test -p 8080:8080 inventory-api:local
if errorlevel 1 (
    echo.
    echo   [FAILED] Could not start container!
    echo   PIPELINE STOPPED at stage: RUN
    exit /b 1
)

echo   Waiting for container to start...
timeout /t 3 /nobreak >nul

echo.
echo   [PASSED] Container started
echo.

REM ===========================================================================
REM STAGE 7: HEALTH CHECK
REM ===========================================================================

echo.
echo ----------------------------------------------------------
echo   STAGE 7/8 - HEALTH CHECK (Test /health Endpoint)
echo ----------------------------------------------------------
echo.
echo   Sending GET request to http://localhost:8080/health ...
echo.

curl -s http://localhost:8080/health > health_response.tmp 2>&1
type health_response.tmp
echo.

findstr /C:"healthy" health_response.tmp >nul 2>&1
if errorlevel 1 (
    del health_response.tmp 2>nul
    echo.
    echo   [FAILED] Health check failed!
    docker logs inventory-api-test
    docker rm -f inventory-api-test >nul 2>&1
    echo   PIPELINE STOPPED at stage: HEALTH CHECK
    exit /b 1
)

del health_response.tmp 2>nul
echo.
echo   [PASSED] Health check passed
echo.

REM ===========================================================================
REM STAGE 8: CLEANUP
REM ===========================================================================

echo.
echo ----------------------------------------------------------
echo   STAGE 8/8 - CLEANUP (Stop ^& Remove Container)
echo ----------------------------------------------------------
echo.
echo   Stopping container...
docker stop inventory-api-test >nul 2>&1
docker rm inventory-api-test >nul 2>&1

echo.
echo   [PASSED] Container cleaned up
echo.

REM ===========================================================================
REM PIPELINE COMPLETE
REM ===========================================================================

echo.
echo ============================================================
echo.
echo        PIPELINE PASSED SUCCESSFULLY!
echo.
echo ============================================================
echo.
echo   Pipeline Summary:
echo     [PASSED] Check      - Project structure verified
echo     [PASSED] Deps       - Dependencies installed
echo     [PASSED] Unit Tests - All business logic working
echo     [PASSED] Docker     - Docker is available
echo     [PASSED] Build      - Docker image built
echo     [PASSED] Run        - Container started
echo     [PASSED] Health     - API responding correctly
echo     [PASSED] Cleanup    - Container removed
echo.

endlocal
