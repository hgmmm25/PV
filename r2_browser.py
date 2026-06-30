"""
r2_browser.py — Cloudflare R2 圖片瀏覽器 (效能優化版)
==================================================
依賴：boto3, python-dotenv, streamlit, pillow

提供：
  • get_r2_client()         — 建立 R2 S3 相容客戶端
  • list_images()           — 列出儲存桶中所有圖片（依修改時間新→舊）
  • get_thumbnail_cached()   — 核心優化：磁碟級快取與高效縮圖讀取
  • render_image_picker()   — Streamlit UI 元件：局部區域重繪網格相簿
"""

import os
import hashlib
from datetime import datetime
from io import BytesIO
from typing import Optional

import boto3
import streamlit as st
from botocore.config import Config
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# ---------------------------------------------------------------------------
# R2 連線設定
# ---------------------------------------------------------------------------
_R2_ACCOUNT_ID  = os.getenv("R2_ACCOUNT_ID", "")
_R2_ACCESS_KEY  = os.getenv("R2_ACCESS_KEY_ID", "")
_R2_SECRET_KEY  = os.getenv("R2_SECRET_ACCESS_KEY", "")
_R2_BUCKET      = os.getenv("R2_BUCKET_NAME", "")
_R2_PUBLIC_DOM  = os.getenv("R2_PUBLIC_DOMAIN", "img.hugely2541.dpdns.org")

# 支援的圖片副檔名
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".avif"}
_CACHE_DIR = ".thumbnail_cache"


