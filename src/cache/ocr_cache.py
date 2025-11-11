"""
Sistema de caché para resultados OCR.

Mejora el rendimiento en:
- Regeneración de datasets con diferentes configuraciones
- Procesamiento incremental de documentos
- Experimentos con diferentes umbrales de matching

El cache guarda resultados OCR por (pdf_path, page_num, hash_imagen).
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OCRCache:
    """
    Cache persistente para resultados OCR.

    Evita reprocesar PDFs que ya fueron extraídos con OCR.
    Ahorra 3-5 segundos por página en PDFs rasterizados.
    """

    def __init__(self, cache_dir: str = ".cache/ocr"):
        """
        Inicializa cache de OCR.

        Args:
            cache_dir: Directorio donde guardar cache
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Estadísticas
        self.stats = {
            'hits': 0,
            'misses': 0,
            'saves': 0
        }

        logger.info(f"OCR cache inicializado en: {self.cache_dir}")

    def _get_cache_key(
        self,
        pdf_path: str,
        page_num: int,
        image_hash: Optional[str] = None
    ) -> str:
        """
        Genera clave única para entrada de cache.

        Args:
            pdf_path: Ruta al PDF
            page_num: Número de página
            image_hash: Hash de la imagen (opcional, para mayor precisión)

        Returns:
            Clave de cache (filename safe)
        """
        # Usar ruta absoluta para consistencia
        pdf_path_abs = str(Path(pdf_path).resolve())

        # Crear clave base
        key_data = f"{pdf_path_abs}:page_{page_num}"

        if image_hash:
            key_data += f":hash_{image_hash}"

        # Hash SHA256 para nombre de archivo seguro
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()

        # Formato: {pdf_name}_p{page}_{hash}.json
        pdf_name = Path(pdf_path).stem
        cache_filename = f"{pdf_name}_p{page_num}_{key_hash[:16]}.json"

        return cache_filename

    def get(
        self,
        pdf_path: str,
        page_num: int,
        image_hash: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Recupera resultado OCR del cache.

        Args:
            pdf_path: Ruta al PDF
            page_num: Número de página
            image_hash: Hash de imagen (opcional)

        Returns:
            Lista de palabras extraídas o None si no existe en cache
        """
        cache_key = self._get_cache_key(pdf_path, page_num, image_hash)
        cache_file = self.cache_dir / cache_key

        if not cache_file.exists():
            self.stats['misses'] += 1
            logger.debug(f"Cache miss: {pdf_path} página {page_num}")
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validar formato
            if not isinstance(data, dict) or 'words_data' not in data:
                logger.warning(f"Cache inválido: {cache_file}")
                return None

            self.stats['hits'] += 1
            logger.debug(
                f"Cache hit: {pdf_path} página {page_num} "
                f"({len(data['words_data'])} palabras)"
            )

            return data['words_data']

        except Exception as e:
            logger.error(f"Error leyendo cache {cache_file}: {e}")
            return None

    def save(
        self,
        pdf_path: str,
        page_num: int,
        words_data: List[Dict[str, Any]],
        image_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Guarda resultado OCR en cache.

        Args:
            pdf_path: Ruta al PDF
            page_num: Número de página
            words_data: Lista de palabras extraídas
            image_hash: Hash de imagen (opcional)
            metadata: Metadata adicional (método, timestamp, etc.)
        """
        cache_key = self._get_cache_key(pdf_path, page_num, image_hash)
        cache_file = self.cache_dir / cache_key

        try:
            data = {
                'pdf_path': str(Path(pdf_path).resolve()),
                'page_num': page_num,
                'words_data': words_data,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.stats['saves'] += 1
            logger.debug(
                f"Cache guardado: {pdf_path} página {page_num} "
                f"({len(words_data)} palabras)"
            )

        except Exception as e:
            logger.error(f"Error guardando cache {cache_file}: {e}")

    def clear(self, pdf_path: Optional[str] = None):
        """
        Limpia cache.

        Args:
            pdf_path: Si se especifica, solo limpia cache de ese PDF.
                     Si es None, limpia todo el cache.
        """
        if pdf_path is None:
            # Limpiar todo
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)

            logger.info("Cache completamente limpiado")
        else:
            # Limpiar solo archivos de este PDF
            pdf_name = Path(pdf_path).stem
            count = 0

            for cache_file in self.cache_dir.glob(f"{pdf_name}_*.json"):
                cache_file.unlink()
                count += 1

            logger.info(f"Eliminadas {count} entradas de cache para {pdf_path}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cache.

        Returns:
            Dict con estadísticas de uso
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        # Calcular tamaño del cache
        cache_size_bytes = sum(
            f.stat().st_size for f in self.cache_dir.glob('*.json')
        )
        cache_size_mb = cache_size_bytes / (1024 * 1024)

        # Contar archivos
        num_cached_files = len(list(self.cache_dir.glob('*.json')))

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'saves': self.stats['saves'],
            'total_requests': total_requests,
            'hit_rate_percent': hit_rate,
            'cached_files': num_cached_files,
            'cache_size_mb': cache_size_mb,
            'cache_dir': str(self.cache_dir)
        }

    def print_stats(self):
        """Imprime estadísticas del cache."""
        stats = self.get_stats()

        print("\n" + "="*60)
        print("ESTADÍSTICAS DE CACHE OCR")
        print("="*60)
        print(f"Hits: {stats['hits']}")
        print(f"Misses: {stats['misses']}")
        print(f"Saves: {stats['saves']}")
        print(f"Hit rate: {stats['hit_rate_percent']:.1f}%")
        print(f"Archivos en cache: {stats['cached_files']}")
        print(f"Tamaño de cache: {stats['cache_size_mb']:.2f} MB")
        print(f"Directorio: {stats['cache_dir']}")
        print()


class CachedHybridExtractor:
    """
    Wrapper para HybridPDFExtractor con cache automático.

    Uso transparente: igual que HybridPDFExtractor pero con cache.
    """

    def __init__(
        self,
        extractor,
        cache_dir: str = ".cache/ocr",
        use_cache: bool = True
    ):
        """
        Inicializa extractor con cache.

        Args:
            extractor: Instancia de HybridPDFExtractor
            cache_dir: Directorio de cache
            use_cache: Habilitar/deshabilitar cache
        """
        self.extractor = extractor
        self.use_cache = use_cache
        self.cache = OCRCache(cache_dir) if use_cache else None

    def extract_words_hybrid(
        self,
        pdf_path: str,
        page_num: int = 0,
        force_ocr: bool = False
    ):
        """
        Extrae palabras con cache automático.

        Compatible con HybridPDFExtractor.extract_words_hybrid().
        """
        # Si cache está habilitado, intentar recuperar
        if self.use_cache and self.cache is not None:
            cached_result = self.cache.get(pdf_path, page_num)

            if cached_result is not None:
                # Cache hit - retornar resultado cacheado
                metodo = cached_result[0].get('source', 'unknown') if cached_result else 'unknown'
                return cached_result, f"{metodo}_cached"

        # Cache miss o deshabilitado - procesar normalmente
        words_data, metodo = self.extractor.extract_words_hybrid(
            pdf_path, page_num, force_ocr
        )

        # Guardar en cache si está habilitado y se usó OCR
        if self.use_cache and self.cache is not None and metodo == 'ocr':
            metadata = {
                'metodo': metodo,
                'num_words': len(words_data),
                'force_ocr': force_ocr
            }
            self.cache.save(pdf_path, page_num, words_data, metadata=metadata)

        return words_data, metodo

    def extract_all_pages_hybrid(self, pdf_path: str):
        """
        Extrae todas las páginas con cache automático.

        Compatible con HybridPDFExtractor.extract_all_pages_hybrid().
        """
        import fitz

        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        doc.close()

        results = {}

        for page_num in range(num_pages):
            logger.info(f"Procesando página {page_num + 1}/{num_pages}...")

            words, metodo = self.extract_words_hybrid(pdf_path, page_num)
            results[page_num] = (words, metodo)

            logger.info(
                f"Página {page_num}: {len(words)} palabras (método: {metodo})"
            )

        return results

    def get_cache_stats(self):
        """Obtiene estadísticas del cache."""
        if self.cache:
            return self.cache.get_stats()
        return None

    def print_cache_stats(self):
        """Imprime estadísticas del cache."""
        if self.cache:
            self.cache.print_stats()


def create_cached_extractor(
    use_ocr_fallback: bool = True,
    ocr_language: str = 'es',
    use_gpu: bool = False,
    cache_dir: str = ".cache/ocr",
    use_cache: bool = True,
    **kwargs
):
    """
    Factory function para crear extractor híbrido con cache.

    Args:
        use_ocr_fallback: Usar OCR cuando extracción nativa falla
        ocr_language: Idioma para OCR
        use_gpu: Usar GPU para OCR
        cache_dir: Directorio de cache
        use_cache: Habilitar cache
        **kwargs: Argumentos adicionales para HybridPDFExtractor

    Returns:
        CachedHybridExtractor configurado
    """
    from ..extractors.hybrid_extractor import HybridPDFExtractor

    extractor = HybridPDFExtractor(
        use_ocr_fallback=use_ocr_fallback,
        ocr_language=ocr_language,
        use_gpu=use_gpu,
        **kwargs
    )

    return CachedHybridExtractor(
        extractor,
        cache_dir=cache_dir,
        use_cache=use_cache
    )
