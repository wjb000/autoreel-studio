use tauri::Manager;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Welcome to AutoReel Studio, {}!", name)
}

#[tauri::command]
fn get_sidecar_url() -> String {
    std::env::var("SIDECAR_URL").unwrap_or_else(|_| "http://127.0.0.1:8765".into())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![greet, get_sidecar_url])
        .setup(|app| {
            // In production, sidecar is spawned by Tauri externalBin / beforeDevCommand scripts.
            // Dev mode: run scripts/dev.sh which starts uvicorn separately.
            let _ = app;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running AutoReel Studio");
}
