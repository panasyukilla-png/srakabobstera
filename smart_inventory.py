"""
smart_inventory.py - Розумний пошук хімікатів та перевірка лейки
"""
import logging
import time
from typing import Optional, Tuple, List, Dict
from pathlib import Path

import cv2
import numpy as np
import pyautogui
from PIL import Image


class SmartInventory:
    """Розумний інвентар з розпізнаванням іконок."""
    
    def __init__(self, window_manager=None, performance_optimizer=None):
        self.window_manager = window_manager
        self.performance_optimizer = performance_optimizer
        
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Шаблони
        self.templates = {}
        self.watering_can_templates = {}
        
        # Налаштування
        self.match_threshold = 0.75  # Поріг схожості для template matching
        self.inventory_open = False
        
        # Статистика
        self.stats = {
            'chemicals_found': 0,
            'searches_performed': 0,
            'water_checks': 0,
        }
        
        self._load_templates()
        logging.info("🎒 Ініціалізовано Smart Inventory")
    
    def _load_templates(self):
        """Завантаження шаблонів з папки data/."""
        try:
            # Завантаження хімікатів
            chemicals_path = self.data_dir / "chemicals.png"
            if chemicals_path.exists():
                chemicals_img = cv2.imread(str(chemicals_path))
                self.templates['chemicals'] = chemicals_img
                logging.info(f"✅ Завантажено хімікати: {chemicals_img.shape}")
            else:
                logging.warning(f"⚠️ Файл не знайдено: {chemicals_path}")
            
            # Завантаження лейки (повна)
            full_leyka_path = self.data_dir / "full_leyka.png"
            if full_leyka_path.exists():
                full_leyka = cv2.imread(str(full_leyka_path))
                self.watering_can_templates['full'] = full_leyka
                logging.info(f"✅ Завантажено повну лейку: {full_leyka.shape}")
            else:
                logging.warning(f"⚠️ Файл не знайдено: {full_leyka_path}")
            
            # Завантаження лейки (пуста)
            empty_leyka_path = self.data_dir / "empty_leyka.png"
            if empty_leyka_path.exists():
                empty_leyka = cv2.imread(str(empty_leyka_path))
                self.watering_can_templates['empty'] = empty_leyka
                logging.info(f"✅ Завантажено пусту лейку: {empty_leyka.shape}")
            else:
                logging.warning(f"⚠️ Файл не знайдено: {empty_leyka_path}")
            
            logging.info(f"📦 Завантажено шаблонів: {len(self.templates) + len(self.watering_can_templates)}")
            
        except Exception as e:
            logging.error(f"❌ Помилка завантаження шаблонів: {e}", exc_info=True)
    
    def find_template_on_screen(self, template_name: str, region: Tuple[int, int, int, int] = None,
                                threshold: Optional[float] = None) -> Optional[Tuple[int, int, float]]:
        """
        Пошук шаблону на екрані.
        
        Returns:
            (x, y, confidence) або None
        """
        if template_name not in self.templates:
            logging.warning(f"⚠️ Шаблон '{template_name}' не завантажено")
            return None
        
        try:
            # Захоплення екрану
            if self.window_manager:
                if region:
                    screenshot = self.window_manager.capture_window(region)
                else:
                    screenshot = self.window_manager.capture_window()
            else:
                from PIL import ImageGrab
                screenshot = ImageGrab.grab(bbox=region) if region else ImageGrab.grab()
            
            if screenshot is None:
                return None
            
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            template = self.templates[template_name]
            
            # Оптимізація для matching
            if self.performance_optimizer:
                screenshot = self.performance_optimizer.optimize_for_template_matching(screenshot)
                template = self.performance_optimizer.optimize_for_template_matching(template)
            
            # Template matching з кількома масштабами
            best_match = None
            best_confidence = 0
            
            for scale in [1.0, 0.9, 0.8, 1.1, 1.2]:
                scaled_template = cv2.resize(template, None, fx=scale, fy=scale)
                
                if scaled_template.shape[0] > screenshot.shape[0] or scaled_template.shape[1] > screenshot.shape[1]:
                    continue
                
                result = cv2.matchTemplate(screenshot, scaled_template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_confidence:
                    best_confidence = max_val
                    h, w = scaled_template.shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    best_match = (center_x, center_y)
            
            threshold = threshold or self.match_threshold
            if best_confidence >= threshold:
                # Додаємо офсет якщо є region
                if region:
                    x, y = best_match
                    best_match = (x + region[0], y + region[1])
                
                logging.info(f"🎯 Знайдено '{template_name}': {best_match}, впевненість: {best_confidence:.2%}")
                return (*best_match, best_confidence)
            
            logging.debug(f"🔍 '{template_name}' не знайдено (макс: {best_confidence:.2%})")
            return None
            
        except Exception as e:
            logging.error(f"❌ Помилка пошуку шаблону '{template_name}': {e}", exc_info=True)
            return None
    
    def check_watering_can_status(self) -> Optional[str]:
        """
        Перевірка статусу лейки.
        
        Returns:
            'full', 'empty', або None
        """
        try:
            self.stats['water_checks'] += 1
            
            # Область пошуку (нижня частина екрану - UI)
            if self.window_manager:
                region = self.window_manager.get_ui_region('bottom')
            else:
                screen_width, screen_height = pyautogui.size()
                region = (0, screen_height // 2, screen_width, screen_height)
            
            # Захоплення скріншоту
            if self.window_manager:
                screenshot = self.window_manager.capture_window(region)
            else:
                from PIL import ImageGrab
                screenshot = ImageGrab.grab(bbox=region)
            
            if screenshot is None:
                return None
            
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Оптимізація
            if self.performance_optimizer:
                screenshot = self.performance_optimizer.optimize_for_template_matching(screenshot)
            
            # Перевірка обох шаблонів
            results = {}
            for status, template in self.watering_can_templates.items():
                if self.performance_optimizer:
                    template_opt = self.performance_optimizer.optimize_for_template_matching(template)
                else:
                    template_opt = template
                
                result = cv2.matchTemplate(screenshot, template_opt, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                results[status] = max_val
                
                logging.debug(f"💧 Лейка '{status}': впевненість {max_val:.2%}")
            
            # Вибираємо найкращий результат
            if results:
                best_status = max(results, key=results.get)
                best_confidence = results[best_status]
                
                if best_confidence >= 0.7:  # Поріг для лейки
                    logging.info(f"💧 Статус лейки: {best_status.upper()} ({best_confidence:.1%})")
                    return best_status
            
            logging.debug("💧 Лейку не знайдено або невизначений статус")
            return None
            
        except Exception as e:
            logging.error(f"❌ Помилка перевірки лейки: {e}", exc_info=True)
            return None
    
    def open_inventory(self) -> bool:
        """Відкриття інвентаря (TAB)."""
        try:
            if self.inventory_open:
                return True
            
            logging.info("🎒 Відкриття інвентаря (TAB)...")
            
            # Фокус на вікні
            if self.window_manager:
                self.window_manager.focus_window()
            
            pyautogui.press('tab')
            time.sleep(0.5)
            self.inventory_open = True
            return True
            
        except Exception as e:
            logging.error(f"❌ Помилка відкриття інвентаря: {e}")
            return False
    
    def close_inventory(self) -> bool:
        """Закриття інвентаря (TAB)."""
        try:
            if not self.inventory_open:
                return True
            
            logging.info("🎒 Закриття інвентаря (TAB)...")
            pyautogui.press('tab')
            time.sleep(0.3)
            self.inventory_open = False
            return True
            
        except Exception as e:
            logging.error(f"❌ Помилка закриття інвентаря: {e}")
            return False
    
    def find_chemical_by_text(self, chemical_name: str) -> Optional[Tuple[int, int]]:
        """
        Пошук хімікату по тексту в інвентарі.
        
        Args:
            chemical_name: Назва хімікату (наприклад, "ТЛЯ")
        
        Returns:
            (x, y) координати або None
        """
        try:
            self.stats['searches_performed'] += 1
            
            # Відкриваємо інвентар
            if not self.open_inventory():
                return None
            
            time.sleep(0.3)
            
            # Область інвентаря
            if self.window_manager:
                region = self.window_manager.get_ui_region('inventory')
            else:
                screen_width, screen_height = pyautogui.size()
                region = (0, int(screen_height * 0.7), screen_width, screen_height)
            
            # Захоплення
            if self.window_manager:
                screenshot = self.window_manager.capture_window(region)
            else:
                from PIL import ImageGrab
                screenshot = ImageGrab.grab(bbox=region)
            
            if screenshot is None:
                return None
            
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # OCR для пошуку тексту
            import pytesseract
            
            # Попередня обробка для OCR
            if self.performance_optimizer:
                processed = self.performance_optimizer.preprocess_for_ocr(screenshot, aggressive=True)
            else:
                gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                _, processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            data = pytesseract.image_to_data(processed, lang='ukr+rus+eng', output_type=pytesseract.Output.DICT)
            
            # Пошук тексту
            chemical_lower = chemical_name.lower()
            for i, word in enumerate(data['text']):
                if word and chemical_lower in word.lower():
                    x = data['left'][i] + data['width'][i] // 2
                    y = data['top'][i] + data['height'][i] // 2
                    
                    # Додаємо офсет регіону
                    final_x = x + region[0]
                    final_y = y + region[1]
                    
                    self.stats['chemicals_found'] += 1
                    logging.info(f"🧪 Знайдено '{chemical_name}' на ({final_x}, {final_y})")
                    return (final_x, final_y)
            
            logging.debug(f"🔍 Хімікат '{chemical_name}' не знайдено по тексту")
            return None
            
        except Exception as e:
            logging.error(f"❌ Помилка пошуку хімікату '{chemical_name}': {e}", exc_info=True)
            return None
        finally:
            # Завжди закриваємо інвентар
            time.sleep(0.2)
            self.close_inventory()
    
    def click_chemical(self, chemical_name: str) -> bool:
        """
        Знайти та клікнути хімікат.
        
        Args:
            chemical_name: Назва хімікату
        """
        try:
            position = self.find_chemical_by_text(chemical_name)
            
            if position:
                logging.info(f"🖱️ Клік по '{chemical_name}' на {position}")
                
                if self.window_manager:
                    self.window_manager.click_in_window(*position, window_coords=False)
                else:
                    pyautogui.moveTo(*position, duration=0.2)
                    time.sleep(0.1)
                    pyautogui.click()
                
                time.sleep(0.3)
                return True
            
            logging.warning(f"⚠️ Не вдалося знайти '{chemical_name}'")
            return False
            
        except Exception as e:
            logging.error(f"❌ Помилка кліку по '{chemical_name}': {e}")
            return False
    
    def needs_water_refill(self, threshold: float = 0.3) -> bool:
        """
        Перевірка чи потрібно поповнити воду.
        
        Args:
            threshold: Поріг (якщо лейка менше 30% повна)
        
        Returns:
            True якщо потрібно поповнити
        """
        status = self.check_watering_can_status()
        
        if status == 'empty':
            logging.info("⚠️ Лейка ПУСТА - потрібне поповнення!")
            return True
        elif status == 'full':
            logging.info("✅ Лейка ПОВНА")
            return False
        else:
            # Невизначено - припускаємо що все ок
            logging.debug("🤷 Статус лейки невизначений")
            return False
    
    def log_stats(self):
        """Логування статистики."""
        logging.info("=" * 60)
        logging.info("📊 СТАТИСТИКА ІНВЕНТАРЯ:")
        logging.info(f"   🔍 Пошуків виконано: {self.stats['searches_performed']}")
        logging.info(f"   🧪 Хімікатів знайдено: {self.stats['chemicals_found']}")
        logging.info(f"   💧 Перевірок лейки: {self.stats['water_checks']}")
        logging.info("=" * 60)