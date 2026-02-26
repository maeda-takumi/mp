import os
import tempfile
from pathlib import Path

import streamlit as st
from faster_whisper import WhisperModel


st.set_page_config(page_title="音声文字起こし", layout="wide")
st.title("音声ファイル文字起こし（Whisper / ローカル無料）")


# -------------------------
# Path helpers
# -------------------------
def app_base_dir() -> Path:
    # PyInstaller onefile でも onedir でも動くようにする
    # onedir配布なら通常は app.py のある場所が基準でOK
    return Path(__file__).resolve().parent


def bundled_model_path(model_key: str) -> Path:
    """
    例:
      models/faster-whisper-medium
      models/faster-whisper-small
      models/faster-whisper-large-v3
    """
    base = app_base_dir()
    mapping = {
        "small": base / "models" / "faster-whisper-small",
        "medium": base / "models" / "faster-whisper-medium",
        "large-v3": base / "models" / "faster-whisper-large-v3",
    }
    return mapping[model_key]


def resolve_model_source(model_key: str) -> str:
    """
    同梱モデルがあればそのパスを返す。
    なければ model_key ("small"/"medium"/"large-v3") を返して通常DL/キャッシュに任せる。
    """
    p = bundled_model_path(model_key)
    if p.exists() and p.is_dir():
        return str(p)
    return model_key


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
    if src != model_key:
        st.success(f"同梱モデル使用: {src}")
    else:
        st.warning("同梱モデルが見つからないため、通常のモデル取得（DL/キャッシュ）になります。"
                   "（オフライン配布では models フォルダ同梱を確認してください）")


@st.cache_resource
def load_model(model_key: str):
    model_src = resolve_model_source(model_key)
    # CPUなら int8 が軽くておすすめ
    return WhisperModel(model_src, device="cpu", compute_type="int8")


# ここでモデルロード（失敗したら画面に理由を出す）
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
        st.error("文字起こしに失敗しました。ffmpeg同梱/PATH設定、音声ファイル形式を確認してください。")
        st.exception(e)
        os.remove(audio_path)
        st.stop()

    # 整形テキスト
    text = "\n".join([s.text.strip() for s in segments]).strip()
    # タイムスタンプ付き
    timed = "\n".join([f"[{s.start:7.2f} - {s.end:7.2f}] {s.text.strip()}" for s in segments]).strip()

    os.remove(audio_path)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("文字起こし結果")
        st.text_area("text", text, height=420)
        st.download_button("TXTダウンロード", text.encode("utf-8"), file_name="transcript.txt")

    with col2:
        st.subheader("タイムスタンプ付き")
        st.text_area("timestamp", timed, height=420)
        st.download_button("TXTダウンロード（timestamp）", timed.encode("utf-8"), file_name="transcript_timestamp.txt")