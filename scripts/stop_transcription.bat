@echo off
REM Script d'arret pour le systeme de transcription v3.0
REM Ferme tous les processus Python du projet (core, ui)
REM Note: API est un thread dans core, pas un processus separe

REM Changer vers le repertoire du projet
cd /d "%~dp0\.."

REM Appeler le script PowerShell qui gere l'arret
powershell -ExecutionPolicy Bypass -File "%~dp0stop.ps1"

REM Pause pour laisser voir les resultats
timeout /t 2 /nobreak >nul
