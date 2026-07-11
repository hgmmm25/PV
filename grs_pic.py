"""
Grsai Image — Streamlit GUI
============================
Grsai 圖片生成工具，基於 gpt-image-2 API。
支援文生圖 / 圖生圖，異步輪詢取得結果。
"""

import os
import time
import base64
from io import BytesIO

import requests
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# ---------------------------------------------------------------------------
# 頁面設定
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Grsai Image 圖片生成工具",
    page_icon="🖼️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# API 設定
# ---------------------------------------------------------------------------
GRSAI_BASE_URL = "https://grsaiapi.com"
GRSAI_GENERATE_URL = f"{GRSAI_BASE_URL}/v1/api/generate"
GRSAI_RESULT_URL = f"{GRSAI_BASE_URL}/v1/api/result"

MODELS = {
    "Grsai Image 2（推薦）": "gpt-image-2",
    "Grsai Image 2 VIP（最高畫質）": "gpt-image-2-vip",
}

# VIP 僅保留 4K 最高畫質
# gpt-image-2 使用比例字串
GRSAI_RATIOS_STANDARD = {
    "21:9 (超寬)": "21:9",
    "16:9 (寬屏)": "16:9",
    "4:3 (標準)": "4:3",
}

# gpt-image-2-vip 使用像素值（4K）
GRSAI_RATIOS_VIP = {
    "21:9 (超寬) — 3840×1648": "3840x1648",
    "16:9 (寬屏) — 3840×2160": "3840x2160",
    "4:3 (標準) — 3264×2448": "3264x2448",
}

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@200..900&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Sans TC', sans-serif !important;
    }
    section[data-testid="stSidebar"] h1 {
        font-size: 1.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 側邊欄
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🖼️ Grsai Image")
    st.caption("圖片生成 API 操作面板")
    st.divider()

    _grsai_key_env = os.getenv("GRSAI_API_KEY", "")
    api_key: str = st.text_input(
        "🔑 API Key",
        value=_grsai_key_env,
        type="password",
        placeholder="請輸入您的 Grsai API Key",
        help="前往 https://grsai.ai/zh/dashboard/api-keys 取得 API Key。可在 `.env` 中設定 `GRSAI_API_KEY`。",
    )

    _oss_id_env = os.getenv("GRSAI_OSS_ID", "")
    oss_id: str = st.text_input(
        "🗄️ OSS 儲存庫 ID",
        value=_oss_id_env,
        placeholder="選填",
        help="自訂儲存庫 ID。可在 `.env` 中設定 `GRSAI_OSS_ID`。",
    )
    _oss_path_env = os.getenv("GRSAI_OSS_PATH", "")
    oss_path: str = st.text_input(
        "📁 OSS 儲存路徑",
        value=_oss_path_env,
        placeholder="選填，如 file/images",
        help="儲存庫內的子路徑。可在 `.env` 中設定 `GRSAI_OSS_PATH`。",
    )

    st.divider()
    st.markdown("### 📐 比例說明")
    st.markdown(
        """
- **21:9** — 超寬銀幕
- **16:9** — 寬屏標準
- **4:3** — 標準比例
- VIP 模型使用 4K 最高畫質
        """
    )

# ---------------------------------------------------------------------------
# 主畫面
# ---------------------------------------------------------------------------
st.header("🎨 Grsai 圖片生成")
st.caption("選擇模型與參數，點擊「開始生成」提交任務。")

# 生成模式
generation_mode: str = st.selectbox(
    "🎨 生成模式",
    options=["文生圖", "圖生圖"],
    index=0,
)

# 模型選擇
model_label: str = st.selectbox(
    "🤖 模型",
    options=list(MODELS.keys()),
    index=0,
)
model_name = MODELS[model_label]

# 比例選擇（根據模型動態切換）
if model_name == "gpt-image-2-vip":
    ratio_options = GRSAI_RATIOS_VIP
else:
    ratio_options = GRSAI_RATIOS_STANDARD

ratio_label: str = st.selectbox(
    "📐 圖片比例",
    options=list(ratio_options.keys()),
    index=1,
)
aspect_ratio = ratio_options[ratio_label]

# 提示詞
prompt: str = st.text_area(
    "📝 提示詞 (Prompt)",
    value=st.session_state.get("grsai_prompt", ""),
    height=140,
    placeholder="請描述您想要生成的圖片內容...",
)
if st.button("📋 從剪貼簿貼上"):
    try:
        import subprocess, platform
        if platform.system() == "Windows":
            clip = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
            )
            st.session_state["grsai_prompt"] = clip.stdout.strip()
        else:
            import pyperclip
            st.session_state["grsai_prompt"] = pyperclip.paste()
        st.rerun()
    except Exception:
        st.warning("⚠️ 無法讀取剪貼簿，請手動貼上。")

