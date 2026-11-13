@echo off
REM ============================================================================
REM BlazeDemo Performance Testing - Windows Batch Script
REM Εργασία Μαθήματος: Απόδοση Συστημάτων 2025
REM ============================================================================

setlocal enabledelayedexpansion

REM Configuration - ΑΛΛΑΞΤΕ ΤΟ PATH ΤΟΥ JMETER
REM Set JMETER_HOME environment variable to your own installed JMeter directory before running.
if not defined JMETER_HOME (
  echo Configure JMETER_HOME first.
  exit /b 1
)
if not defined ALLOW_AUTHORIZED_LOAD_TESTS (
  echo This script can generate significant external traffic. Set ALLOW_AUTHORIZED_LOAD_TESTS=1 only if you have authorization to load test the target host.
  exit /b 1
)
set JMETER_BIN=%JMETER_HOME%\bin\jmeter-n.cmd
set TEST_PLAN=%~dp0..\jmeter\blazedemo_test_plan.jmx
set RESULTS_DIR=%~dp0..\generated\results
set REPORTS_DIR=%~dp0..\generated\reports

REM Test parameters
set "THREADS=10 50 100 200"
set "INTERARRIVAL=500 1000"
set "LOAD_MIX_A=100 50 0"
set "LOAD_MIX_B=0 50 100"
set DURATION=60
set RAMPUP=1

REM Create directories
if not exist "%RESULTS_DIR%" mkdir "%RESULTS_DIR%"
if not exist "%REPORTS_DIR%" mkdir "%REPORTS_DIR%"

echo ================================================
echo BlazeDemo Performance Testing - Batch Execution
echo ================================================
echo.

set EXPERIMENT_NUM=0

REM Main execution loop
for %%t in (%THREADS%) do (
    for %%i in (%INTERARRIVAL%) do (
        REM Load mix combinations
        call :run_test %%t %%i 100 0
        call :run_test %%t %%i 50 50
        call :run_test %%t %%i 0 100
    )
)

echo.
echo ================================================
echo All experiments completed!
echo ================================================
echo Results directory: %RESULTS_DIR%\
echo Reports directory: %REPORTS_DIR%\
echo.
pause
goto :eof

:run_test
    set /a EXPERIMENT_NUM+=1
    set THREADS_VAL=%1
    set INTERARRIVAL_VAL=%2
    set SCENARIO_A=%3
    set SCENARIO_B=%4

    set TEST_ID=t%THREADS_VAL%_ia%INTERARRIVAL_VAL%_mix%SCENARIO_A%-%SCENARIO_B%
    set RESULT_FILE=%RESULTS_DIR%\results_!TEST_ID!.csv
    set REPORT_DIR=%REPORTS_DIR%\report_!TEST_ID!
    set LOG_FILE=%RESULTS_DIR%\jmeter_!TEST_ID!.log

    echo ================================================
    echo [!EXPERIMENT_NUM!] Running: !TEST_ID!
    echo   Threads: %THREADS_VAL%
    echo   Inter-arrival: %INTERARRIVAL_VAL%ms
    echo   Load mix: Scenario A %SCENARIO_A%%% / Scenario B %SCENARIO_B%%%
    echo ================================================

    REM Run JMeter using Java directly
    java -jar "%JMETER_HOME%\bin\ApacheJMeter.jar" -n ^
        -t "%TEST_PLAN%" ^
        -l "!RESULT_FILE!" ^
        -e -o "!REPORT_DIR!" ^
        -Jthreads=%THREADS_VAL% ^
        -Jrampup=%RAMPUP% ^
        -Jduration=%DURATION% ^
        -Jinterarrival=%INTERARRIVAL_VAL% ^
        -Jscenario_a_percent=%SCENARIO_A% ^
        -Jscenario_b_percent=%SCENARIO_B% ^
        -j "!LOG_FILE!"

    if !ERRORLEVEL! EQU 0 (
        echo [SUCCESS] Experiment !TEST_ID! completed
        echo   Results: !RESULT_FILE!
        echo   Report: !REPORT_DIR!\index.html
    ) else (
        echo [ERROR] Experiment !TEST_ID! FAILED
        echo   Check log: !LOG_FILE!
    )

    echo.
    echo Cooldown 30s...
    timeout /t 30 /nobreak >nul
    echo.

goto :eof
