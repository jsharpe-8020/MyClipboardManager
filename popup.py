import tkinter as tk
import time
import pyperclip
import keyboard
import ctypes

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
        if x + 420 > sw: x = sw - 420
        if y + 300 > sh: y = sh - 300
        
        self.geometry(f"+{x}+{y}")
        self.config(bg='#2b2d30')
        
        self.bind("<Escape>", lambda e: self.destroy())
        
        # Use click-away to dismiss instead of FocusOut (which was causing crashes)
        self.bind("<Button-1>", self.on_click_check)
        
        frame = tk.Frame(self, bg='#2b2d30', highlightbackground="#555", highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title bar
        title_bar = tk.Frame(frame, bg='#1e1f22')
        title_bar.pack(fill=tk.X)
        title_label = tk.Label(title_bar, text="📋 My Clipboard Manager", font=("Segoe UI", 10, "bold"), bg='#1e1f22', fg='#e0e0e0', anchor='w', padx=8, pady=4)
        title_label.pack(fill=tk.X)
        
        if not self.history:
            lbl = tk.Label(frame, text="Clipboard history is empty.", bg='#2b2d30', fg='white', padx=10, pady=5)
            lbl.pack()
        else:
            # Search entry
            self.search_var = tk.StringVar()
            self.search_var.trace("w", self.update_list)
            
            entry_frame = tk.Frame(frame, bg='#2b2d30')
            entry_frame.pack(fill=tk.X, padx=5, pady=5)
            
            search_icon = tk.Label(entry_frame, text="🔍", bg='#2b2d30', fg='white')
            search_icon.pack(side=tk.LEFT)
            
            self.search_entry = tk.Entry(
                entry_frame, textvariable=self.search_var,
                relief=tk.FLAT, bg='#3c3f41', fg='white',
                insertbackground='white', font=("Consolas", 10)
            )
            self.search_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5)
            
            self.listbox = tk.Listbox(
                frame, 
                font=("Consolas", 10), 
                width=55, 
                height=min(12, len(self.history)),
                selectbackground="#214283",
                selectforeground="white",
                bg='#2b2d30',
                fg='#bbbbbb',
                activestyle="none",
                highlightthickness=0,
                bd=0
            )
            self.listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            self.populate_list()
                
            self.listbox.bind("<Double-Button-1>", self.on_select)
            self.listbox.bind("<Button-1>", self.on_single_click)
            
            # Key bindings for navigating the list while focused on the entry
            self.search_entry.bind("<Down>", self.move_down)
            self.search_entry.bind("<Up>", self.move_up)
            self.search_entry.bind("<Return>", self.on_select)
            
            self.listbox.bind("<Return>", self.on_select)
            
            # Delete key to remove items
            self.search_entry.bind("<Delete>", self.on_delete)
            self.listbox.bind("<Delete>", self.on_delete)
            
            self.search_entry.focus_set()
        
        # Force focus after a short delay
        self.after(50, self.force_focus)

    def on_click_check(self, event):
        # Only dismiss if the click is outside the window content
        widget = event.widget
        if widget == self:
            self.destroy()

    def on_single_click(self, event):
        # Select and paste on single click in listbox
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
        
        # Remove from filtered list
        self.filtered_history.pop(idx)
        # Remove from master history
        if deleted_text in self.history:
            self.history.remove(deleted_text)
        # Remove from database
        if self.delete_callback:
            self.delete_callback(deleted_text)
        
        # Refresh the listbox
        self.populate_list()
        
        # Re-select nearest item
        if self.filtered_history:
            new_idx = min(idx, len(self.filtered_history) - 1)
            self.listbox.select_set(new_idx)
            self.listbox.see(new_idx)
        
        return "break"

    def force_focus(self):
        try:
            self.withdraw()
            self.deiconify()
            
            # Simulate Alt keypress to bypass Windows foreground lock
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
        for item in self.filtered_history:
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
            
            # Restore focus to the previously active window before pasting
            if self.previous_hwnd:
                try:
                    # Alt trick to bypass foreground lock
                    KEYEVENTF_KEYUP = 0x0002
                    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)
                    ctypes.windll.user32.SetForegroundWindow(self.previous_hwnd)
                    time.sleep(0.15)
                except Exception:
                    pass
            
            keyboard.press_and_release('ctrl+v')

def show(history_list, delete_callback=None):
    # Capture the currently focused window BEFORE creating the popup
    previous_hwnd = ctypes.windll.user32.GetForegroundWindow()
    app = ClipboardPopup(history_list, previous_hwnd=previous_hwnd, delete_callback=delete_callback)
    app.mainloop()
    
if __name__ == "__main__":
    show(["Test 1", "String 2 with more text that is very long indeed", "Line 3"])
