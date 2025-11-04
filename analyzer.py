"""
analyzer.py - Розумний аналізатор з контекстним розумінням гри - ВИПРАВЛЕНО
"""
import time
import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import ImageGrab

from config import ParasiteConfig, TaskConfig, SCREENSHOTS_DIR


# ======================== КОНТЕКСТ ГРИ ========================
@dataclass
class GameContext:
    """Контекст поточного стану гри."""
    current_location: str = "unknown"  # field, inventory, shop, etc
    last_action: str = ""
    last_action_time: float = 0
    consecutive_errors: int = 0
    total_actions: int = 0
    
    # Стан рослин
    plants_watered: int = 0
    plants_treated: int = 0
    water_checks: int = 0
    
    # Стан ресурсів
    water_level: str = "unknown"  # full, medium, low, empty
    has_fertilizer: bool = True
    
    # Історія подій
    recent_parasites: List[str] = field(default_factory=list)
    recent_actions: List[str] = field(default_factory=list)
    
    def add_action(self, action: str):
        """Додавання дії до історії."""
        self.last_action = action
        self.last_action_time = time.time()
        self.total_actions += 1
        self.recent_actions.append(f"{datetime.now().strftime('%H:%M:%S')} - {action}")
        
        # Обмеження історії до 20 подій
        if len(self.recent_actions) > 20:
            self.recent_actions.pop(0)
    
    def add_parasite(self, parasite_name: str):
        """Додавання паразита до історії."""
        self.recent_parasites.append(parasite_name)
        if len(self.recent_parasites) > 10:
            self.recent_parasites.pop(0)
    
    def get_status_summary(self) -> str:
        """Отримання стислого статусу."""
        return (f"Локація: {self.current_location} | "
                f"Полито: {self.plants_watered} | "
                f"Оброблено: {self.plants_treated} | "
                f"Вода: {self.water_level} | "
                f"Дій: {self.total_actions}")


# ======================== РЕЗУЛЬТАТ АНАЛІЗУ ========================
@dataclass
class ScreenAnalysis:
    """Результат аналізу екрану з контекстом."""
    # OCR дані
    text: str
    text_confidence: float
    text_lines: List[str] = field(default_factory=list)
    
    # Виявлені об'єкти
    parasites_found: List[ParasiteConfig] = field(default_factory=list)
    water_level_low: bool = False
    water_amount_needed: Optional[float] = None
    needs_fertilizer: bool = False
    soil_level: Optional[int] = None
    
    # Додаткова інформація
    ui_elements_detected: List[str] = field(default_factory=list)
    current_screen: str = "unknown"  # gameplay, inventory, menu
    player_position: Optional[Tuple[int, int]] = None
    
    # Метрики
    confidence: float = 0.0
    screenshot_path: Optional[Path] = None
    analysis_time: float = 0.0
    
    def get_summary(self) -> str:
        """Стислий опис аналізу."""
        parts = []
        
        if self.parasites_found:
            parasites_str = ", ".join([p.name for p in self.parasites_found])
            parts.append(f"🐛 {len(self.parasites_found)} паразит(ів): {parasites_str}")
        
        if self.water_level_low:
            parts.append(f"💧 Мало води")
        
        if self.water_amount_needed:
            parts.append(f"📊 Потрібно: {self.water_amount_needed:.1f}л")
        
        if self.needs_fertilizer:
            parts.append(f"🌱 Добриво")
        
        if self.soil_level:
            parts.append(f"🌍 Грунт: {self.soil_level}%")
        
        parts.append(f"🎯 {self.confidence:.0%}")
        
        return " | ".join(parts) if parts else "Нічого не виявлено"


