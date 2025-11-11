"""
Módulo de caché para optimización de procesamiento.
"""

from .ocr_cache import OCRCache, CachedHybridExtractor, create_cached_extractor

__all__ = [
    'OCRCache',
    'CachedHybridExtractor',
    'create_cached_extractor'
]