# 圖生圖 — 參考圖
extra_images: list[str] = []
if generation_mode == "圖生圖":
    # 從 Base64 工具「選入」：在 widget 渲染前把值寫入 widget 自己的 key，
    # 這樣即使 widget 已存在（非首次渲染），值也能正確更新。
    if "grs_img_url_input" in st.session_state:
        st.session_state["img_url_input"] = st.session_state.pop("grs_img_url_input")

    img_url = st.text_input(
        "🖼️ 參考圖片 URL",
        key="img_url_input",
        placeholder="https://example.com/image.png 或 Base64 data URI",
        help="輸入一張可公開訪問的圖片網址（支援 Base64 與 URL）。可透過下方 Base64 工具自動填入。",
    )
    if img_url.strip():
        extra_images.append(img_url.strip())

# ---------------------------------------------------------------------------
# 圖片 → Base64 轉換工具
# ---------------------------------------------------------------------------
with st.expander("🔄 圖片 → Base64 轉換工具", expanded=False):
    st.markdown("上傳圖片後自動轉為 Base64 data URI，可直接複製使用。")

    uploaded_file = st.file_uploader(
        "選擇圖片檔案",
        type=["png", "jpg", "jpeg"],
        key="grs_b64_uploader",
        help="支援 PNG、JPG、JPEG 格式。上傳後自動轉為 Base64 data URI。",
    )

    # 利用 session_state 快取，避免 Rerun 時重複計算
    if uploaded_file:
        _file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("grs_b64_file_id") != _file_id:
            try:
                img = Image.open(uploaded_file)
                fmt = img.format or "PNG"
                has_alpha = img.mode in ("RGBA", "LA", "PA")

                buf = BytesIO()
                if fmt == "JPEG" and not has_alpha:
                    img.convert("RGB").save(buf, format="JPEG", quality=90)
                    mime_type = "image/jpeg"
                else:
                    img.convert("RGBA" if has_alpha else "RGB").save(buf, format="PNG")
                    mime_type = "image/png"

                b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                st.session_state["grs_b64_result"] = f"data:{mime_type};base64,{b64_str}"
                st.session_state["grs_b64_filename"] = uploaded_file.name
                st.session_state["grs_b64_file_id"] = _file_id
            except Exception as e:
                st.error(f"❌ 圖片處理失敗：{e}")

    # 顯示結果
    if st.session_state.get("grs_b64_result"):
        _data_uri = st.session_state["grs_b64_result"]
        _fname = st.session_state.get("grs_b64_filename", "image.png")
        _b64_prefix_len = _data_uri.find(",") + 1 if _data_uri.startswith("data:") else 0
        _b64_only = _data_uri[_b64_prefix_len:]
        _size_kb = len(_b64_only) * 3 / 4 / 1024

        st.success("✅ 轉換成功！已生成 Base64 資料")
        st.markdown(f"**🖼️ 來源：** `{_fname}`　|　**📦 Base64 大小：** {_size_kb:.1f} KB")

        # 直接用上傳檔案預覽，不再 base64 → bytes 解碼
        if uploaded_file:
            st.image(uploaded_file, caption="預覽", width="stretch")

        _b64_col1, _b64_col2, _b64_col3 = st.columns([2, 1, 1])
        with _b64_col1:
            st.download_button(
                label="📥 下載 Base64 文字檔",
                data=_data_uri,
                file_name=f"{_fname.rsplit('.', 1)[0]}_base64.txt",
                mime="text/plain",
                key="grs_b64_download",
            )
        with _b64_col2:
            if st.button("📌 選入參考圖欄位", key="grs_b64_select"):
                st.session_state["grs_img_url_input"] = _data_uri
                st.toast("✅ 已填入「參考圖片 URL」欄位", icon="📌")
                st.rerun()
        with _b64_col3:
            if st.button("📋 複製到剪貼簿", key="grs_b64_copy"):
                st.session_state["grs_b64_clipboard"] = _data_uri
                st.toast("✅ Base64 資料已準備就緒", icon="📋")

