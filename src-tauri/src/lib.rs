use serde::Serialize;
use std::collections::HashMap;
use std::os::windows::process::CommandExt;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{Manager, State};

#[derive(Debug, Clone, Serialize)]
struct ServiceConfig {
    id: String,
    command: String,
    args: Vec<String>,
    working_dir: String,
    port: u16,
}

struct ServiceManager {
    configs: HashMap<String, ServiceConfig>,
    processes: Mutex<HashMap<String, Child>>,
}

impl ServiceManager {
    fn new() -> Self {
        let mut configs = HashMap::new();

        configs.insert(
            "agn_pic".to_string(),
            ServiceConfig {
                id: "agn_pic".to_string(),
                command: "streamlit".to_string(),
                args: vec![
                    "run".to_string(),
                    "agn_pic.py".to_string(),
                    "--server.port".to_string(),
                    "8501".to_string(),
                    "--server.headless".to_string(),
                    "true".to_string(),
                    "--server.enableWebsocketCompression".to_string(),
                    "false".to_string(),
                ],
                working_dir: "D:\\PV".to_string(),
                port: 8501,
            },
        );

        configs.insert(
            "agn_vid".to_string(),
            ServiceConfig {
                id: "agn_vid".to_string(),
                command: "streamlit".to_string(),
                args: vec![
                    "run".to_string(),
                    "agn_vid.py".to_string(),
                    "--server.port".to_string(),
                    "8502".to_string(),
                    "--server.headless".to_string(),
                    "true".to_string(),
                    "--server.enableWebsocketCompression".to_string(),
                    "false".to_string(),
                ],
                working_dir: "D:\\PV".to_string(),
                port: 8502,
            },
        );

        configs.insert(
            "grs_pic".to_string(),
            ServiceConfig {
                id: "grs_pic".to_string(),
                command: "streamlit".to_string(),
                args: vec![
                    "run".to_string(),
                    "grs_pic.py".to_string(),
                    "--server.port".to_string(),
                    "8503".to_string(),
                    "--server.headless".to_string(),
                    "true".to_string(),
                    "--server.enableWebsocketCompression".to_string(),
                    "false".to_string(),
                ],
                working_dir: "D:\\PV".to_string(),
                port: 8503,
            },
        );

        configs.insert(
            "history".to_string(),
            ServiceConfig {
                id: "history".to_string(),
                command: "cmd".to_string(),
                args: vec![
                    "/c".to_string(),
                    "npx".to_string(),
                    "vite".to_string(),
                    "--port".to_string(),
                    "3200".to_string(),
                ],
                working_dir: "D:\\PV\\history-viewer".to_string(),
                port: 3200,
            },
        );

        ServiceManager {
            configs,
            processes: Mutex::new(HashMap::new()),
        }
    }
}

/// Check if a port is reachable with a short timeout
async fn is_port_ready(port: u16) -> bool {
    reqwest::Client::new()
        .get(format!("http://localhost:{}", port))
        .timeout(std::time::Duration::from_millis(500))
        .send()
        .await
        .is_ok()
}

#[tauri::command]
async fn start_service(
    service_id: String,
    manager: State<'_, ServiceManager>,
) -> Result<String, String> {
    let config = manager
        .configs
        .get(&service_id)
        .ok_or_else(|| format!("Unknown service: {}", service_id))?
        .clone();

    // Check if already running
    let already_running = {
        let processes = manager.processes.lock().map_err(|e| e.to_string())?;
        processes.contains_key(&service_id)
    }; // Lock released here

    if already_running && is_port_ready(config.port).await {
        return Ok("already_running".to_string());
    }

    // Start the process
    let child = Command::new(&config.command)
        .args(&config.args)
        .current_dir(&config.working_dir)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .env("BROWSER", "none") // Prevent Vite from opening browser
        .creation_flags(0x08000000) // CREATE_NO_WINDOW
        .spawn()
        .map_err(|e| format!("Failed to start {}: {}", service_id, e))?;

    // Store the process handle
    {
        let mut processes = manager.processes.lock().map_err(|e| e.to_string())?;
        processes.insert(service_id.clone(), child);
    }

    // Poll for readiness in background (no manager access needed)
    let sid = service_id.clone();
    let port = config.port;
    tokio::spawn(async move {
        for _ in 0..60 {
            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
            if is_port_ready(port).await {
                println!("Service {} is ready on port {}", sid, port);
                return;
            }
        }
        println!("Service {} startup timeout after 30s", sid);
    });

    Ok("starting".to_string())
}

#[tauri::command]
async fn stop_service(
    service_id: String,
    manager: State<'_, ServiceManager>,
) -> Result<String, String> {
    let mut processes = manager.processes.lock().map_err(|e| e.to_string())?;

    if let Some(mut child) = processes.remove(&service_id) {
        child.kill().map_err(|e| format!("Failed to kill {}: {}", service_id, e))?;
        Ok("stopped".to_string())
    } else {
        Ok("not_running".to_string())
    }
}

#[tauri::command]
async fn get_service_status(
    service_id: String,
    manager: State<'_, ServiceManager>,
) -> Result<String, String> {
    let config = manager
        .configs
        .get(&service_id)
        .ok_or_else(|| format!("Unknown service: {}", service_id))?
        .clone();

    let has_process = {
        let processes = manager.processes.lock().map_err(|e| e.to_string())?;
        processes.contains_key(&service_id)
    }; // Lock released here

    if has_process {
        if is_port_ready(config.port).await {
            Ok("running".to_string())
        } else {
            Ok("starting".to_string())
        }
    } else {
        Ok("stopped".to_string())
    }
}

#[tauri::command]
async fn get_all_statuses(
    manager: State<'_, ServiceManager>,
) -> Result<HashMap<String, String>, String> {
    let mut statuses = HashMap::new();

    for (id, config) in &manager.configs {
        let has_process = {
            let processes = manager.processes.lock().map_err(|e| e.to_string())?;
            processes.contains_key(id)
        }; // Lock released here

        let status = if has_process {
            if is_port_ready(config.port).await {
                "running".to_string()
            } else {
                "starting".to_string()
            }
        } else {
            "stopped".to_string()
        };
        statuses.insert(id.clone(), status);
    }

    Ok(statuses)
}

#[tauri::command]
async fn stop_all_services(
    manager: State<'_, ServiceManager>,
) -> Result<String, String> {
    let mut processes = manager.processes.lock().map_err(|e| e.to_string())?;

    for (id, child) in processes.iter_mut() {
        let _ = child.kill();
        println!("Stopped service: {}", id);
    }

    processes.clear();
    Ok("all_stopped".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let manager = ServiceManager::new();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(manager)
        .invoke_handler(tauri::generate_handler![
            start_service,
            stop_service,
            get_service_status,
            get_all_statuses,
            stop_all_services,
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Stop all services when window is closed
                let state = window.state::<ServiceManager>();
                let mut processes = state.processes.lock().unwrap();
                for (id, child) in processes.iter_mut() {
                    let _ = child.kill();
                    println!("Cleaned up service: {}", id);
                }
                processes.clear();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
