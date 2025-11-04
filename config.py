"""
config.py - Конфігурація бота з оптимізацією
"""
import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from pathlib import Path


# ======================== ШЛЯХИ ========================
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
LOGS_DIR = Path("logs")
SCREENSHOTS_DIR = LOGS_DIR / "screenshots"
CONFIG_FILE = Path("tasks.txt")
DATA_DIR = Path("data")

# Створення директорій
LOGS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


# ======================== НАЛАШТУВАННЯ ПРОДУКТИВНОСТІ ========================
class PerformanceConfig:
    """Налаштування продуктивності для RTX 4070 Ti + i5-13400F + 32GB RAM."""
    
    # GPU налаштування
    USE_GPU = True  # Використання CUDA для OpenCV
    GPU_THREADS = 8  # Потоки для GPU операцій
    
    # CPU налаштування  
    CPU_THREADS = 12  # i5-13400F має 10 ядер (6P+4E), використовуємо 12 потоків
    OCR_PARALLEL = True  # Паралельний OCR
    
    # Скріншоти
    SCREENSHOT_SCALE = 0.5  # 50% розміру для економії (1080p -> 540p)
    SCREENSHOT_QUALITY = 70  # JPEG якість (70 = баланс якості/розміру)
    SCREENSHOT_FORMAT = 'JPEG'  # Формат (JPEG замість PNG)
    
    # OCR оптимізація
    OCR_PREPROCESSING = 'aggressive'  # aggressive/standard/light
    OCR_CACHE_ENABLED = True
    OCR_CACHE_TTL = 3.0  # Кеш на 3 секунди
    
    # Пам'ять
    MAX_SCREENSHOTS_IN_MEMORY = 5  # Максимум скріншотів в RAM
    CLEANUP_INTERVAL = 300  # Очищення старих скріншотів кожні 5 хв


# ======================== ДАТА-КЛАСИ ========================
@dataclass
class ParasiteConfig:
    """Конфігурація для паразита."""
    name: str
    name_variants: List[str]  # Варіанти назв для розпізнавання
    water_amount: Tuple[float, float]
    duration: int
    key: str
    category: str
    icon_path: str = ""  # Шлях до іконки в data/


@dataclass
class TaskConfig:
    """Конфігурація завдань з tasks.txt."""
    parasites: Dict[str, ParasiteConfig] = field(default_factory=dict)
    watering_amount: float = 5.0
    fertilizer_amount: float = 0.95
    water_range: Tuple[float, float] = (5.0, 7.0)
    soil_percentage: int = 85
    watering_interval: int = 300
    
    # Нові параметри для автономності
    auto_walk: bool = True  # Автоматична ходьба до рослин
    auto_refill_water: bool = True  # Автопоповнення води
    check_water_every: int = 5  # Перевірка води кожні 5 поливів
    
    # Window management
    window_process_name: str = "amazing.exe"
    focus_game_window: bool = True


