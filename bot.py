"""
bot.py - Повністю інтегрований Plant Care Bot v2.1
"""
import threading
import time
import logging
from typing import Optional
from pathlib import Path

import pytesseract

from config import (
    ConfigParser, TaskConfig, PerformanceConfig,
    CONFIG_FILE, TESSERACT_PATH, setup_enhanced_logging
)
from analyzer import SmartAnalyzer
from executor import SmartExecutor
from window_manager import WindowManager
from smart_inventory import SmartInventory
from performance_optimizer import PerformanceOptimizer


# ======================== ГОЛОВНИЙ БОТ ========================
class PlantCareBot:
    """Повністю автономний Plant Care Bot з максимальною продуктивністю."""
    
    def __init__(self, log_callback=None):
        # Стан
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._log_callback = log_callback
        self._shutdown_requested = False
        
        # Ініціалізація системи логування
        setup_enhanced_logging()
        
        logging.info("🚀 Ініціалізація Plant Care Bot v2.1 ENHANCED...")
        
        # Перевірка Tesseract
        if not self._check_tesseract():
            raise RuntimeError("Tesseract OCR не знайдено!")
        
        # Завантаження конфігурації
        logging.info("⚙️ Завантаження конфігурації...")
        self.config = ConfigParser.parse(CONFIG_FILE)
        
        # Ініціалізація компонентів
        logging.info("🔧 Ініціалізація компонентів...")
        
        # Performance Optimizer (GPU/CPU)
        self.performance_optimizer = PerformanceOptimizer()
        
        # Window Manager (фокус на грі)
        if self.config.focus_game_window:
            self.window_manager = WindowManager(self.config.window_process_name)
            if not self.window_manager.find_game_window():
                logging.warning("⚠️ Вікно гри не знайдено, буде працювати на всьому екрані")
        else:
            self.window_manager = None
        
        # Smart Inventory (пошук хімікатів та перевірка води)
        self.smart_inventory = SmartInventory(
            window_manager=self.window_manager,
            performance_optimizer=self.performance_optimizer
        )
        
        # Smart Analyzer (розпізнавання тексту та контекст)
        self.analyzer = SmartAnalyzer(
            config=self.config,
            window_manager=self.window_manager,
            performance_optimizer=self.performance_optimizer
        )
        
        # Smart Executor (виконання дій)
        self.executor = SmartExecutor(
            analyzer=self.analyzer,
            window_manager=self.window_manager,
            smart_inventory=self.smart_inventory
        )
        
        # Автоматичне налаштування UI області
        self.analyzer.auto_detect_game_ui()
        
        # Параметри моніторингу
        self.poll_interval = 2.0  # Інтервал сканування
        self.stats_log_interval = 60.0  # Логування статистики кожні 60с
        self.last_stats_log = 0
        
        # Загальна статистика
        self.stats = {
            'scans': 0,
            'actions': 0,
            'parasites_found': 0,
            'waters': 0,
            'errors': 0,
            'uptime': 0,
        }
        
        logging.info("✅ Бот успішно ініціалізовано!")
        self._log_system_status()
    
    def _check_tesseract(self) -> bool:
        """Перевірка Tesseract OCR."""
        try:
            if Path(TESSERACT_PATH).exists():
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
                version = pytesseract.get_tesseract_version()
                logging.info(f"✅ Tesseract версія: {version}")
                
                # Перевірка мов
                langs = pytesseract.get_languages()
                required_langs = ['ukr', 'rus', 'eng']
                missing_langs = [lang for lang in required_langs if lang not in langs]
                
                if missing_langs:
                    logging.warning(f"⚠️ Відсутні мови: {', '.join(missing_langs)}")
                    logging.warning("⚠️ Завантажте з https://github.com/tesseract-ocr/tessdata")
                else:
                    logging.info(f"✅ Мови: {', '.join(required_langs)}")
                
                return True
            else:
                logging.error(f"❌ Tesseract не знайдено: {TESSERACT_PATH}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Помилка перевірки Tesseract: {e}")
            return False
    
    def _log_system_status(self):
        """Логування стану системи."""
        logging.info("=" * 80)
        logging.info("🌱 PLANT CARE BOT v2.1 - ГОТОВИЙ ДО РОБОТИ")
        logging.info("=" * 80)
        logging.info(f"📝 Конфігурація:")
        logging.info(f"   • Паразитів у базі: {len(self.config.parasites)}")
        logging.info(f"   • Базовий полив: {self.config.watering_amount}л")
        logging.info(f"   • З добривом: {self.config.fertilizer_amount}л")
        logging.info(f"   • Діапазон води: {self.config.water_range[0]}-{self.config.water_range[1]}л")
        logging.info(f"   • Рівень грунту: {self.config.soil_percentage}%")
        logging.info("")
        logging.info(f"🎮 Компоненти:")
        logging.info(f"   • Window Manager: {'✅' if self.window_manager else '❌'}")
        logging.info(f"   • Smart Inventory: ✅")
        logging.info(f"   • Performance Optimizer: ✅")
        logging.info(f"   • GPU прискорення: {'✅' if self.performance_optimizer.gpu_available else '❌'}")
        logging.info("")
        logging.info(f"⚙️ Налаштування:")
        logging.info(f"   • Інтервал сканування: {self.poll_interval}с")
        logging.info(f"   • Інтервал скріншотів: {self.analyzer.screenshot_interval}с")
        logging.info(f"   • CPU потоків: {PerformanceConfig.CPU_THREADS}")
        logging.info(f"   • Масштабування скріншотів: {PerformanceConfig.SCREENSHOT_SCALE*100:.0f}%")
        logging.info("=" * 80)
    
    def start(self):
        """Запуск бота."""
        if self._running:
            self._log("⚠️ Бот вже працює")
            return
        
        self._running = True
        self._paused = False
        self._shutdown_requested = False
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        self._log("▶️ Моніторинг запущено")
        logging.info("🔄 Головний цикл розпочато")
    
    def pause(self):
        """Призупинення роботи."""
        self._paused = True
        self._log("⏸️ Призупинено")
        logging.info("⏸️ Бот призупинено")
    
    def resume(self):
        """Відновлення роботи."""
        self._paused = False
        self._log("▶️ Продовжено")
        logging.info("▶️ Бот продовжує роботу")
    
    def stop(self):
        """Зупинка бота."""
        if not self._running:
            return
        
        self._log("⏹️ Зупинка...")
        logging.info("⏹️ Ініціювання зупинки...")
        
        self._running = False
        self._shutdown_requested = True
        
        # Очікування завершення потоку
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        
        # Логування фінальної статистики
        self._log_final_stats()
        
        # Завершення компонентів
        if self.performance_optimizer:
            self.performance_optimizer.shutdown()
        
        if self.smart_inventory:
            self.smart_inventory.log_stats()
        
        if self.analyzer:
            self.analyzer.log_stats()
        
        if self.executor:
            self.executor.log_stats()
        
        self._log("⏹️ Зупинено")
        logging.info("✅ Бот успішно зупинено")
    
    def set_watering_point(self):
        """Встановлення точки поливу."""
        if self.executor:
            self.executor.set_watering_point()
            if self.executor.watering_point:
                self._log(f"✅ Точку встановлено: {self.executor.watering_point}")
    
    def set_analysis_region(self, x1: int, y1: int, x2: int, y2: int):
        """Встановлення області аналізу."""
        if self.analyzer:
            self.analyzer.set_analysis_region(x1, y1, x2, y2)
            self._log(f"📍 Область встановлено: ({x1},{y1}) - ({x2},{y2})")
    
    def _monitor_loop(self):
        """
        Головний цикл моніторингу з розумною обробкою.
        
        Алгоритм:
        1. Захоплення екрану (через Window Manager якщо є)
        2. Аналіз (OCR + розпізнавання об'єктів)
        3. Виконання дій згідно пріоритетів
        4. Періодична перевірка води
        5. Логування статистики
        """
        consecutive_errors = 0
        max_errors = 5
        start_time = time.time()
        
        logging.info("🔄 Головний цикл моніторингу розпочато")
        logging.info(f"⏱️ Параметри: сканування={self.poll_interval}с, скріншоти={self.analyzer.screenshot_interval}с")
        
        while self._running and not self._shutdown_requested:
            try:
                # Пауза
                if self._paused:
                    time.sleep(0.2)
                    continue
                
                loop_start = time.time()
                self.stats['scans'] += 1
                
                # ============ АНАЛІЗ ============
                logging.debug(f"🔍 Скан #{self.stats['scans']}...")
                analysis = self.analyzer.analyze_screen(save_screenshot=True)
                
                # Детальне логування результатів
                if analysis.text:
                    preview = analysis.text[:80].replace('\n', ' ')
                    log_msg = f"🔍 Скан #{self.stats['scans']}: '{preview}...'"
                    
                    # Додаткова інформація
                    if analysis.parasites_found or analysis.water_level_low:
                        log_msg += f"\n   📊 {analysis.get_summary()}"
                        logging.info(log_msg)
                    else:
                        logging.debug(log_msg)
                else:
                    logging.debug(f"⏭️ Скан #{self.stats['scans']}: текст не знайдено")
                
                # ============ ВИКОНАННЯ ДІЙ ============
                if analysis.confidence > 0.3:
                    # Підрахунок паразитів
                    if analysis.parasites_found:
                        self.stats['parasites_found'] += len(analysis.parasites_found)
                    
                    # Виконання через Smart Executor
                    executed = self.executor.execute(analysis)
                    
                    if executed:
                        self.stats['actions'] += 1
                        action_msg = f"✅ Дію виконано (всього: {self.stats['actions']})"
                        self._log(action_msg)
                        logging.info(action_msg)
                
                # ============ ПЕРІОДИЧНІ ПЕРЕВІРКИ ============
                # Логування статистики кожні 60 секунд
                if time.time() - self.last_stats_log > self.stats_log_interval:
                    self._log_periodic_stats()
                    self.last_stats_log = time.time()
                
                # Очищення старих скріншотів (кожні 5 хвилин)
                if self.stats['scans'] % 150 == 0:
                    if self.performance_optimizer:
                        self.performance_optimizer.cleanup_old_screenshots(max_age_hours=24)
                
                # Скидання лічильника помилок
                consecutive_errors = 0
                
                # ============ ОЧІКУВАННЯ ============
                elapsed = time.time() - loop_start
                sleep_time = max(0.1, self.poll_interval - elapsed)
                
                logging.debug(f"⏸️ Очікування {sleep_time:.1f}с до наступного скану...")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logging.info("⚠️ Отримано сигнал переривання")
                break
                
            except Exception as e:
                consecutive_errors += 1
                self.stats['errors'] += 1
                
                logging.error(
                    f"❌ Помилка циклу (спроба {consecutive_errors}/{max_errors}): {e}",
                    exc_info=True
                )
                
                if consecutive_errors >= max_errors:
                    self._log("🛑 Критична кількість помилок, зупинка")
                    logging.critical("🛑 Досягнуто максимум помилок, аварійна зупинка")
                    
                    if self.executor:
                        self.executor.emergency_stop()
                    
                    self._running = False
                    break
                
                time.sleep(self.poll_interval)
        
        # Розрахунок uptime
        self.stats['uptime'] = int(time.time() - start_time)
        
        logging.info("🔄 Головний цикл завершено")
    
    def _log_periodic_stats(self):
        """Періодичне логування статистики."""
        uptime_min = self.stats['uptime'] // 60
        
        logging.info("=" * 80)
        logging.info(f"📊 СТАТИСТИКА (uptime: {uptime_min} хв)")
        logging.info(f"   🔍 Сканів: {self.stats['scans']}")
        logging.info(f"   ⚡ Дій: {self.stats['actions']}")
        logging.info(f"   🐛 Паразитів: {self.stats['parasites_found']}")
        logging.info(f"   💧 Поливів: {self.executor.stats['waterings_performed'] if self.executor else 0}")
        logging.info(f"   ❌ Помилок: {self.stats['errors']}")
        
        # Ефективність
        if self.stats['scans'] > 0:
            action_rate = (self.stats['actions'] / self.stats['scans']) * 100
            logging.info(f"   📈 Ефективність: {action_rate:.1f}% (дій/скан)")
        
        logging.info("=" * 80)
        
        # Статистика компонентів
        if self.performance_optimizer:
            self.performance_optimizer.log_performance_stats()
    
    def _log_final_stats(self):
        """Фінальна статистика при зупинці."""
        uptime_min = self.stats['uptime'] // 60
        uptime_sec = self.stats['uptime'] % 60
        
        self._log("=" * 40)
        self._log(f"📊 ФІНАЛЬНА СТАТИСТИКА")
        self._log(f"⏱️ Uptime: {uptime_min}хв {uptime_sec}с")
        self._log(f"🔍 Сканів: {self.stats['scans']}")
        self._log(f"⚡ Дій: {self.stats['actions']}")
        self._log(f"🐛 Паразитів: {self.stats['parasites_found']}")
        self._log(f"❌ Помилок: {self.stats['errors']}")
        self._log("=" * 40)
    
    def _log(self, message: str):
        """Логування з callback для GUI."""
        logging.info(message)
        
        if self._log_callback:
            try:
                self._log_callback(message)
            except Exception as e:
                logging.debug(f"Помилка GUI callback: {e}")
    
    def get_full_stats(self) -> dict:
        """Повна статистика всіх компонентів."""
        stats = {
            'bot': self.stats,
            'analyzer': self.analyzer.get_stats() if self.analyzer else {},
            'executor': self.executor.get_state_info() if self.executor else {},
            'performance': self.performance_optimizer.get_performance_stats() if self.performance_optimizer else {},
            'inventory': self.smart_inventory.stats if self.smart_inventory else {},
        }
        
        return stats