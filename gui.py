"""
gui.py - Ігровий графічний інтерфейс
"""
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

import pyautogui

from bot import PlantCareBot
from config import LOGS_DIR, SCREENSHOTS_DIR, CONFIG_FILE


# ======================== ІГРОВИЙ GUI ========================
class GamingGUI:
    """Ігровий інтерфейс з темною темою."""
    
    COLORS = {
        'bg': '#0d1117',
        'secondary': '#161b22',
        'card': '#1c2128',
        'border': '#30363d',
        'accent': '#58a6ff',
        'success': '#3fb950',
        'warning': '#f0883e',
        'danger': '#f85149',
        'text': '#c9d1d9',
        'text_dim': '#8b949e',
        'highlight': '#388bfd',
    }
    
    def __init__(self, bot: PlantCareBot):
        self.bot = bot
        self.root = tk.Tk()
        self.root.title("🌱 Plant Care Bot v2.0")
        self.root.geometry("900x700")
        self.root.configure(bg=self.COLORS['bg'])
        self.root.resizable(True, True)
        
        self._setup_styles()
        self._create_ui()
        
        self.bot._log_callback = self.add_log
        self.is_animating = False
    
    def _setup_styles(self):
        """Налаштування стилів."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Кнопки
        style.configure('Gaming.TButton',
                       background=self.COLORS['accent'],
                       foreground=self.COLORS['text'],
                       borderwidth=0,
                       focuscolor='none',
                       padding=(25, 12),
                       font=('Segoe UI', 10, 'bold'))
        
        style.map('Gaming.TButton',
                 background=[('active', self.COLORS['highlight']),
                           ('pressed', self.COLORS['highlight'])])
        
        # Фрейми
        style.configure('Dark.TFrame', background=self.COLORS['bg'])
        style.configure('Card.TFrame', background=self.COLORS['card'])
        
        # Лейбли
        style.configure('Title.TLabel',
                       background=self.COLORS['bg'],
                       foreground=self.COLORS['text'],
                       font=('Segoe UI', 26, 'bold'))
        
        style.configure('Subtitle.TLabel',
                       background=self.COLORS['bg'],
                       foreground=self.COLORS['text_dim'],
                       font=('Segoe UI', 11))
        
        style.configure('Status.TLabel',
                       background=self.COLORS['card'],
                       foreground=self.COLORS['success'],
                       font=('Segoe UI', 16, 'bold'))
        
        style.configure('Stats.TLabel',
                       background=self.COLORS['card'],
                       foreground=self.COLORS['accent'],
                       font=('Segoe UI', 12, 'bold'))
    
    def _create_ui(self):
        """Створення інтерфейсу."""
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # ============ HEADER ============
        header = self._create_header(main_frame)
        header.pack(fill=tk.X, pady=(0, 15))
        
        # ============ CONTENT (2 колонки) ============
        content = ttk.Frame(main_frame, style='Dark.TFrame')
        content.pack(fill=tk.BOTH, expand=True)
        
        # Ліва колонка
        left_column = ttk.Frame(content, style='Dark.TFrame')
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Статус карта
        self._create_status_card(left_column).pack(fill=tk.X, pady=(0, 10))
        
        # Статистика карта
        self._create_stats_card(left_column).pack(fill=tk.X, pady=(0, 10))
        
        # Панель керування
        self._create_controls_card(left_column).pack(fill=tk.X)
        
        # Права колонка (лог)
        right_column = ttk.Frame(content, style='Dark.TFrame')
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self._create_log_card(right_column).pack(fill=tk.BOTH, expand=True)
        
        # ============ FOOTER ============
        footer = self._create_footer(main_frame)
        footer.pack(fill=tk.X, pady=(15, 0))
    
    def _create_header(self, parent) -> ttk.Frame:
        """Створення заголовку."""
        header = ttk.Frame(parent, style='Dark.TFrame')
        
        title_frame = ttk.Frame(header, style='Dark.TFrame')
        title_frame.pack(side=tk.LEFT)
        
        title = ttk.Label(title_frame, text="🌱 Plant Care Bot", style='Title.TLabel')
        title.pack(anchor='w')
        
        subtitle = ttk.Label(title_frame, 
                           text="Розумний помічник для догляду за рослинами",
                           style='Subtitle.TLabel')
        subtitle.pack(anchor='w')
        
        # Індикатор версії
        version_label = tk.Label(header, text="v2.0",
                               bg=self.COLORS['accent'],
                               fg=self.COLORS['bg'],
                               font=('Segoe UI', 10, 'bold'),
                               padx=10, pady=5)
        version_label.pack(side=tk.RIGHT)
        
        return header
    
    def _create_status_card(self, parent) -> ttk.Frame:
        """Створення карти статусу."""
        card = self._create_card(parent, "📊 Статус системи")
        
        status_frame = ttk.Frame(card, style='Card.TFrame')
        status_frame.pack(fill=tk.X, padx=15, pady=10)
        
        self.status_var = tk.StringVar(value="⏹️ Зупинено")
        self.status_label = tk.Label(status_frame, 
                                     textvariable=self.status_var,
                                     bg=self.COLORS['card'],
                                     fg=self.COLORS['text_dim'],
                                     font=('Segoe UI', 16, 'bold'))
        self.status_label.pack()
        
        return card
    
    def _create_stats_card(self, parent) -> ttk.Frame:
        """Створення карти статистики."""
        card = self._create_card(parent, "📈 Статистика")
        
        stats_frame = ttk.Frame(card, style='Card.TFrame')
        stats_frame.pack(fill=tk.X, padx=15, pady=10)
        
        # 4 колонки статистики
        stats_data = [
            ("🔍", "Сканувань", "scans"),
            ("⚡", "Дій", "actions"),
            ("🐛", "Паразитів", "parasites_found"),
            ("💧", "Поливів", "waters"),
        ]
        
        self.stat_vars = {}
        for i, (icon, label, key) in enumerate(stats_data):
            stat_frame = ttk.Frame(stats_frame, style='Card.TFrame')
            stat_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
            
            icon_label = tk.Label(stat_frame, text=icon, 
                                bg=self.COLORS['card'],
                                fg=self.COLORS['accent'],
                                font=('Segoe UI', 20))
            icon_label.pack()
            
            self.stat_vars[key] = tk.StringVar(value="0")
            value_label = tk.Label(stat_frame, 
                                  textvariable=self.stat_vars[key],
                                  bg=self.COLORS['card'],
                                  fg=self.COLORS['text'],
                                  font=('Segoe UI', 16, 'bold'))
            value_label.pack()
            
            text_label = tk.Label(stat_frame, text=label,
                                bg=self.COLORS['card'],
                                fg=self.COLORS['text_dim'],
                                font=('Segoe UI', 9))
            text_label.pack()
        
        # Автооновлення статистики
        self._update_stats()
        
        return card
    
    def _create_controls_card(self, parent) -> ttk.Frame:
        """Створення карти керування."""
        card = self._create_card(parent, "🎮 Керування")
        
        controls_frame = ttk.Frame(card, style='Card.TFrame')
        controls_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Кнопки у 2 ряди
        row1 = ttk.Frame(controls_frame, style='Card.TFrame')
        row1.pack(fill=tk.X, pady=(0, 8))
        
        self.start_btn = self._create_button(row1, "▶️ СТАРТ", self.start, self.COLORS['success'])
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        self.pause_btn = self._create_button(row1, "⏸️ ПАУЗА", self.pause, self.COLORS['warning'])
        self.pause_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.pause_btn.config(state=tk.DISABLED)
        
        self.stop_btn = self._create_button(row1, "⏹️ СТОП", self.stop, self.COLORS['danger'])
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        self.stop_btn.config(state=tk.DISABLED)
        
        row2 = ttk.Frame(controls_frame, style='Card.TFrame')
        row2.pack(fill=tk.X)
        
        self.resume_btn = self._create_button(row2, "▶️ ПРОДОВЖИТИ", self.resume, self.COLORS['success'])
        self.resume_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.resume_btn.config(state=tk.DISABLED)
        
        self.point_btn = self._create_button(row2, "📍 ТОЧКА ПОЛИВУ", self.set_watering_point, self.COLORS['accent'])
        self.point_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.region_btn = self._create_button(row2, "🔍 ОБЛАСТЬ", self.set_region, self.COLORS['accent'])
        self.region_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        
        return card
    
    def _create_log_card(self, parent) -> ttk.Frame:
        """Створення карти логу."""
        card = self._create_card(parent, "📜 Журнал подій")
        
        log_frame = ttk.Frame(card, style='Card.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Текстове поле з прокруткою
        scroll_frame = ttk.Frame(log_frame, style='Card.TFrame')
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(scroll_frame, bg=self.COLORS['border'])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(scroll_frame, 
                               height=20,
                               bg=self.COLORS['secondary'],
                               fg=self.COLORS['text'],
                               font=('Consolas', 9),
                               relief='flat',
                               padx=10, 
                               pady=10,
                               yscrollcommand=scrollbar.set,
                               wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Кольорові теги
        self.log_text.tag_config('success', foreground=self.COLORS['success'])
        self.log_text.tag_config('warning', foreground=self.COLORS['warning'])
        self.log_text.tag_config('error', foreground=self.COLORS['danger'])
        self.log_text.tag_config('info', foreground=self.COLORS['accent'])
        
        return card
    
    def _create_footer(self, parent) -> ttk.Frame:
        """Створення футера."""
        footer = ttk.Frame(parent, style='Dark.TFrame')
        
        info_text = f"📁 Логи: {LOGS_DIR}  |  📸 Скріншоти: {SCREENSHOTS_DIR}  |  ⚙️ Конфіг: {CONFIG_FILE}"
        info_label = tk.Label(footer, 
                            text=info_text,
                            bg=self.COLORS['bg'],
                            fg=self.COLORS['text_dim'],
                            font=('Segoe UI', 9))
        info_label.pack()
        
        return footer
    
    def _create_card(self, parent, title: str) -> ttk.Frame:
        """Створення картки."""
        card = tk.Frame(parent, bg=self.COLORS['card'], 
                       highlightbackground=self.COLORS['border'],
                       highlightthickness=1)
        
        title_label = tk.Label(card, text=title,
                             bg=self.COLORS['card'],
                             fg=self.COLORS['text'],
                             font=('Segoe UI', 12, 'bold'))
        title_label.pack(anchor='w', padx=15, pady=(10, 5))
        
        return card
    
    def _create_button(self, parent, text: str, command, color: str) -> tk.Button:
        """Створення кнопки."""
        btn = tk.Button(parent, text=text, command=command,
                       bg=color,
                       fg='white',
                       font=('Segoe UI', 10, 'bold'),
                       relief='flat',
                       padx=15, 
                       pady=10,
                       cursor='hand2',
                       activebackground=color,
                       activeforeground='white',
                       borderwidth=0)
        
        # Hover ефект
        def on_enter(e):
            btn['bg'] = self._lighten_color(color)
        
        def on_leave(e):
            btn['bg'] = color
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def _lighten_color(self, color: str) -> str:
        """Освітлення кольору."""
        color = color.lstrip('#')
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def _update_stats(self):
        """Оновлення статистики."""
        if hasattr(self, 'stat_vars'):
            for key, var in self.stat_vars.items():
                var.set(str(self.bot.stats.get(key, 0)))
        
        self.root.after(1000, self._update_stats)
    
    def add_log(self, message: str):
        """Додавання логу з кольоровим форматуванням."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        
        # Визначення тегу
        tag = 'info'
        if '✅' in message or 'успішно' in message.lower():
            tag = 'success'
        elif '⚠️' in message or 'попередження' in message.lower():
            tag = 'warning'
        elif '❌' in message or 'помилка' in message.lower():
            tag = 'error'
        
        self.log_text.insert(tk.END, full_message, tag)
        self.log_text.see(tk.END)
        
        # Обмеження розміру логу
        lines = int(self.log_text.index('end-1c').split('.')[0])
        if lines > 500:
            self.log_text.delete('1.0', '100.0')
    
    def start(self):
        """Запуск бота."""
        self.bot.start()
        if self.bot._running:
            self.status_var.set("▶️ Працює")
            self.status_label.config(fg=self.COLORS['success'])
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            self.resume_btn.config(state=tk.DISABLED)
    
    def pause(self):
        """Пауза."""
        self.bot.pause()
        self.status_var.set("⏸️ Пауза")
        self.status_label.config(fg=self.COLORS['warning'])
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.NORMAL)
    
    def resume(self):
        """Продовження."""
        self.bot.resume()
        self.status_var.set("▶️ Працює")
        self.status_label.config(fg=self.COLORS['success'])
        self.pause_btn.config(state=tk.NORMAL)
        self.resume_btn.config(state=tk.DISABLED)
    
    def stop(self):
        """Зупинка."""
        self.bot.stop()
        self.status_var.set("⏹️ Зупинено")
        self.status_label.config(fg=self.COLORS['text_dim'])
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
    
    def set_watering_point(self):
        """Встановлення точки поливу."""
        result = messagebox.askokcancel(
            "Точка поливу",
            "Через 1.5 сек після OK\nнаведіть курсор на точку поливу"
        )
        if result:
            self.bot.set_watering_point()
            if self.bot.executor.watering_point:
                messagebox.showinfo("Готово", 
                                  f"✅ Точку встановлено: {self.bot.executor.watering_point}")
    
    def set_region(self):
        """Встановлення області аналізу."""
        msg = """Встановлення області аналізу:

🎯 За замовчуванням бот аналізує НИЖНЮ 50% екрану

Якщо хочете змінити область:
1. Натисніть OK
2. Через 2 секунди наведіть курсор на ВЕРХНІЙ ЛІВИЙ кут області
3. Зачекайте 2 секунди
4. Наведіть курсор на НИЖНІЙ ПРАВИЙ кут області

Або натисніть СКАСУВАТИ для використання автоматичної області"""
        
        result = messagebox.askokcancel("Область аналізу", msg)
        if result:
            time.sleep(2)
            x1, y1 = pyautogui.position()
            self.add_log(f"📍 Верхній лівий кут: ({x1}, {y1})")
            
            time.sleep(2)
            x2, y2 = pyautogui.position()
            self.add_log(f"📍 Нижній правий кут: ({x2}, {y2})")
            
            self.bot.set_analysis_region(x1, y1, x2, y2)
            messagebox.showinfo("Готово", 
                              f"✅ Область встановлено:\n({x1}, {y1}) -> ({x2}, {y2})\nРозмір: {x2-x1}x{y2-y1}px")
        else:
            # Використовуємо автоматичну нижню половину
            self.bot.analyzer.auto_detect_bottom_half()
            screen_w, screen_h = pyautogui.size()
            messagebox.showinfo("Автоматично", 
                              f"✅ Використовується нижня 50% екрану:\nРозмір: {screen_w}x{screen_h//2}px")
    
    def on_exit(self):
        """Обробка виходу."""
        if self.bot._running:
            if messagebox.askokcancel("Вихід", "Бот працює. Зупинити?"):
                self.bot.stop()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Запуск GUI."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.mainloop()