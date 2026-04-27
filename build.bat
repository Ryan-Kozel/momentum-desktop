@echo off
echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building Momentum.exe...
pyinstaller --onefile --windowed --name "Momentum" ^
    --icon="logo.ico" ^
    --add-data "logo.ico;." ^
    --collect-all customtkinter ^
    --collect-data matplotlib ^
    --collect-data tkcalendar ^
    main.py

echo.
echo Done! Your exe is at: dist\Momentum.exe
echo Copy it anywhere — it carries all dependencies with it.
echo The momentum.db database will be created next to the exe on first run.
pause
