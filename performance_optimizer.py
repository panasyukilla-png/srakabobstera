"""
performance_optimizer.py - ВИПРАВЛЕНА ВЕРСІЯ
Фікси:
1. Видалено подвійне масштабування
2. М'якша обробка для OCR
3. PNG для скріншотів замість JPEG
"""
import logging
import time
from typing import Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib

import cv2
import numpy as np
from PIL import Image
import psutil

from config import PerformanceConfig


class PerformanceOptimizer:
    """Оптимізатор з ВИПРАВЛЕННЯМИ для якісних скріншотів."""
    
    def __init__(self):
        self.config = PerformanceConfig()
        self.gpu_available = self._check_and_init_gpu()
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.CPU_THREADS)
        
        # Кеш для OCR результатів
        self.ocr_cache = {}
        self.cache_timestamps = {}
        
        # Буфер для скріншотів
        self.screenshot_buffer = []
        self.max_buffer_size = self.config.MAX_SCREENSHOTS_IN_MEMORY
        
        # Статистика
        self.stats = {
            'screenshots_saved': 0,
            'screenshots_optimized': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'gpu_operations': 0,
            'avg_process_time': 0.0,
            'total_size_saved_mb': 0.0,
        }
        
        self._log_system_info()
    
    def _check_and_init_gpu(self) -> bool:
        """Перевірка та ініціалізація GPU (CUDA)."""
        if not self.config.USE_GPU:
            logging.info("💻 GPU прискорення ВИМКНЕНО в конфігу")
            return False
        
        try:
            cuda_devices = cv2.cuda.getCudaEnabledDeviceCount()
            
            if cuda_devices > 0:
                cv2.cuda.setDevice(0)
                cv2.cuda.setGpuWorkspace(512 * 1024 * 1024)
                
                logging.info("=" * 80)
                logging.info(f"🎮 GPU АКТИВОВАНО (RTX 4070 Ti)")
                logging.info(f"   CUDA пристроїв: {cuda_devices}")
                logging.info("=" * 80)
                
                return True
            
            logging.warning("⚠️ CUDA недоступна, використовується CPU")
            return False
            
        except Exception as e:
            logging.error(f"❌ Помилка ініціалізації GPU: {e}")
            return False
    
    def _log_system_info(self):
        """Системна інформація."""
        try:
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            ram = psutil.virtual_memory()
            ram_total = ram.total / (1024**3)
            
            logging.info("=" * 80)
            logging.info("⚙️ СИСТЕМНА ІНФОРМАЦІЯ:")
            logging.info(f"   CPU: {cpu_count}P+{cpu_count_logical-cpu_count}E cores")
            logging.info(f"   RAM: {ram_total:.1f} GB")
            logging.info(f"   GPU: {'✅ CUDA' if self.gpu_available else '❌ CPU only'}")
            logging.info("=" * 80)
            
        except Exception as e:
            logging.debug(f"Помилка інфо: {e}")
    
    def optimize_screenshot(self, image: np.ndarray, for_ocr: bool = False) -> np.ndarray:
        """
        🔧 ВИПРАВЛЕНО: Розумне масштабування залежно від призначення
        
        Args:
            image: Вхідне зображення
            for_ocr: True якщо для OCR (НЕ масштабувати!), False для збереження
        """
        start_time = time.time()
        original_size = image.shape[:2]
        
        try:
            # ✅ ДЛЯ OCR - ЗАЛИШАЄМО ОРИГІНАЛЬНИЙ РОЗМІР
            if for_ocr:
                logging.debug(f"📸 OCR mode: зберігаємо оригінал {original_size[1]}x{original_size[0]}")
                return image.copy()
            
            # ✅ ДЛЯ ЗБЕРЕЖЕННЯ - масштабуємо лише якщо потрібно
            if self.config.SCREENSHOT_SCALE != 1.0:
                new_width = int(image.shape[1] * self.config.SCREENSHOT_SCALE)
                new_height = int(image.shape[0] * self.config.SCREENSHOT_SCALE)
                
                # Мінімальний розмір для читабельності: 720p
                if new_height < 720:
                    new_height = 720
                    new_width = int(new_height * image.shape[1] / image.shape[0])
                    logging.warning(f"⚠️ Підняли розмір до мінімуму: {new_width}x{new_height}")
                
                if self.gpu_available:
                    # GPU масштабування
                    gpu_img = cv2.cuda_GpuMat()
                    gpu_img.upload(image)
                    gpu_resized = cv2.cuda.resize(gpu_img, (new_width, new_height))
                    image = gpu_resized.download()
                    self.stats['gpu_operations'] += 1
                else:
                    # CPU fallback - LANCZOS для якості
                    image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
                
                reduction = (1 - (new_width * new_height) / (original_size[1] * original_size[0])) * 100
                logging.debug(f"📐 Масштабування: {original_size[1]}x{original_size[0]} → {new_width}x{new_height} (-{reduction:.1f}%)")
            
            elapsed = time.time() - start_time
            self.stats['screenshots_optimized'] += 1
            self.stats['avg_process_time'] = (self.stats['avg_process_time'] + elapsed) / 2
            
            return image
            
        except Exception as e:
            logging.error(f"❌ Помилка оптимізації: {e}")
            return image
    
    def save_screenshot_optimized(self, image: np.ndarray, path: Path) -> bool:
        """
        🔧 ВИПРАВЛЕНО: PNG замість JPEG, без подвійного масштабування
        """
        try:
            # ✅ ОДНОКРАТНЕ масштабування для збереження
            optimized = self.optimize_screenshot(image, for_ocr=False)
            
            # Конвертація BGR → RGB
            image_rgb = cv2.cvtColor(optimized, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
            
            # ✅ PNG замість JPEG - без артефактів компресії
            # Для економії місця - PNG з compression=6 (баланс)
            pil_image.save(
                path,
                format='PNG',
                compress_level=6,  # 0-9, 6 = баланс швидкість/розмір
                optimize=True
            )
            
            file_size_kb = path.stat().st_size / 1024
            self.stats['screenshots_saved'] += 1
            
            logging.debug(f"💾 Збережено: {path.name} ({file_size_kb:.0f} KB, PNG)")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Помилка збереження: {e}")
            return False
    
    def preprocess_for_ocr(self, image: np.ndarray, mode: str = 'standard') -> np.ndarray:
        """
        🔧 ВИПРАВЛЕНО: М'якша обробка, збереження деталей тексту
        
        Args:
            mode: 'light' (мінімум), 'standard' (баланс), 'aggressive' (макс)
        """
        mode = mode or self.config.OCR_PREPROCESSING
        
        try:
            # Конвертація в сірий
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # ✅ LIGHT MODE (рекомендовано для більшості випадків)
            if mode == 'light':
                # Просто CLAHE + Otsu - найкраща якість для чіткого тексту
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                _, processed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                logging.debug("📝 OCR preprocessing: LIGHT (CLAHE + Otsu)")
            
            # ✅ STANDARD MODE
            elif mode == 'standard':
                # Легкий денойзинг + CLAHE + Otsu
                denoised = cv2.fastNlMeansDenoising(gray, h=5)  # h=5 замість 10
                clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
                enhanced = clahe.apply(denoised)
                _, processed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                logging.debug("📝 OCR preprocessing: STANDARD")
            
            # ⚠️ AGGRESSIVE MODE (тільки для дуже поганих зображень)
            else:
                # Повна обробка
                denoised = cv2.fastNlMeansDenoising(gray, h=7)
                
                # Adaptive threshold замість CLAHE (краще для нерівного освітлення)
                processed = cv2.adaptiveThreshold(
                    denoised, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 11, 2
                )
                
                # М'яка морфологія
                kernel = np.ones((1, 1), np.uint8)  # 1x1 замість 2x2
                processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
                logging.debug("📝 OCR preprocessing: AGGRESSIVE")
            
            return processed
            
        except Exception as e:
            logging.error(f"❌ Помилка обробки для OCR: {e}")
            return image
    
    def cache_ocr_result(self, image_hash: str, result: str):
        """Кешування OCR."""
        if not self.config.OCR_CACHE_ENABLED:
            return
        
        self.ocr_cache[image_hash] = result
        self.cache_timestamps[image_hash] = time.time()
    
    def get_cached_ocr(self, image: np.ndarray) -> Optional[str]:
        """Отримання кешованого OCR."""
        if not self.config.OCR_CACHE_ENABLED:
            return None
        
        # Хеш зображення (тільки перші 100 пікселів для швидкості)
        sample = image[:10, :10].flatten()
        image_hash = hashlib.md5(sample.tobytes()).hexdigest()[:16]
        
        if image_hash not in self.ocr_cache:
            self.stats['cache_misses'] += 1
            return None
        
        # Перевірка TTL
        if time.time() - self.cache_timestamps[image_hash] > self.config.OCR_CACHE_TTL:
            del self.ocr_cache[image_hash]
            del self.cache_timestamps[image_hash]
            self.stats['cache_misses'] += 1
            return None
        
        self.stats['cache_hits'] += 1
        logging.debug(f"💾 Cache HIT")
        return self.ocr_cache[image_hash]
    
    def parallel_ocr(self, images: list, ocr_func, *args, **kwargs) -> list:
        """Паралельний OCR."""
        if not self.config.OCR_PARALLEL or len(images) == 1:
            return [ocr_func(img, *args, **kwargs) for img in images]
        
        try:
            futures = []
            for img in images:
                future = self.thread_pool.submit(ocr_func, img, *args, **kwargs)
                futures.append(future)
            
            return [f.result() for f in futures]
            
        except Exception as e:
            logging.error(f"❌ Помилка паралельного OCR: {e}")
            return []
    
    def get_performance_stats(self) -> dict:
        """Статистика."""
        try:
            process = psutil.Process()
            mem_info = process.memory_info()
            sys_mem = psutil.virtual_memory()
            
            cache_hit_rate = 0
            total_cache = self.stats['cache_hits'] + self.stats['cache_misses']
            if total_cache > 0:
                cache_hit_rate = (self.stats['cache_hits'] / total_cache) * 100
            
            return {
                'memory': {
                    'process_mb': mem_info.rss / (1024**2),
                    'system_available_gb': sys_mem.available / (1024**3),
                },
                'gpu': {
                    'available': self.gpu_available,
                    'operations': self.stats['gpu_operations']
                },
                'cache': {
                    'hit_rate': cache_hit_rate,
                },
                'screenshots': {
                    'saved': self.stats['screenshots_saved'],
                    'optimized': self.stats['screenshots_optimized'],
                }
            }
            
        except Exception as e:
            logging.error(f"❌ Помилка статистики: {e}")
            return {}
    
    def log_performance_stats(self):
        """Логування статистики."""
        stats = self.get_performance_stats()
        
        if not stats:
            return
        
        logging.info("=" * 80)
        logging.info("📊 СТАТИСТИКА ПРОДУКТИВНОСТІ:")
        logging.info(f"   💾 Скріншотів: {stats['screenshots']['saved']}")
        logging.info(f"   🎯 Cache hit: {stats['cache']['hit_rate']:.1f}%")
        logging.info(f"   🎮 GPU: {'✅' if stats['gpu']['available'] else '❌'} ({stats['gpu']['operations']} ops)")
        logging.info(f"   🧠 RAM: {stats['memory']['process_mb']:.1f} MB")
        logging.info("=" * 80)
    
    def cleanup_old_screenshots(self, max_age_hours: int = 24):
        """Видалення старих скріншотів."""
        try:
            from datetime import datetime, timedelta
            from config import SCREENSHOTS_DIR
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            deleted = 0
            
            for screenshot in SCREENSHOTS_DIR.glob("*.png"):
                file_time = datetime.fromtimestamp(screenshot.stat().st_mtime)
                if file_time < cutoff_time:
                    screenshot.unlink()
                    deleted += 1
            
            if deleted > 0:
                logging.info(f"🗑️ Видалено {deleted} старих скріншотів")
            
        except Exception as e:
            logging.error(f"❌ Помилка очищення: {e}")
    
    def shutdown(self):
        """Завершення."""
        try:
            self.log_performance_stats()
            self.thread_pool.shutdown(wait=True)
            logging.info("✅ Performance Optimizer завершено")
        except Exception as e:
            logging.error(f"❌ Помилка завершення: {e}")