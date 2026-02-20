# My Clipboard Manager

A lightweight clipboard history manager for Windows 11. Runs silently in your system tray, saves everything you copy to a local SQLite database, and lets you instantly search and paste from your history.

## Features

- **Double-tap Alt** to open the popup at your cursor
- **Search** your clipboard history by typing
- **Arrow keys + Enter** to navigate and select
- **Auto-paste** directly into the previously active window
- **Delete key** to remove items from history
- **SQLite persistence** - history survives reboots (last 50 items)
- **System tray** - runs invisibly in the background
- **Dark theme** popup UI

## Tech Stack

| Component | Purpose |
|-----------|---------|
| Python | Core runtime |
| Tkinter | Popup UI (ships with Python) |
| SQLite | Persistent clipboard history |
| keyboard | Global hotkey capture (double-tap Alt) |
| pyperclip | Clipboard polling |
| pystray + Pillow | System tray icon |
| ctypes | Windows API for focus management |

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

Double-click `start_myclipboardmanager.vbs` for silent background operation.

Or run directly for debugging:

```bash
python main.py
```

## Usage

| Action | How |
|--------|-----|
| Open popup | Double-tap Alt |
| Search history | Just start typing |
| Navigate | Arrow keys (Up/Down) |
| Paste selection | Enter or click |
| Delete item | Delete key |
| Dismiss | Escape |
| Clear all history | Right-click tray icon > Clear History |
| Quit | Right-click tray icon > Quit |

## License

MIT
