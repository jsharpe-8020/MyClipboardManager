import tkinter as tk
import time
import pyperclip
import keyboard
import ctypes

# BuildOps-inspired theme: white dominant, green (#00AF66) highlight
THEME = {
    'bg': '#FFFFFF',
    'fg': '#1a1a1a',
    'fg_secondary': '#6b7280',
    'accent': '#00AF66',
    'accent_hover': '#009957',
    'border': '#e5e7eb',
    'input_bg': '#f9fafb',
    'input_border': '#d1d5db',
    'select_bg': '#00AF66',
    'select_fg': '#FFFFFF',
    'hover_bg': '#f0fdf4',
    'title_bg': '#FFFFFF',
    'shadow': '#00000010',
    'font': 'Segoe UI',
    'mono': 'Cascadia Code',
}


def _enable_window_drag(window, *widgets):
    """Allow dragging a borderless window by clicking supplied widgets."""
    drag_state = {"x": 0, "y": 0}

    def _start_drag(event):
        drag_state["x"] = event.x_root
        drag_state["y"] = event.y_root

    def _do_drag(event):
        dx = event.x_root - drag_state["x"]
        dy = event.y_root - drag_state["y"]
        drag_state["x"] = event.x_root
        drag_state["y"] = event.y_root
        x = window.winfo_x() + dx
        y = window.winfo_y() + dy
        window.geometry(f"+{x}+{y}")

    for widget in widgets:
        if widget is None:
            continue
        widget.bind("<ButtonPress-1>", _start_drag, add="+")
        widget.bind("<B1-Motion>", _do_drag, add="+")

