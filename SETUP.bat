@echo off
REM ============================================================
REM  Klicker MCP Server - Windows Setup Script
REM  Run this once to get everything installed and configured.
REM ============================================================
echo.
echo ================================================
echo   Klicker MCP Server Setup
echo   Connecting: GA4, Google Ads, GTM, Ahrefs
echo ================================================
echo.

REM Step 1: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please download Python from: https://www.python.org/downloads/
    echo IMPORTANT: During install, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo [OK] Python found

REM Step 2: Get script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Step 3: Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Step 4: Install dependencies
echo.
echo Installing Python packages...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install packages. Check above for details.
    pause
    exit /b 1
)
echo [OK] Packages installed

REM Step 5: Create credentials directory
if not exist credentials (
    mkdir credentials
    echo [OK] Created credentials folder
)

REM Step 6: Check credentials
echo.
echo ================================================
echo   Checking credentials...
echo ================================================
echo.

set GA_CREDS=credentials\google-analytics-credentials.json
set ADS_CREDS=credentials\google-ads-credentials.json
set GTM_CREDS=credentials\google-tag-manager-credentials.json
set AHREFS_CREDS=credentials\ahrefs-api-key.txt

set ALL_DONE=1

if exist "%GA_CREDS%" (
    echo [GA4] Credentials found
) else (
    echo [GA4] NOT configured - see docs\GOOGLE-ANALYTICS-SETUP.md
    set ALL_DONE=0
)

if exist "%ADS_CREDS%" (
    echo [Ads] Credentials found
) else (
    echo [Ads] NOT configured - see docs\GOOGLE-ADS-SETUP.md
    set ALL_DONE=0
)

if exist "%GTM_CREDS%" (
    echo [GTM] Credentials found
) else (
    echo [GTM] NOT configured - see docs\GOOGLE-TAG-MANAGER-SETUP.md
    set ALL_DONE=0
)

if exist "%AHREFS_CREDS%" (
    echo [Ahrefs] API key found
) else (
    echo [Ahrefs] NOT configured - see docs\AHREFS-SETUP.md
    set ALL_DONE=0
)

echo.

if "%ALL_DONE%"=="1" (
    echo ================================================
    echo   All set! Here is how to connect to Claude:
    echo ================================================
    echo.
    echo 1. Open Claude Desktop
    echo 2. Go to Settings (wrench icon) -^> MCP Servers
    echo 3. Click "Add MCP Server"
    echo 4. Fill in:
    echo.
    echo    Name:    marketing-mcp
    echo    Command: python
    echo    Args:    -m marketing_mcp.server
    echo.
    echo 5. For Working Directory, paste this path:
    echo    %CD%
    echo.
    echo Then ask Claude:
    echo   "Show me my GA traffic for the last 30 days"
    echo   "What's my Google Ads spend this month?"
    echo.
) else (
    echo ================================================
    echo   Setup complete, but some credentials are missing.
    echo ================================================
    echo.
    echo Read the docs in the "docs" folder for each service
    echo you want to connect. Then restart this setup:
    echo   python scripts\setup_google_ads.py
    echo   python scripts\setup_gtm.py
    echo   python scripts\setup_ahrefs.py
    echo.
)

echo ================================================
echo  To test the server manually, run:
echo  python -m marketing_mcp.server
echo ================================================
echo.
pause