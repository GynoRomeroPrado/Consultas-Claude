"""
Utilidades para procesamiento paralelo de documentos.

Mejora el rendimiento en:
- Generación de datasets con múltiples PDFs
- Procesamiento batch de facturas
- Validación de grandes volúmenes

Usa multiprocessing para aprovechar múltiples CPUs.
"""

import logging
import multiprocessing as mp
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Tuple
from functools import partial
from tqdm import tqdm

logger = logging.getLogger(__name__)


class ParallelDocumentProcessor:
    """
    Procesador paralelo de documentos.

    Procesa múltiples PDFs en paralelo usando multiprocessing.
    Speedup típico: 3-4x en CPU de 4 cores.
    """

    def __init__(
        self,
        num_workers: Optional[int] = None,
        show_progress: bool = True,
        chunk_size: int = 1
    ):
        """
        Inicializa procesador paralelo.

        Args:
            num_workers: Número de procesos paralelos.
                        None = usar todos los cores disponibles
            show_progress: Mostrar barra de progreso
            chunk_size: Tamaño de chunks para procesamiento
        """
        if num_workers is None:
            # Usar todos los cores disponibles menos 1 (para no saturar)
            num_workers = max(1, mp.cpu_count() - 1)

        self.num_workers = num_workers
        self.show_progress = show_progress
        self.chunk_size = chunk_size

        logger.info(f"Procesador paralelo inicializado con {num_workers} workers")

    def process_documents(
        self,
        pdf_paths: List[str],
        json_paths: List[str],
        process_func: Callable,
        process_kwargs: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[bool, Any]]:
        """
        Procesa múltiples documentos en paralelo.

        Args:
            pdf_paths: Lista de rutas a PDFs
            json_paths: Lista de rutas a JSONs (mismo orden que pdf_paths)
            process_func: Función de procesamiento
                         Firma: func(pdf_path, json_path, **kwargs) -> resultado
            process_kwargs: Kwargs adicionales para process_func

        Returns:
            Lista de tuplas (exito, resultado/error)
        """
        if len(pdf_paths) != len(json_paths):
            raise ValueError("pdf_paths y json_paths deben tener el mismo tamaño")

        if process_kwargs is None:
            process_kwargs = {}

        # Crear argumentos para cada documento
        tasks = [
            (pdf_path, json_path, process_kwargs)
            for pdf_path, json_path in zip(pdf_paths, json_paths)
        ]

        # Procesar en paralelo
        if self.num_workers == 1:
            # Modo secuencial (útil para debugging)
            results = []
            iterator = tqdm(tasks, desc="Procesando") if self.show_progress else tasks

            for task in iterator:
                result = self._process_single_document(task, process_func)
                results.append(result)
        else:
            # Modo paralelo
            with mp.Pool(processes=self.num_workers) as pool:
                # Usar partial para pasar process_func
                worker_func = partial(self._process_single_document, process_func=process_func)

                if self.show_progress:
                    results = list(tqdm(
                        pool.imap(worker_func, tasks, chunksize=self.chunk_size),
                        total=len(tasks),
                        desc=f"Procesando ({self.num_workers} workers)"
                    ))
                else:
                    results = pool.map(worker_func, tasks, chunksize=self.chunk_size)

        return results

    @staticmethod
    def _process_single_document(
        task: Tuple[str, str, Dict[str, Any]],
        process_func: Callable
    ) -> Tuple[bool, Any]:
        """
        Procesa un solo documento (worker function).

        Args:
            task: Tupla (pdf_path, json_path, kwargs)
            process_func: Función de procesamiento

        Returns:
            Tupla (exito, resultado/error)
        """
        pdf_path, json_path, kwargs = task

        try:
            resultado = process_func(pdf_path, json_path, **kwargs)
            return (True, resultado)

        except Exception as e:
            logger.error(f"Error procesando {pdf_path}: {e}")
            return (False, str(e))

    def process_pages_parallel(
        self,
        pdf_path: str,
        page_numbers: List[int],
        process_func: Callable,
        process_kwargs: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[bool, Any]]:
        """
        Procesa múltiples páginas de un PDF en paralelo.

        Args:
            pdf_path: Ruta al PDF
            page_numbers: Lista de números de página a procesar
            process_func: Función de procesamiento
                         Firma: func(pdf_path, page_num, **kwargs) -> resultado
            process_kwargs: Kwargs adicionales

        Returns:
            Lista de tuplas (exito, resultado/error)
        """
        if process_kwargs is None:
            process_kwargs = {}

        # Crear tareas
        tasks = [
            (pdf_path, page_num, process_kwargs)
            for page_num in page_numbers
        ]

        # Procesar
        if self.num_workers == 1:
            results = []
            iterator = tqdm(tasks, desc="Procesando páginas") if self.show_progress else tasks

            for task in iterator:
                result = self._process_single_page(task, process_func)
                results.append(result)
        else:
            with mp.Pool(processes=self.num_workers) as pool:
                worker_func = partial(self._process_single_page, process_func=process_func)

                if self.show_progress:
                    results = list(tqdm(
                        pool.imap(worker_func, tasks, chunksize=self.chunk_size),
                        total=len(tasks),
                        desc=f"Procesando páginas ({self.num_workers} workers)"
                    ))
                else:
                    results = pool.map(worker_func, tasks, chunksize=self.chunk_size)

        return results

    @staticmethod
    def _process_single_page(
        task: Tuple[str, int, Dict[str, Any]],
        process_func: Callable
    ) -> Tuple[bool, Any]:
        """
        Procesa una sola página (worker function).

        Args:
            task: Tupla (pdf_path, page_num, kwargs)
            process_func: Función de procesamiento

        Returns:
            Tupla (exito, resultado/error)
        """
        pdf_path, page_num, kwargs = task

        try:
            resultado = process_func(pdf_path, page_num, **kwargs)
            return (True, resultado)

        except Exception as e:
            logger.error(f"Error procesando {pdf_path} página {page_num}: {e}")
            return (False, str(e))


