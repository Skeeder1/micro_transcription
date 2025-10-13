@echo off
REM Active le venv si présent, sinon utilise python global
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python mic_visualizer.py
