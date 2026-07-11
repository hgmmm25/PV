"""
Agnes Video V2.0 — Streamlit GUI 桌面網頁應用程式 (效能優化版)
==========================================================
基於 Agnes-Video-V2.0 非同步 API，支援：
  • 文生視頻 (Text-to-Video)
  • 圖生視頻 (Image-to-Video)
  • 關鍵幀動畫 (Keyframe Animation)
"""

import json
import os
import time
from datetime import datetime
from io import BytesIO

import requests
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
import hashlib  # 👈 記得加入這個標準庫

# 👈 直接把快取函數寫在 app.py 裡面
def get_thumbnail_cached(client, bucket: str, key: str, last_modified, thumb_size: tuple = (160, 160)):
    """
    磁碟級快取與高效縮圖讀取 (內嵌版)
    """
    _CACHE_DIR = ".thumbnail_cache"
    if not os.path.exists(_CACHE_DIR):
        os.makedirs(_CACHE_DIR, exist_ok=True)
        
    ts = int(last_modified.timestamp()) if isinstance(last_modified, datetime) else 0
    unique_str = f"{key}_{ts}_{thumb_size[0]}x{thumb_size[1]}"
    file_hash = hashlib.md5(unique_str.encode("utf-8")).hexdigest()
    cache_path = os.path.join(_CACHE_DIR, f"{file_hash}.png")
    
    # 1. 嘗試命中本地快取
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                return Image.open(BytesIO(f.read()))
        except Exception:
            try:
                os.remove(cache_path)
            except:
                pass

    # 2. 快取未命中，從 R2 下載原圖並建立快取
    try:
        resp = client.get_object(Bucket=bucket, Key=key)
        pil_img = Image.open(BytesIO(resp["Body"].read()))
        pil_img.thumbnail(thumb_size)
        
        pil_img.save(cache_path, "PNG")
        return pil_img
    except Exception:
        return None

load_dotenv()

# 導入 R2 優化模組與快取機制
from r2_browser import list_images, get_r2_client, _R2_BUCKET, _R2_PUBLIC_DOM

# ---------------------------------------------------------------------------
# 頁面設定
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Agnes Video V2.0 影片生成工具",
    page_icon="🎬",
    layout="wide",
)

API_BASE = "https://apihub.agnes-ai.com"
CREATE_URL = f"{API_BASE}/v1/videos"
POLL_URL = f"{API_BASE}/agnesapi"
MODEL_NAME = "agnes-video-v2.0"

FRAME_OPTIONS_BY_RES_FPS = {
    "1080p": {
        "fps": [24, 30],  # 1080p 下取消 50 fps
        24: [(121, "約 5 秒"), (169, "最大長度 約 7 秒")],
        30: [(169, "最大長度 約 5.6 秒")],
    },
    "720p": {
        "fps": [24, 30, 50],
        24: [(121, "約 5 秒"), (241, "約 10 秒"), (409, "最大長度 約 17 秒")],
        30: [(241, "精準 8 秒"), (361, "精準 12 秒")],
        50: [(401, "精準 8 秒")],
    },
}

STATUS_QUEUED = "queued"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

POLL_INTERVAL_SECONDS = 15

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght=200..900&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Serif TC', serif !important;
    }
    section[data-testid="stSidebar"] h1 {
        font-size: 1.4rem;
    }
    .stVideo {
        display: flex;
        justify-content: center;
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
                        # 局部 fragment 刷新，不調用全域 st.rerun()
                with _pc2:
                    st.caption(f"{st.session_state.r2_sidebar_page + 1} / {_PAGES} 共 {_TOTAL} 張")
                with _pc3:
                    if st.button("▶", key="r2_next", width="stretch"):
                        st.session_state.r2_sidebar_page = min(_PAGES - 1, st.session_state.r2_sidebar_page + 1)
                        # 局部 fragment 刷新，不調用全域 st.rerun()
            else:
                st.caption(f"共 {_TOTAL} 張圖片｜新→舊")

            _start = st.session_state.r2_sidebar_page * _PER_PAGE
            _page_imgs = _r2_images[_start : _start + _PER_PAGE]

            for _row_i in range(0, len(_page_imgs), 2):
                _row = _page_imgs[_row_i : _row_i + 2]
                _cols = st.columns(2)
                for _col, _img in zip(_cols, _row):
                    with _col:
                        # 運用高效快取讀取縮圖
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
                            st.rerun()  # 選取時需要同步回主畫面表單，故進行全域刷新
        else:
            st.info("📭 R2 中暫無圖片")
    else:
        st.caption("⚠️ 請先在 `.env` 中設定 R2 憑證")


# 側邊欄渲染
with st.sidebar:
    st.title("🎬 Agnes Video V2.0")
    st.caption("視訊生成 API 操作面板")
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
        "🎞️ 生成模式",
        options=["文生視頻", "圖生視頻", "關鍵幀動畫"],
        index=0,
        help="選擇您要使用的視訊生成工作流。",
    )
    st.divider()

    # 執行渲染優化後的 Fragment 相簿
    r2_client = get_r2_client()
    sidebar_r2_album_fragment(r2_client)

    st.divider()
    st.markdown("### 📐 分辨率與尺寸說明")
    st.markdown(
        """
- 模型支援三檔標準分辨率：**480p / 720p / 1080p**
- 系統會自動將輸入尺寸映射到最近的標準規格。
- 推薦寬高比：

| 比例 | 場景 |
|------|------|
| 16:9 | 橫版、YouTube |
| 9:16 | 竖版、TikTok / Reels |
| 1:1 | 方形、社群 |
| 4:3 | 傳統橫版 |
| 3:4 | 竖版演示 |

> ⚠️ 最終尺寸以 API 回應中的 `size` 欄位為準。
        """
    )

