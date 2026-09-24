# App icons

Binary icon assets (PNG / ICO / ICNS) are not committed in the initial text push.

Regenerate them from a source PNG with:

```bash
npm run tauri icon path/to/app-icon.png
```

Tauri expects at least: `32x32.png`, `128x128.png`, `128x128@2x.png`, `icon.icns`, `icon.ico`, `icon.png`.
