"""
debug_ocr_output.py - Дебаг скрипт для перегляду що саме бачить бот

Запуск: python debug_ocr_output.py
"""
import time
import logging
from pathlib import Path

from config import TaskConfig, setup_enhanced_logging
from analyzer import SmartAnalyzer
from window_manager import WindowManager
from performance_optimizer import PerformanceOptimizer

# Налаштування логування
setup_enhanced_logging(level=logging.INFO)

def main():
    print("\n" + "="*80)
    print("🔍 DEBUG: Що бачить бот?")
    print("="*80 + "\n")
    
    # Ініціалізація
    config = TaskConfig()
    perf_optimizer = PerformanceOptimizer()
    window_manager = WindowManager("amazing.exe")
    
    # Спроба знайти вікно
    if window_manager.find_game_window():
        print(f"✅ Вікно знайдено: {window_manager.game_window.title}")
        window_manager.restore_and_focus()
        time.sleep(1)
    else:
        print("⚠️ Вікно гри не знайдено, працюємо на всьому екрані")
    
    analyzer = SmartAnalyzer(
        config=config,
        window_manager=window_manager,
        performance_optimizer=perf_optimizer
    )
    
    # Автовиявлення області
    analyzer.auto_detect_game_ui()
    
    print("\n🎯 Починаємо аналіз через 2 секунди...")
    print("📍 Переконайся що гра відкрита і на екрані видно текст\n")
    time.sleep(2)
    
    # Аналіз
    print("📸 Захоплення екрану...")
    analysis = analyzer.analyze_screen(save_screenshot=True)
    
    print("\n" + "="*80)
    print("📊 РЕЗУЛЬТАТИ АНАЛІЗУ:")
    print("="*80)
    
    # Основна інформація
    print(f"\n📝 OCR впевненість: {analysis.text_confidence:.1%}")
    print(f"🎯 Загальна впевненість: {analysis.confidence:.1%}")
    print(f"📱 Тип екрану: {analysis.current_screen}")
    
    # Розпізнаний текст
    print(f"\n📄 РОЗПІЗНАНИЙ ТЕКСТ ({len(analysis.text)} символів):")
    print("-" * 80)
    if analysis.text:
        # Показуємо перші 500 символів
        preview = analysis.text[:500]
        print(preview)
        if len(analysis.text) > 500:
            print(f"\n... (ще {len(analysis.text) - 500} символів)")
    else:
        print("⚠️ ТЕКСТ НЕ РОЗПІЗНАНО!")
    
    # По рядках
    if analysis.text_lines:
        print(f"\n📋 РЯДКИ ТЕКСТУ ({len(analysis.text_lines)} шт):")
        print("-" * 80)
        for i, line in enumerate(analysis.text_lines[:20], 1):  # Перші 20
            if line.strip():
                print(f"{i:2d}. {line[:70]}")
        if len(analysis.text_lines) > 20:
            print(f"... (ще {len(analysis.text_lines) - 20} рядків)")
    
    # Пошук паразитів
    print(f"\n🐛 ПАРАЗИТИ:")
    print("-" * 80)
    if analysis.parasites_found:
        for p in analysis.parasites_found:
            print(f"  ✅ {p.name} (клавіша: {p.key}, категорія: {p.category})")
    else:
        print("  ❌ Паразитів не виявлено")
        
        # Спробуємо знайти вручну
        text_lower = analysis.text.lower()
        print("\n  🔍 Ручний пошук паразитів в тексті:")
        
        parasite_keywords = {
            'тля': 'ТЛЯ',
            'слизни': 'ГОЛЫЕ СЛИЗНИ',
            'колорадский': 'КОЛОРАДСКИЙ ЖУК',
            'щелкун': 'ЖУК-ЩЕЛКУН',
            'кравчик': 'КРАВЧИК-ГОЛОВАЧ',
            'медведка': 'МЕДВЕДКА',
            'проволочник': 'ПРОВОЛОЧНИК',
            'нематода': 'ГАЛЛОВА НЕМАТОДА',
            'трипс': 'ТРИПС',
            'клещ': 'ПАУТИННЫЙ КЛЕЩ',
        }
        
        found_manual = []
        for keyword, name in parasite_keywords.items():
            if keyword in text_lower:
                found_manual.append(name)
                # Знайти контекст
                idx = text_lower.find(keyword)
                context_start = max(0, idx - 20)
                context_end = min(len(text_lower), idx + len(keyword) + 20)
                context = analysis.text[context_start:context_end]
                print(f"    • '{keyword}' → {name}")
                print(f"      Контекст: ...{context}...")
        
        if not found_manual:
            print("    ❌ Жодного ключового слова не знайдено")
    
    # Вода
    print(f"\n💧 ВОДА:")
    print("-" * 80)
    if analysis.water_level_low:
        print(f"  ⚠️ НИЗЬКИЙ РІВЕНЬ")
        if analysis.water_amount_needed:
            print(f"  📊 Потрібно: {analysis.water_amount_needed:.1f}л")
    else:
        print("  ✅ Рівень нормальний")
        
        # Ручний пошук
        text_lower = analysis.text.lower()
        water_keywords = ['вода', 'води', 'полив', 'налити', 'літр', 'water']
        found_water = [kw for kw in water_keywords if kw in text_lower]
        
        if found_water:
            print(f"  🔍 Знайдені слова про воду: {', '.join(found_water)}")
        else:
            print("  ❌ Слів про воду не знайдено")
    
    # Добриво
    print(f"\n🌱 ДОБРИВО:")
    print("-" * 80)
    if analysis.needs_fertilizer:
        print("  ✅ Потрібне")
    else:
        print("  ❌ Не потрібне")
    
    # Грунт
    if analysis.soil_level:
        print(f"\n🌍 ГРУНТ: {analysis.soil_level}%")
    
    # UI елементи
    if analysis.ui_elements_detected:
        print(f"\n🎮 UI ЕЛЕМЕНТИ:")
        print("-" * 80)
        for elem in analysis.ui_elements_detected:
            print(f"  • {elem}")
    
    # Скріншот
    if analysis.screenshot_path:
        print(f"\n📸 СКРІНШОТ: {analysis.screenshot_path}")
        print(f"   Розмір файлу: {analysis.screenshot_path.stat().st_size / 1024:.1f} KB")
    
    # Підсумок
    print("\n" + "="*80)
    print("📊 ПІДСУМОК:")
    print("="*80)
    print(analysis.get_summary())
    
    # Рекомендації
    print("\n" + "="*80)
    print("💡 РЕКОМЕНДАЦІЇ:")
    print("="*80)
    
    if analysis.text_confidence < 0.5:
        print("⚠️ НИЗЬКА ЯКІСТЬ OCR (<50%):")
        print("  1. Перевір чи на екрані видно текст (не меню, не чорний екран)")
        print("  2. Збільш шрифт в грі (якщо є налаштування)")
        print("  3. Перевір роздільність гри (мінімум 1080p)")
        print("  4. Встанови мовні пакети Tesseract: ukr, rus, eng")
    
    if not analysis.parasites_found and analysis.text_confidence > 0.5:
        print("⚠️ ТЕКСТ РОЗПІЗНАЄТЬСЯ, АЛЕ ПАРАЗИТИ НЕ ЗНАЙДЕНІ:")
        print("  1. Можливо на екрані немає паразитів (це нормально)")
        print("  2. Перевір чи правильно написані назви в tasks.txt")
        print("  3. Подивись 'РУЧНИЙ ПОШУК' вище - чи є схожі слова?")
    
    if analysis.confidence < 0.3:
        print("⚠️ ЗАГАЛЬНА ВПЕВНЕНІСТЬ ДУЖЕ НИЗЬКА (<30%):")
        print("  1. Можливо захоплюється не та область екрану")
        print("  2. Спробуй встановити область вручну через GUI")
        print("  3. Перевір скріншот - чи на ньому гра чи щось інше")
    
    print("\n" + "="*80)
    print("✅ Дебаг завершено!")
    print("="*80)
    
    # Статистика аналізатора
    print("\n📊 Статистика аналізатора:")
    stats = analyzer.get_stats()
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            print(f"   {key}: {value}")
        else:
            print(f"   {key}: {value}")

if __name__ == "__main__":
    main()