# ======================== РОЗУМНИЙ АНАЛІЗАТОР ========================
class SmartAnalyzer:
    """Розумний аналізатор з контекстним розумінням - ВИПРАВЛЕНО."""
    
    def __init__(self, config: TaskConfig, window_manager=None, performance_optimizer=None):
        self.config = config
        self.window_manager = window_manager
        self.performance_optimizer = performance_optimizer
        
        # Контекст гри
        self.game_context = GameContext()
        
        # Параметри аналізу
        self.analysis_region: Optional[Tuple[int, int, int, int]] = None
        self.last_screenshot_time = 0
        self.screenshot_interval = 5.0
        
        # Кеш для OCR
        self.last_ocr_result = ""
        self.last_ocr_time = 0
        self.ocr_cache_duration = 2.0
        
        # Cooldown для дій
        self.action_cooldowns: Dict[str, float] = {}
        self.default_cooldown = 3.0
        
        # Статистика
        self.stats = {
            'scans_total': 0,
            'scans_successful': 0,
            'parasites_detected': 0,
            'water_warnings': 0,
            'avg_analysis_time': 0.0
        }
        
        logging.info("🔍 Ініціалізовано Smart Analyzer (FIXED VERSION)")
    
    def set_analysis_region(self, x1: int, y1: int, x2: int, y2: int):
        """Встановлення області аналізу."""
        self.analysis_region = (x1, y1, x2, y2)
        logging.info(f"📍 Область аналізу: ({x1}, {y1}) -> ({x2}, {y2}) = {x2-x1}x{y2-y1}px")
    
    def auto_detect_game_ui(self):
        """Автоматичне визначення UI області гри."""
        if self.window_manager:
            # Використовуємо window manager для отримання нижньої частини
            self.analysis_region = self.window_manager.get_ui_region('bottom')
            logging.info(f"🎮 Автоматично встановлено UI область гри через Window Manager")
        else:
            # Fallback - нижня 50% екрану
            import pyautogui
            screen_width, screen_height = pyautogui.size()
            x1, y1 = 0, screen_height // 2
            x2, y2 = screen_width, screen_height
            self.set_analysis_region(x1, y1, x2, y2)
            logging.info(f"🖥️ Автоматично встановлено нижню 50% екрану")
    
    def capture_screen(self) -> Optional[np.ndarray]:
        """Захоплення екрану через Window Manager або PIL."""
        try:
            if self.window_manager:
                # Використовуємо window manager
                region = self.analysis_region or self.window_manager.get_ui_region('bottom')
                screenshot = self.window_manager.capture_window(region)
                if screenshot:
                    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    return screenshot
            
            # Fallback - PIL
            if self.analysis_region:
                screenshot = ImageGrab.grab(bbox=self.analysis_region)
            else:
                # Автоматично нижня половина
                import pyautogui
                screen_width, screen_height = pyautogui.size()
                screenshot = ImageGrab.grab(bbox=(0, screen_height // 2, screen_width, screen_height))
            
            return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            logging.error(f"❌ Помилка захоплення екрану: {e}")
            return None
    
    def analyze_screen(self, save_screenshot: bool = True) -> ScreenAnalysis:
        """Головний метод аналізу екрану - ВИПРАВЛЕНО з детальним логуванням."""
        start_time = time.time()
        self.stats['scans_total'] += 1
        
        analysis = ScreenAnalysis(text="", text_confidence=0.0)
        
        # Захоплення
        screenshot = self.capture_screen()
        if screenshot is None:
            logging.error("❌ Не вдалося захопити екран")
            return analysis
        
        # Оптимізація
        if self.performance_optimizer:
            screenshot = self.performance_optimizer.optimize_screenshot(screenshot)
        
        # Збереження скріншоту (економія ресурсів)
        current_time = time.time()
        should_save = save_screenshot and (current_time - self.last_screenshot_time >= self.screenshot_interval)
        
        if should_save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = SCREENSHOTS_DIR / f"screen_{timestamp}.jpg"
            
            if self.performance_optimizer:
                self.performance_optimizer.save_screenshot_optimized(screenshot, screenshot_path)
            else:
                cv2.imwrite(str(screenshot_path), screenshot)
            
            analysis.screenshot_path = screenshot_path
            self.last_screenshot_time = current_time
            logging.debug(f"💾 Збережено: {screenshot_path.name}")
        
        # OCR аналіз
        text, confidence, lines = self._extract_text_enhanced(screenshot)
        analysis.text = text
        analysis.text_confidence = confidence
        analysis.text_lines = lines
        
        if not text:
            logging.debug("⏭️ Текст не розпізнано на кадрі")
            analysis.analysis_time = time.time() - start_time
            return analysis
        
        text_lower = text.lower()
        
        # Визначення поточного екрану
        analysis.current_screen = self._detect_screen_type(text_lower, lines)
        self.game_context.current_location = analysis.current_screen
        
        logging.info(f"📱 Екран: {analysis.current_screen} | Впевненість OCR: {confidence:.1%}")
        
        # ========== ДЕТАЛЬНА ДІАГНОСТИКА (НОВЕ!) ==========
        logging.info("=" * 80)
        logging.info("🔍 ДЕТАЛЬНА ДІАГНОСТИКА АНАЛІЗУ:")
        logging.info(f"   📝 Текст розпізнано: {len(text)} символів")
        logging.info(f"   📄 Рядків: {len(lines)}")
        logging.info(f"   🎯 Впевненість OCR: {confidence:.1%}")
        
        if text:
            # Показуємо перші 300 символів
            preview = text[:300].replace('\n', ' | ')
            logging.info(f"   📋 Приклад тексту: '{preview}...'")
            
            # Пошук ключових слів
            keywords = ['полив', 'вода', 'рослин', 'грунт', 'добрив', 'літр', 'паразит',
                       'тля', 'слизн', 'жук', 'медвед', 'трипс', 'клещ', 'нематод', 'проволочник',
                       'кравчик', 'щелкун', 'колорадск']
            found_keywords = [kw for kw in keywords if kw in text.lower()]
            if found_keywords:
                logging.info(f"   🔑 Знайдено ключові слова: {', '.join(found_keywords)}")
            else:
                logging.warning(f"   ⚠️ ЖОДНОГО ключового слова не знайдено!")
                logging.warning(f"   💡 Можливо потрібно покращити область аналізу або якість OCR")
        
        # Пошук паразитів (покращена логіка)
        parasites = self._detect_parasites(text_lower, lines)
        analysis.parasites_found = parasites
        
        parasites_info = ", ".join([p.name for p in parasites]) if parasites else "немає"
        logging.info(f"   🐛 Паразити: {parasites_info}")
        
        if parasites:
            for p in parasites:
                self.game_context.add_parasite(p.name)
                self.stats['parasites_detected'] += 1
            
            parasites_str = ", ".join([p.name for p in parasites])
            logging.info(f"🐛 ВИЯВЛЕНО ПАРАЗИТІВ: {parasites_str}")
        
        # Перевірка рівня води (контекстний аналіз)
        water_info = self._analyze_water_status(text_lower, lines)
        analysis.water_level_low = water_info['low']
        analysis.water_amount_needed = water_info.get('amount')
        
        logging.info(f"   💧 Низька вода: {water_info['low']}")
        logging.info(f"   📊 Кількість води: {water_info.get('amount', 'не визначено')}")
        if water_info.get('keywords'):
            logging.info(f"   🔍 Ключові слова води: {', '.join(water_info['keywords'])}")
        
        if water_info['low']:
            self.stats['water_warnings'] += 1
            self.game_context.water_level = "low"
            logging.warning(f"💧 НИЗЬКИЙ РІВЕНЬ ВОДИ: {water_info}")
        
        # Перевірка добрива
        analysis.needs_fertilizer = self._check_fertilizer_need(text_lower, lines)
        if analysis.needs_fertilizer:
            logging.info(f"   🌱 Потрібне добриво: ТАК")
        
        # Рівень грунту
        soil = self._parse_soil_level(text_lower)
        if soil:
            analysis.soil_level = soil
            logging.info(f"   🌍 Рівень грунту: {soil}%")
        
        # UI елементи
        ui_elements = self._detect_ui_elements(text_lower, lines)
        analysis.ui_elements_detected = ui_elements
        logging.info(f"   🎮 UI елементи: {len(ui_elements)} - {', '.join(ui_elements) if ui_elements else 'немає'}")
        
        # Розрахунок впевненості (ПОКРАЩЕНО!)
        confidence_score = self._calculate_confidence(analysis)
        analysis.confidence = confidence_score
        
        logging.info(f"   ⭐ Загальна впевненість: {confidence_score:.1%}")
        logging.info("=" * 80)
        # ========== КІНЕЦЬ ДІАГНОСТИКИ ==========
        
        analysis.analysis_time = time.time() - start_time
        self.stats['avg_analysis_time'] = (self.stats['avg_analysis_time'] + analysis.analysis_time) / 2
        
        if analysis.confidence > 0.15:  # Знижений поріг
            self.stats['scans_successful'] += 1
        
        # Логування
        summary = analysis.get_summary()
        if summary != "Нічого не виявлено":
            logging.info(f"✅ Аналіз: {summary} | Час: {analysis.analysis_time:.2f}с")
        else:
            logging.debug(f"⏭️ Аналіз: нічого важливого | Час: {analysis.analysis_time:.2f}с")
        
        return analysis
    
    def _extract_text_enhanced(self, image: np.ndarray) -> Tuple[str, float, List[str]]:
        """Покращене розпізнавання тексту з багатьма спробами."""
        try:
            # Перевірка кешу
            if self.performance_optimizer:
                cached = self.performance_optimizer.get_cached_ocr(image)
                if cached:
                    lines = cached.split('\n')
                    return cached, 0.85, lines
            
            # Попередня обробка
            if self.performance_optimizer:
                processed = self.performance_optimizer.preprocess_for_ocr(image, mode='aggressive')
            else:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                _, processed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Спроби з різними конфігураціями
            configs = [
                ('ukr+rus+eng', '--psm 6 --oem 3'),  # Найкраща якість
                ('ukr+rus+eng', '--psm 11 --oem 3'),  # Sparse text
                ('rus+eng', '--psm 6 --oem 3'),
                ('ukr', '--psm 6 --oem 3'),
            ]
            
            best_text = ""
            best_conf = 0.0
            best_lines = []
            
            for lang, config in configs:
                try:
                    data = pytesseract.image_to_data(
                        processed, 
                        lang=lang, 
                        config=config,
                        output_type=pytesseract.Output.DICT
                    )
                    
                    # Фільтруємо по впевненості
                    words = []
                    confidences = []
                    
                    for i in range(len(data['text'])):
                        conf = int(data['conf'][i])
                        text = data['text'][i].strip()
                        
                        if conf > 30 and text:
                            words.append(text)
                            confidences.append(conf)
                    
                    if words:
                        text = " ".join(words)
                        avg_conf = np.mean(confidences) / 100.0
                        
                        if avg_conf > best_conf:
                            best_conf = avg_conf
                            best_text = text
                            best_lines = text.split('\n')
                
                except Exception as e:
                    logging.debug(f"OCR спроба ({lang}): {e}")
                    continue
            
            # Кешування
            if best_text and self.performance_optimizer:
                self.performance_optimizer.cache_ocr_result(
                    np.array2string(image[:10, :10].flatten()),  # Простий хеш
                    best_text
                )
            
            return best_text, best_conf, best_lines
            
        except Exception as e:
            logging.error(f"❌ Помилка OCR: {e}")
            return "", 0.0, []
    
    def _detect_screen_type(self, text: str, lines: List[str]) -> str:
        """Визначення типу екрану."""
        # Ігрове поле
        if any(kw in text for kw in ['полив', 'грунт', 'рослин', 'цибул', 'добрив']):
            return "gameplay"
        
        # Інвентар
        if any(kw in text for kw in ['інвентар', 'inventory', 'предмет', 'хімікат']):
            return "inventory"
        
        # Магазин
        if any(kw in text for kw in ['магазин', 'shop', 'купити', 'продати']):
            return "shop"
        
        # Меню
        if any(kw in text for kw in ['меню', 'menu', 'налаштування', 'settings']):
            return "menu"
        
        return "unknown"
    
    def _detect_parasites(self, text: str, lines: List[str]) -> List[ParasiteConfig]:
        """Покращене виявлення паразитів."""
        found = []
        
        for keyword, parasite in self.config.parasites.items():
            # Перевірка всіх варіантів назв
            for variant in parasite.name_variants:
                variant_lower = variant.lower()
                
                # Точне співпадіння
                if variant_lower in text:
                    if parasite not in found:
                        found.append(parasite)
                        logging.debug(f"🎯 Паразит '{parasite.name}' знайдено по варіанту '{variant}'")
                    break
                
                # Нечітке співпадіння (для помилок OCR)
                if self._fuzzy_match(variant_lower, text):
                    if parasite not in found:
                        found.append(parasite)
                        logging.debug(f"🎯 Паразит '{parasite.name}' знайдено (нечітке)")
                    break
        
        return found
    
    def _fuzzy_match(self, pattern: str, text: str, threshold: float = 0.8) -> bool:
        """Нечітке співпадіння для помилок OCR."""
        from difflib import SequenceMatcher
        
        # Розбиваємо на слова
        pattern_words = pattern.split()
        text_words = text.split()
        
        for pw in pattern_words:
            if len(pw) < 3:  # Пропускаємо короткі слова
                continue
            
            for tw in text_words:
                ratio = SequenceMatcher(None, pw, tw).ratio()
                if ratio >= threshold:
                    return True
        
        return False
    
    def _analyze_water_status(self, text: str, lines: List[str]) -> dict:
        """Контекстний аналіз рівня води."""
        info = {'low': False, 'amount': None, 'keywords': []}
        
        # Ключові слова про низьку воду
        low_water_keywords = [
            'мало води', 'низьк', 'недостатн', 'потрібн', 
            'треба полив', 'додати вод', 'долити',
            'water low', 'need water'
        ]
        
        for keyword in low_water_keywords:
            if keyword in text:
                info['low'] = True
                info['keywords'].append(keyword)
        
        # Парсинг кількості
        patterns = [
            r'(\d+[\.,]?\d*)\s*л',
            r'(\d+[\.,]?\d*)\s*літр',
            r'води.*?(\d+[\.,]?\d*)',
            r'налити.*?(\d+[\.,]?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    amount = float(match.group(1).replace(",", "."))
                    if 0.5 <= amount <= 10:  # Валідація
                        info['amount'] = amount
                        break
                except (ValueError, IndexError):
                    pass
        
        return info
    
    def _check_fertilizer_need(self, text: str, lines: List[str]) -> bool:
        """Перевірка потреби в добриві."""
        fertilizer_keywords = [
            'добрив', 'азотн', 'fertilizer', 'nitrogen',
            'підживлення', 'удобрение'
        ]
        
        return any(kw in text for kw in fertilizer_keywords)
    
    def _parse_soil_level(self, text: str) -> Optional[int]:
        """Парсинг рівня грунту."""
        patterns = [
            r'грунт.*?(\d+)\s*%',
            r'soil.*?(\d+)\s*%',
            r'земл.*?(\d+)\s*%'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                level = int(match.group(1))
                if 0 <= level <= 100:
                    return level
        
        return None
    
    def _detect_ui_elements(self, text: str, lines: List[str]) -> List[str]:
        """Виявлення UI елементів."""
        elements = []
        
        ui_keywords = {
            'button_watering': ['полити', 'water', 'лейка'],
            'button_chemical': ['хімікат', 'chemical', 'обробити'],
            'status_bar': ['здоров', 'health', 'енергія', 'energy'],
            'inventory': ['інвентар', 'inventory'],
        }
        
        for element_type, keywords in ui_keywords.items():
            if any(kw in text for kw in keywords):
                elements.append(element_type)
        
        return elements
    
    def _calculate_confidence(self, analysis: ScreenAnalysis) -> float:
        """Розрахунок загальної впевненості аналізу - ПОКРАЩЕНО."""
        score = 0.0
        
        # 1. БАЗОВА ВПЕВНЕНІСТЬ ВІД OCR (більш лояльно)
        if analysis.text_confidence > 0.6:  # Було 0.7
            score += 0.4  # Було 0.3
        elif analysis.text_confidence > 0.4:  # Було 0.5
            score += 0.3  # Було 0.2
        elif analysis.text_confidence > 0.2:  # Було 0.3
            score += 0.2  # Було 0.1
        
        # 2. БОНУС ЗА ТЕКСТ (якщо щось розпізнано)
        if analysis.text and len(analysis.text) > 10:
            score += 0.1  # Додатковий бонус
        
        # 3. Виявлені паразити
        if analysis.parasites_found:
            score += 0.4
        
        # 4. Низька вода
        if analysis.water_level_low:
            score += 0.2
        
        # 5. Кількість води
        if analysis.water_amount_needed:
            score += 0.1
        
        # 6. UI елементи
        if analysis.ui_elements_detected:
            score += 0.1
        
        # НОВE: Логування для діагностики
        logging.debug(f"📊 Розрахунок впевненості:")
        logging.debug(f"   • OCR: {analysis.text_confidence:.1%} → базовий score")
        logging.debug(f"   • Текст довжина: {len(analysis.text)} → +{0.1 if len(analysis.text) > 10 else 0}")
        logging.debug(f"   • Паразити: {len(analysis.parasites_found)} → +{0.4 if analysis.parasites_found else 0}")
        logging.debug(f"   • Вода: {analysis.water_level_low} → +{0.2 if analysis.water_level_low else 0}")
        logging.debug(f"   • Загальна: {min(score, 1.0):.1%}")
        
        return min(score, 1.0)
    
    def can_perform_action(self, action_key: str, cooldown: Optional[float] = None) -> bool:
        """Перевірка cooldown для дії."""
        cooldown = cooldown or self.default_cooldown
        current_time = time.time()
        
        last_time = self.action_cooldowns.get(action_key, 0)
        
        if current_time - last_time >= cooldown:
            self.action_cooldowns[action_key] = current_time
            return True
        
        remaining = cooldown - (current_time - last_time)
        logging.debug(f"⏳ Cooldown для '{action_key}': {remaining:.1f}с")
        return False
    
    def get_stats(self) -> dict:
        """Статистика аналізатора."""
        success_rate = 0
        if self.stats['scans_total'] > 0:
            success_rate = (self.stats['scans_successful'] / self.stats['scans_total']) * 100
        
        return {
            **self.stats,
            'success_rate': success_rate,
            'game_context': self.game_context.get_status_summary()
        }
    
    def log_stats(self):
        """Логування статистики."""
        stats = self.get_stats()
        
        logging.info("=" * 80)
        logging.info("📊 СТАТИСТИКА АНАЛІЗАТОРА:")
        logging.info(f"   🔍 Сканів: {stats['scans_total']} (успішних: {stats['scans_successful']}, {stats['success_rate']:.1f}%)")
        logging.info(f"   🐛 Паразитів виявлено: {stats['parasites_detected']}")
        logging.info(f"   💧 Попереджень про воду: {stats['water_warnings']}")
        logging.info(f"   ⏱️ Середній час аналізу: {stats['avg_analysis_time']*1000:.1f}ms")
        logging.info(f"   🎮 Контекст: {stats['game_context']}")
        logging.info("=" * 80)