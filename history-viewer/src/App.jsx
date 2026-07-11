import React, { useState, useEffect, useMemo, useCallback } from "react";

// ═══════════════════════════════════════════════════════════════════
//  Helpers
// ═══════════════════════════════════════════════════════════════════

/**
 * Extract filename from a URL string.
 * e.g. "https://example.com/path/cat.png" → "cat.png"
 */
const extractFilename = (url) => {
  if (!url) return null;
  try {
    const decoded = decodeURIComponent(new URL(url.trim()).pathname);
    return decoded.split("/").filter(Boolean).pop() || url;
  } catch {
    const parts = url.trim().split("/");
    return decodeURIComponent(parts[parts.length - 1]) || url;
  }
};

/**
 * image_source may contain multiple comma-separated URLs.
 */
const parseImageSources = (raw) => {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
};

/**
 * Colour mapping per generation_mode.
 */
const MODE_STYLES = {
  "關鍵幀動畫": {
    bg: "bg-violet-100",
    text: "text-violet-800",
    ring: "ring-violet-300",
  },
  "文字轉影片": {
    bg: "bg-sky-100",
    text: "text-sky-800",
    ring: "ring-sky-300",
  },
  "圖片轉影片": {
    bg: "bg-amber-100",
    text: "text-amber-800",
    ring: "ring-amber-300",
  },
  "圖生視頻": {
    bg: "bg-emerald-100",
    text: "text-emerald-800",
    ring: "ring-emerald-300",
  },
};

const FALLBACK_STYLE = {
  bg: "bg-gray-100",
  text: "text-gray-700",
  ring: "ring-gray-300",
};

const getModeStyle = (mode) => MODE_STYLES[mode] || FALLBACK_STYLE;

// ═══════════════════════════════════════════════════════════════════
//  Data Loading  (Vite glob → runtime fetch fallback)
// ═══════════════════════════════════════════════════════════════════

async function loadAllHistory() {
  // ① Vite import.meta.glob (eager, resolved at build/dev time)
  try {
    const mods = import.meta.glob("/history/*.json", { eager: true });
    const result = {};
    for (const [path, mod] of Object.entries(mods)) {
      const m = path.match(/history_(\d{4}-\d{2}-\d{2})\.json$/);
      if (m) result[m[1]] = mod.default ?? mod;
    }
    if (Object.keys(result).length > 0) return result;
  } catch {
    /* not in Vite – fall through */
  }

  // ② Runtime fetch fallback (production / non-Vite)
  try {
    const res = await fetch("/history/dates.json");
    if (res.ok) {
      const dates = await res.json();
      const result = {};
      await Promise.all(
        dates.map(async (d) => {
          try {
            const r = await fetch(`/history/history_${d}.json`);
            if (r.ok) {
              const data = await r.json();
              if (Array.isArray(data) && data.length) result[d] = data;
            }
          } catch {
            /* skip */
          }
        })
      );
      return result;
    }
  } catch {
    /* no dates.json */
  }

  // ③ Brute-force: try the last 14 days
  const result = {};
  const now = new Date();
  await Promise.all(
    Array.from({ length: 14 }, (_, i) => {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      return fetch(`/history/history_${key}.json`)
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (Array.isArray(data) && data.length) result[key] = data;
        })
        .catch(() => {});
    })
  );
  return result;
}

// ═══════════════════════════════════════════════════════════════════
//  Sub-components
// ═══════════════════════════════════════════════════════════════════

// ─── Clipboard Hook ─────────────────────────────────────────────────
function useCopy() {
  const [copiedId, setCopiedId] = useState(null);

  const copy = useCallback((text, id) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1600);
    });
  }, []);

  return { copiedId, copy };
}

// ─── Copy Button ─────────────────────────────────────────────────────
function CopyBtn({ text, id, copiedId, onCopy }) {
  return (
    <button
      onClick={() => onCopy(text, id)}
      className="absolute top-2 right-2 p-1.5 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-200/80 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400"
      title="一鍵複製"
    >
      {copiedId === id ? (
        <svg
          className="w-4 h-4 text-green-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2.5}
            d="M5 13l4 4L19 7"
          />
        </svg>
      ) : (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
          />
        </svg>
      )}
    </button>
  );
}

