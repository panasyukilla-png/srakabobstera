"""
window_manager_COMPLETE.py - ПОВНА виправлена версія
Фічі:
1. Always on Top режим
2. Агресивний метод фокусу через AttachThreadInput
3. Автоматичне розгортання з мінімізованого стану
4. Перевірка видимості перед кожною дією
5. Детальна статистика та логування

ЗАМІНИ весь window_manager.py на цей файл
"""
import logging
import time
from typing import Optional, Tuple
from dataclasses import dataclass

import win32gui
import win32process
import win32con
import win32api
import psutil
import pyautogui
from PIL import ImageGrab
import ctypes


@dataclass
class WindowInfo:
    """Інформація про вікно."""
    hwnd: int
    title: str
    rect: Tuple[int, int, int, int]  # (left, top, right, bottom)
    pid: int
    is_foreground: bool
    is_visible: bool


class WindowManager:
    """
    🔧 ПОВНІСТЮ ВИПРАВЛЕНИЙ менеджер вікон з максимальною надійністю.
    
    Новинки v2.0:
    - Always on Top режим (вікно завжди зверху)
    - Агресивний метод фокусу (обхід захисту Windows)
    - Автоматичне розгортання з мінімізованого стану
    - Перевірка видимості перед кожною дією
    - Детальна статистика
    """
    
    def __init__(self, process_name: str = "amazing.exe"):
        self.process_name = process_name.lower()
        self.game_window: Optional[WindowInfo] = None
        self.auto_focus = True
        self.always_on_top = True  # ✅ Завжди зверху
        self.last_check = 0
        self.check_interval = 5.0  # Перевірка кожні 5 сек
        
        # Статистика
        self.stats = {
            'focus_attempts': 0,
            'focus_successes': 0,
            'focus_failures': 0,
            'aggressive_focus_used': 0,
            'window_lost': 0,
            'clicks_performed': 0,
        }
        
        logging.info(f"🪟 Window Manager ініціалізовано для '{process_name}'")
        logging.info(f"   📌 Always on Top: {'✅ ENABLED' if self.always_on_top else '❌ DISABLED'}")
        logging.info(f"   🔄 Автоматичний фокус: {'✅ ENABLED' if self.auto_focus else '❌ DISABLED'}")
    
    def find_game_window(self) -> Optional[WindowInfo]:
        """
        Пошук вікна гри по імені процесу.
        
        Returns:
            WindowInfo або None
        """
        try:
            game_windows = []
            
            def enum_callback(hwnd, _):
                """Callback для енумерації вікон."""
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
                        is_visible = win32gui.IsWindowVisible(hwnd)
                        
                        window = WindowInfo(
                            hwnd=hwnd,
                            title=title,
                            rect=rect,
                            pid=pid,
                            is_foreground=is_foreground,
                            is_visible=is_visible
                        )
                        game_windows.append(window)
                        
                        left, top, right, bottom = rect
                        width = right - left
                        height = bottom - top
                        logging.info(f"🎮 Знайдено: '{title}' [{width}x{height}px]")
                        logging.debug(f"   Position: ({left}, {top})")
                        logging.debug(f"   Foreground: {is_foreground}")
                        logging.debug(f"   Visible: {is_visible}")
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Енумерація всіх вікон
            win32gui.EnumWindows(enum_callback, None)
            
            if game_windows:
                # Вибираємо найкраще вікно
                active = next((w for w in game_windows if w.is_foreground), None)
                visible = next((w for w in game_windows if w.is_visible), None)
                self.game_window = active or visible or game_windows[0]
                
                left, top, right, bottom = self.game_window.rect
                width = right - left
                height = bottom - top
                
                logging.info(f"✅ Вибрано: '{self.game_window.title}'")
                logging.info(f"   📐 Розмір: {width}x{height}px")
                logging.info(f"   📍 Позиція: ({left}, {top})")
                
                # ✅ Встановлюємо Always on Top якщо потрібно
                if self.always_on_top:
                    self._set_always_on_top(True)
                
                return self.game_window
            
            logging.warning(f"⚠️ Вікно '{self.process_name}' не знайдено")
            logging.info("💡 Переконайся що гра запущена")
            self.stats['window_lost'] += 1
            return None
            
        except Exception as e:
            logging.error(f"❌ Помилка пошуку вікна: {e}", exc_info=True)
            return None
    
    def _set_always_on_top(self, enable: bool = True) -> bool:
        """
        🔧 Встановлення Always on Top режиму.
        
        Вікно завжди буде поверх інших (навіть терміналу).
        
        Args:
            enable: True - увімкнути, False - вимкнути
        
        Returns:
            True якщо успішно
        """
        if not self.game_window:
            return False
        
        try:
            hwnd = self.game_window.hwnd
            
            if enable:
                # HWND_TOPMOST = -1 (завжди зверху)
                result = win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                )
                
                if result:
                    logging.info(f"✅ Always on Top УВІМКНЕНО для '{self.game_window.title}'")
                else:
                    logging.warning(f"⚠️ Не вдалося увімкнути Always on Top")
            else:
                # HWND_NOTOPMOST = -2 (нормальний режим)
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_NOTOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                )
                logging.info(f"ℹ️ Always on Top ВИМКНЕНО")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Помилка встановлення Always on Top: {e}")
            return False
    
    def force_focus_aggressive(self) -> bool:
        """
        🔥 АГРЕСИВНИЙ метод фокусу через AttachThreadInput.
        
        Використовується коли SetForegroundWindow не працює через захист Windows.
        Цей метод обходить обмеження Windows на зміну фокусу.
        
        Returns:
            True якщо успішно
        """
        if not self.game_window:
            return False
        
        try:
            logging.info("🔥 Спроба агресивного фокусу...")
            self.stats['aggressive_focus_used'] += 1
            
            hwnd = self.game_window.hwnd
            
            # Крок 1: Перевірка існування
            if not win32gui.IsWindow(hwnd):
                logging.error("❌ Вікно більше не існує")
                self.game_window = None
                return False
            
            # Крок 2: Розгортання якщо згорнуте
            if win32gui.IsIconic(hwnd):
                logging.info("   📤 Розгортаємо з мінімізованого стану...")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.3)
            
            # Крок 3: Показати якщо приховане
            if not win32gui.IsWindowVisible(hwnd):
                logging.info("   👁️ Показуємо приховане вікно...")
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                time.sleep(0.2)
            
            # Крок 4: Отримання thread ID поточного та цільового вікна
            foreground_hwnd = win32gui.GetForegroundWindow()
            
            if foreground_hwnd == hwnd:
                logging.info("   ✅ Вікно вже в фокусі!")
                return True
            
            foreground_thread = win32process.GetWindowThreadProcessId(foreground_hwnd)[0]
            target_thread = win32process.GetWindowThreadProcessId(hwnd)[0]
            
            logging.debug(f"   🧵 Foreground thread: {foreground_thread}")
            logging.debug(f"   🧵 Target thread: {target_thread}")
            
            # Крок 5: AttachThreadInput (обхід захисту Windows)
            attached = False
            if foreground_thread != target_thread:
                logging.info("   🔗 Прив'язуємо потоки (AttachThreadInput)...")
                
                result = ctypes.windll.user32.AttachThreadInput(
                    foreground_thread,
                    target_thread,
                    True
                )
                
                if result:
                    attached = True
                    logging.debug("   ✅ Потоки прив'язані")
                else:
                    logging.warning("   ⚠️ Не вдалося прив'язати потоки")
                
                time.sleep(0.1)
            
            # Крок 6: BringWindowToTop
            try:
                logging.info("   ⬆️ BringWindowToTop...")
                win32gui.BringWindowToTop(hwnd)
                time.sleep(0.1)
            except Exception as e:
                logging.debug(f"   ⚠️ BringWindowToTop: {e}")
            
            # Крок 7: Always on Top (примусово)
            try:
                logging.info("   📌 Встановлюємо TOPMOST...")
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
                )
                time.sleep(0.1)
            except Exception as e:
                logging.debug(f"   ⚠️ SetWindowPos: {e}")
            
            # Крок 8: SetForegroundWindow
            try:
                logging.info("   🎯 SetForegroundWindow...")
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.2)
            except Exception as e:
                logging.warning(f"   ⚠️ SetForegroundWindow: {e}")
            
            # Крок 9: SetFocus (додатково)
            try:
                logging.info("   👁️ SetFocus...")
                win32gui.SetFocus(hwnd)
                time.sleep(0.1)
            except Exception as e:
                logging.debug(f"   ⚠️ SetFocus: {e}")
            
            # Крок 10: Відчеплюємо потоки
            if attached:
                logging.info("   🔓 Відчеплюємо потоки...")
                ctypes.windll.user32.AttachThreadInput(
                    foreground_thread,
                    target_thread,
                    False
                )
                time.sleep(0.1)
            
            # Крок 11: Перевірка успіху
            time.sleep(0.2)
            is_success = win32gui.GetForegroundWindow() == hwnd
            
            if is_success:
                logging.info("   ✅ Агресивний фокус УСПІШНИЙ!")
                self.stats['focus_successes'] += 1
                return True
            else:
                logging.warning("   ⚠️ Агресивний фокус НЕ спрацював")
                
                # Останній шанс - симулюємо Alt
                logging.info("   🎹 Спроба через Alt...")
                win32api.keybd_event(0x12, 0, 0, 0)  # Alt down
                win32gui.SetForegroundWindow(hwnd)
                win32api.keybd_event(0x12, 0, 2, 0)  # Alt up
                time.sleep(0.2)
                
                is_success = win32gui.GetForegroundWindow() == hwnd
                
                if is_success:
                    logging.info("   ✅ Alt метод спрацював!")
                    self.stats['focus_successes'] += 1
                    return True
                else:
                    self.stats['focus_failures'] += 1
                    return False
            
        except Exception as e:
            logging.error(f"❌ Помилка агресивного фокусу: {e}", exc_info=True)
            self.stats['focus_failures'] += 1
            return False
    
    def restore_and_focus(self) -> bool:
        """
        🔧 Розгортання та фокус з максимальною надійністю.
        
        Порядок дій:
        1. Перевірка існування вікна
        2. Примусове розгортання якщо згорнуте
        3. Підняття на передній план
        4. Always on Top
        5. Активація (SetForegroundWindow)
        6. Fallback на агресивний метод якщо не спрацювало
        
        Returns:
            True якщо успішно
        """
        try:
            self.stats['focus_attempts'] += 1
            
            # Перевірка вікна
            if not self.game_window:
                logging.warning("⚠️ Вікно невідоме, шукаємо...")
                self.find_game_window()
            
            if not self.game_window:
                logging.error("❌ Вікно гри не знайдено!")
                self.stats['focus_failures'] += 1
                return False
            
            hwnd = self.game_window.hwnd
            
            # Крок 1: Перевірка чи вікно ще існує
            if not win32gui.IsWindow(hwnd):
                logging.warning("⚠️ Вікно більше не існує, шукаємо знову...")
                self.game_window = None
                self.stats['window_lost'] += 1
                return self.restore_and_focus()
            
            # Крок 2: Розгортання якщо згорнуте/мінімізоване
            if win32gui.IsIconic(hwnd):
                logging.info("📤 Розгортаємо вікно з мінімізованого стану...")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.3)
            
            # Крок 3: Показати якщо приховане
            if not win32gui.IsWindowVisible(hwnd):
                logging.info("👁️ Показуємо приховане вікно...")
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                time.sleep(0.2)
            
            # Крок 4: Always on Top (якщо увімкнено)
            if self.always_on_top:
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
                )
                time.sleep(0.1)
            
            # Крок 5: Підняття на передній план
            try:
                win32gui.BringWindowToTop(hwnd)
                time.sleep(0.1)
            except:
                pass
            
            # Крок 6: Встановлення фокусу
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.2)
            except Exception as e:
                # ⚠️ SetForegroundWindow не спрацював - пробуємо агресивний метод
                logging.warning(f"⚠️ SetForegroundWindow failed: {e}")
                logging.info("🔥 Переключаємось на агресивний метод...")
                return self.force_focus_aggressive()
            
            # Крок 7: Перевірка успіху
            is_foreground = win32gui.GetForegroundWindow() == hwnd
            
            if is_foreground:
                self.stats['focus_successes'] += 1
                success_rate = (self.stats['focus_successes'] / self.stats['focus_attempts']) * 100
                logging.info(f"✅ Фокус встановлено! (успішність: {success_rate:.1f}%)")
                return True
            else:
                # Якщо не вдалось - агресивний метод
                logging.warning("⚠️ Базовий метод не спрацював")
                logging.info("🔥 Переключаємось на агресивний метод...")
                return self.force_focus_aggressive()
            
        except Exception as e:
            logging.error(f"❌ Помилка restore_and_focus: {e}", exc_info=True)
            self.stats['focus_failures'] += 1
            return False
    
    def focus_window(self) -> bool:
        """
        🔧 Встановлення фокусу на вікно.
        
        Алиас для restore_and_focus() для зворотної сумісності.
        
        Returns:
            True якщо успішно
        """
        return self.restore_and_focus()
    
    def get_window_region(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Отримання області вікна для скріншотів.
        
        Returns:
            (left, top, right, bottom) або None
        """
        current_time = time.time()
        
        # Перевірка вікна періодично
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
            zone: 'bottom' (нижня 50%), 'inventory' (нижня 30%), 
                  'top' (верхня 20%), 'center' (центр 60%)
        
        Returns:
            (left, top, right, bottom)
        """
        rect = self.get_window_region()
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        
        zones = {
            "bottom": (left, top + height // 2, right, bottom),
            "inventory": (left, top + int(height * 0.7), right, bottom),
            "top": (left, top, right, top + int(height * 0.2)),
            "center": (left, top + int(height * 0.2), right, top + int(height * 0.8)),
            "full": rect,
        }
        
        return zones.get(zone, rect)
    
    def capture_window(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[any]:
        """
        Захоплення вікна гри.
        
        Args:
            region: Опціональна область, якщо None - вся вікно
        
        Returns:
            PIL Image або None
        """
        try:
            # ✅ Перевіряємо видимість перед захопленням
            if self.game_window:
                hwnd = self.game_window.hwnd
                
                if not win32gui.IsWindow(hwnd):
                    logging.warning("⚠️ Вікно більше не існує")
                    self.game_window = None
                    self.stats['window_lost'] += 1
                    return None
                
                if not win32gui.IsWindowVisible(hwnd):
                    logging.warning("⚠️ Вікно невидиме, відновлюємо...")
                    self.restore_and_focus()
            
            if region is None:
                region = self.get_window_region()
            
            screenshot = ImageGrab.grab(bbox=region)
            return screenshot
            
        except Exception as e:
            logging.error(f"❌ Помилка захоплення вікна: {e}")
            return None
    
    def translate_coords(self, x: int, y: int, from_window: bool = True) -> Tuple[int, int]:
        """
        Перетворення координат між віконними та екранними.
        
        Args:
            x, y: Координати
            from_window: True - з віконних в екранні, False - навпаки
        
        Returns:
            (screen_x, screen_y)
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
        🔧 Клік відносно вікна гри з гарантією фокусу.
        
        Args:
            x, y: Координати
            window_coords: True якщо координати відносно вікна
            duration: Тривалість руху миші
        """
        try:
            # ✅ КРИТИЧНО: Завжди відновлюємо фокус перед кліком
            if self.auto_focus:
                if not self.restore_and_focus():
                    logging.error("❌ Не вдалося отримати фокус перед кліком!")
                    return
                
                # Додаткова затримка для стабільності
                time.sleep(0.1)
            
            # Перетворення координат
            if window_coords:
                screen_x, screen_y = self.translate_coords(x, y, from_window=True)
            else:
                screen_x, screen_y = x, y
            
            # Перевірка що координати в межах вікна
            if self.game_window:
                left, top, right, bottom = self.game_window.rect
                if not (left <= screen_x <= right and top <= screen_y <= bottom):
                    logging.warning(
                        f"⚠️ Координати ({screen_x},{screen_y}) поза вікном "
                        f"[{left},{top},{right},{bottom}]"
                    )
            
            # Клік
            pyautogui.moveTo(screen_x, screen_y, duration=duration)
            time.sleep(0.1)
            pyautogui.click()
            
            self.stats['clicks_performed'] += 1
            
            logging.debug(f"🖱️ Клік: віконні ({x},{y}) → екранні ({screen_x},{screen_y})")
            
        except Exception as e:
            logging.error(f"❌ Помилка кліку: {e}")
    
    def is_window_active(self) -> bool:
        """
        Перевірка чи вікно активне (в фокусі).
        
        Returns:
            True якщо вікно в фокусі
        """
        try:
            if not self.game_window:
                return False
            
            hwnd = self.game_window.hwnd
            
            # Перевірка існування
            if not win32gui.IsWindow(hwnd):
                logging.warning("⚠️ Вікно більше не існує")
                self.game_window = None
                self.stats['window_lost'] += 1
                return False
            
            # Перевірка видимості
            if not win32gui.IsWindowVisible(hwnd):
                logging.debug("⚠️ Вікно невидиме")
                return False
            
            # Перевірка фокусу
            foreground_hwnd = win32gui.GetForegroundWindow()
            return foreground_hwnd == hwnd
            
        except Exception as e:
            logging.error(f"❌ Помилка перевірки активності: {e}")
            return False
    
    def get_window_size(self) -> Tuple[int, int]:
        """
        Отримання розміру вікна.
        
        Returns:
            (width, height)
        """
        if not self.game_window:
            self.find_game_window()
        
        if self.game_window:
            left, top, right, bottom = self.game_window.rect
            return (right - left, bottom - top)
        
        return pyautogui.size()
    
    def wait_for_window(self, timeout: float = 30.0) -> bool:
        """
        Очікування появи вікна гри.
        
        Args:
            timeout: Максимальний час очікування (секунди)
        
        Returns:
            True якщо вікно знайдено
        """
        logging.info(f"⏳ Очікування вікна '{self.process_name}' (timeout: {timeout}с)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.find_game_window():
                return True
            time.sleep(1.0)
        
        logging.error(f"❌ Вікно не з'явилося за {timeout}с")
        return False
    
    def toggle_always_on_top(self, enable: Optional[bool] = None):
        """
        🔧 Перемикання Always on Top режиму.
        
        Args:
            enable: True/False або None (toggle)
        """
        if enable is None:
            self.always_on_top = not self.always_on_top
        else:
            self.always_on_top = enable
        
        logging.info(f"ℹ️ Always on Top: {'✅ ENABLED' if self.always_on_top else '❌ DISABLED'}")
        
        if self.game_window:
            self._set_always_on_top(self.always_on_top)
    
    def log_stats(self):
        """Логування детальної статистики."""
        success_rate = 0
        if self.stats['focus_attempts'] > 0:
            success_rate = (self.stats['focus_successes'] / self.stats['focus_attempts']) * 100
        
        aggressive_rate = 0
        if self.stats['focus_attempts'] > 0:
            aggressive_rate = (self.stats['aggressive_focus_used'] / self.stats['focus_attempts']) * 100
        
        logging.info("=" * 80)
        logging.info("📊 СТАТИСТИКА WINDOW MANAGER:")
        logging.info(f"   🎯 Спроб фокусу: {self.stats['focus_attempts']}")
        logging.info(f"   ✅ Успішних: {self.stats['focus_successes']} ({success_rate:.1f}%)")
        logging.info(f"   ❌ Невдалих: {self.stats['focus_failures']}")
        logging.info(f"   🔥 Агресивний метод: {self.stats['aggressive_focus_used']} ({aggressive_rate:.1f}%)")
        logging.info(f"   ⚠️ Втрат вікна: {self.stats['window_lost']}")
        logging.info(f"   🖱️ Кліків виконано: {self.stats['clicks_performed']}")
        logging.info(f"   📌 Always on Top: {'✅ ENABLED' if self.always_on_top else '❌ DISABLED'}")
        
        if self.game_window:
            logging.info(f"   🪟 Поточне вікно: '{self.game_window.title}'")
            logging.info(f"   📍 Активне: {'✅' if self.is_window_active() else '❌'}")
        else:
            logging.info(f"   🪟 Поточне вікно: НЕ ЗНАЙДЕНО")
        
        logging.info("=" * 80)
    
    def get_diagnostics(self) -> dict:
        """
        Отримання повної діагностичної інформації.
        
        Returns:
            dict з детальною інформацією
        """
        diag = {
            'window_found': self.game_window is not None,
            'window_active': self.is_window_active(),
            'always_on_top': self.always_on_top,
            'auto_focus': self.auto_focus,
            'stats': self.stats.copy(),
        }
        
        if self.game_window:
            diag['window_info'] = {
                'title': self.game_window.title,
                'pid': self.game_window.pid,
                'rect': self.game_window.rect,
                'size': self.get_window_size(),
                'is_visible': win32gui.IsWindowVisible(self.game_window.hwnd),
                'is_iconic': win32gui.IsIconic(self.game_window.hwnd),
            }
        
        return diag
    
    def emergency_restore(self) -> bool:
        """
        🚨 Аварійне відновлення вікна.
        
        Використовується коли всі інші методи не спрацювали.
        Намагається знайти вікно знову та відновити з будь-якого стану.
        
        Returns:
            True якщо вдалося відновити
        """
        logging.warning("🚨 АВАРІЙНЕ ВІДНОВЛЕННЯ ВІКНА")
        
        try:
            # Скидаємо поточне вікно
            self.game_window = None
            
            # Шукаємо знову
            if not self.find_game_window():
                logging.error("❌ Не вдалося знайти вікно під час аварійного відновлення")
                return False
            
            # Максимально агресивне відновлення
            hwnd = self.game_window.hwnd
            
            # Відновлення з будь-якого стану
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)
            
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            time.sleep(0.2)
            
            # Примусовий Always on Top
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
            )
            time.sleep(0.2)
            
            # Агресивний фокус
            success = self.force_focus_aggressive()
            
            if success:
                logging.info("✅ Аварійне відновлення УСПІШНЕ")
            else:
                logging.error("❌ Аварійне відновлення НЕВДАЛЕ")
            
            return success
            
        except Exception as e:
            logging.error(f"❌ Помилка аварійного відновлення: {e}")
            return False


# ============ ТЕСТУВАННЯ ============
if __name__ == "__main__":
    """
    Тестовий скрипт для перевірки Window Manager.
    
    Запуск: python window_manager_COMPLETE.py
    """
    import sys
    
    print("\n" + "="*80)
    print("🧪 ТЕСТ WINDOW MANAGER")
    print("="*80 + "\n")
    
    # Налаштування логування
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s [%(asctime)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    print("📋 Цей тест перевірить:")
    print("   1. Пошук вікна гри")
    print("   2. Встановлення Always on Top")
    print("   3. Відновлення фокусу")
    print("   4. Агресивний метод (якщо потрібно)")
    print()
    
    # Створення менеджера
    wm = WindowManager("amazing.exe")
    
    # Тест 1: Пошук вікна
    print("🔍 Тест 1: Пошук вікна гри...")
    if wm.find_game_window():
        print(f"   ✅ Вікно знайдено: {wm.game_window.title}")
        print(f"   📐 Розмір: {wm.get_window_size()}")
        print(f"   📌 Always on Top: {wm.always_on_top}")
    else:
        print("   ❌ Вікно не знайдено")
        print("   💡 Запусти гру і спробуй ще раз")
        sys.exit(1)
    
    # Тест 2: Перевірка активності
    print("\n👁️ Тест 2: Перевірка активності...")
    is_active = wm.is_window_active()
    print(f"   {'✅' if is_active else '❌'} Вікно {'активне' if is_active else 'неактивне'}")
    
    # Тест 3: Відкрий інше вікно
    print("\n⏳ Тест 3: Тест фокусу...")
    print("   💡 Відкрий інше вікно (наприклад, браузер) протягом 5 секунд...")
    
    for i in range(5, 0, -1):
        print(f"   {i}...")
        time.sleep(1)
    
    # Перевірка чи втрачено фокус
    if wm.is_window_active():
        print("   ℹ️ Вікно все ще активне (нічого не відкрили)")
    else:
        print("   ✅ Фокус втрачено (відкрито інше вікно)")
    
    # Тест 4: Відновлення фокусу
    print("\n🔄 Тест 4: Відновлення фокусу...")
    if wm.restore_and_focus():
        print("   ✅ Фокус відновлено успішно!")
        
        # Перевірка
        time.sleep(0.5)
        if wm.is_window_active():
            print("   ✅ Вікно в фокусі")
        else:
            print("   ⚠️ Вікно не в фокусі (можливо Always on Top не працює)")
    else:
        print("   ❌ Не вдалося відновити фокус")
    
    # Тест 5: Області UI
    print("\n📍 Тест 5: Області UI...")
    zones = ['bottom', 'top', 'center', 'inventory']
    for zone in zones:
        x1, y1, x2, y2 = wm.get_ui_region(zone)
        width = x2 - x1
        height = y2 - y1
        print(f"   • {zone:10s}: {width}x{height}px")
    
    # Тест 6: Захоплення скріншоту
    print("\n📸 Тест 6: Захоплення скріншоту...")
    screenshot = wm.capture_window()
    if screenshot:
        test_path = Path("test_screenshot.png")
        screenshot.save(test_path)
        size_kb = test_path.stat().st_size / 1024
        print(f"   ✅ Скріншот збережено: {test_path}")
        print(f"   📊 Розмір: {size_kb:.1f} KB")
        print(f"   📐 Розміри: {screenshot.size}")
    else:
        print("   ❌ Не вдалося захопити скріншот")
    
    # Тест 7: Статистика
    print("\n📊 Тест 7: Статистика...")
    wm.log_stats()
    
    # Діагностика
    print("\n🔬 Діагностика:")
    diag = wm.get_diagnostics()
    print(f"   • Вікно знайдено: {'✅' if diag['window_found'] else '❌'}")
    print(f"   • Вікно активне: {'✅' if diag['window_active'] else '❌'}")
    print(f"   • Always on Top: {'✅' if diag['always_on_top'] else '❌'}")
    print(f"   • Автофокус: {'✅' if diag['auto_focus'] else '❌'}")
    
    if 'window_info' in diag:
        info = diag['window_info']
        print(f"\n   Інформація про вікно:")
        print(f"   • Назва: {info['title']}")
        print(f"   • PID: {info['pid']}")
        print(f"   • Розмір: {info['size']}")
        print(f"   • Видиме: {'✅' if info['is_visible'] else '❌'}")
        print(f"   • Згорнуте: {'⚠️' if info['is_iconic'] else '✅'}")
    
    print("\n" + "="*80)
    print("✅ Тестування завершено!")
    print("="*80 + "\n")
    
    # Рекомендації
    print("💡 Рекомендації:")
    if diag['window_active']:
        print("   ✅ Все працює чудово!")
    else:
        print("   ⚠️ Вікно не в фокусі:")
        print("      1. Спробуй запустити Python як адміністратор")
        print("      2. Перевір чи Always on Top працює")
        print("      3. Використовуй force_focus_aggressive() якщо потрібно")
    
    print()