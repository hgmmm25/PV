import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import Sidebar from "./components/Sidebar.jsx";
import ContentArea from "./components/ContentArea.jsx";
import StatusBar from "./components/StatusBar.jsx";

const SERVICES = [
  {
    id: "agn_pic",
    name: "Agnes 圖片生成",
    icon: "🖼️",
    url: "http://localhost:8501",
  },
  {
    id: "agn_vid",
    name: "Agnes 影片生成",
    icon: "🎬",
    url: "http://localhost:8502",
  },
  {
    id: "grs_pic",
    name: "GRS 圖片生成",
    icon: "🖼️",
    url: "http://localhost:8503",
  },
  {
    id: "history",
    name: "歷史記錄",
    icon: "📋",
    url: "http://localhost:3200/history-viewer/",
  },
];

export default function App() {
  const [activeService, setActiveService] = useState(null);
  const [statuses, setStatuses] = useState({});

  const refreshStatuses = useCallback(async () => {
    try {
      const result = await invoke("get_all_statuses");
      setStatuses(result);
    } catch (e) {
      console.error("Failed to get statuses:", e);
    }
  }, []);

  // Poll statuses every 3 seconds
  useEffect(() => {
    refreshStatuses();
    const interval = setInterval(refreshStatuses, 3000);
    return () => clearInterval(interval);
  }, [refreshStatuses]);

  const handleSelectService = useCallback(
    async (serviceId) => {
      setActiveService(serviceId);
      const status = statuses[serviceId];
      if (status !== "running") {
        try {
          await invoke("start_service", { serviceId });
          // Status will be updated by the polling interval
        } catch (e) {
          console.error(`Failed to start ${serviceId}:`, e);
        }
      }
    },
    [statuses]
  );

  const handleStopService = useCallback(async (serviceId) => {
    try {
      await invoke("stop_service", { serviceId });
      setStatuses((prev) => ({ ...prev, [serviceId]: "stopped" }));
    } catch (e) {
      console.error(`Failed to stop ${serviceId}:`, e);
    }
  }, []);

  const handleStopAll = useCallback(async () => {
    try {
      await invoke("stop_all_services");
      setStatuses((prev) => {
        const next = { ...prev };
        for (const key of Object.keys(next)) {
          next[key] = "stopped";
        }
        return next;
      });
    } catch (e) {
      console.error("Failed to stop all services:", e);
    }
  }, []);

  const activeServiceData = SERVICES.find((s) => s.id === activeService);

  return (
    <div className="flex h-full">
      <Sidebar
        services={SERVICES}
        activeService={activeService}
        statuses={statuses}
        onSelect={handleSelectService}
        onStop={handleStopService}
      />
      <div className="flex flex-col flex-1 min-w-0">
        <ContentArea
          services={SERVICES}
          activeService={activeService}
          statuses={statuses}
        />
        <StatusBar
          services={SERVICES}
          statuses={statuses}
          onStopAll={handleStopAll}
        />
      </div>
    </div>
  );
}