st.divider()

# ---------------------------------------------------------------------------
# API 呼叫
# ---------------------------------------------------------------------------
def build_headers() -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}",
    }
    if oss_id.strip():
        headers["oss-id"] = oss_id.strip()
    if oss_path.strip():
        headers["oss-path"] = oss_path.strip()
    return headers


def call_generate(payload: dict, hdrs: dict) -> dict | None:
    resp = requests.post(GRSAI_GENERATE_URL, json=payload, headers=hdrs, timeout=120)
    if resp.status_code != 200:
        st.error(f"❌ HTTP {resp.status_code}：{resp.text}")
        return None
    return resp.json()


def poll_result(task_id: str, hdrs: dict, max_wait: int = 600) -> dict | None:
    progress_bar = st.progress(0)
    status_text = st.empty()
    start = time.time()

    while time.time() - start < max_wait:
        resp = requests.get(
            GRSAI_RESULT_URL,
            params={"id": task_id},
            headers=hdrs,
            timeout=30,
        )
        if resp.status_code != 200:
            st.error(f"❌ 輪詢失敗（HTTP {resp.status_code}）：{resp.text}")
            return None

        data = resp.json()
        status = data.get("status", "")
        progress = data.get("progress", 0)

        progress_bar.progress(min(progress, 100))
        status_text.text(f"⏳ 狀態：{status}　進度：{progress}%")

        if status == "succeeded":
            progress_bar.progress(100)
            status_text.text("✅ 生成完成！")
            return data
        elif status in ("failed", "violation"):
            st.error(f"❌ 任務失敗：{data.get('error', status)}")
            return None

        time.sleep(3)

    st.error("❌ 超時：超過最大等待時間。")
    return None


def display_image(data: dict):
    results = data.get("results", [])
    if not results:
        st.warning("⚠️ 回應中沒有圖片資料。")
        return

    for idx, item in enumerate(results):
        url = item.get("url", "")
        if url:
            st.image(url, caption=f"生成圖片 #{idx + 1}", width="stretch")
            try:
                img_resp = requests.get(url, timeout=30)
                if img_resp.status_code == 200:
                    st.download_button(
                        label=f"📥 下載圖片 #{idx + 1}",
                        data=img_resp.content,
                        file_name=f"grsai_image_{idx + 1}.png",
                        mime="image/png",
                    )
            except Exception:
                st.markdown(f"📥 [點擊下載圖片 #{idx + 1}]({url})")

    with st.expander("📄 查看完整 API 回應", expanded=False):
        st.json(data)


# ---------------------------------------------------------------------------
# 生成按鈕
# ---------------------------------------------------------------------------
if st.button("🚀 開始生成圖片", type="primary", width="stretch"):
    if not api_key.strip():
        st.error("❌ 請先在側邊欄輸入 Grsai API Key。")
        st.stop()
    if not prompt.strip():
        st.warning("⚠️ 請輸入提示詞。")
        st.stop()
    if generation_mode == "圖生圖" and not extra_images:
        st.warning("⚠️ 圖生圖模式需要至少一張參考圖片 URL。")
        st.stop()

    payload: dict = {
        "model": model_name,
        "prompt": prompt.strip(),
        "aspectRatio": aspect_ratio,
        "replyType": "async",
    }
    if extra_images:
        payload["images"] = extra_images

    headers = build_headers()

    with st.spinner("📡 正在提交生成任務…"):
        init = call_generate(payload, headers)

    if init is None:
        st.stop()

    task_id = init.get("id")
    if not task_id:
        st.error("❌ 未取得任務 ID。")
        st.stop()

    st.info(f"📋 任務 ID：`{task_id}`")

    result = poll_result(task_id, headers)
    if result:
        display_image(result)

st.divider()
st.caption(f"Grsai Image GUI — Powered by Streamlit | 模型：`{model_name}`")
