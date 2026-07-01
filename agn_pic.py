"""
Agnes Image — Streamlit GUI 桌面網頁應用程式
=============================================
基於 Agnes Image API，支援：
  • 文生圖 (Text-to-Image)
  • 圖生圖 (Image-to-Image)
  • 多圖合成 (Multi-Image Compose)
"""

import os
import base64
from datetime import datetime
from io import BytesIO

import requests
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
import hashlib

# ---------------------------------------------------------------------------
# 磁碟級快取與高效縮圖讀取（與 app_vid 共用邏輯）
# ---------------------------------------------------------------------------
def get_thumbnail_cached(client, bucket: str, key: str, last_modified, thumb_size: tuple = (160, 160)):
    _CACHE_DIR = ".thumbnail_cache"
    if not os.path.exists(_CACHE_DIR):
        os.makedirs(_CACHE_DIR, exist_ok=True)

    ts = int(last_modified.timestamp()) if isinstance(last_modified, datetime) else 0
    unique_str = f"{key}_{ts}_{thumb_size[0]}x{thumb_size[1]}"
    file_hash = hashlib.md5(unique_str.encode("utf-8")).hexdigest()
    cache_path = os.path.join(_CACHE_DIR, f"{file_hash}.png")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                return Image.open(BytesIO(f.read()))
        except Exception:
            try:
                os.remove(cache_path)
            except Exception:
                pass

    try:
        resp = client.get_object(Bucket=bucket, Key=key)
        pil_img = Image.open(BytesIO(resp["Body"].read()))
        pil_img.thumbnail(thumb_size)
        pil_img.save(cache_path, "PNG")
        return pil_img
    except Exception:
        return None


load_dotenv()

# 用 try/except 包裹 r2_browser 導入，避免模組錯誤導致白屏
try:
    from r2_browser import list_images, get_r2_client, _R2_BUCKET, _R2_PUBLIC_DOM
    _R2_IMPORT_OK = True
except Exception as _r2_err:
    _R2_IMPORT_OK = False
    _R2_IMPORT_ERR = str(_r2_err)
    list_images = None
    get_r2_client = None
    _R2_BUCKET = ""
    _R2_PUBLIC_DOM = ""

# ---------------------------------------------------------------------------
# 頁面設定
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Agnes Image 圖片生成工具",
    page_icon="🖼️",
    layout="wide",
)

API_BASE = "https://apihub.agnes-ai.com"
IMAGE_URL = f"{API_BASE}/v1/images/generations"

MODEL_OPTIONS = {
    "Agnes Image 2.1 Flash（推薦）": "agnes-image-2.1-flash",
    "Agnes Image 2.0 Flash": "agnes-image-2.0-flash",
}