// ─── Sidebar ─────────────────────────────────────────────────────────
function Sidebar({ dates, selected, onSelect }) {
  return (
    <aside className="w-64 shrink-0 border-r border-gray-200 bg-gray-50/80 flex flex-col h-screen overflow-hidden">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-gray-200">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">🎬</span>
          <h1 className="text-sm font-bold text-gray-900 tracking-tight leading-tight">
            AI 影片生成
            <br />
            歷史日誌
          </h1>
        </div>
      </div>

      {/* Date list */}
      <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-0.5">
        <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400 select-none">
          歷史檔案列表
        </p>

        {!dates.length && (
          <p className="px-2 text-xs text-gray-400 italic">No records found</p>
        )}

        {dates.map((date) => {
          const active = date === selected;
          return (
            <button
              key={date}
              onClick={() => onSelect(date)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 flex items-center gap-2.5
                ${
                  active
                    ? "bg-white text-gray-900 shadow-sm ring-1 ring-gray-200"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-800"
                }`}
            >
              <svg
                className={`w-4 h-4 shrink-0 ${
                  active ? "text-blue-500" : "text-gray-400"
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <span>{date}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-200 text-[10px] text-gray-400 select-none">
        共 {dates.length} 天紀錄
      </div>
    </aside>
  );
}

// ─── Single Log Item ─────────────────────────────────────────────────
function LogItem({ item, index, copiedId, onCopy }) {
  const mode = getModeStyle(item.generation_mode);
  const images = parseImageSources(item.image_source);
  const videoName = extractFilename(item.video_url);
  const time = item.timestamp?.split(" ")[1] ?? item.timestamp;

  return (
    <article className="group relative flex gap-4">
      {/* Timeline */}
      <div className="flex flex-col items-center pt-1.5">
        <div className="w-3 h-3 rounded-full bg-blue-500 ring-4 ring-blue-100 shrink-0 z-10" />
        <div className="w-px flex-1 bg-gray-200 group-last:hidden" />
      </div>

      {/* Card */}
      <div className="flex-1 pb-8 group-last:pb-0 min-w-0">
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden">
          {/* ── Header: timestamp + mode pill ── */}
          <div className="flex items-center gap-3 px-4 py-2.5 border-b border-gray-100 bg-gray-50/60">
            <span className="font-mono text-xs text-gray-500 tracking-wide">
              {time}
            </span>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold ring-1 ring-inset ${mode.bg} ${mode.text} ${mode.ring}`}
            >
              {item.generation_mode}
            </span>
          </div>

          <div className="px-4 py-3 space-y-3">
            {/* ── Files ── */}
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs">
              {/* Input images */}
              <div className="flex items-start gap-1.5 min-w-0">
                <span className="text-gray-400 font-medium whitespace-nowrap pt-px">
                  輸入圖：
                </span>
                <div className="flex flex-col gap-0.5 min-w-0">
                  {images.map((url, i) => (
                    <a
                      key={i}
                      href={url.trim()}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 hover:underline font-mono break-all leading-relaxed"
                    >
                      {extractFilename(url)}
                    </a>
                  ))}
                </div>
              </div>

              {/* Output video (text only, no link) */}
              <div className="flex items-start gap-1.5 min-w-0">
                <span className="text-gray-400 font-medium whitespace-nowrap pt-px">
                  輸出影片：
                </span>
                <span className="font-mono text-gray-700 break-all leading-relaxed">
                  {videoName || "—"}
                </span>
              </div>
            </div>

            {/* ── Prompt block ── */}
            <div className="relative rounded-lg bg-gray-50 border border-gray-200 p-3 pr-10">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5 select-none">
                Prompt
              </p>
              <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap break-words font-mono">
                {item.prompt || "（empty）"}
              </p>
              <CopyBtn
                text={item.prompt || ""}
                id={`p-${index}`}
                copiedId={copiedId}
                onCopy={onCopy}
              />
            </div>

            {/* ── Negative Prompt (only when present) ── */}
            {item.negative_prompt?.trim() && (
              <div className="relative rounded-lg bg-red-50/40 border border-red-100 p-3 pr-10">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-red-400 mb-1.5 select-none">
                  Negative Prompt
                </p>
                <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap break-words font-mono">
                  {item.negative_prompt}
                </p>
                <CopyBtn
                  text={item.negative_prompt}
                  id={`np-${index}`}
                  copiedId={copiedId}
                  onCopy={onCopy}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

// ─── Main Panel ──────────────────────────────────────────────────────
function MainPanel({ date, items }) {
  const { copiedId, copy } = useCopy();

  if (!date) {
    return (
      <main className="flex-1 flex items-center justify-center bg-white">
        <div className="text-center space-y-3 text-gray-400">
          <svg
            className="w-16 h-16 mx-auto text-gray-200"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.2}
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
          <p className="text-sm">← 從左側邊欄選擇日期</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 overflow-y-auto h-screen bg-white">
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Date heading */}
        <header className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-3">
            <span className="text-3xl">📋</span>
            {date}
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            共 {items.length} 條生成紀錄
          </p>
        </header>

        {/* Timeline feed */}
        {items.length === 0 ? (
          <p className="text-sm text-gray-400 italic">此日期無紀錄。</p>
        ) : (
          items.map((item, idx) => (
            <LogItem
              key={idx}
              item={item}
              index={idx}
              copiedId={copiedId}
              onCopy={copy}
            />
          ))
        )}
      </div>
    </main>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  App Root
// ═══════════════════════════════════════════════════════════════════

export default function App() {
  const [history, setHistory] = useState({});
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAllHistory()
      .then((data) => {
        setHistory(data);
        const sorted = Object.keys(data).sort().reverse();
        if (sorted.length) setSelected(sorted[0]);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const dates = useMemo(
    () => Object.keys(history).sort().reverse(),
    [history]
  );

  const currentItems = useMemo(() => {
    if (!selected || !history[selected]) return [];
    return [...history[selected]].sort((a, b) =>
      (a.timestamp || "").localeCompare(b.timestamp || "")
    );
  }, [history, selected]);

  // ── Loading state ──
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="flex items-center gap-3 text-gray-500 text-sm">
          <svg
            className="animate-spin w-5 h-5 text-blue-500"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
          正在載入歷史紀錄…
        </div>
      </div>
    );
  }

  // ── Error state ──
  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="text-center space-y-2 text-sm">
          <p className="text-red-500 font-medium">載入失敗</p>
          <p className="text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-white text-gray-900 antialiased">
      <Sidebar dates={dates} selected={selected} onSelect={setSelected} />
      <MainPanel date={selected} items={currentItems} />
    </div>
  );
}
