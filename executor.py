"""
executor.py - Розумний виконавець дій з повною автономністю
"""
import time
import logging
from typing import Optional, Tuple
from enum import Enum

import pyautogui

from config import ParasiteConfig
from analyzer import SmartAnalyzer, ScreenAnalysis


# ======================== СТАНИ ВИКОНАННЯ ========================
class ExecutionState(Enum):
    """Стани виконання дій."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    TREATING_PARASITE = "treating_parasite"
    WATERING = "watering"
    CHECKING_WATER = "checking_water"
    REFILLING_WATER = "refilling_water"
    WALKING = "walking"
    ERROR = "error"


# ======================== РОЗУМНИЙ ВИКОНАВЕЦЬ ========================
class SmartExecutor:
    """Виконавець з автономністю та розумінням контексту."""
    
    def __init__(self, analyzer: SmartAnalyzer, window_manager=None, smart_inventory=None):
        self.analyzer = analyzer
        self.window_manager = window_manager
        self.smart_inventory = smart_inventory
        
        # Налаштування
        self.watering_point: Optional[Tuple[int, int]] = None
        self.action_delay = 0.5
        self.typing_delay = 0.1
        
        # Стан
        self.current_state = ExecutionState.IDLE
        self.last_action_time = 0
        
        # Лічильники для автоматизації
        self.watering_count = 0
        self.water_check_interval = 5  # Перевірка води кожні 5 поливів
        self.last_parasite_treatment = 0
        
        # Статистика
        self.stats = {
            'parasites_treated': 0,
            'waterings_performed': 0,
            'water_refills': 0,
            'failed_actions': 0,
            'total_actions': 0,
        }
        
        logging.info("⚡ Ініціалізовано Smart Executor")
    
    def execute(self, analysis: ScreenAnalysis) -> bool:
        """
        Головний метод виконання дій згідно логіки завдань.
        
        ЛОГІКА (з інструкцій):
        1. ПАРАЗИТИ - найвищий пріоритет
        2. Після паразитів - полив БЕЗ добрива
        3. Якщо паразитів немає - звичайний полив (з добривом за потреби)
        4. Кожні 5 поливів - перевірка рівня води в лейці
        """
        if analysis.confidence < 0.3:
            logging.debug(f"⭐ Пропуск (низька впевненість: {analysis.confidence:.1%})")
            return False
        
        executed = False
        
        # ПРІОРИТЕТ 1: Паразити
        if analysis.parasites_found:
            logging.info(f"🐛 Виявлено {len(analysis.parasites_found)} паразит(ів) - починаємо обробку")
            
            for parasite in analysis.parasites_found:
                action_key = f"parasite_{parasite.name}"
                
                if self.analyzer.can_perform_action(action_key, cooldown=5.0):
                    self.current_state = ExecutionState.TREATING_PARASITE
                    
                    if self._handle_parasite_smart(parasite):
                        executed = True
                        self.stats['parasites_treated'] += 1
                        self.stats['total_actions'] += 1
                        self.last_parasite_treatment = time.time()
                        time.sleep(self.action_delay)
                    else:
                        self.stats['failed_actions'] += 1
                else:
                    logging.debug(f"⏳ Cooldown для {parasite.name}")
        
        # ПРІОРИТЕТ 2: Полив
        if analysis.water_level_low or analysis.water_amount_needed:
            logging.info(f"💧 Виявлено потребу в поливі")
            
            if self.analyzer.can_perform_action("water", cooldown=3.0):
                self.current_state = ExecutionState.WATERING
                
                # Визначаємо параметри поливу
                water_amount = analysis.water_amount_needed or self.analyzer.config.watering_amount
                
                # Якщо були паразити недавно (останні 10 сек) - БЕЗ добрива
                recently_treated = (time.time() - self.last_parasite_treatment) < 10
                use_fertilizer = analysis.needs_fertilizer and not recently_treated
                
                if recently_treated:
                    logging.info(f"💧 Після паразитів - полив БЕЗ добрива ({water_amount:.1f}л)")
                else:
                    logging.info(f"💧 Стандартний полив ({water_amount:.1f}л, добриво: {use_fertilizer})")
                
                if self._water_plant_smart(water_amount, use_fertilizer):
                    executed = True
                    self.stats['waterings_performed'] += 1
                    self.stats['total_actions'] += 1
                    self.watering_count += 1
                else:
                    self.stats['failed_actions'] += 1
        
        # Перевірка лейки кожні N поливів
        if self.watering_count > 0 and self.watering_count % self.water_check_interval == 0:
            if self.smart_inventory:
                self._check_and_refill_water()
        
        if executed:
            self.current_state = ExecutionState.IDLE
        
        return executed
    
    def _handle_parasite_smart(self, parasite: ParasiteConfig) -> bool:
        """
        Розумна обробка паразита з пошуком в інвентарі.
        
        Алгоритм:
        1. Спроба через швидку клавішу
        2. Якщо не працює - пошук в інвентарі
        3. Встановлення об'єму
        4. Застосування
        """
        try:
            logging.info(f"🧪 Обробка паразита: {parasite.name}")
            logging.info(f"   ├─ Категорія: {parasite.category}")
            logging.info(f"   ├─ Клавіша: {parasite.key}")
            logging.info(f"   ├─ Об'єм: {parasite.water_amount[0]}-{parasite.water_amount[1]}л")
            logging.info(f"   └─ Тривалість: {parasite.duration}с")
            
            # Фокус на вікно
            if self.window_manager:
                self.window_manager.focus_window()
            
            # МЕТОД 1: Швидка клавіша
            success = self._try_quick_chemical(parasite)
            
            # МЕТОД 2: Пошук в інвентарі (якщо є smart_inventory)
            if not success and self.smart_inventory:
                logging.info(f"🎒 Спроба знайти '{parasite.name}' в інвентарі...")
                success = self.smart_inventory.click_chemical(parasite.name)
            
            if not success:
                logging.warning(f"⚠️ Не вдалося активувати хімікат для {parasite.name}")
                return False
            
            time.sleep(0.5)
            
            # Встановлення кількості
            avg_amount = sum(parasite.water_amount) / 2
            self._set_amount(avg_amount)
            
            logging.info(f"✅ Паразита {parasite.name} оброблено ({avg_amount:.1f}л)")
            
            # Оновлення контексту
            self.analyzer.game_context.add_action(f"Обробка: {parasite.name}")
            self.analyzer.game_context.plants_treated += 1
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Помилка обробки паразита {parasite.name}: {e}", exc_info=True)
            return False
    
    def _try_quick_chemical(self, parasite: ParasiteConfig) -> bool:
        """Спроба використати швидку клавішу."""
        try:
            pyautogui.press(parasite.key)
            time.sleep(0.3)
            
            # TODO: Перевірка чи з'явилось UI вибору кількості
            # Поки що припускаємо що працює
            
            logging.debug(f"⌨️ Натиснуто клавішу '{parasite.key}'")
            return True
            
        except Exception as e:
            logging.debug(f"Помилка швидкої клавіші: {e}")
            return False
    
    def _water_plant_smart(self, amount: float, with_fertilizer: bool = False) -> bool:
        """
        Розумний полив з автоматичним пошуком точки.
        
        Алгоритм:
        1. Перевірка точки поливу
        2. Активація режиму поливу
        3. Встановлення кількості
        4. Клік на точку або автопошук
        """
        try:
            fertilizer_text = "З ДОБРИВОМ" if with_fertilizer else "БЕЗ добрива"
            logging.info(f"💧 Полив: {amount:.1f}л {fertilizer_text}")
            
            # Фокус
            if self.window_manager:
                self.window_manager.focus_window()
            
            # Активація поливу (клавіша '1')
            pyautogui.press("1")
            time.sleep(0.3)
            
            # Встановлення кількості
            self._set_amount(amount)
            time.sleep(0.2)
            
            # Клік на точку поливу
            if self.watering_point:
                x, y = self.watering_point
                logging.info(f"   └─ Клік на точку: ({x}, {y})")
                
                if self.window_manager:
                    self.window_manager.click_in_window(x, y, window_coords=False)
                else:
                    pyautogui.moveTo(x, y, duration=0.2)
                    time.sleep(0.1)
                    pyautogui.click()
                
                logging.info(f"✅ Полив виконано: {amount:.1f}л {fertilizer_text}")
                
                # Оновлення контексту
                self.analyzer.game_context.add_action(f"Полив: {amount:.1f}л ({fertilizer_text})")
                self.analyzer.game_context.plants_watered += 1
                
                return True
            else:
                logging.warning("⚠️ Точка поливу не встановлена!")
                logging.warning("⚠️ Встановіть через GUI або автоматично")
                return False
                
        except Exception as e:
            logging.error(f"❌ Помилка поливу: {e}", exc_info=True)
            return False
    
    def _set_amount(self, amount: float):
        """Встановлення кількості рідини з покращеною точністю."""
        try:
            logging.debug(f"⚙️ Встановлення: {amount:.1f}л")
            
            # Очищення поля (більше спроб для надійності)
            for _ in range(8):
                pyautogui.press("backspace")
                time.sleep(0.03)
            
            time.sleep(0.1)
            
            # Введення значення
            amount_str = f"{amount:.1f}".replace(".", ",")  # Українська локаль
            
            for char in amount_str:
                pyautogui.press(char)
                time.sleep(self.typing_delay)
            
            logging.debug(f"   └─ Введено: {amount_str}л")
            time.sleep(0.2)
            
        except Exception as e:
            logging.error(f"❌ Помилка встановлення кількості: {e}")
    
    def _check_and_refill_water(self):
        """Перевірка та поповнення води в лейці."""
        if not self.smart_inventory:
            logging.debug("Smart Inventory недоступний для перевірки води")
            return
        
        try:
            logging.info("💧 Перевірка рівня води в лейці...")
            self.current_state = ExecutionState.CHECKING_WATER
            
            status = self.smart_inventory.check_watering_can_status()
            
            if status == 'empty':
                logging.warning("⚠️ Лейка ПУСТА - потрібне поповнення!")
                self._refill_water()
            elif status == 'full':
                logging.info("✅ Лейка повна")
            else:
                logging.debug("🤷 Статус лейки невизначений")
            
            self.analyzer.game_context.water_checks += 1
            
        except Exception as e:
            logging.error(f"❌ Помилка перевірки води: {e}")
    
    def _refill_water(self):
        """Поповнення води (placeholder - потребує реалізації логіки гри)."""
        try:
            logging.info("🚰 Поповнення води...")
            self.current_state = ExecutionState.REFILLING_WATER
            
            # TODO: Реалізувати логіку:
            # 1. Знайти колодязь/бочку
            # 2. Наблизитись
            # 3. Взаємодіяти
            # 4. Перевірити наповнення
            
            # Поки що заглушка
            logging.warning("⚠️ Автопоповнення води ще не реалізовано")
            logging.info("💡 Поповніть воду вручну або реалізуйте логіку в _refill_water()")
            
            self.stats['water_refills'] += 1
            self.analyzer.game_context.add_action("Спроба поповнити воду")
            
        except Exception as e:
            logging.error(f"❌ Помилка поповнення води: {e}")
    
    def set_watering_point(self):
        """Встановлення точки поливу через курсор."""
        try:
            logging.info("📍 Встановлення точки поливу...")
            logging.info("   Після 1.5с наведіть курсор на точку поливу")
            
            time.sleep(1.5)
            
            position = pyautogui.position()
            self.watering_point = (position.x, position.y)
            
            logging.info(f"✅ Точку встановлено: {self.watering_point}")
            self.analyzer.game_context.add_action(f"Точка поливу: {self.watering_point}")
            
        except Exception as e:
            logging.error(f"❌ Помилка встановлення точки: {e}")
    
    def auto_detect_watering_point(self):
        """
        Автоматичне виявлення точки поливу (placeholder).
        
        TODO: Використати template matching для пошуку іконки рослини
        """
        logging.warning("⚠️ Автовиявлення точки поливу ще не реалізовано")
        logging.info("💡 Використовуйте ручне встановлення через GUI")
    
    def emergency_stop(self):
        """Аварійна зупинка всіх дій."""
        logging.warning("🛑 АВАРІЙНА ЗУПИНКА")
        self.current_state = ExecutionState.ERROR
        
        # Закриття всіх можливих меню
        for _ in range(3):
            pyautogui.press('esc')
            time.sleep(0.2)
    
    def get_state_info(self) -> dict:
        """Інформація про поточний стан."""
        return {
            'state': self.current_state.value,
            'watering_point_set': self.watering_point is not None,
            'watering_count': self.watering_count,
            'next_water_check': self.water_check_interval - (self.watering_count % self.water_check_interval),
            'stats': self.stats,
        }
    
    def log_stats(self):
        """Логування статистики."""
        state_info = self.get_state_info()
        
        logging.info("=" * 80)
        logging.info("📊 СТАТИСТИКА ВИКОНАВЦЯ:")
        logging.info(f"   🐛 Паразитів оброблено: {self.stats['parasites_treated']}")
        logging.info(f"   💧 Поливів виконано: {self.stats['waterings_performed']}")
        logging.info(f"   🚰 Поповнень води: {self.stats['water_refills']}")
        logging.info(f"   ❌ Невдалих дій: {self.stats['failed_actions']}")
        logging.info(f"   ✅ Всього дій: {self.stats['total_actions']}")
        logging.info(f"   📍 Точка поливу: {'✅ Встановлена' if state_info['watering_point_set'] else '❌ Не встановлена'}")
        logging.info(f"   🔄 Наступна перевірка води через: {state_info['next_water_check']} поливів")
        logging.info("=" * 80)