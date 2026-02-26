import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path
import runpy
import socket



# -----------------------------
# 重要：app.exe -m streamlit ... のときは
# launcherを走らせず streamlit を実行する（再帰防止）
# -----------------------------
def _maybe_dispatch_to_streamlit():
    argv = sys.argv
    if len(argv) >= 3 and argv[1] == "-m" and argv[2] == "streamlit":
        sys.argv = ["streamlit"] + argv[3:]
        runpy.run_module("streamlit", run_name="__main__")
        raise SystemExit(0)


def runtime_base_dir() -> Path:
    # 手動配布（app.exe / models / ffmpeg）を優先するため
    # 凍結時は実行ファイルのあるディレクトリを基準にする
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def build_env() -> dict:
    env = os.environ.copy()

    base = runtime_base_dir()

    # ffmpeg フォルダを PATH 先頭へ（手動配置）
    ffmpeg_dir = base / "ffmpeg"
    env["PATH"] = str(ffmpeg_dir) + os.pathsep + env.get("PATH", "")

    # ffmpeg フォルダを PATH 先頭へ（手動配置）
    ffmpeg_dir = base / "ffmpeg"
    env["PATH"] = str(ffmpeg_dir) + os.pathsep + env.get("PATH", "")
    env["HF_HUB_DISABLE_XET"] = "1"

    # キャッシュは実行場所配下（手動配布一式で完結しやすくする）
    hf_home = base / ".hf_cache"
    hf_home.mkdir(parents=True, exist_ok=True)
    env["HF_HOME"] = str(hf_home)
    env["HUGGINGFACE_HUB_CACHE"] = str(hf_home / "hub")

    return env


def wait_port(port: int, timeout_sec: float = 15.0) -> bool:
    end = time.time() + timeout_sec
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def find_free_port(start: int = 8501) -> int:
    for p in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start

def ensure_ffmpeg_exists(base: Path) -> None:
    # Windows配布を主眼にしつつ、他OSも一応見る
    candidates = [base / "ffmpeg" / "ffmpeg.exe", base / "ffmpeg" / "ffmpeg"]
    if any(p.exists() for p in candidates):
        return

    expected = candidates[0]
    raise FileNotFoundError(
        "ffmpeg が見つかりません。\n"
        f"期待パス: {expected}\n"
        "app.exe と同階層に ffmpeg フォルダを配置し、"
        "ffmpeg(.exe) を入れてください。"
    )


def main():
    base = runtime_base_dir()
    ensure_ffmpeg_exists(base)
    port = find_free_port(8501)
    env = build_env()

    app_path = base / "app.py"
    if not app_path.exists():
        raise FileNotFoundError(f"app.py not found: {app_path}")

    cmd = [
        sys.executable, "-m", "streamlit", "run", str(app_path),
        "--server.headless=true",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
    ]

    proc = subprocess.Popen(cmd, env=env)

    if wait_port(port, 20.0):
        webbrowser.open(f"http://localhost:{port}")
    else:
        webbrowser.open(f"http://localhost:{port}")

    try:
        proc.wait()
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    _maybe_dispatch_to_streamlit()
    main()