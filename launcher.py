import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path
import runpy
import socket


# -----------------------------
# 重要：Transcriber.exe -m streamlit ... のときは
# launcherを走らせず streamlit を実行する（再帰防止）
# -----------------------------
def _maybe_dispatch_to_streamlit():
    argv = sys.argv
    if len(argv) >= 3 and argv[1] == "-m" and argv[2] == "streamlit":
        # streamlit 側に渡す argv を整形
        # 例: Transcriber.exe -m streamlit run app.py ...
        # -> sys.argv = ["streamlit", "run", "app.py", ...]
        sys.argv = ["streamlit"] + argv[3:]
        runpy.run_module("streamlit", run_name="__main__")
        raise SystemExit(0)


def base_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def build_env() -> dict:
    env = os.environ.copy()

    # vendor を PATH 先頭へ（同梱ffmpeg）
    vendor = base_dir() / "vendor"
    env["PATH"] = str(vendor) + os.pathsep + env.get("PATH", "")

    # telemetry off
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    # 過去の xet 由来エラー回避
    env["HF_HUB_DISABLE_XET"] = "1"

    # キャッシュ先をアプリ配下（オフライン運用の保険）
    hf_home = base_dir() / ".hf_cache"
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


def main():
    port = find_free_port(8501)
    env = build_env()

    app_path = base_dir() / "app.py"
    if not app_path.exists():
        raise FileNotFoundError(f"app.py not found: {app_path}")

    cmd = [
        sys.executable, "-m", "streamlit", "run", str(app_path),
        "--server.headless=true",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
    ]

    proc = subprocess.Popen(cmd, env=env)

    # サーバ起動を待ってからブラウザを開く（localhost接続失敗を防ぐ）
    if wait_port(port, 20.0):
        webbrowser.open(f"http://localhost:{port}")
    else:
        webbrowser.open(f"http://localhost:{port}")  # それでも一応開く

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