class ClipboardPopup(tk.Tk):
    def __init__(self, history_list, previous_hwnd=None, delete_callback=None):
        super().__init__()
        self.history = history_list
        self.filtered_history = history_list.copy()
        self.has_search = bool(self.history)
        self.previous_hwnd = previous_hwnd
        self.delete_callback = delete_callback
        
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        
        # Position at mouse cursor
        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        
        # Make sure we're on-screen
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        if x + 440 > sw: x = sw - 440
        if y + 360 > sh: y = sh - 360
        
        self.geometry(f"+{x}+{y}")
        self.config(bg=THEME['border'])  # thin border effect
        
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Button-1>", self.on_click_check)
        
        # Main container with 1px border simulation
        container = tk.Frame(self, bg=THEME['bg'], padx=0, pady=0)
        container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # ── Title bar ──
        title_bar = tk.Frame(container, bg=THEME['title_bg'], pady=8)
        title_bar.pack(fill=tk.X)
        
        accent_bar = tk.Frame(title_bar, bg=THEME['accent'], width=3, height=18)
        accent_bar.pack(side=tk.LEFT, padx=(12, 8))
        
        title_label = tk.Label(
            title_bar, text="My Clipboard Manager",
            font=(THEME['font'], 11, "bold"),
            bg=THEME['title_bg'], fg=THEME['fg']
        )
        title_label.pack(side=tk.LEFT)
        _enable_window_drag(self, title_bar, accent_bar, title_label)
        
        # Subtle divider
        tk.Frame(container, bg=THEME['border'], height=1).pack(fill=tk.X)
        
        if not self.history:
            empty = tk.Frame(container, bg=THEME['bg'], pady=20)
            empty.pack(fill=tk.X)
            tk.Label(
                empty, text="No items in clipboard history",
                font=(THEME['font'], 10), bg=THEME['bg'], fg=THEME['fg_secondary']
            ).pack()
        else:
            # ── Search bar ──
            search_frame = tk.Frame(container, bg=THEME['bg'], pady=8, padx=12)
            search_frame.pack(fill=tk.X)
            
            # Search container with border
            search_container = tk.Frame(
                search_frame, bg=THEME['input_border'],
                highlightthickness=0
            )
            search_container.pack(fill=tk.X)
            
            search_inner = tk.Frame(search_container, bg=THEME['input_bg'])
            search_inner.pack(fill=tk.X, padx=1, pady=1)
            
            search_icon = tk.Label(
                search_inner, text="⌕", font=(THEME['font'], 12),
                bg=THEME['input_bg'], fg=THEME['fg_secondary']
            )
            search_icon.pack(side=tk.LEFT, padx=(8, 4))
            
            self.search_var = tk.StringVar(master=self)
            self.search_var.trace("w", self.update_list)
            
            self.search_entry = tk.Entry(
                search_inner, textvariable=self.search_var,
                relief=tk.FLAT, bg=THEME['input_bg'], fg=THEME['fg'],
                insertbackground=THEME['accent'],
                font=(THEME['font'], 10),
                highlightthickness=0, bd=0
            )
            self.search_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 8), ipady=6)
            
            # Hint text
            hint = tk.Label(
                search_inner, text="Del to remove",
                font=(THEME['font'], 8), bg=THEME['input_bg'], fg='#c0c0c0'
            )
            hint.pack(side=tk.RIGHT, padx=(0, 8))
            
            # ── Listbox ──
            list_frame = tk.Frame(container, bg=THEME['bg'])
            list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
            
            self.listbox = tk.Listbox(
                list_frame,
                font=(THEME['mono'], 10),
                width=55,
                height=min(12, len(self.history)),
                selectbackground=THEME['select_bg'],
                selectforeground=THEME['select_fg'],
                bg=THEME['bg'],
                fg=THEME['fg'],
                activestyle="none",
                highlightthickness=0,
                bd=0,
                relief=tk.FLAT,
                selectmode=tk.SINGLE
            )
            self.listbox.pack(fill=tk.BOTH, expand=True)
            
            self.populate_list()
                
            self.listbox.bind("<Double-Button-1>", self.on_select)
            self.listbox.bind("<Button-1>", self.on_single_click)
            
            # Key bindings
            self.search_entry.bind("<Down>", self.move_down)
            self.search_entry.bind("<Up>", self.move_up)
            self.search_entry.bind("<Return>", self.on_select)
            self.listbox.bind("<Return>", self.on_select)
            
            # Delete key to remove items
            self.search_entry.bind("<Delete>", self.on_delete)
            self.listbox.bind("<Delete>", self.on_delete)
            
            self.search_entry.focus_set()
        
        # ── Bottom status bar ──
        status_bar = tk.Frame(container, bg=THEME['bg'], pady=6)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(container, bg=THEME['border'], height=1).pack(fill=tk.X, side=tk.BOTTOM)
        
        count = len(self.history) if self.history else 0
        status_text = f"{count} item{'s' if count != 1 else ''}"
        tk.Label(
            status_bar, text=status_text,
            font=(THEME['font'], 8), bg=THEME['bg'], fg=THEME['fg_secondary']
        ).pack(side=tk.LEFT, padx=12)
        
        tk.Label(
            status_bar, text="↵ Paste  |  Esc Close",
            font=(THEME['font'], 8), bg=THEME['bg'], fg='#c0c0c0'
        ).pack(side=tk.RIGHT, padx=12)
        
        # Force focus after a short delay
        self.after(50, self.force_focus)

    def on_click_check(self, event):
        widget = event.widget
        if widget == self:
            self.destroy()

    def on_single_click(self, event):
        self.listbox.selection_clear(0, tk.END)
        idx = self.listbox.nearest(event.y)
        self.listbox.selection_set(idx)
        self.after(50, lambda: self.on_select(event))

    def on_delete(self, event):
        selection = self.listbox.curselection()
        if not selection:
            return "break"
        idx = selection[0]
        deleted_text = self.filtered_history[idx]
        
        self.filtered_history.pop(idx)
        if deleted_text in self.history:
            self.history.remove(deleted_text)
        if self.delete_callback:
            self.delete_callback(deleted_text)
        
        self.populate_list()
        
        if self.filtered_history:
            new_idx = min(idx, len(self.filtered_history) - 1)
            self.listbox.select_set(new_idx)
            self.listbox.see(new_idx)
        
        return "break"

    def force_focus(self):
        try:
            self.withdraw()
            self.deiconify()
            
            KEYEVENTF_KEYUP = 0x0002
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)
            
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
            
        self.focus_force()
        if self.has_search:
            self.search_entry.focus_set()

    def update_list(self, *args):
        search_term = self.search_var.get().lower()
        if not search_term:
            self.filtered_history = self.history.copy()
        else:
            self.filtered_history = [item for item in self.history if search_term in item.lower()]
        self.populate_list()
        
    def populate_list(self):
        self.listbox.delete(0, tk.END)
        # Limit UI rendering to top 100 items to prevent lag, search will still pull from all 500
        display_items = self.filtered_history[:100]
        for item in display_items:
            display_text = item.replace('\n', ' ').replace('\r', '')
            if len(display_text) > 52:
                display_text = display_text[:49] + "..."
            self.listbox.insert(tk.END, display_text)
        if self.filtered_history:
            self.listbox.select_set(0)
            
    def move_down(self, event):
        if not self.filtered_history: return "break"
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            if idx < len(self.filtered_history) - 1:
                self.listbox.selection_clear(0, tk.END)
                self.listbox.select_set(idx + 1)
                self.listbox.see(idx + 1)
        return "break"
        
    def move_up(self, event):
        if not self.filtered_history: return "break"
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            if idx > 0:
                self.listbox.selection_clear(0, tk.END)
                self.listbox.select_set(idx - 1)
                self.listbox.see(idx - 1)
        return "break"

    def on_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            selected_text = self.filtered_history[index]
            
            pyperclip.copy(selected_text)
            self.destroy()
            time.sleep(0.15)
            
            if self.previous_hwnd:
                try:
                    KEYEVENTF_KEYUP = 0x0002
                    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)
                    ctypes.windll.user32.SetForegroundWindow(self.previous_hwnd)
                    time.sleep(0.15)
                except Exception:
                    pass
            
            keyboard.press_and_release('ctrl+v')

def show(history_list, delete_callback=None):
    previous_hwnd = ctypes.windll.user32.GetForegroundWindow()
    app = ClipboardPopup(history_list, previous_hwnd=previous_hwnd, delete_callback=delete_callback)
    app.mainloop()
    
if __name__ == "__main__":
    show(["Test 1", "String 2 with more text that is very long indeed", "Line 3"])
