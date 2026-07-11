export default function ContentArea({ services, activeService, statuses }) {
  if (!activeService) {
    return (
      <div className="flex-1 flex items-center justify-center bg-content-bg">
        <div className="text-center">
          <div className="text-6xl mb-4">🤖</div>
          <h2 className="text-xl font-semibold text-gray-300 mb-2">
            歡迎使用 Agnes AI Toolkit
          </h2>
          <p className="text-sm text-gray-500">
            點擊左側導航選擇要使用的服務
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 relative bg-content-bg overflow-hidden">
      {services.map((service) => {
        const status = statuses[service.id] || "stopped";
        const isActive = activeService === service.id;

        if (!isActive) return null;

        if (status !== "running") {
          return (
            <div
              key={service.id}
              className="absolute inset-0 flex items-center justify-center"
            >
              <div className="text-center">
                <div
                  className={`inline-block w-8 h-8 border-3 rounded-full animate-spin mb-3 ${
                    status === "starting"
                      ? "border-status-starting border-t-transparent"
                      : "border-gray-600 border-t-transparent"
                  }`}
                  style={{ borderWidth: "3px" }}
                />
                <p className="text-sm text-gray-400">
                  {status === "starting"
                    ? `${service.name} 啟動中...`
                    : `${service.name} 未啟動`}
                </p>
                <p className="text-xs text-gray-600 mt-1">
                  {status === "starting"
                    ? "請稍候，服務正在準備中"
                    : "點擊左側按鈕啟動服務"}
                </p>
              </div>
            </div>
          );
        }

        return (
          <iframe
            key={service.id}
            src={service.url}
            className="absolute inset-0 w-full h-full border-0"
            title={service.name}
            allow="clipboard-read; clipboard-write"
          />
        );
      })}
    </div>
  );
}
