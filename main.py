import os
import time
import threading
import sqlite3
import keyboard
import pystray
import pyperclip
from PIL import Image, ImageDraw
import popup

APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "MyClipboardManager")
os.makedirs(APPDATA_DIR, exist_ok=True)
DB_FILE = os.path.join(APPDATA_DIR, "clipboard.db")
MAX_HISTORY = 50
icon_instance = None
running = True

# Double-tap detection state
last_alt_time = 0
DOUBLE_TAP_INTERVAL = 0.35  # seconds

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def load_history():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT content FROM history ORDER BY created_at DESC LIMIT ?', (MAX_HISTORY,))
    items = [row[0] for row in c.fetchall()]
    conn.close()
    return items

def add_to_history(text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Remove duplicates (bump to top by deleting and re-inserting)
    c.execute('DELETE FROM history WHERE content = ?', (text,))
    c.execute('INSERT INTO history (content) VALUES (?)', (text,))
    # Trim to max size
    c.execute('''DELETE FROM history WHERE id NOT IN (
        SELECT id FROM history ORDER BY created_at DESC LIMIT ?
    )''', (MAX_HISTORY,))
    conn.commit()
    conn.close()

def clear_history():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM history')
    conn.commit()
    conn.close()

def delete_from_history(text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM history WHERE content = ?', (text,))
    conn.commit()
    conn.close()

def clipboard_poller():
    recent_value = ""
    while running:
        try:
            tmp_value = pyperclip.paste()
            if tmp_value and tmp_value != recent_value:
                recent_value = tmp_value
                add_to_history(recent_value)
        except:
            pass
        time.sleep(0.5)

def on_hotkey_pressed():
    history = load_history()
    if not history:
        return
    def safe_show():
        try:
            popup.show(history, delete_from_history)
        except Exception:
            pass
    threading.Thread(target=safe_show, daemon=True).start()

def on_alt_event(event):
    global last_alt_time
    if event.event_type == keyboard.KEY_DOWN:
        return
    # Only trigger on key UP for alt (to avoid repeats while held)
    now = time.time()
    if now - last_alt_time < DOUBLE_TAP_INTERVAL:
        last_alt_time = 0  # reset so triple-tap doesn't re-trigger
        on_hotkey_pressed()
    else:
        last_alt_time = now

def create_image():
    width, height = 64, 64
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    dc = ImageDraw.Draw(image)
    # Green clipboard body
    dc.rectangle((16, 10, 48, 54), fill=(0, 175, 102))
    # White clipboard clip
    dc.rectangle((24, 6, 40, 14), fill=(255, 255, 255))
    return image

def on_clear(icon, item):
    clear_history()

def on_quit(icon, item):
    global running
    running = False
    keyboard.unhook_all()
    icon.stop()

def setup_tray():
    global icon_instance
    menu = pystray.Menu(
        pystray.MenuItem('Clear History', on_clear),
        pystray.MenuItem('Quit', on_quit)
    )
    image = create_image()
    icon_instance = pystray.Icon("MyClipboardManager", image, "MyClipboardManager", menu)

def main():
    init_db()
    
    # Register double-tap Alt listener
    keyboard.on_release_key('alt', lambda e: on_alt_event(e))
    
    # Start polling thread
    poller_thread = threading.Thread(target=clipboard_poller, daemon=True)
    poller_thread.start()
    
    # Run tray (blocks until quit)
    setup_tray()
    icon_instance.run()

if __name__ == "__main__":
    main()
