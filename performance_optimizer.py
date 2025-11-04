"""
performance_optimizer.py - Максимальне використання RTX 4070 Ti + i5-13400F + 32GB RAM
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
    """Оптимізатор з МАКСИМАЛЬНИМ використанням GPU/CPU."""
    
    def __init__(self):
        self.config = PerformanceConfig()
        self.gpu_available = self._check_and_init_gpu()
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.CPU_THREADS)
        
        # Кеш для OCR результатів
        self.ocr_cache = {}
        self.cache_timestamps = {}
        
        # Буфер для скріншотів (обмежена пам'ять)
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
                # Отримання інформації про GPU
                cv2.cuda.printShortCudaDeviceInfo(0)
                cv2.cuda.setDevice(0)
                
                # Встановлення потоків GPU
                cv2.cuda.setGpuWorkspace(512 * 1024 * 1024)  # 512MB workspace
                
                device_name = cv2.cuda.getDevice()
                logging.info("=" * 80)
                logging.info(f"🎮 GPU АКТИВОВАНО:")
                logging.info(f"   Пристрій: {device_name}")
                logging.info(f"   CUDA пристроїв: {cuda_devices}")
                logging.info(f"   Workspace: 512 MB")
                logging.info(f"   Потоків: {self.config.GPU_THREADS}")
                logging.info("=" * 80)
                
                return True
            
            logging.warning("⚠️ CUDA недоступна, використовується CPU")
            return False
            
        except Exception as e:
            logging.error(f"❌ Помилка ініціалізації GPU: {e}")
            logging.info("💻 Fallback на CPU")
            return False
    
    def _log_system_info(self):
        """Детальна інформація про систему."""
        try:
            # CPU
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()
            
            # RAM
            ram = psutil.virtual_memory()
            ram_total = ram.total / (1024**3)
            ram_available = ram.available / (1024**3)
            
            logging.info("=" * 80)
            logging.info("⚙️ СИСТЕМНА ІНФОРМАЦІЯ:")
            logging.info(f"   CPU: i5-13400F ({cpu_count}P+{cpu_count_logical-cpu_count}E cores)")
            logging.info(f"   CPU частота: {cpu_freq.current:.0f} MHz (max: {cpu_freq.max:.0f} MHz)")
            logging.info(f"   RAM: {ram_total:.1f} GB (доступно: {ram_available:.1f} GB)")
            logging.info(f"   Потоків для обробки: {self.config.CPU_THREADS}")
            logging.info(f"   GPU: {'✅ RTX 4070 Ti (CUDA)' if self.gpu_available else '❌ Недоступний'}")
            logging.info("=" * 80)
            
        except Exception as e:
            logging.debug(f"Помилка отримання системної інформації: {e}")
    
    def optimize_screenshot(self, image: np.ndarray) -> np.ndarray:
        """
        Оптимізація скріншоту з GPU прискоренням.
        
        Масштабування 1080p -> 540p = -75% розміру
        """
        start_time = time.time()
        original_size = image.shape[:2]
        
        try:
            if self.gpu_available and self.config.SCREENSHOT_SCALE != 1.0:
                # GPU прискорене масштабування
                gpu_img = cv2.cuda_GpuMat()
                gpu_img.upload(image)
                
                new_width = int(image.shape[1] * self.config.SCREENSHOT_SCALE)
                new_height = int(image.shape[0] * self.config.SCREENSHOT_SCALE)
                
                gpu_resized = cv2.cuda.resize(gpu_img, (new_width, new_height))
                image = gpu_resized.download()
                
                self.stats['gpu_operations'] += 1
                
                reduction = (1 - (image.shape[0] * image.shape[1]) / (original_size[0] * original_size[1])) * 100
                logging.debug(f"🎮 GPU масштабування: {original_size[1]}x{original_size[0]} -> {new_width}x{new_height} (-{reduction:.1f}%)")
                
            elif self.config.SCREENSHOT_SCALE != 1.0:
                # CPU fallback
                new_width = int(image.shape[1] * self.config.SCREENSHOT_SCALE)
                new_height = int(image.shape[0] * self.config.SCREENSHOT_SCALE)
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logging.debug(f"💻 CPU масштабування: {new_width}x{new_height}")
            
            # Легке підвищення різкості після масштабування
            if self.config.SCREENSHOT_SCALE < 1.0:
                kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]) * 0.3
                image = cv2.filter2D(image, -1, kernel)
            
            elapsed = time.time() - start_time
            self.stats['screenshots_optimized'] += 1
            self.stats['avg_process_time'] = (self.stats['avg_process_time'] + elapsed) / 2
            
            logging.debug(f"⚡ Оптимізація: {elapsed*1000:.1f}ms")
            
            return image
            
        except Exception as e:
            logging.error(f"❌ Помилка оптимізації: {e}")
            return image
    
    def save_screenshot_optimized(self, image: np.ndarray, path: Path) -> bool:
        """
        Збереження з максимальним стисненням.
        
        PNG 1920x1080 ~5MB -> JPEG 960x540 ~50KB = -99% розміру!
        """
        try:
            # Оптимізація перед збереженням
            optimized = self.optimize_screenshot(image)
            
            # Конвертація BGR -> RGB
            image_rgb = cv2.cvtColor(optimized, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
            
            # Розрахунок розміру до збереження
            original_estimate = image.shape[0] * image.shape[1] * 3 / (1024**2)  # MB
            
            # Збереження як JPEG
            pil_image.save(
                path,
                format=self.config.SCREENSHOT_FORMAT,
                quality=self.config.SCREENSHOT_QUALITY,
                optimize=True,
                progressive=True
            )
            
            # Статистика
            file_size_kb = path.stat().st_size / 1024
            file_size_mb = file_size_kb / 1024
            saved_mb = original_estimate - file_size_mb
            
            self.stats['screenshots_saved'] += 1
            self.stats['total_size_saved_mb'] += saved_mb
            
            logging.debug(f"💾 Збережено: {path.name} ({file_size_kb:.0f} KB, економія: {saved_mb:.2f} MB)")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Помилка збереження: {e}")
            return False
    
    def preprocess_for_ocr(self, image: np.ndarray, mode: str = None) -> np.ndarray:
        """
        Агресивна підготовка для OCR з GPU.
        
        Args:
            mode: 'aggressive', 'standard', 'light' (або з конфігу)
        """
        mode = mode or self.config.OCR_PREPROCESSING
        
        try:
            # Конвертація в сірий
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            if self.gpu_available:
                # GPU обробка
                gpu_img = cv2.cuda_GpuMat()
                gpu_img.upload(gray)
                
                if mode == 'aggressive':
                    # 1. Денойзинг (GPU)
                    gpu_filter = cv2.cuda.createNonLocalMeansDenoising(10, 7, 21)
                    gpu_denoised = gpu_filter.apply(gpu_img)
                    
                    # 2. Адаптивна бінаризація (потрібно на CPU)
                    denoised = gpu_denoised.download()
                    binary = cv2.adaptiveThreshold(
                        denoised, 255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY, 11, 2
                    )
                    
                    # 3. Морфологія
                    kernel = np.ones((2, 2), np.uint8)
                    processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
                    
                elif mode == 'standard':
                    # CLAHE (потрібно на CPU)
                    gray_cpu = gpu_img.download()
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    enhanced = clahe.apply(gray_cpu)
                    _, processed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    
                else:  # light
                    gray_cpu = gpu_img.download()
                    _, processed = cv2.threshold(gray_cpu, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                self.stats['gpu_operations'] += 1
                
            else:
                # CPU обробка
                if mode == 'aggressive':
                    denoised = cv2.fastNlMeansDenoising(gray, h=10)
                    binary = cv2.adaptiveThreshold(
                        denoised, 255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY, 11, 2
                    )
                    kernel = np.ones((2, 2), np.uint8)
                    processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
                    
                elif mode == 'standard':
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    enhanced = clahe.apply(gray)
                    _, processed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    
                else:  # light
                    _, processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return processed
            
        except Exception as e:
            logging.error(f"❌ Помилка обробки для OCR: {e}")
            return image
    
    def cache_ocr_result(self, image_hash: str, result: str):
        """Кешування OCR з TTL."""
        if not self.config.OCR_CACHE_ENABLED:
            return
        
        self.ocr_cache[image_hash] = result
        self.cache_timestamps[image_hash] = time.time()
    
    def get_cached_ocr(self, image: np.ndarray) -> Optional[str]:
        """Отримання кешованого OCR."""
        if not self.config.OCR_CACHE_ENABLED:
            return None
        
        # Хеш зображення
        image_hash = hashlib.md5(image.tobytes()).hexdigest()[:16]
        
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
        logging.debug(f"💾 Cache HIT для {image_hash}")
        return self.ocr_cache[image_hash]
    
    def parallel_ocr(self, images: list, ocr_func, *args, **kwargs) -> list:
        """Паралельний OCR на всіх CPU потоках."""
        if not self.config.OCR_PARALLEL or len(images) == 1:
            return [ocr_func(img, *args, **kwargs) for img in images]
        
        try:
            logging.debug(f"🧵 Паралельний OCR: {len(images)} зображень на {self.config.CPU_THREADS} потоках")
            
            futures = []
            for img in images:
                future = self.thread_pool.submit(ocr_func, img, *args, **kwargs)
                futures.append(future)
            
            results = [f.result() for f in futures]
            return results
            
        except Exception as e:
            logging.error(f"❌ Помилка паралельного OCR: {e}")
            return []
    
    def get_performance_stats(self) -> dict:
        """Детальна статистика продуктивності."""
        try:
            # Пам'ять процесу
            process = psutil.Process()
            mem_info = process.memory_info()
            
            # Системна пам'ять
            sys_mem = psutil.virtual_memory()
            
            # CPU
            cpu_percent = process.cpu_percent(interval=0.1)
            
            # Кеш
            cache_hit_rate = 0
            total_cache = self.stats['cache_hits'] + self.stats['cache_misses']
            if total_cache > 0:
                cache_hit_rate = (self.stats['cache_hits'] / total_cache) * 100
            
            return {
                'memory': {
                    'process_mb': mem_info.rss / (1024**2),
                    'process_percent': process.memory_percent(),
                    'system_total_gb': sys_mem.total / (1024**3),
                    'system_available_gb': sys_mem.available / (1024**3),
                    'system_percent': sys_mem.percent
                },
                'cpu': {
                    'process_percent': cpu_percent,
                    'system_percent': psutil.cpu_percent(interval=0.1),
                    'threads_used': self.config.CPU_THREADS
                },
                'gpu': {
                    'available': self.gpu_available,
                    'operations': self.stats['gpu_operations']
                },
                'cache': {
                    'hit_rate': cache_hit_rate,
                    'hits': self.stats['cache_hits'],
                    'misses': self.stats['cache_misses']
                },
                'screenshots': {
                    'saved': self.stats['screenshots_saved'],
                    'optimized': self.stats['screenshots_optimized'],
                    'total_size_saved_mb': self.stats['total_size_saved_mb']
                },
                'performance': {
                    'avg_process_time_ms': self.stats['avg_process_time'] * 1000
                }
            }
            
        except Exception as e:
            logging.error(f"❌ Помилка отримання статистики: {e}")
            return {}
    
    def log_performance_stats(self):
        """Логування статистики."""
        stats = self.get_performance_stats()
        
        if not stats:
            return
        
        logging.info("=" * 80)
        logging.info("📊 СТАТИСТИКА ПРОДУКТИВНОСТІ:")
        logging.info(f"   💾 Скріншотів: {stats['screenshots']['saved']} (оптимізовано: {stats['screenshots']['optimized']})")
        logging.info(f"   💰 Економія простору: {stats['screenshots']['total_size_saved_mb']:.1f} MB")
        logging.info(f"   🎯 Cache hit rate: {stats['cache']['hit_rate']:.1f}% ({stats['cache']['hits']}/{stats['cache']['hits'] + stats['cache']['misses']})")
        logging.info(f"   🎮 GPU операцій: {stats['gpu']['operations']} {'✅' if stats['gpu']['available'] else '❌ (недоступний)'}")
        logging.info(f"   🧠 Пам'ять процесу: {stats['memory']['process_mb']:.1f} MB ({stats['memory']['process_percent']:.1f}%)")
        logging.info(f"   🖥️ Системна пам'ять: {stats['memory']['system_percent']:.1f}% ({stats['memory']['system_available_gb']:.1f}/{stats['memory']['system_total_gb']:.1f} GB доступно)")
        logging.info(f"   ⚡ CPU процесу: {stats['cpu']['process_percent']:.1f}% (система: {stats['cpu']['system_percent']:.1f}%)")
        logging.info(f"   ⏱️ Середній час обробки: {stats['performance']['avg_process_time_ms']:.1f}ms")
        logging.info("=" * 80)
    
    def cleanup_old_screenshots(self, max_age_hours: int = 24):
        """Видалення старих скріншотів."""
        try:
            from datetime import datetime, timedelta
            from config import SCREENSHOTS_DIR
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            deleted = 0
            freed_mb = 0
            
            for screenshot in SCREENSHOTS_DIR.glob("*.jpg"):
                file_time = datetime.fromtimestamp(screenshot.stat().st_mtime)
                if file_time < cutoff_time:
                    size_mb = screenshot.stat().st_size / (1024**2)
                    screenshot.unlink()
                    deleted += 1
                    freed_mb += size_mb
            
            if deleted > 0:
                logging.info(f"🗑️ Видалено {deleted} старих скріншотів ({freed_mb:.1f} MB)")
            
        except Exception as e:
            logging.error(f"❌ Помилка очищення скріншотів: {e}")
    
    def shutdown(self):
        """Завершення роботи."""
        try:
            self.log_performance_stats()
            self.thread_pool.shutdown(wait=True)
            self.cleanup_old_screenshots()
            logging.info("✅ Performance Optimizer завершено")
        except Exception as e:
            logging.error(f"❌ Помилка завершення: {e}")