@st.cache_resource
def get_r2_client():
    """建立並快取 R2 S3 相容客戶端。"""
    if not all([_R2_ACCOUNT_ID, _R2_ACCESS_KEY, _R2_SECRET_KEY]):
        return None
    return boto3.client(
        "s3",
        endpoint_url=f"https://{_R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=_R2_ACCESS_KEY,
        aws_secret_access_key=_R2_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


@st.cache_data(ttl=60)
def list_images(bucket: str = "", prefix: str = "") -> list[dict]:
    """
    列出 R2 儲存桶中的所有圖片，按最後修改時間新→舊排序。
    """
    client = get_r2_client()
    if client is None:
        return []

    bucket = bucket or _R2_BUCKET
    if not bucket:
        return []

    images = []
    paginator = client.get_paginator("list_objects_v2")
    page_kwargs = {"Bucket": bucket}
    if prefix:
        page_kwargs["Prefix"] = prefix

    for page in paginator.paginate(**page_kwargs):
        for obj in page.get("Contents", []):
            key: str = obj["Key"]
            ext = os.path.splitext(key)[1].lower()
            if ext not in _IMAGE_EXTENSIONS:
                continue

            public_url = f"https://{_R2_PUBLIC_DOM}/{key}"

            images.append({
                "key": key,
                "filename": os.path.basename(key),
                "size": obj.get("Size", 0),
                "last_modified": obj.get("LastModified", datetime.min),
                "url": public_url,
            })

    images.sort(key=lambda x: x["last_modified"], reverse=True)
    return images


def get_thumbnail_cached(client, bucket: str, key: str, last_modified, thumb_size: tuple = (160, 160)) -> Optional[Image.Image]:
    """
    【核心快取優化】
    結合 Key 與修改時間戳記生成唯一的 MD5 雜湊檔名。
    快取命中：直接從磁碟以二進位讀入記憶體，釋放檔案鎖，毫秒級渲染。
    快取未命中：才從 R2 下載大圖，利用 PIL 快速建立縮圖並持久化儲存。
    """
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
        
        # 安全儲存為本地輕量 PNG 快取
        pil_img.save(cache_path, "PNG")
        return pil_img
    except Exception:
        return None


def _format_size(size_bytes: int) -> str:
    """人類可讀的檔案大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / 1024 ** 2:.1f} MB"


@st.fragment
def render_image_picker(
    label: str = "🖼️ 從 R2 相簿選擇圖片",
    key: str = "r2_picker",
    bucket: str = "",
    prefix: str = "",
    cols_per_row: int = 4,
    thumb_width: int = 200,
) -> Optional[str]:
    """
    在 Streamlit 中渲染一個優化後的 R2 圖片瀏覽器。
    加上 @st.fragment 確保翻頁操作不會引發全網頁大重繪。
    """
    bucket = bucket or _R2_BUCKET

    client = get_r2_client()
    if client is None:
        st.warning("⚠️ R2 連線未設定。")
        return None

    if not bucket:
        st.warning("⚠️ 請在 `.env` 中設定 `R2_BUCKET_NAME`。")
        return None

    images = list_images(bucket=bucket, prefix=prefix)
    if not images:
        st.info("📭 儲存桶中沒有找到圖片。")
        return None

    st.markdown(f"### {label}")
    st.caption(f"共 **{len(images)}** 張圖片｜按上傳時間新→舊排列")

    options = [
        f"[{img['last_modified'].strftime('%Y-%m-%d %H:%M')}] {img['filename']}"
        if isinstance(img["last_modified"], datetime)
        else img["filename"]
        for img in images
    ]

    selected_index = st.selectbox(
        "快速選擇（下拉）",
        options=range(len(options)),
        format_func=lambda i: options[i],
        key=f"{key}_select",
        label_visibility="collapsed",
        placeholder="選擇一張圖片…",
    )

    selected_url = images[selected_index]["url"] if selected_index is not None else None
    st.divider()

    st.markdown("#### 📂 相簿瀏覽 點擊縮圖可快速選取")

    state_key = f"{key}_selected_idx"
    if state_key not in st.session_state:
        st.session_state[state_key] = None

    per_page = cols_per_row * 3
    total_pages = max(1, (len(images) + per_page - 1) // per_page)

    page_key = f"{key}_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    if total_pages > 1:
        pcol1, pcol2, pcol3 = st.columns([1, 3, 1])
        with pcol1:
            if st.button("⬅️ 上一頁", key=f"{key}_prev", use_container_width=True):
                st.session_state[page_key] = max(0, st.session_state[page_key] - 1)
                # 移除 st.rerun() 讓 fragment 局部重繪即可
        with pcol2:
            st.markdown(
                f"<p style='text-align:center;'>第 {st.session_state[page_key] + 1} / {total_pages} 頁</p>",
                unsafe_allow_html=True,
            )
        with pcol3:
            if st.button("下一頁 ➡️", key=f"{key}_next", use_container_width=True):
                st.session_state[page_key] = min(total_pages - 1, st.session_state[page_key] + 1)
                # 移除 st.rerun() 讓 fragment 局部重繪即可

    start = st.session_state[page_key] * per_page
    end = min(start + per_page, len(images))
    page_images = images[start:end]

    for row_start in range(0, len(page_images), cols_per_row):
        row_imgs = page_images[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row)

        for col_idx, (col, img) in enumerate(zip(cols, row_imgs)):
            global_idx = start + row_start + col_idx
            with col:
                # 引入高效磁碟快取優化
                pil_img = get_thumbnail_cached(client, bucket, img["key"], img["last_modified"], (thumb_width, thumb_width))
                if pil_img:
                    st.image(pil_img, use_container_width=True)
                else:
                    st.markdown(
                        f"<div style='width:{thumb_width}px;height:{thumb_width}px;"
                        f"background:#eee;display:flex;align-items:center;"
                        f"justify-content:center;border-radius:8px;'>🖼️</div>",
                        unsafe_allow_html=True,
                    )

                mtime = img["last_modified"]
                time_str = mtime.strftime("%m-%d %H:%M") if isinstance(mtime, datetime) else "—"
                st.caption(f"`{img['filename']}`")
                st.caption(f"{time_str} | {_format_size(img['size'])}")

                is_selected = st.session_state[state_key] == global_idx
                btn_label = "✅ 已選取" if is_selected else "選取"
                if st.button(
                    btn_label,
                    key=f"{key}_btn_{global_idx}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state[state_key] = global_idx
                    st.session_state["r2_picked_url"] = img["url"]
                    st.rerun()  # 選取時保留全域 rerun 以便刷新主畫面表單輸入框

    if st.session_state[state_key] is not None:
        idx = st.session_state[state_key]
        if 0 <= idx < len(images):
            selected_url = images[idx]["url"]

    if selected_url:
        st.success(f"🔗 **已選圖片 URL**：`{selected_url}`")

    return selected_url