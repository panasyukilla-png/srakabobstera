"""
main.py - Plant Care Bot v2.1 ENHANCED - Головний файл запуску
"""
import sys
import logging
from pathlib import Path
from tkinter import messagebox

from config import TESSERACT_PATH, setup_enhanced_logging
from bot import PlantCareBot
from gui import GamingGUI


# ======================== ПЕРЕВІРКА СИСТЕМИ ========================
def check_system_requirements() -> bool:
    """Перевірка системних вимог."""
    errors = []
    
    # Перевірка Tesseract
    if not Path(TESSERACT_PATH).exists():
        errors.append(
            f"❌ Tesseract OCR не знайдено:\n{TESSERACT_PATH}\n\n"
            "Завантажте з: https://github.com/UB-Mannheim/tesseract/wiki"
        )
    
    # Перевірка папки data
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir(exist_ok=True)
        logging.warning("⚠️ Створено папку 'data' для шаблонів")
        logging.info("💡 Додайте файли: chemicals.png, full_leyka.png, empty_leyka.png")
    
    # Перевірка OpenCV CUDA (опціонально)
    try:
        import cv2
        cuda_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
        if cuda_available:
            logging.info("✅ OpenCV CUDA доступний - GPU прискорення активне!")
        else:
            logging.warning("⚠️ OpenCV CUDA недоступний - використовується CPU")
            logging.info("💡 Для GPU прискорення встановіть: pip install opencv-contrib-python")
    except Exception as e:
        logging.debug(f"CUDA перевірка: {e}")
    
    # Якщо є помилки - виводимо
    if errors:
        error_msg = "\n\n".join(errors)
        logging.error(error_msg)
        
        if 'pytest' not in sys.modules:  # Не показувати messagebox в тестах
            messagebox.showerror("Помилка системи", error_msg)
        
        return False
    
    return True


# ======================== ГОЛОВНА ФУНКЦІЯ ========================
def main():
    """Головна функція запуску."""
    print("\n" + "=" * 80)
    print("🌱 PLANT CARE BOT v2.1 ENHANCED EDITION")
    print("🎮 GPU/CPU оптимізований | Розумний аналіз | Повна автономність")
    print("=" * 80 + "\n")
    
    try:
        # Налаштування логування
        setup_enhanced_logging(level=logging.INFO)
        
        # Перевірка системи
        logging.info("🔍 Перевірка системних вимог...")
        if not check_system_requirements():
            logging.error("❌ Системні вимоги не виконані")
            input("\nНатисніть Enter для виходу...")
            return 1
        
        logging.info("✅ Системні вимоги виконані")
        
        # Створення бота
        logging.info("🔧 Ініціалізація Plant Care Bot...")
        bot = PlantCareBot()
        
        # Створення GUI
        logging.info("🎨 Ініціалізація графічного інтерфейсу...")
        gui = GamingGUI(bot)
        
        logging.info("✅ Систему запущено успішно!")
        logging.info("=" * 80)
        logging.info("💡 ПОРАДИ ДЛЯ ПОЧАТКУ:")
        logging.info("   1. Натисніть 'СТАРТ' для запуску моніторингу")
        logging.info("   2. Встановіть 'ТОЧКУ ПОЛИВУ' через GUI")
        logging.info("   3. Бот автоматично аналізує нижню 50% екрану")
        logging.info("   4. Для зміни області натисніть 'ОБЛАСТЬ'")
        logging.info("=" * 80)
        
        # Запуск GUI (блокуючий виклик)
        gui.run()
        
        logging.info("👋 Завершення програми")
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ Перервано користувачем (Ctrl+C)")
        logging.info("⚠️ Перервано користувачем")
        return 130
        
    except Exception as e:
        error_msg = f"❌ Критична помилка: {e}"
        logging.error(error_msg, exc_info=True)
        
        if 'pytest' not in sys.modules:
            messagebox.showerror("Критична помилка", error_msg)
        
        return 1
        
    finally:
        # Очищення ресурсів
        try:
            if 'bot' in locals() and bot._running:
                logging.info("🛑 Зупинка бота...")
                bot.stop()
        except Exception as e:
            logging.error(f"Помилка зупинки: {e}")
        
        logging.info("=" * 80)
        logging.info("✅ Plant Care Bot завершено")
        logging.info("=" * 80)


# ======================== ТОЧКА ВХОДУ ========================
if __name__ == "__main__":
    sys.exit(main())