# =========================================================================
# 主畫面 — 輸入控制區
# =========================================================================
st.header(f"🎬 {generation_mode}")
st.caption("填寫以下參數後，點擊「開始生成視訊」按鈕提交任務。")

prompt: str = st.text_area(
    "📝 提示詞 (Prompt)",
    value=st.session_state.get("prompt_text", ""),
    height=140,
    placeholder="請描述您想要生成的影片內容...",
    help="建議結構：[主體] + [動作] + [場景] + [鏡頭運動] + [光線] + [風格]。",
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

image_url_single: str = ""
extra_image_urls: list[str] = []
r2_picked: str = st.session_state.get("r2_picked_url", "")

if generation_mode == "圖生視頻":
    default_val = r2_picked if r2_picked else ""
    image_url_single = st.text_input(
        "🖼️ 圖片 URL",
        value=default_val,
        placeholder="https://example.com/image.png",
        help="輸入一張可公開訪問的圖片網址，或從左側 R2 相簿選取。",
    )

elif generation_mode == "關鍵幀動畫":
    st.markdown("#### 🖼️ 關鍵幀圖片 URLs（至少兩張）")
    if r2_picked:
        if st.button("➕ 加入 R2 選取的圖片", key="kf_add_r2", width="stretch"):
            filled = False
            for _i in range(st.session_state.kf_img_count):
                _k = f"kf_img_{_i}"
                if not st.session_state.get(_k, "").strip():
                    st.session_state[_k] = r2_picked
                    filled = True
                    break
            if not filled:
                st.session_state[f"kf_img_{st.session_state.kf_img_count}"] = r2_picked
                st.session_state.kf_img_count += 1
            st.rerun()

    if "kf_img_count" not in st.session_state:
        st.session_state.kf_img_count = 2

    for i in range(st.session_state.kf_img_count):
        url = st.text_input(f"關鍵幀 URL #{i + 1}", key=f"kf_img_{i}", placeholder="https://example.com/keyframe.png")
        if url.strip():
            extra_image_urls.append(url.strip())

    col_add2, col_rem2 = st.columns(2)
    with col_add2:
        if st.button("➕ 增加關鍵幀", width="stretch"):
            st.session_state.kf_img_count += 1
            st.rerun()
    with col_rem2:
        if st.button("➖ 移除最後一幀", width="stretch"):
            if st.session_state.kf_img_count > 2:
                st.session_state.kf_img_count -= 1
                st.rerun()

with st.expander("⚙️ 進階參數調整", expanded=False):
    adv_col1, adv_col2, adv_col3 = st.columns(3)
    with adv_col1:
        resolution_options = {
            "1920 × 1080 (16:9 全高清)": (1920, 1080),
            "1440 × 1080 (4:3 高清)": (1440, 1080),
            "1280 × 720 (16:9 高清)": (1280, 720),
            "960 × 720 (4:3 標清)": (960, 720),
        }
        resolution_label: str = st.selectbox("📐 解析度 (Resolution)", options=list(resolution_options.keys()), index=2)
        width, height = resolution_options[resolution_label]
    with adv_col2:
        # 根據所選解析度決定 1080p / 720p 模式
        _res_tier = "1080p" if height == 1080 else "720p"
        _res_frame_cfg = FRAME_OPTIONS_BY_RES_FPS[_res_tier]
        _fps_options = _res_frame_cfg["fps"]
        frame_rate: int = st.selectbox("幀率 (frame_rate)", options=_fps_options, index=0, format_func=lambda x: f"{x} fps")
        _frame_options = _res_frame_cfg[frame_rate]
        _frame_labels = [f"{frames} 幀（{label}）" for frames, label in _frame_options]
        _selected_idx = st.selectbox("幀數 (num_frames)", options=range(len(_frame_options)), index=0, format_func=lambda i: _frame_labels[i])
        num_frames = _frame_options[_selected_idx][0]
    with adv_col3:
        negative_prompt: str = st.text_input("反向提示詞 (negative_prompt)", placeholder="blurry, low quality")
        seed = st.number_input("隨機種子 (seed)", min_value=0, max_value=2_147_483_647, value=0, step=1)

estimated_seconds = num_frames / frame_rate
st.info(f"📊 **預估影片參數**：{num_frames} 幀 ÷ {frame_rate} fps ≈ **{estimated_seconds:.1f} 秒** ｜ 尺寸 {width}×{height}")
st.divider()

# =========================================================================
# 發送與封裝工作流邏輯 (維持原本 API 調用與輪詢不變)
# =========================================================================
def build_payload() -> dict | None:
    payload = {"model": MODEL_NAME, "prompt": prompt.strip(), "width": int(width), "height": int(height), "num_frames": int(num_frames), "frame_rate": int(frame_rate)}
    if negative_prompt.strip():
        payload["negative_prompt"] = negative_prompt.strip()
    if seed and seed > 0:
        payload["seed"] = int(seed)
    if generation_mode == "圖生視頻":
        if not image_url_single.strip():
            st.warning("⚠️ 圖生視頻模式需要輸入至少一張圖片 URL。")
            return None
        payload["image"] = image_url_single.strip()
    elif generation_mode == "關鍵幀動畫":
        if len(extra_image_urls) < 2:
            st.warning("⚠️ 關鍵幀動畫模式需要至少兩張關鍵幀圖片 URL。")
            return None
        payload["extra_body"] = {"image": extra_image_urls, "mode": "keyframes"}
    return payload

def create_video_task(payload: dict, headers: dict, max_retries: int = 3) -> dict | None:
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(CREATE_URL, json=payload, headers=headers, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            st.error(f"❌ 創建任務失敗（HTTP {resp.status_code}）：{resp.text}")
            return None
        except requests.RequestException as exc:
            if attempt < max_retries:
                time.sleep(attempt * 5)
                continue
            st.error(f"❌ 網路連線超時或失敗：{exc}")
    return None

def poll_video_status(video_id: str, headers: dict) -> dict | None:
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    poll_count = 0
    while poll_count < 360:
        poll_count += 1
        try:
            resp = requests.get(POLL_URL, params={"video_id": video_id, "model_name": MODEL_NAME}, headers=headers, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "")
                progress = data.get("progress", 0)
                progress_bar.progress(min(progress, 100))

                status_text = {STATUS_QUEUED: "🟡 排隊中", STATUS_IN_PROGRESS: "🔵 生成中", STATUS_COMPLETED: "🟢 已完成", STATUS_FAILED: "🔴 失敗"}.get(status, f"❓ {status}")
                status_placeholder.info(f"**狀態**：{status_text} | **進度**：{progress}% | **已輪詢**：{poll_count} 次")

                if status == STATUS_COMPLETED:
                    return data
                if status == STATUS_FAILED:
                    st.error(f"❌ 視訊生成失敗：{data.get('error', '未知錯誤')}")
                    return None
            else:
                # 非 200 回應（如 content_policy_violation 400/403）→ 立即中止
                try:
                    err_data = resp.json()
                    err_msg = err_data.get("error", {}).get("message", "") if isinstance(err_data.get("error"), dict) else str(err_data.get("error", resp.text))
                except Exception:
                    err_msg = resp.text
                st.error(f"❌ 輪詢收到錯誤回應（HTTP {resp.status_code}）：{err_msg}")
                return None
        except Exception as e:
            status_placeholder.warning(f"⚠️ 輪詢異常：{e}，繼續重試…")
        time.sleep(POLL_INTERVAL_SECONDS)
    return None

def save_generation_history(generation_mode: str, prompt: str, negative_prompt: str,
                            image_source: str, video_url: str) -> None:
    """將成功的生成記錄追加寫入 history/history_YYYY-MM-DD.json"""
    _HISTORY_DIR = "history"
    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generation_mode": generation_mode,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "image_source": image_source,
        "video_url": video_url,
    }

    os.makedirs(_HISTORY_DIR, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(_HISTORY_DIR, f"history_{today_str}.json")

    history_list: list[dict] = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                history_list = json.load(f)
        except (json.JSONDecodeError, OSError):
            history_list = []

    history_list.append(record)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=2)

if st.button("🚀 開始生成視訊", type="primary", width="stretch"):
    if not api_key.strip():
        st.error("❌ 請先在側邊欄輸入您的 API Key。")
        st.stop()
    if not prompt.strip():
        st.error("❌ 請輸入提示詞 (Prompt)。")
        st.stop()

    payload = build_payload()
    if payload is None:
        st.stop()

    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}

    with st.spinner("📡 正在向 API 發送視訊生成任務…"):
        create_data = create_video_task(payload, headers)

    if create_data is None:
        st.stop()

    video_id = create_data.get("video_id", "")
    task_id = create_data.get("task_id", create_data.get("id", ""))
    poll_id = video_id if video_id else task_id

    st.success(f"✅ 任務已建立！ 識別碼：`{poll_id}`")

    with st.spinner("⏳ 正在輪詢影片生成狀態，請耐心等候…"):
        if video_id:
            final_data = poll_video_status(video_id, headers)
        else:
            legacy_url = f"{CREATE_URL}/{task_id}"
            final_data = None
            status_ph = st.empty()
            prog_bar = st.progress(0)
            _poll = 0
            while _poll < 360:
                _poll += 1
                try:
                    _r = requests.get(legacy_url, headers=headers, timeout=120)
                    if _r.status_code == 200:
                        _d = _r.json()
                        _s = _d.get("status", "")
                        _p = _d.get("progress", 0)
                        prog_bar.progress(min(_p, 100))
                        status_ph.info(f"**狀態**：{_s} | **進度**：{_p}%")
                        if _s == STATUS_COMPLETED:
                            final_data = _d
                            break
                        if _s == STATUS_FAILED:
                            st.error(f"❌ 失敗：{_d.get('error', '未知')}")
                            break
                    else:
                        try:
                            _err = _r.json()
                            _em = _err.get("error", {}).get("message", "") if isinstance(_err.get("error"), dict) else str(_err.get("error", _r.text))
                        except Exception:
                            _em = _r.text
                        st.error(f"❌ 輪詢收到錯誤回應（HTTP {_r.status_code}）：{_em}")
                        break
                except Exception:
                    pass
                time.sleep(POLL_INTERVAL_SECONDS)

    if final_data:
        # 嘗試多個可能的影片 URL 欄位名（不同模式/版本可能使用不同欄位）
        output = final_data.get("output")
        video_url = (
            final_data.get("remixed_from_video_id")
            or final_data.get("video_url")
            or final_data.get("url")
            or (output.get("video_url") if isinstance(output, dict) else None)
            or ""
        )
        # 確保 video_url 為字串
        video_url = str(video_url).strip() if video_url else ""

        st.divider()
        st.subheader("🎉 影片生成完成！")

        if video_url and video_url.startswith("http"):
            # 先嘗試 st.video，失敗則回退到 HTML <video> 標籤
            try:
                st.video(video_url)
            except Exception:
                st.markdown(
                    f'<video src="{video_url}" controls autoplay loop muted style="width:100%;max-width:800px;"></video>',
                    unsafe_allow_html=True,
                )
            st.markdown(f"📥 [點擊下載影片]({video_url})")
        else:
            # 找不到影片 URL 時，列出所有回應 key 幫助除錯
            st.warning("⚠️ API 回應中未找到影片 URL，請查看下方完整回應以確認欄位名稱。")
            st.caption(f"已檢查欄位：remixed_from_video_id / video_url / url / output.video_url")
            if video_url:
                st.code(f"取得的值（非 http 開頭）：{video_url}")

        with st.expander("📄 查看完整 API 回應", expanded=not bool(video_url and video_url.startswith("http"))):
            st.json(final_data)

        # 儲存生成記錄到本地 history
        _img_src = ""
        if generation_mode == "圖生視頻":
            _img_src = image_url_single.strip()
        elif generation_mode == "關鍵幀動畫":
            _img_src = ", ".join(extra_image_urls)
        save_generation_history(generation_mode, prompt.strip(), negative_prompt.strip(), _img_src, video_url)

st.divider()
st.caption(f"Agnes Video V2.0 GUI — Powered by Streamlit | 模型：`{MODEL_NAME}`")