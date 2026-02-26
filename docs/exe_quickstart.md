# EXE最短手順（Windows）

## 1. 事前準備
この構成をプロジェクト直下に置く。

- `app.py`
- `launcher.py`
- `ffmpeg/ffmpeg.exe`
- `models/faster-whisper-medium/...`

## 2. EXEをビルド
PowerShellで実行:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

## 3. 実行
```powershell
.\dist\transcriber_app\transcriber.exe
```

起動するとブラウザが開き、ローカルUIで文字起こしできる。

## 配布時の最低構成
- `transcriber.exe`
- `app.py`
- `ffmpeg/`
- `models/`

同じフォルダ階層で配布する。
