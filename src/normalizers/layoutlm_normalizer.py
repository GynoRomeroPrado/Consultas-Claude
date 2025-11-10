"""
Normalizador de coordenadas específico para LayoutLMv3.
Convierte coordenadas PDF absolutas a escala 0-1000 requerida por LayoutLM.
"""

from typing import Tuple, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LayoutLMNormalizer:
    """
    Normaliza coordenadas para el formato exacto requerido por LayoutLMv3.

    LayoutLMv3 requiere:
    - Coordenadas en escala 0-1000 (no 0-1)
    - Formato: [x0, y0, x1, y1] donde x0 < x1 y y0 < y1
    - Coordenadas siempre válidas y dentro de límites
    """

    TARGET_SCALE = 1000

    @staticmethod
    def normalize_bbox(
        bbox: Tuple[float, float, float, float],
        page_width: float,
        page_height: float
    ) -> List[int]:
        """
        Normaliza bbox a escala 0-1000 (formato LayoutLMv3).

        Args:
            bbox: Bounding box (x0, y0, x1, y1) en coordenadas PDF absolutas
            page_width: Ancho de la página en puntos
            page_height: Alto de la página en puntos

        Returns:
            Lista [x0, y0, x1, y1] en escala 0-1000

        Raises:
            ValueError: Si las dimensiones de página son inválidas
        """
        if page_width <= 0 or page_height <= 0:
            raise ValueError(
                f"Dimensiones de página inválidas: {page_width}x{page_height}"
            )

        x0, y0, x1, y1 = bbox

        # Normalizar a escala 0-1000
        x0_norm = int((x0 / page_width) * LayoutLMNormalizer.TARGET_SCALE)
        y0_norm = int((y0 / page_height) * LayoutLMNormalizer.TARGET_SCALE)
        x1_norm = int((x1 / page_width) * LayoutLMNormalizer.TARGET_SCALE)
        y1_norm = int((y1 / page_height) * LayoutLMNormalizer.TARGET_SCALE)

        # VALIDACIÓN CRÍTICA: Asegurar coordenadas válidas
        # LayoutLMv3 falla silenciosamente con coordenadas inválidas
        x0_norm = max(0, min(x0_norm, LayoutLMNormalizer.TARGET_SCALE))
        y0_norm = max(0, min(y0_norm, LayoutLMNormalizer.TARGET_SCALE))
        x1_norm = max(0, min(x1_norm, LayoutLMNormalizer.TARGET_SCALE))
        y1_norm = max(0, min(y1_norm, LayoutLMNormalizer.TARGET_SCALE))

        # Asegurar x1 > x0 y y1 > y0 (requerimiento de LayoutLM)
        if x1_norm <= x0_norm:
            x1_norm = min(x0_norm + 1, LayoutLMNormalizer.TARGET_SCALE)
        if y1_norm <= y0_norm:
            y1_norm = min(y0_norm + 1, LayoutLMNormalizer.TARGET_SCALE)

        return [x0_norm, y0_norm, x1_norm, y1_norm]

    @staticmethod
    def normalize_bbox_safe(
        bbox: Tuple[float, float, float, float],
        page_width: float,
        page_height: float
    ) -> Tuple[List[int], bool]:
        """
        Versión segura de normalize_bbox que retorna flag de validez.

        Returns:
            Tupla (bbox_normalizado, es_valido)
        """
        try:
            bbox_norm = LayoutLMNormalizer.normalize_bbox(bbox, page_width, page_height)

            # Verificar que la bbox no sea degenerada
            x0, y0, x1, y1 = bbox_norm
            area = (x1 - x0) * (y1 - y0)

            # Área mínima: 10 unidades (0.01% de la página)
            es_valido = area >= 10

            if not es_valido:
                logger.warning(
                    f"Bbox con área muy pequeña: {bbox_norm} (área={area})"
                )

            return bbox_norm, es_valido

        except Exception as e:
            logger.error(f"Error normalizando bbox {bbox}: {e}")
            return [0, 0, 1, 1], False

    @staticmethod
    def denormalize_bbox(
        bbox_norm: List[int],
        page_width: float,
        page_height: float
    ) -> Tuple[float, float, float, float]:
        """
        Convierte bbox normalizada (0-1000) de vuelta a coordenadas absolutas.
        Útil para visualización y debugging.

        Args:
            bbox_norm: Bbox en escala 0-1000
            page_width: Ancho de la página
            page_height: Alto de la página

        Returns:
            Bbox en coordenadas absolutas (x0, y0, x1, y1)
        """
        x0_norm, y0_norm, x1_norm, y1_norm = bbox_norm

        x0 = (x0_norm / LayoutLMNormalizer.TARGET_SCALE) * page_width
        y0 = (y0_norm / LayoutLMNormalizer.TARGET_SCALE) * page_height
        x1 = (x1_norm / LayoutLMNormalizer.TARGET_SCALE) * page_width
        y1 = (y1_norm / LayoutLMNormalizer.TARGET_SCALE) * page_height

        return (x0, y0, x1, y1)

    @staticmethod
    def validate_normalized_bbox(bbox_norm: List[int]) -> Dict[str, Any]:
        """
        Valida que una bbox normalizada cumpla con los requisitos de LayoutLMv3.

        Args:
            bbox_norm: Bbox normalizada [x0, y0, x1, y1]

        Returns:
            Dict con resultados de validación:
            {
                'valido': bool,
                'errores': List[str],
                'advertencias': List[str],
                'metricas': dict
            }
        """
        x0, y0, x1, y1 = bbox_norm

        errores = []
        advertencias = []

        # 1. Verificar que esté en rango 0-1000
        if not (0 <= x0 <= LayoutLMNormalizer.TARGET_SCALE):
            errores.append(f"x0={x0} fuera de rango [0, 1000]")
        if not (0 <= y0 <= LayoutLMNormalizer.TARGET_SCALE):
            errores.append(f"y0={y0} fuera de rango [0, 1000]")
        if not (0 <= x1 <= LayoutLMNormalizer.TARGET_SCALE):
            errores.append(f"x1={x1} fuera de rango [0, 1000]")
        if not (0 <= y1 <= LayoutLMNormalizer.TARGET_SCALE):
            errores.append(f"y1={y1} fuera de rango [0, 1000]")

        # 2. Verificar x1 > x0 y y1 > y0
        if x1 <= x0:
            errores.append(f"x1 ({x1}) debe ser mayor que x0 ({x0})")
        if y1 <= y0:
            errores.append(f"y1 ({y1}) debe ser mayor que y0 ({y0})")

        # 3. Calcular métricas
        ancho = x1 - x0
        alto = y1 - y0
        area = ancho * alto
        aspect_ratio = ancho / alto if alto > 0 else 0

        # 4. Verificar área mínima
        if area < 10:
            advertencias.append(f"Área muy pequeña: {area} (puede ser ruido)")

        # 5. Verificar aspect ratio extremo
        if aspect_ratio > 50 or aspect_ratio < 0.02:
            advertencias.append(
                f"Aspect ratio extremo: {aspect_ratio:.2f} "
                "(bbox puede ser línea o muy delgada)"
            )

        return {
            'valido': len(errores) == 0,
            'errores': errores,
            'advertencias': advertencias,
            'metricas': {
                'ancho': ancho,
                'alto': alto,
                'area': area,
                'aspect_ratio': aspect_ratio
            }
        }

    @staticmethod
    def normalize_batch(
        bboxes: List[Tuple[float, float, float, float]],
        page_dimensions: List[Tuple[float, float]]
    ) -> Tuple[List[List[int]], List[bool]]:
        """
        Normaliza un batch de bboxes de forma eficiente.

        Args:
            bboxes: Lista de bboxes absolutas
            page_dimensions: Lista de (width, height) para cada bbox

        Returns:
            Tupla (bboxes_normalizadas, flags_validos)
        """
        if len(bboxes) != len(page_dimensions):
            raise ValueError(
                f"Mismatch: {len(bboxes)} bboxes vs {len(page_dimensions)} dimensiones"
            )

        bboxes_norm = []
        flags_validos = []

        for bbox, (width, height) in zip(bboxes, page_dimensions):
            bbox_norm, es_valido = LayoutLMNormalizer.normalize_bbox_safe(
                bbox, width, height
            )
            bboxes_norm.append(bbox_norm)
            flags_validos.append(es_valido)

        return bboxes_norm, flags_validos

    @staticmethod
    def calculate_iou(
        bbox1: List[int],
        bbox2: List[int]
    ) -> float:
        """
        Calcula Intersection over Union (IoU) entre dos bboxes normalizadas.
        Útil para detectar solapamientos y duplicados.

        Args:
            bbox1: Primera bbox [x0, y0, x1, y1]
            bbox2: Segunda bbox [x0, y0, x1, y1]

        Returns:
            IoU en rango [0, 1]
        """
        x0_1, y0_1, x1_1, y1_1 = bbox1
        x0_2, y0_2, x1_2, y1_2 = bbox2

        # Calcular intersección
        x0_inter = max(x0_1, x0_2)
        y0_inter = max(y0_1, y0_2)
        x1_inter = min(x1_1, x1_2)
        y1_inter = min(y1_1, y1_2)

        # Si no hay intersección
        if x1_inter <= x0_inter or y1_inter <= y0_inter:
            return 0.0

        # Área de intersección
        area_inter = (x1_inter - x0_inter) * (y1_inter - y0_inter)

        # Áreas individuales
        area_1 = (x1_1 - x0_1) * (y1_1 - y0_1)
        area_2 = (x1_2 - x0_2) * (y1_2 - y0_2)

        # Unión
        area_union = area_1 + area_2 - area_inter

        if area_union == 0:
            return 0.0

        return area_inter / area_union
