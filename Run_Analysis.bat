@echo off
echo ===================================================
echo   NVDA Institutional Research Agent - Auto Runner
echo ===================================================

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python.
    pause
    exit /b
)

:: 2. Install/Update Dependencies
echo [STEP 1/3] Checking and installing dependencies...
pip install pandas matplotlib seaborn fpdf2 python-dotenv yfinance requests openai >nul

:: 3. Run the Main Analysis
echo [STEP 2/3] Running financial analysis and AI synthesis...
echo (This may take 60-90 seconds due to deep synthesis)
python main.py

:: 4. Check if PDF was generated and open it
echo [STEP 3/3] Finalizing report...
set "LATEST_PDF="
for /f "tokens=*" %%a in ('dir /b /s /o-d "data\processed\NVDA_Investment_Report_*.pdf" 2^>nul') do (
    set "LATEST_PDF=%%a"
    goto :found
)

:found
if defined LATEST_PDF (
    echo [SUCCESS] Report generated successfully: %LATEST_PDF%
    echo Opening now...
    start "" "%LATEST_PDF%"
) else (
    echo [ERROR] PDF report was not found. Please check terminal errors above.
)

echo ===================================================
echo   Process Complete.
echo ===================================================
pause
