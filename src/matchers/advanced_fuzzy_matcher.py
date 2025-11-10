"""
Fuzzy matching mejorado con normalización avanzada y estrategias ponderadas.

Mejoras sobre fuzzy matcher básico:
- Normalización avanzada de texto (unicode, acentos, puntuación)
- Múltiples estrategias de matching ponderadas
- Manejo robusto de variaciones comunes en facturas
- Scoring calibrado para mejor precisión
"""

import unicodedata
import re
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import fuzz, process
import logging

from .exact_matcher import Match
from ..normalizers.coord_normalizer import CoordinateNormalizer

logger = logging.getLogger(__name__)


class AdvancedTextNormalizer:
    """
    Normalizador avanzado de texto para matching robusto.

    Maneja variaciones comunes en documentos:
    - Acentos y diacríticos
    - Puntuación
    - Espacios múltiples
    - Mayúsculas/minúsculas
    - Caracteres especiales
    """

    @staticmethod
    def normalize_for_matching(text: str, aggressive: bool = False) -> str:
        """
        Normaliza texto para matching robusto.

        Args:
            text: Texto a normalizar
            aggressive: Si aplicar normalización agresiva (remueve más caracteres)

        Returns:
            Texto normalizado
        """
        if not text:
            return ""

        # 1. Normalización Unicode (NFKD: descompone caracteres)
        text = unicodedata.normalize('NFKD', text)

        # 2. Remover acentos (convertir á→a, é→e, etc.)
        text = text.encode('ASCII', 'ignore').decode('ASCII')

        # 3. Minúsculas
        text = text.lower()

        # 4. Normalizar espacios en blanco
        text = ' '.join(text.split())

        if aggressive:
            # 5. Remover puntuación común (modo agresivo)
            for char in ['.', ',', '-', '_', ':', ';', '!', '?', '(', ')', '[', ']', '{', '}']:
                text = text.replace(char, ' ')

            # 6. Remover caracteres especiales
            text = re.sub(r'[^\w\s]', ' ', text)

            # 7. Normalizar espacios nuevamente
            text = ' '.join(text.split())
        else:
            # Solo remover puntuación que causa falsos negativos
            for char in [',', '.']:
                text = text.replace(char, '')

        return text.strip()

    @staticmethod
    def normalize_numbers(text: str) -> str:
        """
        Normaliza números para matching robusto.

        Maneja:
        - Separadores de miles: 1,000 → 1000
        - Decimales: 1.50 vs 1,50
        - Espacios en números: 1 000 → 1000
        """
        # Remover separadores de miles comunes
        text = text.replace(',', '')
        text = text.replace(' ', '')

        # Normalizar punto decimal a punto
        # (solo si no parece ser separador de miles)
        if ',' in text and '.' not in text:
            text = text.replace(',', '.')

        return text

    @staticmethod
    def clean_ruc_nit(text: str) -> str:
        """
        Limpia RUC/NIT/Tax IDs.

        Remueve: guiones, puntos, espacios
        """
        # Mantener solo dígitos
        return re.sub(r'[^\d]', '', text)

    @staticmethod
    def normalize_date(text: str) -> str:
        """
        Normaliza fechas para matching.

        Ejemplos:
        - 01/02/2023 → 01022023
        - 01-02-2023 → 01022023
        - 01.02.2023 → 01022023
        """
        # Remover separadores
        text = re.sub(r'[/\-.]', '', text)
        return text

    @staticmethod
    def get_field_type(field_name: str) -> str:
        """
        Detecta tipo de campo para aplicar normalización específica.

        Returns:
            'number', 'ruc', 'date', 'text'
        """
        field_lower = field_name.lower()

        if any(x in field_lower for x in ['ruc', 'nit', 'tax', 'cuit', 'dni']):
            return 'ruc'
        elif any(x in field_lower for x in ['fecha', 'date', 'vencimiento']):
            return 'date'
        elif any(x in field_lower for x in ['total', 'subtotal', 'precio', 'monto', 'amount', 'igv', 'iva']):
            return 'number'
        else:
            return 'text'


