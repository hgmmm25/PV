import React, { useState, useEffect, useMemo } from "react";

// ─── Helper: Extract filename from a URL ────────────────────────────
const extractFilename = (url) => {
  if (!url) return null;
  try {
    const pathname = new URL(url.trim()).pathname;
    const decoded = decodeURIComponent(pathname);
    return decoded.split("/").filter(Boolean).pop() || url;
  } catch {
    // fallback: just grab the last segment
    const parts = url.trim().split("/");
    return decodeURIComponent(parts[parts.length - 1]) || url;
  }
};

// ─── Helper: Parse image_source which may contain multiple URLs ─────
const parseImageSources = (raw) => {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
};

// ─── Pill colour map for generation_mode ─────────────────────────────
const modeColors = {
  "關鍵幀動畫": { bg: "bg-violet-100", text: "text-violet-800", ring: "ring-violet-300" },
  "文字轉影片": { bg: "bg-sky-100", text: "text-sky-800", ring: "ring-sky-300" },
  "圖片轉影片": { bg: "bg-amber-100", text: "text-amber-800", ring: "ring-amber-300" },
};

const defaultModeColor = { bg: "bg-gray-100", text: "text-gray-700", ring: "ring-gray-300" };

const getModeStyle = (mode) => modeColors[mode] || defaultModeColor;

// ─── Copy-to-clipboard hook ─────────────────────────────────────────
const useCopy = () => {
  const [copiedIdx, setCopiedIdx] = useState(null);

  const copy = (text, idx) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(null), 1600);
    });
  };

  return { copiedIdx, copy };
};

// ─── Data loading (Vite / webpack import.meta.glob fallback) ────────
// In production, replace this with a real fetch to your API or static files.
const loadHistoryData = async () => {
  // Attempt dynamic import of JSON files under /history/*.json
  // Works with Vite's import.meta.glob
  try {
    const modules = import.meta.glob("/history/*.json", { eager: true });
    const result = {};
    for (const path in modules) {
      const dateMatch = path.match(/history_(\d{4}-\d{2}-\d{2})\.json$/);
      if (dateMatch) {
        result[dateMatch[1]] = modules[path].default || modules[path];
      }
    }
    if (Object.keys(result).length > 0) return result;
  } catch {
    // fall through
  }

  // Fallback: try fetching from /history/ directory
  try {
    // We can't list a directory from the browser, so we attempt known dates
    // In a real app, you'd have an API endpoint that lists available dates.
    const candidates = [
      "2026-07-11",
      "2026-07-10",
      "2026-07-09",
      "2026-07-08",
      "2026-07-07",
    ];
    const result = {};
    await Promise.all(
      candidates.map(async (date) => {
        try {
          const res = await fetch(`/history/history_${date}.json`);
          if (res.ok) {
            const data = await res.json();
            if (Array.isArray(data) && data.length > 0) {
              result[date] = data;
            }
          }
        } catch {
          /* skip */
        }
      })
    );
    return result;
  } catch {
    return {};
  }
};

// ═════════════════════════════════════════════════════════════════════
//  COMPONENTS
// ═════════════════════════════════════════════════════════════════════

