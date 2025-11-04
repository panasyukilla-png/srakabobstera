"""
window_manager.py - Управління вікном гри та багатомонітор підтримка
"""
import logging
import time
from typing import Optional, Tuple
from dataclasses import dataclass

import win32gui
import win32process
import win32con
import psutil
import pyautogui
from PIL import ImageGrab


@dataclass
class WindowInfo:
    """Інформація про вікно."""
    hwnd: int
    title: str
    rect: Tuple[int, int, int, int]  # (left, top, right, bottom)
    pid: int
    is_foreground: bool


class WindowManager:
    """Менеджер для роботи з вікном гри."""
    
    def __init__(self, process_name: str = "amazing.exe"):
        self.process_name = process_name.lower()
        self.game_window: Optional[WindowInfo] = None
        self.auto_focus = True
        self.last_check = 0
        self.check_interval = 5.0  # Перевірка кожні 5 сек
        
        logging.info(f"🪟 Ініціалізовано Window Manager для '{process_name}'")
    
    def find_game_window(self) -> Optional[WindowInfo]:
        """Пошук вікна гри по процесу."""
        try:
            game_windows = []
            
            def enum_callback(hwnd, _):
                if not win32gui.IsWindowVisible(hwnd):
                    return
                
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return
                
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    
                    if process.name().lower() == self.process_name:
                        rect = win32gui.GetWindowRect(hwnd)
                        is_foreground = win32gui.GetForegroundWindow() == hwnd
                        
                        window = WindowInfo(
                            hwnd=hwnd,
                            title=title,
                            rect=rect,
                            pid=pid,
                            is_foreground=is_foreground
                        )
                        game_windows.append(window)
                        logging.info(f"🎮 Знайдено вікно: '{title}' [{rect[0]},{rect[1]} {rect[2]-rect[0]}x{rect[3]-rect[1]}]")
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            win32gui.EnumWindows(enum_callback, None)
            
            if game_windows:
                # Вибираємо активне або перше
                active = next((w for w in game_windows if w.is_foreground), None)
                self.game_window = active or game_windows[0]
                
                left, top, right, bottom = self.game_window.rect
                width = right - left
                height = bottom - top
                logging.info(f"✅ Вибрано вікно: '{self.game_window.title}'")
                logging.info(f"   📐 Позиція: ({left}, {top}), Розмір: {width}x{height}")
                
                return self.game_window
            
            logging.warning(f"⚠️ Вікно '{self.process_name}' не знайдено")
            return None
            
        except Exception as e:
            logging.error(f"❌ Помилка пошуку вікна: {e}", exc_info=True)
            return None
    
    def get_window_region(self) -> Optional[Tuple[int, int, int, int]]:
        """Отримання області вікна для скріншотів."""
        current_time = time.time()
        
        # Перевіряємо вікно періодично
        if not self.game_window or (current_time - self.last_check > self.check_interval):
            self.find_game_window()
            self.last_check = current_time
        
        if self.game_window:
            return self.game_window.rect
        
        # Fallback - повний екран
        screen_width, screen_height = pyautogui.size()
        logging.debug("⚠️ Використовується повний екран (вікно не знайдено)")
        return (0, 0, screen_width, screen_height)
    
    def get_ui_region(self, zone: str = "bottom") -> Tuple[int, int, int, int]:
        """
        Отримання області UI для аналізу.
        
        Args:
            zone: 'bottom' (нижня 50%), 'inventory' (нижня 30%), 'top' (верхня 20%)
        """
        rect = self.get_window_region()
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        
        if zone == "bottom":
            # Нижня 50% - основний UI
            return (left, top + height // 2, right, bottom)
        
        elif zone == "inventory":
            # Нижня 30% - інвентар
            return (left, top + int(height * 0.7), right, bottom)
        
        elif zone == "top":
            # Верхня 20% - статус бари
            return (left, top, right, top + int(height * 0.2))
        
        elif zone == "center":
            # Центр 60% - геймплей
            return (left, top + int(height * 0.2), right, top + int(height * 0.8))
        
        else:
            return rect
    
    def capture_window(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[any]:
        """Захоплення вікна гри."""
        try:
            if region is None:
                region = self.get_window_region()
            
            screenshot = ImageGrab.grab(bbox=region)
            return screenshot
            
        except Exception as e:
            logging.error(f"❌ Помилка захоплення вікна: {e}")
            return None
    
    def focus_window(self) -> bool:
        """Фокус на вікні гри."""
        try:
            if not self.game_window:
                self.find_game_window()
            
            if self.game_window:
                hwnd = self.game_window.hwnd
                
                # Відновлення якщо згорнуте
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                
                # Встановлення фокусу
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
                
                logging.info(f"✅ Фокус встановлено на '{self.game_window.title}'")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"❌ Помилка встановлення фокусу: {e}")
            return False
    
    def translate_coords(self, x: int, y: int, from_window: bool = True) -> Tuple[int, int]:
        """
        Перетворення координат між віконними та екранними.
        
        Args:
            from_window: True - з віконних в екранні, False - навпаки
        """
        if not self.game_window:
            return (x, y)
        
        left, top, _, _ = self.game_window.rect
        
        if from_window:
            # Віконні -> Екранні
            return (x + left, y + top)
        else:
            # Екранні -> Віконні
            return (x - left, y - top)
    
    def click_in_window(self, x: int, y: int, window_coords: bool = True, duration: float = 0.2):
        """
        Клік відносно вікна гри.
        
        Args:
            x, y: Координати
            window_coords: True якщо координати відносно вікна
        """
        try:
            if self.auto_focus:
                self.focus_window()
            
            if window_coords:
                screen_x, screen_y = self.translate_coords(x, y, from_window=True)
            else:
                screen_x, screen_y = x, y
            
            pyautogui.moveTo(screen_x, screen_y, duration=duration)
            time.sleep(0.1)
            pyautogui.click()
            
            logging.debug(f"🖱️ Клік: віконні ({x},{y}) -> екранні ({screen_x},{screen_y})")
            
        except Exception as e:
            logging.error(f"❌ Помилка кліку: {e}")
    
    def is_window_active(self) -> bool:
        """Перевірка чи вікно активне."""
        try:
            if not self.game_window:
                return False
            
            foreground_hwnd = win32gui.GetForegroundWindow()
            return foreground_hwnd == self.game_window.hwnd
            
        except Exception as e:
            logging.error(f"❌ Помилка перевірки активності: {e}")
            return False
    
    def get_window_size(self) -> Tuple[int, int]:
        """Отримання розміру вікна."""
        if not self.game_window:
            self.find_game_window()
        
        if self.game_window:
            left, top, right, bottom = self.game_window.rect
            return (right - left, bottom - top)
        
        return pyautogui.size()
    
    def wait_for_window(self, timeout: float = 30.0) -> bool:
        """Очікування появи вікна гри."""
        logging.info(f"⏳ Очікування вікна '{self.process_name}' (timeout: {timeout}с)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.find_game_window():
                return True
            time.sleep(1.0)
        
        logging.error(f"❌ Вікно не з'явилося за {timeout}с")
        return False