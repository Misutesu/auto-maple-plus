"""User friendly GUI to interact with Auto Maple."""

import time
import threading
import tkinter as tk
from tkinter import ttk
import ctypes
from src.common import config, settings
from src.gui import Menu, View, Edit, Settings, Notifer_Settings, Runtime_Flags, Automation_Settings
from src.gui.menu.file import Import_Settings

class GUI:
    DISPLAY_FRAME_RATE = 30
    RESOLUTIONS = {
        'DEFAULT': '700x525',
        'Edit': '1100x525',
        'Settings': '700x650',
        'Notifier': '600x650',
        'Monitoring': '400x525',
        'Automation': '400x525'
    }

    def __init__(self):
        config.gui = self

        # 设置DPI感知
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_PER_MONITOR_DPI_AWARE
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass

        self.root = tk.Tk()
        self.root.title('OBS 31.0.3 - 配置文件:未命名 - 场景:未命名')
        icon = tk.PhotoImage(file='assets/icon.png')
        self.root.iconphoto(False, icon)
        
        # 获取DPI缩放比例
        self.dpi_scale = self._get_dpi_scale()
        
        # 根据DPI缩放调整窗口大小
        self.root.geometry(self._get_scaled_resolution('DEFAULT'))
        self.root.resizable(False, False)

        # Initialize GUI variables
        self.routine_var = tk.StringVar()

        # Build the GUI
        self.menu = Menu(self.root)
        self.root.config(menu=self.menu)

        self.navigation = ttk.Notebook(self.root)

        self.view = View(self.navigation)
        self.edit = Edit(self.navigation)
        self.settings = Settings(self.navigation)
        self.watcher_settings = Notifer_Settings(self.navigation)
        self.runtime_console = Runtime_Flags(self.navigation)
        self.automation_settings = Automation_Settings(self.navigation)

        self.navigation.pack(expand=True, fill='both')
        self.navigation.bind('<<NotebookTabChanged>>', self._resize_window)
        self.root.focus()

    def _get_dpi_scale(self):
        """获取当前显示器的DPI缩放比例"""
        try:
            # 获取主显示器的DPI
            dc = ctypes.windll.user32.GetDC(0)
            dpi_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, dc)
            return dpi_x / 96.0  # 96是标准DPI
        except:
            return 1.0

    def _get_scaled_resolution(self, page):
        """根据DPI缩放调整分辨率"""
        if page not in GUI.RESOLUTIONS:
            page = 'DEFAULT'
        
        resolution = GUI.RESOLUTIONS[page]
        width, height = map(int, resolution.split('x'))
        
        # 根据DPI缩放调整尺寸
        scaled_width = int(width * self.dpi_scale)
        scaled_height = int(height * self.dpi_scale)
        
        return f"{scaled_width}x{scaled_height}"

    def set_routine(self, arr):
        self.routine_var.set(arr)

    def clear_routine_info(self):
        """
        Clears information in various GUI elements regarding the current routine.
        Does not clear Listboxes containing routine Components, as that is handled by Routine.
        """

        self.view.details.clear_info()
        self.view.status.set_routine('')

        self.edit.minimap.redraw()
        self.edit.routine.commands.clear_contents()
        self.edit.routine.commands.update_display()
        self.edit.editor.reset()

    def _resize_window(self, e):
        """Callback to resize entire Tkinter window every time a new Page is selected."""

        nav = e.widget
        curr_id = nav.select()
        nav.nametowidget(curr_id).focus()      # Focus the current Tab
        page = nav.tab(curr_id, 'text')
        if self.root.state() != 'zoomed':
            # 使用DPI缩放调整后的分辨率
            self.root.geometry(self._get_scaled_resolution(page))

    def start(self):
        """Starts the GUI as well as any scheduled functions."""

        display_thread = threading.Thread(target=self._display_minimap)
        display_thread.daemon = True
        display_thread.start()

        layout_thread = threading.Thread(target=self._save_layout)
        layout_thread.daemon = True
        layout_thread.start()

        # Load previously used config
        print("[~] Attempting to load last used command book and routine")
        import_root = Import_Settings("CBR")
        last_cb = import_root.get("last_cb")
        last_routine = import_root.get("last_routine")
        if last_cb != None:
            print()
            try:
                if hasattr(config, 'bot') and config.bot is not None:
                    config.bot.load_commands(last_cb)
                if last_routine != None and hasattr(config, 'routine') and config.routine is not None:
                   config.routine.load(last_routine)
            except:
                pass
        else:
            print("[!] Last loaded command book not found)")
            
        self.root.mainloop()

    def _display_minimap(self):
        delay = 1 / GUI.DISPLAY_FRAME_RATE
        while True:
            self.view.minimap.display_minimap()
            time.sleep(delay)

    def _save_layout(self):
        """Periodically saves the current Layout object."""

        while True:
            if config.layout is not None and settings.record_layout:
                config.layout.save()
            time.sleep(5)


if __name__ == '__main__':
    gui = GUI()
    gui.start()