def find_document_pairs(
    pdfs_dir: str,
    json_dir: str,
    pdf_pattern: str = "*.pdf",
    json_suffix: str = ".json"
) -> Tuple[List[str], List[str]]:
    """
    Encuentra pares PDF-JSON en directorios.

    Args:
        pdfs_dir: Directorio con PDFs
        json_dir: Directorio con JSONs
        pdf_pattern: Patrón para buscar PDFs
        json_suffix: Sufijo de archivos JSON

    Returns:
        Tupla (pdf_paths, json_paths) con pares correspondientes
    """
    pdfs_dir = Path(pdfs_dir)
    json_dir = Path(json_dir)

    pdf_paths = []
    json_paths = []

    for pdf_path in sorted(pdfs_dir.glob(pdf_pattern)):
        # Buscar JSON correspondiente
        json_name = pdf_path.stem + json_suffix
        json_path = json_dir / json_name

        if json_path.exists():
            pdf_paths.append(str(pdf_path))
            json_paths.append(str(json_path))
        else:
            logger.warning(f"JSON no encontrado para {pdf_path.name}: {json_path}")

    logger.info(f"Encontrados {len(pdf_paths)} pares PDF-JSON")

    return pdf_paths, json_paths


def batch_process_documents(
    pdfs_dir: str,
    json_dir: str,
    output_dir: str,
    process_func: Callable,
    num_workers: Optional[int] = None,
    show_progress: bool = True,
    **process_kwargs
) -> Dict[str, Any]:
    """
    Procesa batch de documentos en paralelo (función de conveniencia).

    Args:
        pdfs_dir: Directorio con PDFs
        json_dir: Directorio con JSONs
        output_dir: Directorio de salida
        process_func: Función de procesamiento
        num_workers: Número de workers (None = auto)
        show_progress: Mostrar progreso
        **process_kwargs: Kwargs para process_func

    Returns:
        Dict con resultados y estadísticas
    """
    # Crear directorio de salida
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Encontrar pares
    pdf_paths, json_paths = find_document_pairs(pdfs_dir, json_dir)

    if not pdf_paths:
        logger.error("No se encontraron pares PDF-JSON")
        return {
            'total': 0,
            'exitosos': 0,
            'fallidos': 0,
            'resultados': []
        }

    # Procesar en paralelo
    processor = ParallelDocumentProcessor(
        num_workers=num_workers,
        show_progress=show_progress
    )

    # Agregar output_dir a kwargs
    process_kwargs['output_dir'] = output_dir

    results = processor.process_documents(
        pdf_paths,
        json_paths,
        process_func,
        process_kwargs
    )

    # Contar éxitos/fallos
    exitosos = sum(1 for exito, _ in results if exito)
    fallidos = len(results) - exitosos

    # Recopilar errores
    errores = [
        (pdf_paths[i], error)
        for i, (exito, error) in enumerate(results)
        if not exito
    ]

    logger.info(f"\nProcesamiento completado:")
    logger.info(f"  Total: {len(results)}")
    logger.info(f"  Exitosos: {exitosos}")
    logger.info(f"  Fallidos: {fallidos}")

    if errores:
        logger.warning(f"\nErrores en {len(errores)} documentos:")
        for pdf_path, error in errores[:5]:  # Mostrar primeros 5
            logger.warning(f"  {Path(pdf_path).name}: {error}")

    return {
        'total': len(results),
        'exitosos': exitosos,
        'fallidos': fallidos,
        'resultados': results,
        'errores': errores
    }


def parallel_ocr_extraction(
    pdf_path: str,
    use_gpu: bool = False,
    num_workers: Optional[int] = None
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Extrae texto de todas las páginas de un PDF en paralelo.

    Útil para PDFs grandes (>10 páginas).

    Args:
        pdf_path: Ruta al PDF
        use_gpu: Usar GPU para OCR (no compatible con multiprocessing)
        num_workers: Número de workers

    Returns:
        Dict mapeando page_num → words_data
    """
    import fitz
    from ..extractors.hybrid_extractor import HybridPDFExtractor

    # Obtener número de páginas
    doc = fitz.open(pdf_path)
    num_pages = len(doc)
    doc.close()

    if use_gpu:
        logger.warning(
            "GPU no es compatible con procesamiento paralelo. "
            "Procesando secuencialmente..."
        )
        num_workers = 1

    # Crear procesador
    processor = ParallelDocumentProcessor(num_workers=num_workers)

    # Función de extracción para cada página
    def extract_page(pdf_path, page_num, extractor_kwargs):
        extractor = HybridPDFExtractor(**extractor_kwargs)
        words, _ = extractor.extract_words_hybrid(pdf_path, page_num)
        return words

    # Procesar páginas en paralelo
    results = processor.process_pages_parallel(
        pdf_path,
        list(range(num_pages)),
        extract_page,
        {'use_gpu': False, 'use_ocr_fallback': True}
    )

    # Convertir a dict
    pages_data = {}
    for page_num, (exito, words) in enumerate(results):
        if exito:
            pages_data[page_num] = words
        else:
            logger.error(f"Error en página {page_num}: {words}")
            pages_data[page_num] = []

    return pages_data
