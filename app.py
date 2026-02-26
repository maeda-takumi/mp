import os
import sys
import tempfile
from pathlib import Path

import streamlit as st
from faster_whisper import WhisperModel


st.set_page_config(page_title="音声文字起こし", layout="wide")
st.title("音声ファイル文字起こし（Whisper / ローカル無料）")


# -------------------------
# Path helpers
# -------------------------
def runtime_base_dir() -> Path:
    """
    手動配布を前提に、以下の順でベースディレクトリを決定する。
      1. launcher から渡される TRANSCRIBER_BASE_DIR
      2. 凍結実行時の実行ファイル配置ディレクトリ
      3. 通常実行時の app.py 配置ディレクトリ
    """
    env_dir = os.environ.get("TRANSCRIBER_BASE_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def bundled_model_path(model_key: str) -> Path:
    """
    期待配置:
      models/faster-whisper-small
      models/faster-whisper-medium
      models/faster-whisper-large-v3
    """
    base = runtime_base_dir()
    mapping = {
        "small": base / "models" / "faster-whisper-small",
        "medium": base / "models" / "faster-whisper-medium",
        "large-v3": base / "models" / "faster-whisper-large-v3",
    }
    return mapping[model_key]


def resolve_model_source(model_key: str) -> str | None:
    """
    手動配置されたモデルのみを使用する。
    未配置時は None を返して呼び出し側で明示エラーにする。
    """
    p = bundled_model_path(model_key)
    if p.exists() and p.is_dir():
        return str(p)
    return None


# -------------------------
# UI
# -------------------------
with st.sidebar:
    st.header("設定")
    model_key = st.selectbox("モデル（精度↑ほど重い）", ["small", "medium", "large-v3"], index=1)
    language = st.text_input("言語（空なら自動）", value="ja")
    beam_size = st.slider("beam_size（精度↑/速度↓）", 1, 10, 5)
    vad_filter = st.checkbox("無音除去（VAD）", value=True)

    # 状態表示（配布時のトラブルを減らす）
    src = resolve_model_source(model_key)
    if src:
        st.success(f"手動配置モデル検出: {src}")
    else:
        required = bundled_model_path(model_key)
        st.error(
            "モデルが見つかりません。\n"
            f"以下のフォルダを配置してください:\n{required}"
        )


@st.cache_resource
def load_model(model_key: str):
    model_src = resolve_model_source(model_key)
    if not model_src:
        required = bundled_model_path(model_key)
        raise FileNotFoundError(
            "モデルが見つかりません。\n"
            "手動配布構成では自動ダウンロードを行いません。\n"
            f"必要フォルダ: {required}"
        )
    return WhisperModel(model_src, device="cpu", compute_type="int8")


try:
    model = load_model(model_key)
except Exception as e:
    st.error("モデルの読み込みに失敗しました。")
    st.exception(e)
    st.stop()


uploaded = st.file_uploader("音声ファイルをアップロード（mp3 / m4a / wav など）")

if uploaded:
    suffix = os.path.splitext(uploaded.name)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        audio_path = tmp.name

    st.info("文字起こし中…（音声長・PC性能で時間が変わります）")

    try:
        segments, info = model.transcribe(
            audio_path,
            language=language.strip() or None,
            beam_size=beam_size,
            vad_filter=vad_filter,
        )
    except Exception as e:
        ffmpeg_path = runtime_base_dir() / "ffmpeg"
        st.error(
            "文字起こしに失敗しました。\n"
            "ffmpeg の配置または PATH 設定を確認してください。\n"
            f"推奨配置: {ffmpeg_path}"
        )
        st.exception(e)
        os.remove(audio_path)
        st.stop()

    text = "\n".join([s.text.strip() for s in segments]).strip()
    timed = "\n".join([f"[{s.start:7.2f} - {s.end:7.2f}] {s.text.strip()}" for s in segments]).strip()

    os.remove(audio_path)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("文字起こし結果")
        st.text_area("text", text, height=420)
        st.download_button("TXTダウンロード（timestamp）", timed.encode("utf-8"), file_name="transcript_timestamp.txt")

    with col2:
        st.subheader("タイムスタンプ付き")
        st.text_area("timestamp", timed, height=420)
        st.download_button("TXTダウンロード（timestamp）", timed.encode("utf-8"), file_name="transcript_timestamp.txt")