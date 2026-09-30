# Установка окружения для сборки CAD-модели GrowBox (Windows PowerShell)
# Запуск: правой кнопкой по файлу → Run with PowerShell (или: powershell -ExecutionPolicy Bypass -File setup.ps1)
$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python не найден!" -ForegroundColor Red
    Write-Host "Установи Python 3.12 с https://python.org/downloads/ и обязательно поставь галочку 'Add python.exe to PATH'"
    exit 1
}

Write-Host "Создаю виртуальное окружение .venv ..." -ForegroundColor Cyan
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip --quiet
Write-Host "Устанавливаю CadQuery (это ~500 МБ, минуты 2-3) ..." -ForegroundColor Cyan
pip install -r requirements.txt --quiet

Write-Host ""
Write-Host "Готово! Сборка модели: запусти build.bat" -ForegroundColor Green
