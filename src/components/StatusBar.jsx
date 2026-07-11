export default function StatusBar({ services, statuses, onStopAll }) {
  const runningCount = services.filter(
    (s) => statuses[s.id] === "running"
  ).length;
  const startingCount = services.filter(
    (s) => statuses[s.id] === "starting"
  ).length;

  return (
    <div className="h-8 bg-sidebar-bg border-t border-gray-700/50 flex items-center justify-between px-4 text-xs text-sidebar-muted">
      <div className="flex items-center gap-3">
        <span>
          {runningCount > 0 ? (
            <>
              <span className="text-status-running">●</span>{" "}
              {runningCount} 個服務運行中
            </>
          ) : (
            <>
              <span className="text-status-stopped">●</span> 無服務運行
            </>
          )}
        </span>
        {startingCount > 0 && (
          <span className="text-status-starting animate-pulse">
            {startingCount} 個啟動中...
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {runningCount > 0 && (
          <button
            onClick={onStopAll}
            className="text-red-400 hover:text-red-300 hover:bg-red-900/30 px-2 py-0.5 rounded transition-colors"
          >
            全部停止
          </button>
        )}
      </div>
    </div>
  );
}
