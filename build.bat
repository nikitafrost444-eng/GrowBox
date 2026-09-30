@echo off
chcp 65001 >nul
rem Пересборка CAD-модели v3.1 rev.2 (STEP/DXF/CSV/рендеры)
call .venv\Scripts\activate.bat
python models\v3.1\build_v31_modular.py
echo.
echo Готово. Результаты:
echo   models\v3.1\step          - сборка и детали STEP (для КОМПАС)
echo   models\v3.1\dxf           - развёртки под раскрой
echo   models\v3.1\csv           - карта раскроя и ведомость
echo   models\v3.1\renders       - превью SVG
echo   models\v3.1\reports       - протокол проверок
pause
