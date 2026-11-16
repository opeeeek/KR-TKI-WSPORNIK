@echo off
REM Budowa KRÓTKI WSPORNIK ST dla Windows (wymaga Python 3.10+ w PATH).
REM Wynik: dist\KrotkiWspornikST\KrotkiWspornikST.exe oraz (opcjonalnie) instalator Inno Setup.
setlocal
cd /d %~dp0\..
python -m venv .venv-build || goto :error
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip || goto :error
pip install -r requirements-dev.txt || goto :error
set QT_QPA_PLATFORM=offscreen
python -m pytest -q || goto :error
set QT_QPA_PLATFORM=
pyinstaller --noconfirm --clean packaging\krotki_wspornik_st.spec || goto :error
where iscc >nul 2>nul && iscc packaging\installer.iss
echo.
echo Gotowe: dist\KrotkiWspornikST\KrotkiWspornikST.exe
exit /b 0
:error
echo Blad budowy (kod %errorlevel%).
exit /b 1
