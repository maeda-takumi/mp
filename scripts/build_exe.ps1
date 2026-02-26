$ErrorActionPreference = 'Stop'

Write-Host '[1/4] Installing PyInstaller...'
py -m pip install -U pyinstaller

Write-Host '[2/4] Building launcher.exe (one-folder compatible layout)...'
py -m PyInstaller --noconfirm --clean --name transcriber launcher.py

Write-Host '[3/4] Preparing distributable folder dist/transcriber_app ...'
$target = 'dist/transcriber_app'
if (Test-Path $target) { Remove-Item -Recurse -Force $target }
New-Item -ItemType Directory -Path $target | Out-Null

Copy-Item 'dist/transcriber.exe' "$target/transcriber.exe"
Copy-Item 'app.py' "$target/app.py"

if (Test-Path 'ffmpeg') {
    Copy-Item 'ffmpeg' "$target/ffmpeg" -Recurse
} else {
    Write-Warning 'ffmpeg folder was not found. Put ffmpeg/ next to transcriber.exe before running.'
}

if (Test-Path 'models') {
    Copy-Item 'models' "$target/models" -Recurse
} else {
    Write-Warning 'models folder was not found. Put models/ next to transcriber.exe before running.'
}

Write-Host '[4/4] Done!'
Write-Host 'Run: dist/transcriber_app/transcriber.exe'