# ======================== ПАРСЕР КОНФІГУРАЦІЇ ========================
class ConfigParser:
    """Парсер tasks.txt з покращеною логікою."""
    
    @staticmethod
    def parse(file_path: Path) -> TaskConfig:
        """Парсинг конфігураційного файла."""
        config = TaskConfig()
        
        if not file_path.exists():
            logging.warning(f"Файл {file_path} не знайдено, створюємо новий")
            ConfigParser._create_default_config(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Парсинг паразитів з іконками
            parasites_data = {
                "тля": ParasiteConfig(
                    "ТЛЯ",
                    ["тля", "тли", "tля", "tli", "aphid", "тл", "тлi"],
                    (2.0, 2.4), 120, "2", "біологічні",
                    icon_path="data/chemicals.png"  # Загальна іконка хімікатів
                ),
                "слизни": ParasiteConfig(
                    "ГОЛЫЕ СЛИЗНИ",
                    ["голые слизни", "слизни", "голі слизні", "слизень", "slug", "slugs", "голi слизнi"],
                    (2.0, 2.4), 120, "3", "біологічні",
                    icon_path="data/chemicals.png"
                ),
                "колорадський": ParasiteConfig(
                    "КОЛОРАДСКИЙ ЖУК",
                    ["колорадский жук", "колорадський жук", "жук", "colorado beetle", "beetle", "колорадський"],
                    (2.0, 2.4), 120, "4", "біологічні",
                    icon_path="data/chemicals.png"
                ),
                "щелкун": ParasiteConfig(
                    "ЖУК-ЩЕЛКУН",
                    ["жук-щелкун", "щелкун", "жук щелкун", "click beetle", "щелкун"],
                    (1.0, 1.6), 80, "1", "системні",
                    icon_path="data/chemicals.png"
                ),
                "кравчик": ParasiteConfig(
                    "КРАВЧИК-ГОЛОВАЧ",
                    ["кравчик-головач", "кравчик", "головач", "kravchyk", "кравчик"],
                    (1.0, 1.6), 80, "1", "системні",
                    icon_path="data/chemicals.png"
                ),
                "медведка": ParasiteConfig(
                    "МЕДВЕДКА",
                    ["медведка", "медведь", "mole cricket", "медвiдка"],
                    (4.0, 4.7), 120, "5", "кишкові",
                    icon_path="data/chemicals.png"
                ),
                "проволочник": ParasiteConfig(
                    "ПРОВОЛОЧНИК",
                    ["проволочник", "проволочник", "wireworm", "проволочнiк"],
                    (4.0, 4.7), 120, "6", "кишкові",
                    icon_path="data/chemicals.png"
                ),
                "нематода": ParasiteConfig(
                    "ГАЛЛОВА НЕМАТОДА",
                    ["нематода", "галлова нематода", "галова", "nematode", "галлова", "нематода"],
                    (4.0, 4.7), 120, "7", "кишкові",
                    icon_path="data/chemicals.png"
                ),
                "трипс": ParasiteConfig(
                    "ТРИПС",
                    ["трипс", "трипси", "thrips", "трiпс"],
                    (3.0, 3.5), 150, "8", "контактні",
                    icon_path="data/chemicals.png"
                ),
                "клещ": ParasiteConfig(
                    "ПАУТИННЫЙ КЛЕЩ",
                    ["паутинный клещ", "павутинний кліщ", "клещ", "кліщ", "spider mite", "mite", "павутинний"],
                    (3.0, 3.5), 150, "9", "контактні",
                    icon_path="data/chemicals.png"
                ),
            }
            
            config.parasites = parasites_data
            
            # Парсинг параметрів з файлу
            content_lower = content.lower()
            
            water_match = re.search(r'вода:\s*(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', content_lower)
            if water_match:
                config.water_range = (float(water_match.group(1)), float(water_match.group(2)))
                logging.info(f"📌 Діапазон води: {config.water_range[0]}-{config.water_range[1]}л")
            
            fertilizer_match = re.search(r'(\d+\.?\d*)\s*л\s+води\s+з\s+добривом', content_lower)
            if fertilizer_match:
                config.fertilizer_amount = float(fertilizer_match.group(1))
                logging.info(f"📌 Кількість з добривом: {config.fertilizer_amount}л")
            
            watering_match = re.search(r'поливаємо.*?(\d+\.?\d*)\s*літрами', content_lower)
            if watering_match:
                config.watering_amount = float(watering_match.group(1))
                logging.info(f"📌 Базовий полив: {config.watering_amount}л")
            
            soil_match = re.search(r'грунт:\s*(\d+)', content_lower)
            if soil_match:
                config.soil_percentage = int(soil_match.group(1))
                logging.info(f"📌 Грунт: {config.soil_percentage}%")
            
            logging.info(f"✅ Конфігурацію завантажено: {len(config.parasites)} паразитів")
            
        except Exception as e:
            logging.error(f"❌ Помилка парсингу конфігурації: {e}", exc_info=True)
        
        return config
    
    @staticmethod
    def _create_default_config(file_path: Path):
        """Створення стандартного конфігураційного файла."""
        default_config = """# Plant Care Bot - Конфігурація завдань

# БАЗОВІ ІНСТРУКЦІЇ:
# 1) Садимо цибулю
# 2) Поливаємо кожну цибулю 5 літрами води без добрива
# 3) На кожну цибулю по 0.95л води з добривом, 1 ходка в 4-6 хвилин
# 4) Якщо води мало але є паразити - спочатку травимо паразитів
# 5) Вода: 5-7 літрів. Грунт: 85%.
# 6) Після паразитів - ОБОВ'ЯЗКОВО поливати БЕЗ добрива
# 7) Перевіряти рівень води в лейці кожні 5 поливів

# ХІМІКАТИ:
# Біологічні (2.0-2.4л, 120с): ТЛЯ [2], ГОЛЫЕ СЛИЗНИ [3], КОЛОРАДСКИЙ ЖУК [4]
# Системні (1.0-1.6л, 80с): ЖУК-ЩЕЛКУН [1], КРАВЧИК-ГОЛОВАЧ [1]
# Кишкові (4.0-4.7л, 120с): МЕДВЕДКА [5], ПРОВОЛОЧНИК [6], ГАЛЛОВА НЕМАТОДА [7]
# Контактні (3.0-3.5л, 150с): ТРИПС [8], ПАУТИННЫЙ КЛЕЩ [9]

# АВТОМАТИЗАЦІЯ:
# Автоходьба: ТАК
# Автопоповнення води: ТАК
# Перевірка води кожні N поливів: 5
"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(default_config)
            logging.info(f"✅ Створено стандартний конфіг: {file_path}")
        except Exception as e:
            logging.error(f"❌ Помилка створення конфігу: {e}")


# ======================== ЛОГУВАННЯ ========================
def setup_enhanced_logging(level=logging.INFO):
    """Покращене логування з кольорами та деталями."""
    
    # Кольорові коди для консолі (Windows)
    class ColoredFormatter(logging.Formatter):
        """Форматер з кольорами."""
        
        COLORS = {
            'DEBUG': '\033[36m',     # Cyan
            'INFO': '\033[32m',      # Green
            'WARNING': '\033[33m',   # Yellow
            'ERROR': '\033[31m',     # Red
            'CRITICAL': '\033[35m',  # Magenta
            'RESET': '\033[0m'
        }
        
        def format(self, record):
            # Додаємо емодзі для швидкої ідентифікації
            emoji_map = {
                'DEBUG': '🔧',
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }
            
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            emoji = emoji_map.get(record.levelname, '•')
            
            # Форматування часу
            record.asctime = self.formatTime(record, '%H:%M:%S')
            
            # Додаємо інформацію про модуль
            module_info = f"{record.module}:{record.lineno}"
            
            formatted = f"{color}{emoji} [{record.asctime}] {record.levelname:8s} [{module_info}] {record.getMessage()}{self.COLORS['RESET']}"
            
            return formatted
    
    # Налаштування хендлерів
    from datetime import datetime
    log_file = LOGS_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Консольний хендлер з кольорами
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    
    # Файловий хендлер (без кольорів)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Файл завжди DEBUG
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(module)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Базове налаштування
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[console_handler, file_handler]
    )
    
    logging.info("=" * 80)
    logging.info("🌱 Plant Care Bot v2.1 - ENHANCED EDITION")
    logging.info("=" * 80)
    logging.info(f"💾 Логи зберігаються в: {log_file}")
    logging.info(f"📸 Скріншоти: {SCREENSHOTS_DIR}")
    logging.info(f"⚙️ Конфіг: {CONFIG_FILE}")
    logging.info(f"🎮 GPU прискорення: {'✅ УВІМКНЕНО' if PerformanceConfig.USE_GPU else '❌ ВИМКНЕНО'}")
    logging.info(f"🧵 CPU потоків: {PerformanceConfig.CPU_THREADS}")
    logging.info("=" * 80)