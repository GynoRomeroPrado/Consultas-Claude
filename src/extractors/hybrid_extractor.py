"""
Extractor híbrido que detecta automáticamente tipo de PDF y usa OCR cuando es necesario.

Pipeline:
1. Detecta si PDF es nativo (texto vectorial) o rasterizado (imagen)
2. PDF nativo → Usa PyMuPDF directo (rápido, preciso)
3. PDF rasterizado → Usa PaddleOCR con preprocesamiento (robusto)
"""

import fitz
import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import cv2
except ImportError:
    cv2 = None
    logger.warning("OpenCV no disponible. Preprocesamiento limitado.")

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning(
        "PaddleOCR no está instalado. OCR no disponible. "
        "Instala con: pip install paddlepaddle paddleocr"
    )

from ..preprocessing.image_processor import ImagePreprocessor


class HybridPDFExtractor:
    """
    Extractor híbrido inteligente para PDFs nativos y rasterizados.

    Detecta automáticamente el tipo de PDF y aplica la mejor estrategia:
    - PDFs nativos: Extracción directa con PyMuPDF (40x más rápido)
    - PDFs rasterizados: OCR con PaddleOCR + preprocesamiento (20-30% más preciso)
    """

    def __init__(
        self,
        use_ocr_fallback: bool = True,
        ocr_language: str = 'es',
        use_gpu: bool = False,
        detection_threshold: int = 10,
        ocr_confidence_threshold: float = 0.5,
        preprocess_images: bool = True
    ):
        """
        Inicializa extractor híbrido.

        Args:
            use_ocr_fallback: Usar OCR cuando extracción nativa falla
            ocr_language: Idioma para OCR ('es', 'en', 'pt', etc.)
            use_gpu: Usar GPU para OCR (requiere CUDA)
            detection_threshold: Mínimo de palabras para considerar PDF nativo
            ocr_confidence_threshold: Confianza mínima para aceptar resultado OCR
            preprocess_images: Aplicar preprocesamiento antes de OCR
        """
        self.use_ocr_fallback = use_ocr_fallback
        self.ocr_language = ocr_language
        self.use_gpu = use_gpu
        self.detection_threshold = detection_threshold
        self.ocr_confidence_threshold = ocr_confidence_threshold
        self.preprocess_images = preprocess_images

        # Inicializar OCR si está disponible
        self.ocr = None
        if PADDLEOCR_AVAILABLE and use_ocr_fallback:
            self._initialize_ocr()

        # Inicializar preprocesador
        self.preprocessor = None
        if cv2 is not None and preprocess_images:
            self.preprocessor = ImagePreprocessor()

    def _initialize_ocr(self):
        """Inicializa PaddleOCR con configuración óptima."""
        try:
            # Mapear códigos de idioma
            lang_map = {
                'es': 'es',
                'spa': 'es',
                'spanish': 'es',
                'en': 'en',
                'eng': 'en',
                'english': 'en',
                'pt': 'pt',
                'por': 'pt',
                'portuguese': 'pt'
            }
            lang = lang_map.get(self.ocr_language.lower(), 'es')

            self.ocr = PaddleOCR(
                use_angle_cls=True,  # Detectar y corregir orientación del texto
                lang=lang,
                use_gpu=self.use_gpu,
                show_log=False,
                det_db_thresh=0.3,  # Umbral de detección de texto
                det_db_box_thresh=0.5,  # Umbral de bbox de texto
                rec_algorithm='CRNN'  # Algoritmo de reconocimiento
            )

            logger.info(f"PaddleOCR inicializado (idioma={lang}, gpu={self.use_gpu})")

        except Exception as e:
            logger.error(f"Error inicializando PaddleOCR: {e}")
            self.ocr = None

    def detect_pdf_type(
        self,
        pdf_path: str,
        page_num: int = 0
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Detecta si un PDF es nativo (texto vectorial) o rasterizado (imagen).

        Args:
            pdf_path: Ruta al PDF
            page_num: Número de página a analizar (default: primera)

        Returns:
            Tupla (tipo, metadata)
            - tipo: 'native' o 'rasterized'
            - metadata: Dict con info del análisis
        """
        try:
            doc = fitz.open(pdf_path)

            if page_num >= len(doc):
                logger.warning(f"Página {page_num} no existe. Usando página 0.")
                page_num = 0

            page = doc[page_num]

            # 1. Intentar extracción nativa
            words = page.get_text("words")
            num_words = len(words) if words else 0

            # 2. Contar imágenes en la página
            images = page.get_images()
            num_images = len(images)

            # 3. Obtener dimensiones de página
            rect = page.rect
            page_area = rect.width * rect.height

            # 4. Calcular área cubierta por imágenes
            image_coverage = 0
            if num_images > 0:
                for img_info in images:
                    try:
                        img_bbox = page.get_image_bbox(img_info[7])  # xref
                        img_area = (img_bbox.x1 - img_bbox.x0) * (img_bbox.y1 - img_bbox.y0)
                        image_coverage += img_area
                    except:
                        pass

            image_coverage_percent = (image_coverage / page_area * 100) if page_area > 0 else 0

            doc.close()

            # 5. Determinar tipo de PDF
            metadata = {
                'num_words': num_words,
                'num_images': num_images,
                'image_coverage_percent': image_coverage_percent,
                'page_area': page_area,
                'detection_threshold': self.detection_threshold
            }

            # Criterios de decisión:
            # - Si tiene pocas palabras Y gran cobertura de imagen → Rasterizado
            # - Si tiene muchas palabras → Nativo
            if num_words < self.detection_threshold and image_coverage_percent > 50:
                tipo = 'rasterized'
                metadata['reason'] = f'Pocas palabras ({num_words}) y alta cobertura de imagen ({image_coverage_percent:.1f}%)'
            elif num_words >= self.detection_threshold:
                tipo = 'native'
                metadata['reason'] = f'Suficientes palabras extraídas ({num_words})'
            else:
                # Caso ambiguo: pocas palabras pero poca imagen
                if num_images > 0:
                    tipo = 'rasterized'
                    metadata['reason'] = 'Contiene imágenes y pocas palabras'
                else:
                    tipo = 'native'
                    metadata['reason'] = 'Sin imágenes grandes'

            logger.info(
                f"PDF detectado como '{tipo}': {metadata['reason']}"
            )

            return tipo, metadata

        except Exception as e:
            logger.error(f"Error detectando tipo de PDF: {e}")
            return 'native', {'error': str(e)}

    def extract_words_native(
        self,
        pdf_path: str,
        page_num: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Extrae palabras usando método nativo de PyMuPDF.

        Rápido y preciso para PDFs con texto vectorial.

        Args:
            pdf_path: Ruta al PDF
            page_num: Número de página

        Returns:
            Lista de diccionarios con palabras y coordenadas
        """
        words_data = []

        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]

            rect = page.rect
            page_width, page_height = rect.width, rect.height

            words = page.get_text("words")

            for word in words:
                # word format: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
                word_data = {
                    'text': word[4],
                    'bbox': (word[0], word[1], word[2], word[3]),
                    'page_num': page_num,
                    'page_width': page_width,
                    'page_height': page_height,
                    'block_no': word[5],
                    'line_no': word[6],
                    'word_no': word[7],
                    'source': 'native',
                    'confidence': 1.0
                }
                words_data.append(word_data)

            doc.close()

            logger.debug(f"Extraídas {len(words_data)} palabras (método nativo)")

        except Exception as e:
            logger.error(f"Error en extracción nativa: {e}")

        return words_data

    def extract_words_ocr(
        self,
        pdf_path: str,
        page_num: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Extrae palabras usando PaddleOCR.

        Robusto para PDFs rasterizados y de baja calidad.

        Args:
            pdf_path: Ruta al PDF
            page_num: Número de página

        Returns:
            Lista de diccionarios con palabras y coordenadas
        """
        if self.ocr is None:
            logger.error("PaddleOCR no está disponible")
            return []

        words_data = []

        try:
            # 1. Convertir PDF a imagen de alta calidad
            doc = fitz.open(pdf_path)
            page = doc[page_num]

            # DPI alto para mejor OCR (300 DPI es estándar)
            zoom = 300 / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            # Obtener dimensiones de página original
            rect = page.rect
            page_width = rect.width
            page_height = rect.height

            # Convertir a numpy array
            img_data = pix.tobytes("png")
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            doc.close()

            # 2. Preprocesar imagen si está habilitado
            if self.preprocessor is not None:
                img = self.preprocessor.preprocess(img)

            # 3. Aplicar OCR
            resultado = self.ocr.ocr(img, cls=True)

            # 4. Procesar resultados
            if not resultado or not resultado[0]:
                logger.warning("OCR no detectó texto en la página")
                return []

            img_height, img_width = img.shape[:2]
            scale_x = page_width / img_width
            scale_y = page_height / img_height

            for idx, line in enumerate(resultado[0]):
                try:
                    # Formato PaddleOCR: [bbox, (texto, confianza)]
                    bbox_ocr = line[0]  # [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
                    text_info = line[1]
                    texto = text_info[0]
                    confianza = text_info[1]

                    # Filtrar por confianza
                    if confianza < self.ocr_confidence_threshold:
                        logger.debug(
                            f"Descartado por baja confianza: '{texto}' ({confianza:.2f})"
                        )
                        continue

                    # Convertir coordenadas de imagen a PDF
                    # Usar esquina superior izquierda e inferior derecha
                    x0 = bbox_ocr[0][0] * scale_x
                    y0 = bbox_ocr[0][1] * scale_y
                    x1 = bbox_ocr[2][0] * scale_x
                    y1 = bbox_ocr[2][1] * scale_y

                    word_data = {
                        'text': texto,
                        'bbox': (x0, y0, x1, y1),
                        'page_num': page_num,
                        'page_width': page_width,
                        'page_height': page_height,
                        'source': 'ocr',
                        'confidence': float(confianza),
                        'block_no': 0,
                        'line_no': idx,
                        'word_no': 0
                    }
                    words_data.append(word_data)

                except Exception as e:
                    logger.warning(f"Error procesando resultado OCR: {e}")
                    continue

            logger.info(
                f"OCR extrajo {len(words_data)} elementos "
                f"(confianza promedio: {np.mean([w['confidence'] for w in words_data]):.2f})"
            )

        except Exception as e:
            logger.error(f"Error en extracción OCR: {e}")
            import traceback
            traceback.print_exc()

        return words_data

    def extract_words_hybrid(
        self,
        pdf_path: str,
        page_num: int = 0,
        force_ocr: bool = False
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Extrae palabras usando estrategia híbrida inteligente.

        Args:
            pdf_path: Ruta al PDF
            page_num: Número de página
            force_ocr: Forzar uso de OCR sin importar detección

        Returns:
            Tupla (words_data, metodo_usado)
            - words_data: Lista de palabras con coordenadas
            - metodo_usado: 'native', 'ocr', o 'hybrid'
        """
        # 1. Forzar OCR si se solicita
        if force_ocr:
            if not PADDLEOCR_AVAILABLE:
                logger.error("OCR forzado pero PaddleOCR no disponible")
                return [], 'error'

            words = self.extract_words_ocr(pdf_path, page_num)
            return words, 'ocr'

        # 2. Detectar tipo de PDF
        tipo, metadata = self.detect_pdf_type(pdf_path, page_num)

        # 3. Extraer según tipo
        if tipo == 'native':
            # Intentar extracción nativa
            words = self.extract_words_native(pdf_path, page_num)

            # Si falló y OCR está disponible, usar OCR como fallback
            if len(words) < self.detection_threshold and self.use_ocr_fallback:
                logger.warning(
                    f"Extracción nativa dio pocas palabras ({len(words)}). "
                    "Intentando con OCR..."
                )
                words_ocr = self.extract_words_ocr(pdf_path, page_num)

                if len(words_ocr) > len(words):
                    logger.info(
                        f"OCR extrajo más palabras ({len(words_ocr)} vs {len(words)}). "
                        "Usando resultado OCR."
                    )
                    return words_ocr, 'ocr'

            return words, 'native'

        else:  # tipo == 'rasterized'
            if not PADDLEOCR_AVAILABLE:
                logger.warning(
                    "PDF rasterizado pero PaddleOCR no disponible. "
                    "Intentando extracción nativa (puede fallar)."
                )
                words = self.extract_words_native(pdf_path, page_num)
                return words, 'native'

            # Usar OCR para PDFs rasterizados
            words = self.extract_words_ocr(pdf_path, page_num)
            return words, 'ocr'

    def extract_all_pages_hybrid(
        self,
        pdf_path: str
    ) -> Dict[int, Tuple[List[Dict[str, Any]], str]]:
        """
        Extrae palabras de todas las páginas usando estrategia híbrida.

        Args:
            pdf_path: Ruta al PDF

        Returns:
            Dict mapeando page_num → (words_data, metodo_usado)
        """
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        doc.close()

        results = {}

        for page_num in range(num_pages):
            logger.info(f"Procesando página {page_num + 1}/{num_pages}...")

            words, metodo = self.extract_words_hybrid(pdf_path, page_num)
            results[page_num] = (words, metodo)

            logger.info(
                f"Página {page_num}: {len(words)} palabras "
                f"(método: {metodo})"
            )

        return results