class AdvancedFuzzyMatcher:
    """
    Fuzzy matcher mejorado con estrategias ponderadas.

    Combina múltiples algoritmos de fuzzy matching y pondera
    resultados para mejor precisión.
    """

    def __init__(
        self,
        threshold: float = 80.0,
        use_field_specific_normalization: bool = True,
        use_weighted_strategies: bool = True
    ):
        """
        Inicializa matcher avanzado.

        Args:
            threshold: Umbral mínimo de similitud (0-100)
            use_field_specific_normalization: Aplicar normalización específica por tipo de campo
            use_weighted_strategies: Usar scoring ponderado de múltiples estrategias
        """
        self.threshold = threshold
        self.use_field_specific_normalization = use_field_specific_normalization
        self.use_weighted_strategies = use_weighted_strategies
        self.normalizer = AdvancedTextNormalizer()

    def match_text(
        self,
        search_text: str,
        candidate_text: str,
        field_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calcula similitud entre dos textos con estrategias avanzadas.

        Args:
            search_text: Texto buscado (del JSON)
            candidate_text: Texto candidato (del PDF)
            field_name: Nombre del campo (para normalización específica)

        Returns:
            Dict con resultado del match:
            {
                'match': bool,
                'confidence': float,
                'type': str,
                'scores': dict
            }
        """
        # 1. Detectar tipo de campo
        field_type = 'text'
        if field_name and self.use_field_specific_normalization:
            field_type = self.normalizer.get_field_type(field_name)

        # 2. Normalizar según tipo de campo
        search_norm = self._normalize_by_field_type(search_text, field_type)
        candidate_norm = self._normalize_by_field_type(candidate_text, field_type)

        # 3. Exact match (máxima prioridad)
        if search_norm == candidate_norm:
            return {
                'match': True,
                'confidence': 1.0,
                'type': 'exact',
                'scores': {'exact': 100}
            }

        # 4. Calcular múltiples scores
        if self.use_weighted_strategies:
            result = self._weighted_fuzzy_match(search_norm, candidate_norm)
        else:
            result = self._simple_fuzzy_match(search_norm, candidate_norm)

        # 5. Agregar info de normalización
        result['search_normalized'] = search_norm
        result['candidate_normalized'] = candidate_norm
        result['field_type'] = field_type

        return result

    def _normalize_by_field_type(self, text: str, field_type: str) -> str:
        """
        Aplica normalización específica según tipo de campo.
        """
        if field_type == 'ruc':
            return self.normalizer.clean_ruc_nit(text)
        elif field_type == 'number':
            normalized = self.normalizer.normalize_numbers(text)
            return self.normalizer.normalize_for_matching(normalized, aggressive=False)
        elif field_type == 'date':
            return self.normalizer.normalize_date(text)
        else:  # text
            return self.normalizer.normalize_for_matching(text, aggressive=False)

    def _weighted_fuzzy_match(
        self,
        search_text: str,
        candidate_text: str
    ) -> Dict[str, Any]:
        """
        Matching con múltiples estrategias ponderadas.

        Combina 4 algoritmos con pesos calibrados:
        1. ratio: Similitud global (peso 1.0)
        2. partial_ratio: Contiene subcadena (peso 0.9)
        3. token_sort_ratio: Orden irrelevante (peso 0.85)
        4. token_set_ratio: Palabras únicas (peso 0.8)
        """
        # Calcular scores individuales
        ratio = fuzz.ratio(search_text, candidate_text)
        partial = fuzz.partial_ratio(search_text, candidate_text)
        token_sort = fuzz.token_sort_ratio(search_text, candidate_text)
        token_set = fuzz.token_set_ratio(search_text, candidate_text)

        # Scoring ponderado
        score_final = max(
            ratio * 1.0,
            partial * 0.9,
            token_sort * 0.85,
            token_set * 0.8
        )

        scores = {
            'ratio': ratio,
            'partial': partial,
            'token_sort': token_sort,
            'token_set': token_set,
            'weighted': score_final
        }

        # Determinar tipo de match
        if score_final >= 98:
            match_type = 'exact'
        elif score_final >= self.threshold:
            match_type = 'fuzzy'
        else:
            match_type = 'no_match'

        return {
            'match': score_final >= self.threshold,
            'confidence': score_final / 100.0,
            'type': match_type,
            'scores': scores
        }

    def _simple_fuzzy_match(
        self,
        search_text: str,
        candidate_text: str
    ) -> Dict[str, Any]:
        """
        Matching simple usando solo ratio.
        """
        score = fuzz.ratio(search_text, candidate_text)

        return {
            'match': score >= self.threshold,
            'confidence': score / 100.0,
            'type': 'fuzzy' if score >= self.threshold else 'no_match',
            'scores': {'ratio': score}
        }

    def find_best_match(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]],
        field_name: Optional[str] = None,
        return_all_candidates: bool = False
    ) -> Optional[Match]:
        """
        Encuentra mejor match en lista de palabras.

        Args:
            search_text: Texto a buscar
            words_data: Lista de palabras del PDF
            field_name: Nombre del campo (para normalización específica)
            return_all_candidates: Si retornar todos los candidatos con sus scores

        Returns:
            Match object o None
        """
        if not words_data:
            return None

        # Crear segmentos de texto (ventanas deslizantes)
        segments = self._create_text_segments(words_data, search_text)

        if not segments:
            return None

        # Evaluar cada segmento
        best_match = None
        best_confidence = 0
        all_candidates = []

        for segment in segments:
            segment_text = segment['text']

            # Calcular similitud
            result = self.match_text(search_text, segment_text, field_name)

            if return_all_candidates:
                all_candidates.append({
                    'segment': segment,
                    'result': result
                })

            if result['match'] and result['confidence'] > best_confidence:
                best_confidence = result['confidence']

                # Crear Match object
                best_match = Match(
                    text=search_text,
                    bbox=segment['bbox'],
                    page_num=segment['page_num'],
                    confidence=result['confidence'],
                    match_type=result['type'],
                    metadata={
                        'matched_text': segment_text,
                        'scores': result['scores'],
                        'word_count': segment['word_count'],
                        'page_width': segment['page_width'],
                        'page_height': segment['page_height'],
                        'field_type': result.get('field_type', 'text'),
                        'source': segment.get('source', 'unknown')
                    }
                )

        if return_all_candidates:
            # Ordenar candidatos por confianza
            all_candidates.sort(key=lambda c: c['result']['confidence'], reverse=True)
            logger.debug(
                f"Top 3 candidatos para '{search_text}': "
                f"{[(c['segment']['text'], c['result']['confidence']) for c in all_candidates[:3]]}"
            )

        return best_match

    def _create_text_segments(
        self,
        words_data: List[Dict[str, Any]],
        reference_text: str,
        tolerance: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Crea segmentos de texto (ventanas deslizantes) para matching.

        Similar al fuzzy matcher básico pero considera fuente de palabra (native vs OCR).
        """
        # Estimar número de palabras
        ref_tokens = reference_text.split()
        ref_word_count = len(ref_tokens)

        # Calcular rango de tamaños de ventana
        min_words = max(1, int(ref_word_count * (1 - tolerance)))
        max_words = int(ref_word_count * (1 + tolerance))

        segments = []

        # Crear segmentos
        for window_size in range(min_words, min(max_words + 1, len(words_data) + 1)):
            for i in range(len(words_data) - window_size + 1):
                segment_words = words_data[i:i + window_size]

                # Verificar que todas las palabras estén en la misma página
                pages = set(w['page_num'] for w in segment_words)
                if len(pages) > 1:
                    continue

                # Combinar texto
                segment_text = ' '.join(w['text'] for w in segment_words)

                # Combinar bboxes
                bboxes = [w['bbox'] for w in segment_words]
                merged_bbox = CoordinateNormalizer.merge_bboxes(bboxes)

                # Confianza promedio (para OCR)
                confidences = [w.get('confidence', 1.0) for w in segment_words]
                avg_confidence = sum(confidences) / len(confidences)

                segment = {
                    'text': segment_text,
                    'bbox': merged_bbox,
                    'page_num': segment_words[0]['page_num'],
                    'word_count': len(segment_words),
                    'page_width': segment_words[0]['page_width'],
                    'page_height': segment_words[0]['page_height'],
                    'source': segment_words[0].get('source', 'unknown'),
                    'ocr_confidence': avg_confidence
                }

                segments.append(segment)

        return segments
