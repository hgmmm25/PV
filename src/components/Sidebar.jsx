import { useState } from "react";

const STATUS_COLORS = {
  running: "bg-status-running",
  starting: "bg-status-starting",
  stopped: "bg-status-stopped",
};

const STATUS_LABELS = {
  running: "運行中",
  starting: "啟動中",
  stopped: "已停止",
};

export default function Sidebar({ services, activeService, statuses, onSelect, onStop }) {
  return (
    <div className="w-56 flex flex-col bg-sidebar-bg border-r border-gray-700/50 h-full">
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-700/50">
        <h1 className="text-lg font-bold text-sidebar-text">Agnes AI</h1>
        <p className="text-xs text-sidebar-muted">Toolkit</p>
      </div>

      {/* Service List */}
      <nav className="flex-1 overflow-y-auto py-2">
        {services.map((service) => {
          const status = statuses[service.id] || "stopped";
          const isActive = activeService === service.id;

          return (
            <div key={service.id} className="px-2 mb-1">
              <button
                onClick={() => onSelect(service.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 text-left ${
                  isActive
                    ? "bg-sidebar-active text-white"
                    : "text-sidebar-text hover:bg-sidebar-hover"
                }`}
              >
                <span className="text-xl flex-shrink-0">{service.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{service.name}</div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_COLORS[status]} ${
                        status === "starting" ? "animate-pulse" : ""
                      }`}
                    />
                    <span className="text-xs text-sidebar-muted">
                      {STATUS_LABELS[status]}
                    </span>
                  </div>
                </div>
                {status === "running" && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onStop(service.id);
                    }}
                    className="text-xs text-red-400 hover:text-red-300 hover:bg-red-900/30 px-1.5 py-0.5 rounded"
                    title="停止服務"
                  >
                    ■
                  </button>
                )}
              </button>
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-700/50 text-xs text-sidebar-muted">
        Agnes AI Toolkit v1.0
      </div>
    </div>
  );
}