// ─── Sidebar ─────────────────────────────────────────────────────────
const Sidebar = ({ dates, selectedDate, onSelect }) => (
  <aside className="w-64 shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col h-screen overflow-hidden">
    {/* Brand header */}
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
      <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
        History Files
      </p>
      {dates.length === 0 && (
        <p className="px-2 text-xs text-gray-400 italic">No records found</p>
      )}
      {dates.map((date) => {
        const isActive = date === selectedDate;
        return (
          <button
            key={date}
            onClick={() => onSelect(date)}
            className={`
              w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150
              flex items-center gap-2.5
              ${
                isActive
                  ? "bg-white text-gray-900 shadow-sm ring-1 ring-gray-200"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-800"
              }
            `}
          >
            <svg
              className={`w-4 h-4 shrink-0 ${isActive ? "text-blue-500" : "text-gray-400"}`}
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
    <div className="px-5 py-3 border-t border-gray-200 text-[10px] text-gray-400">
      {dates.length} day{dates.length !== 1 ? "s" : ""} on record
    </div>
  </aside>
);

// ─── Copy Button ─────────────────────────────────────────────────────
const CopyButton = ({ text, idx, copiedIdx, onCopy }) => (
  <button
    onClick={() => onCopy(text, idx)}
    className="
      absolute top-2 right-2 p-1.5 rounded-md
      text-gray-400 hover:text-gray-700 hover:bg-gray-200
      transition-colors duration-150
      focus:outline-none focus:ring-2 focus:ring-blue-400
    "
    title="Copy prompt"
  >
    {copiedIdx === idx ? (
      // check icon
      <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
      </svg>
    ) : (
      // clipboard icon
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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

// ─── Single Log Item ─────────────────────────────────────────────────
const LogItem = ({ item, index, copiedIdx, onCopy }) => {
  const modeStyle = getModeStyle(item.generation_mode);
  const images = parseImageSources(item.image_source);
  const videoFilename = extractFilename(item.video_url);
  const time = item.timestamp?.split(" ")[1] || item.timestamp;

  return (
    <article className="group relative flex gap-4">
      {/* Timeline connector */}
      <div className="flex flex-col items-center pt-1">
        <div className="w-3 h-3 rounded-full bg-blue-500 ring-4 ring-blue-100 shrink-0 z-10" />
        <div className="w-px flex-1 bg-gray-200 group-last:hidden" />
      </div>

      {/* Card */}
      <div className="flex-1 pb-8 group-last:pb-0">
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden">
          {/* ── Header ── */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 bg-gray-50/50">
            {/* Timestamp */}
            <span className="font-mono text-xs text-gray-500 tracking-wide">{time}</span>
            {/* Mode pill */}
            <span
              className={`
                inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold
                ring-1 ring-inset ${modeStyle.bg} ${modeStyle.text} ${modeStyle.ring}
              `}
            >
              {item.generation_mode}
            </span>
          </div>

          <div className="px-4 py-3 space-y-3">
            {/* ── Files row ── */}
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
              {/* Input images */}
              <div className="flex items-start gap-1.5">
                <span className="text-gray-400 font-medium whitespace-nowrap">輸入圖：</span>
                <div className="flex flex-col gap-0.5">
                  {images.map((url, i) => {
                    const fname = extractFilename(url);
                    return (
                      <a
                        key={i}
                        href={url.trim()}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 hover:underline font-mono break-all leading-relaxed"
                      >
                        {fname}
                      </a>
                    );
                  })}
                </div>
              </div>

              {/* Output video */}
              <div className="flex items-start gap-1.5">
                <span className="text-gray-400 font-medium whitespace-nowrap">輸出影片：</span>
                <span className="font-mono text-gray-700 break-all leading-relaxed">
                  {videoFilename || "—"}
                </span>
              </div>
            </div>

            {/* ── Prompt block ── */}
            <div className="relative rounded-lg bg-gray-50 border border-gray-200 p-3 pr-10">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Prompt
              </p>
              <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap break-words font-mono">
                {item.prompt || "（empty）"}
              </p>
              <CopyButton text={item.prompt || ""} idx={`p-${index}`} copiedIdx={copiedIdx} onCopy={onCopy} />
            </div>

            {/* ── Negative prompt (only if present) ── */}
            {item.negative_prompt && item.negative_prompt.trim() !== "" && (
              <div className="relative rounded-lg bg-red-50/50 border border-red-100 p-3 pr-10">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-red-400 mb-1.5">
                  Negative Prompt
                </p>
                <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap break-words font-mono">
                  {item.negative_prompt}
                </p>
                <CopyButton
                  text={item.negative_prompt}
                  idx={`np-${index}`}
                  copiedIdx={copiedIdx}
                  onCopy={onCopy}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </article>
  );
};

// ─── Main Content ────────────────────────────────────────────────────
const MainContent = ({ date, items }) => {
  const { copiedIdx, copy } = useCopy();

  if (!date) {
    return (
      <main className="flex-1 flex items-center justify-center text-gray-400 text-sm">
        <div className="text-center space-y-2">
          <svg className="w-12 h-12 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 4V2m0 2a7 7 0 1014 0M7 2a7 7 0 0114 0" />
          </svg>
          <p>← Select a date from the sidebar</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 overflow-y-auto h-screen">
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Date heading */}
        <header className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-3">
            <span className="text-3xl">📋</span>
            {date}
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            {items.length} generation record{items.length !== 1 ? "s" : ""}
          </p>
        </header>

        {/* Timeline feed */}
        {items.length === 0 ? (
          <p className="text-sm text-gray-400 italic">No records for this date.</p>
        ) : (
          <div className="space-y-0">
            {items.map((item, idx) => (
              <LogItem
                key={idx}
                item={item}
                index={idx}
                copiedIdx={copiedIdx}
                onCopy={copy}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
};

// ═════════════════════════════════════════════════════════════════════
//  ROOT COMPONENT
// ═════════════════════════════════════════════════════════════════════

export default function AIVideoHistoryPanel({ data: externalData }) {
  const [historyData, setHistoryData] = useState(externalData || {});
  const [selectedDate, setSelectedDate] = useState(null);
  const [loading, setLoading] = useState(!externalData);

  // Load data on mount (unless passed via props)
  useEffect(() => {
    if (externalData && Object.keys(externalData).length > 0) {
      setHistoryData(externalData);
      const sorted = Object.keys(externalData).sort().reverse();
      if (sorted.length > 0) setSelectedDate(sorted[0]);
      return;
    }

    loadHistoryData().then((data) => {
      setHistoryData(data);
      const sorted = Object.keys(data).sort().reverse();
      if (sorted.length > 0) setSelectedDate(sorted[0]);
      setLoading(false);
    });
  }, [externalData]);

  // Sorted date list (newest first)
  const dates = useMemo(
    () => Object.keys(historyData).sort().reverse(),
    [historyData]
  );

  // Current items
  const currentItems = useMemo(() => {
    if (!selectedDate || !historyData[selectedDate]) return [];
    // Sort by timestamp ascending
    return [...historyData[selectedDate]].sort((a, b) =>
      (a.timestamp || "").localeCompare(b.timestamp || "")
    );
  }, [historyData, selectedDate]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 text-gray-500 text-sm">
        <svg className="animate-spin w-5 h-5 mr-2 text-blue-500" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
        Loading history…
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-white text-gray-900 font-sans antialiased">
      <Sidebar dates={dates} selectedDate={selectedDate} onSelect={setSelectedDate} />
      <MainContent date={selectedDate} items={currentItems} />
    </div>
  );
}