SIZE_OPTIONS = [
    "1280x720",
    "960x720",
]

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@200..900&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Serif TC', serif !important;
    }
    section[data-testid="stSidebar"] h1 {
        font-size: 1.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================================
# 側邊欄 R2 元件局部刷新封裝
# =========================================================================
@st.fragment
def sidebar_r2_album_fragment(r2_client):
    """將側邊欄相簿隔離到獨立 fragment 中，確保翻頁、載入不卡頓全域介面"""
    st.markdown("### 📸 R2 相簿")
    if r2_client and _R2_BUCKET:
        _r2_images = list_images()
        if _r2_images:
            _PER_PAGE = 6
            _TOTAL = len(_r2_images)
            _PAGES = max(1, (_TOTAL + _PER_PAGE - 1) // _PER_PAGE)

            if "r2_sidebar_page" not in st.session_state:
                st.session_state.r2_sidebar_page = 0

            if _PAGES > 1:
                _pc1, _pc2, _pc3 = st.columns([1, 2, 1])
                with _pc1:
                    if st.button("◀", key="r2_prev", width="stretch"):
                        st.session_state.r2_sidebar_page = max(0, st.session_state.r2_sidebar_page - 1)
                with _pc2:
                    st.caption(f"{st.session_state.r2_sidebar_page + 1} / {_PAGES} 共 {_TOTAL} 張")
                with _pc3:
                    if st.button("▶", key="r2_next", width="stretch"):
                        st.session_state.r2_sidebar_page = min(_PAGES - 1, st.session_state.r2_sidebar_page + 1)
            else:
                st.caption(f"共 {_TOTAL} 張圖片｜新→舊")

            _start = st.session_state.r2_sidebar_page * _PER_PAGE
            _page_imgs = _r2_images[_start : _start + _PER_PAGE]

            for _row_i in range(0, len(_page_imgs), 2):
                _row = _page_imgs[_row_i : _row_i + 2]
                _cols = st.columns(2)
                for _col, _img in zip(_cols, _row):
                    with _col:
                        _pil = get_thumbnail_cached(r2_client, _R2_BUCKET, _img["key"], _img["last_modified"], (160, 160))
                        if _pil:
                            st.image(_pil, width="stretch")
                        else:
                            st.markdown("🖼️ *載入失敗*")

                        _mtime = _img["last_modified"]
                        _ts = _mtime.strftime("%m-%d %H:%M") if isinstance(_mtime, datetime) else ""
                        st.caption(f"{_img['filename']}\n{_ts}")

                        if st.button("選取", key=f"r2_pick_{_start + _row_i + _row.index(_img)}", width="stretch"):
                            st.session_state["r2_picked_url"] = _img["url"]
                            st.rerun()
        else:
            st.info("📭 R2 中暫無圖片")
    else:
        st.caption("⚠️ 請先在 `.env` 中設定 R2 憑證")


# 側邊欄渲染
with st.sidebar:
    st.title("🖼️ Agnes Image")
    st.caption("圖片生成 API 操作面板")
    st.divider()

    _agnes_api_key_env = os.getenv("AGNES_API_KEY", "")
    api_key: str = st.text_input(
        "🔑 API Key",
        value=_agnes_api_key_env,
        type="password",
        placeholder="請輸入您的 Agnes AI API Key",
        help="前往 Agnes AI 平台取得您的 API Key。可在 `.env` 中設定 `AGNES_API_KEY` 作為預設值。",
    )
    st.divider()

    generation_mode: str = st.selectbox(
        "🎨 生成模式",
        options=["文生圖", "圖生圖", "多圖合成"],
        index=0,
        help="選擇您要使用的圖片生成工作流。",
    )
    st.divider()

    # 渲染 Fragment 相簿（安全載入）
    if _R2_IMPORT_OK:
        r2_client = get_r2_client()
        sidebar_r2_album_fragment(r2_client)
    else:
        st.caption(f"⚠️ R2 模組載入失敗：{_R2_IMPORT_ERR}")

    st.divider()
    st.markdown("### 📐 尺寸說明")
    st.markdown(
        """
- **1280×720**（16:9 橫式）
- **960×720**（4:3 橫式）
- 圖生圖建議與原圖保持相同比例

> ⚠️ 最終尺寸以 API 回應為準。
        """
    )

# =========================================================================
# 主畫面 — 輸入控制區
# =========================================================================
st.header(f"🎨 {generation_mode}")
st.caption("填寫以下參數後，點擊「開始生成圖片」按鈕提交任務。")

# 模型選擇
model_label: str = st.selectbox(
    "🤖 模型",
    options=list(MODEL_OPTIONS.keys()),
    index=0,
    help="Agnes Image 2.1 Flash 在高資訊密度圖像方面表現更好。",
)
model_name = MODEL_OPTIONS[model_label]

# 提示詞
prompt: str = st.text_area(
    "📝 提示詞 (Prompt)",
    value=st.session_state.get("prompt_text", ""),
    height=140,
    placeholder="請描述您想要生成的圖片內容...",
    help="建議結構：[主體] + [場景/背景] + [風格] + [光照] + [構圖] + [品質要求]。",
)
if st.button("📋 從剪貼簿貼上"):
    try:
        import subprocess, platform
        if platform.system() == "Windows":
            clip = subprocess.run(["powershell", "-command", "Get-Clipboard"], capture_output=True, text=True, timeout=5)
            st.session_state["prompt_text"] = clip.stdout.strip()
        else:
            import pyperclip
            st.session_state["prompt_text"] = pyperclip.paste()
        st.rerun()
    except Exception:
        st.warning("⚠️ 無法讀取剪貼簿，請手動貼上。")

# 圖片 URL（圖生圖 / 多圖合成）
extra_image_urls: list[str] = []
r2_picked: str = st.session_state.get("r2_picked_url", "")

if generation_mode == "圖生圖":
    default_val = r2_picked if r2_picked else ""
    img_url = st.text_input(
        "🖼️ 輸入圖片 URL",
        value=default_val,
        placeholder="https://example.com/image.png",
        help="輸入一張可公開訪問的圖片網址，或從左側 R2 相簿選取。",
    )
    if img_url.strip():
        extra_image_urls.append(img_url.strip())

elif generation_mode == "多圖合成":
    st.markdown("#### 🖼️ 參考圖片 URLs（至少兩張）")
    if r2_picked:
        if st.button("➕ 加入 R2 選取的圖片", key="multi_add_r2", width="stretch"):
            filled = False
            for _i in range(st.session_state.multi_img_count):
                _k = f"multi_img_{_i}"
                if not st.session_state.get(_k, "").strip():
                    st.session_state[_k] = r2_picked
                    filled = True
                    break
            if not filled:
                st.session_state[f"multi_img_{st.session_state.multi_img_count}"] = r2_picked
                st.session_state.multi_img_count += 1
            st.rerun()

    if "multi_img_count" not in st.session_state:
        st.session_state.multi_img_count = 2

    for i in range(st.session_state.multi_img_count):
        url = st.text_input(f"圖片 URL #{i + 1}", key=f"multi_img_{i}", placeholder="https://example.com/image.png")
        if url.strip():
            extra_image_urls.append(url.strip())

    col_add, col_rem = st.columns(2)
    with col_add:
        if st.button("➕ 增加一張圖片", width="stretch"):
            st.session_state.multi_img_count += 1
            st.rerun()
    with col_rem:
        if st.button("➖ 移除最後一張", width="stretch"):
            if st.session_state.multi_img_count > 2:
                st.session_state.multi_img_count -= 1
                st.rerun()

# ---------------------------------------------------------------------------
# 圖片 → Base64 轉換工具
# ---------------------------------------------------------------------------
with st.expander("🔄 圖片 → Base64 轉換工具", expanded=False):
    st.markdown("上傳圖片後自動轉為 Base64 data URI，可直接複製使用。")

    uploaded_file = st.file_uploader(
        "選擇圖片檔案",
        type=["png", "jpg", "jpeg"],
        key="agn_b64_uploader",
        help="支援 PNG、JPG、JPEG 格式。上傳後自動轉為 Base64 data URI。",
    )
    if uploaded_file:
        try:
            img = Image.open(uploaded_file).convert("RGB")
            buf = BytesIO()
            img.save(buf, format="PNG")
            b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            st.session_state["agn_b64_result"] = f"data:image/png;base64,{b64_str}"
            st.session_state["agn_b64_filename"] = uploaded_file.name
        except Exception as e:
            st.error(f"❌ 圖片處理失敗：{e}")

    # 顯示結果
    if st.session_state.get("agn_b64_result"):
        _data_uri = st.session_state["agn_b64_result"]
        _fname = st.session_state.get("agn_b64_filename", "image.png")
        _b64_prefix_len = _data_uri.find(",") + 1 if _data_uri.startswith("data:") else 0
        _b64_only = _data_uri[_b64_prefix_len:]
        _size_kb = len(_b64_only) * 3 / 4 / 1024

        st.markdown(f"**🖼️ 來源：** `{_fname}`　|　**📦 Base64 大小：** {_size_kb:.1f} KB")

        try:
            _preview_bytes = base64.b64decode(_b64_only)
            st.image(Image.open(BytesIO(_preview_bytes)), caption="預覽", width="stretch")
        except Exception:
            pass

        _b64_col1, _b64_col2 = st.columns([3, 1])
        with _b64_col1:
            st.code(_data_uri, language=None)
        with _b64_col2:
            st.download_button(
                label="📥 下載 Base64 文字檔",
                data=_data_uri,
                file_name=f"{_fname.rsplit('.', 1)[0]}_base64.txt",
                mime="text/plain",
                key="agn_b64_download",
            )

# 進階參數
with st.expander("⚙️ 進階參數調整", expanded=False):
    adv_col1, adv_col2, adv_col3 = st.columns(3)
    with adv_col1:
        size: str = st.selectbox("📐 輸出尺寸 (size)", options=SIZE_OPTIONS, index=0)
    with adv_col2:
        return_base64: bool = st.checkbox("📦 返回 Base64", value=False, help="勾選後以 Base64 格式返回圖片，否則返回 URL。")
    with adv_col3:
        use_url_input: bool = False
        if generation_mode == "圖生圖":
            use_url_input = st.checkbox("🔗 圖片以 URL 方式傳入（非 Base64）", value=True, help="取消勾選時，系統會自動將圖片轉為 Base64 傳入。")

st.divider()

# =========================================================================
# 發送與生成邏輯
# =========================================================================
def build_payload() -> dict | None:
    if not prompt.strip():
        st.warning("⚠️ 請輸入提示詞 (Prompt)。")
        return None

    payload: dict = {
        "model": model_name,
        "prompt": prompt.strip(),
        "size": size,
    }

    # ---- 文生圖 ----
    if generation_mode == "文生圖":
        if return_base64:
            payload["return_base64"] = True
        else:
            payload["extra_body"] = {"response_format": "url"}

    # ---- 圖生圖 ----
    elif generation_mode == "圖生圖":
        if not extra_image_urls:
            st.warning("⚠️ 圖生圖模式需要輸入至少一張圖片 URL。")
            return None
        extra_body: dict = {"image": extra_image_urls}
        if return_base64:
            extra_body["response_format"] = "b64_json"
        else:
            extra_body["response_format"] = "url"
        payload["extra_body"] = extra_body

    # ---- 多圖合成 ----
    elif generation_mode == "多圖合成":
        if len(extra_image_urls) < 2:
            st.warning("⚠️ 多圖合成模式需要至少兩張圖片 URL。")
            return None
        extra_body = {"image": extra_image_urls}
        if return_base64:
            extra_body["response_format"] = "b64_json"
        else:
            extra_body["response_format"] = "url"
        payload["extra_body"] = extra_body

    return payload


def generate_image(payload: dict, headers: dict, max_retries: int = 3) -> dict | None:
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(IMAGE_URL, json=payload, headers=headers, timeout=360)
            if resp.status_code == 200:
                return resp.json()
            st.error(f"❌ 生成失敗（HTTP {resp.status_code}）：{resp.text}")
            return None
        except requests.RequestException as exc:
            if attempt < max_retries:
                import time
                time.sleep(attempt * 5)
                continue
            st.error(f"❌ 網路連線超時或失敗：{exc}")
    return None


if st.button("🚀 開始生成圖片", type="primary", width="stretch"):
    if not api_key.strip():
        st.error("❌ 請先在側邊欄輸入您的 API Key。")
        st.stop()

    payload = build_payload()
    if payload is None:
        st.stop()

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }

    with st.spinner("📡 正在向 API 發送圖片生成任務…"):
        result = generate_image(payload, headers)

    if result is None:
        st.stop()

    data_list = result.get("data", [])
    if not data_list:
        st.error("❌ API 回應中沒有圖片資料。")
        st.stop()

    st.divider()
    st.subheader("🎉 圖片生成完成！")

    for idx, item in enumerate(data_list):
        b64_data = item.get("b64_json")
        url_data = item.get("url")

        if b64_data:
            # Base64 圖片
            img_bytes = base64.b64decode(b64_data)
            pil_img = Image.open(BytesIO(img_bytes))
            st.image(pil_img, caption=f"生成圖片 #{idx + 1}", width="stretch")

            # 下載按鈕
            buf = BytesIO()
            pil_img.save(buf, format="PNG")
            st.download_button(
                label=f"📥 下載圖片 #{idx + 1}（PNG）",
                data=buf.getvalue(),
                file_name=f"agnes_image_{idx + 1}.png",
                mime="image/png",
            )
        elif url_data:
            # URL 圖片
            st.image(url_data, caption=f"生成圖片 #{idx + 1}", width="stretch")
            st.markdown(f"📥 [點擊下載圖片 #{idx + 1}]({url_data})")
        else:
            st.warning(f"⚠️ 圖片 #{idx + 1} 無可顯示的內容。")

    with st.expander("📄 查看完整 API 回應", expanded=False):
        st.json(result)

st.divider()
st.caption(f"Agnes Image GUI — Powered by Streamlit | 模型：`{model_name}`")
