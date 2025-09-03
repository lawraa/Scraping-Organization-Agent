@echo off
REM =====================================================
REM  Setup Anaconda Virtual Environment from requirements.txt
REM =====================================================

REM Change this to the environment name you want
set ENV_NAME=myenv

REM Path to your requirements.txt (edit if needed)
set REQ_FILE=requirements.txt

echo Creating new conda environment: %ENV_NAME% ...
conda create -y -n %ENV_NAME% python=3.11

echo Activating environment...
call conda activate %ENV_NAME%

echo Installing dependencies from %REQ_FILE% ...
pip install -r %REQ_FILE%

echo Done! Your environment '%ENV_NAME%' is ready.
echo To activate later, run:
echo   conda activate %ENV_NAME%
pause
