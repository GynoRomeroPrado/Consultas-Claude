"""
Validador de calidad del dataset para entrenamiento de LayoutLMv3.
Detecta errores críticos que pueden arruinar el entrenamiento.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import logging

from ..normalizers.layoutlm_normalizer import LayoutLMNormalizer

logger = logging.getLogger(__name__)


class DatasetValidator:
    """
    Valida calidad de datasets de coordenadas antes del entrenamiento.

    Detecta:
    - Coordenadas fuera de límites
    - Bboxes degeneradas (área muy pequeña)
    - Texto vacío o inválido
    - Baja confianza en matching
    - Distribución anómala de campos
    """

    def __init__(
        self,
        confianza_minima: float = 0.70,
        area_minima: int = 10,
        umbral_error_critico: float = 0.05  # 5%
    ):
        """
        Inicializa validador.

        Args:
            confianza_minima: Umbral mínimo de confianza aceptable
            area_minima: Área mínima de bbox en escala 0-1000
            umbral_error_critico: % máximo de errores para aprobar dataset
        """
        self.confianza_minima = confianza_minima
        self.area_minima = area_minima
        self.umbral_error_critico = umbral_error_critico

    def validar_dataset(
        self,
        coordenadas_dir: str,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Valida todos los archivos de coordenadas en un directorio.

        Args:
            coordenadas_dir: Directorio con archivos *_coordenadas.json
            verbose: Si mostrar reporte detallado

        Returns:
            Dict con métricas y errores encontrados
        """
        coordenadas_path = Path(coordenadas_dir)

        if not coordenadas_path.exists():
            raise FileNotFoundError(f"Directorio no encontrado: {coordenadas_dir}")

        archivos = list(coordenadas_path.glob("*_coordenadas.json"))

        if not archivos:
            raise ValueError(f"No se encontraron archivos en: {coordenadas_dir}")

        metricas = {
            'total_documentos': 0,
            'total_campos': 0,
            'errores_criticos': [],
            'advertencias': [],
            'estadisticas': defaultdict(list),
            'documentos_problematicos': []
        }

        for archivo in archivos:
            resultado_doc = self._validar_documento(archivo)
            metricas = self._merge_resultados(metricas, resultado_doc)

        # Calcular estadísticas finales
        metricas['estadisticas_finales'] = self._calcular_estadisticas_finales(metricas)

        # Determinar si el dataset es apto
        metricas['apto_entrenamiento'] = self._es_apto_entrenamiento(metricas)

        if verbose:
            self._imprimir_reporte(metricas)

        return metricas

    def _validar_documento(self, archivo_path: Path) -> Dict[str, Any]:
        """
        Valida un archivo de coordenadas individual.

        Args:
            archivo_path: Ruta al archivo JSON

        Returns:
            Dict con errores y advertencias del documento
        """
        resultado = {
            'documento': archivo_path.name,
            'total_campos': 0,
            'errores': [],
            'advertencias': [],
            'metricas': defaultdict(list)
        }

        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            coordenadas = data.get('coordenadas', [])
            resultado['total_campos'] = len(coordenadas)

            for i, coord in enumerate(coordenadas):
                errores_campo, advertencias_campo = self._validar_campo(
                    coord,
                    data.get('documento_origen', archivo_path.name)
                )
                resultado['errores'].extend(errores_campo)
                resultado['advertencias'].extend(advertencias_campo)

                # Recopilar métricas
                resultado['metricas']['confianzas'].append(coord.get('confianza', 1.0))

                bbox = coord.get('bbox', [0, 0, 1, 1])
                if len(bbox) == 4:
                    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    resultado['metricas']['areas'].append(area)

        except Exception as e:
            resultado['errores'].append({
                'tipo': 'error_lectura',
                'mensaje': f"Error leyendo archivo: {e}",
                'documento': archivo_path.name
            })

        return resultado

    def _validar_campo(
        self,
        coord: Dict[str, Any],
        documento: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Valida un campo individual.

        Returns:
            Tupla (errores, advertencias)
        """
        errores = []
        advertencias = []

        campo = coord.get('campo', 'desconocido')
        bbox = coord.get('bbox', [0, 0, 1, 1])
        texto = coord.get('texto', '')
        confianza = coord.get('confianza', 1.0)

        # 1. Validar bbox
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            errores.append({
                'tipo': 'bbox_invalida',
                'campo': campo,
                'documento': documento,
                'mensaje': f"Bbox debe ser lista/tupla de 4 elementos: {bbox}"
            })
        else:
            x0, y0, x1, y1 = bbox

            # Verificar que las coordenadas estén normalizadas (0-1000)
            # Si están en rango 0-1, asumir que NO están normalizadas
            if all(0 <= c <= 1 for c in bbox):
                errores.append({
                    'tipo': 'bbox_no_normalizada',
                    'campo': campo,
                    'documento': documento,
                    'mensaje': f"Bbox parece estar en escala 0-1, debe ser 0-1000: {bbox}"
                })

            # Verificar límites 0-1000
            elif not (0 <= x0 < x1 <= 1000 and 0 <= y0 < y1 <= 1000):
                errores.append({
                    'tipo': 'bbox_fuera_limites',
                    'campo': campo,
                    'documento': documento,
                    'bbox': bbox,
                    'mensaje': f"Bbox fuera de límites [0, 1000]: {bbox}"
                })

            # Verificar área mínima
            area = (x1 - x0) * (y1 - y0)
            if area < self.area_minima:
                advertencias.append({
                    'tipo': 'bbox_muy_pequena',
                    'campo': campo,
                    'documento': documento,
                    'area': area,
                    'mensaje': f"Área muy pequeña: {area:.1f} < {self.area_minima}"
                })

            # Verificar aspect ratio extremo
            ancho = x1 - x0
            alto = y1 - y0
            if alto > 0:
                aspect_ratio = ancho / alto
                if aspect_ratio > 50 or aspect_ratio < 0.02:
                    advertencias.append({
                        'tipo': 'aspect_ratio_extremo',
                        'campo': campo,
                        'documento': documento,
                        'aspect_ratio': aspect_ratio,
                        'mensaje': f"Aspect ratio extremo: {aspect_ratio:.2f}"
                    })

        # 2. Validar texto
        if not texto or len(texto.strip()) == 0:
            errores.append({
                'tipo': 'texto_vacio',
                'campo': campo,
                'documento': documento,
                'mensaje': "Campo con texto vacío"
            })

        # 3. Validar confianza
        if not isinstance(confianza, (int, float)):
            advertencias.append({
                'tipo': 'confianza_invalida',
                'campo': campo,
                'documento': documento,
                'confianza': confianza,
                'mensaje': f"Confianza debe ser número: {type(confianza)}"
            })
        elif confianza < self.confianza_minima:
            advertencias.append({
                'tipo': 'confianza_baja',
                'campo': campo,
                'documento': documento,
                'confianza': confianza,
                'mensaje': f"Confianza baja: {confianza:.2f} < {self.confianza_minima}"
            })

        # 4. Validar página
        pagina = coord.get('pagina')
        if pagina is None:
            advertencias.append({
                'tipo': 'pagina_faltante',
                'campo': campo,
                'documento': documento,
                'mensaje': "Campo sin número de página"
            })
        elif not isinstance(pagina, int) or pagina < 0:
            errores.append({
                'tipo': 'pagina_invalida',
                'campo': campo,
                'documento': documento,
                'pagina': pagina,
                'mensaje': f"Número de página inválido: {pagina}"
            })

        return errores, advertencias

    def _merge_resultados(
        self,
        metricas: Dict,
        resultado_doc: Dict
    ) -> Dict:
        """
        Fusiona resultados de un documento en métricas globales.
        """
        metricas['total_documentos'] += 1
        metricas['total_campos'] += resultado_doc['total_campos']

        # Agregar errores y advertencias
        for error in resultado_doc['errores']:
            metricas['errores_criticos'].append(error)

        for advertencia in resultado_doc['advertencias']:
            metricas['advertencias'].append(advertencia)

        # Agregar métricas
        for key, valores in resultado_doc['metricas'].items():
            metricas['estadisticas'][key].extend(valores)

        # Marcar documento si tiene problemas
        if resultado_doc['errores'] or len(resultado_doc['advertencias']) > 5:
            metricas['documentos_problematicos'].append({
                'documento': resultado_doc['documento'],
                'num_errores': len(resultado_doc['errores']),
                'num_advertencias': len(resultado_doc['advertencias'])
            })

        return metricas

    def _calcular_estadisticas_finales(self, metricas: Dict) -> Dict:
        """
        Calcula estadísticas agregadas finales.
        """
        total_campos = metricas['total_campos']
        total_docs = metricas['total_documentos']

        if total_campos == 0:
            return {}

        stats = {
            'campos_por_documento': total_campos / total_docs if total_docs > 0 else 0,
            'tasa_error_critico': len(metricas['errores_criticos']) / total_campos,
            'tasa_advertencia': len(metricas['advertencias']) / total_campos,
        }

        # Confianza promedio
        confianzas = metricas['estadisticas'].get('confianzas', [])
        if confianzas:
            stats['confianza_promedio'] = sum(confianzas) / len(confianzas)
            stats['confianza_minima'] = min(confianzas)
            stats['confianza_maxima'] = max(confianzas)

        # Área promedio
        areas = metricas['estadisticas'].get('areas', [])
        if areas:
            stats['area_promedio'] = sum(areas) / len(areas)
            stats['area_minima'] = min(areas)
            stats['area_maxima'] = max(areas)

        # Distribución de errores por tipo
        errores_por_tipo = defaultdict(int)
        for error in metricas['errores_criticos']:
            errores_por_tipo[error['tipo']] += 1
        stats['errores_por_tipo'] = dict(errores_por_tipo)

        return stats

    def _es_apto_entrenamiento(self, metricas: Dict) -> bool:
        """
        Determina si el dataset es apto para entrenamiento.
        """
        stats = metricas.get('estadisticas_finales', {})

        # Criterio 1: Tasa de error crítico
        tasa_error = stats.get('tasa_error_critico', 1.0)
        if tasa_error > self.umbral_error_critico:
            return False

        # Criterio 2: Al menos un documento válido
        if metricas['total_documentos'] == 0 or metricas['total_campos'] == 0:
            return False

        # Criterio 3: No todos los documentos problemáticos
        num_problematicos = len(metricas['documentos_problematicos'])
        if num_problematicos == metricas['total_documentos']:
            return False

        return True

    def _imprimir_reporte(self, metricas: Dict):
        """
        Imprime reporte detallado de validación.
        """
        print("\n" + "="*80)
        print("📊 VALIDACIÓN DE CALIDAD DEL DATASET")
        print("="*80)

        print(f"\n📁 Dataset:")
        print(f"  Total documentos:     {metricas['total_documentos']}")
        print(f"  Total campos:         {metricas['total_campos']}")

        stats = metricas.get('estadisticas_finales', {})

        if stats:
            print(f"  Campos/documento:     {stats.get('campos_por_documento', 0):.1f}")

            if 'confianza_promedio' in stats:
                print(f"\n🎯 Confianza:")
                print(f"  Promedio:  {stats['confianza_promedio']:.3f}")
                print(f"  Rango:     {stats['confianza_minima']:.3f} - {stats['confianza_maxima']:.3f}")

            if 'area_promedio' in stats:
                print(f"\n📐 Áreas de Bbox:")
                print(f"  Promedio:  {stats['area_promedio']:.1f}")
                print(f"  Rango:     {stats['area_minima']:.1f} - {stats['area_maxima']:.1f}")

        print(f"\n❌ Errores críticos:  {len(metricas['errores_criticos'])}")
        print(f"⚠️  Advertencias:      {len(metricas['advertencias'])}")

        # Mostrar primeros errores
        if metricas['errores_criticos']:
            print("\n❌ ERRORES CRÍTICOS ENCONTRADOS:")
            for i, error in enumerate(metricas['errores_criticos'][:10], 1):
                print(f"  {i}. [{error['tipo']}] {error['documento']}: "
                      f"{error.get('campo', 'N/A')} - {error['mensaje']}")

            if len(metricas['errores_criticos']) > 10:
                print(f"  ... y {len(metricas['errores_criticos']) - 10} más")

        # Distribución de errores
        if stats.get('errores_por_tipo'):
            print("\n📊 Distribución de Errores:")
            for tipo, count in stats['errores_por_tipo'].items():
                print(f"  - {tipo}: {count}")

        # Documentos problemáticos
        if metricas['documentos_problematicos']:
            print(f"\n⚠️  Documentos con Problemas ({len(metricas['documentos_problematicos'])}):")
            for doc in metricas['documentos_problematicos'][:5]:
                print(f"  - {doc['documento']}: {doc['num_errores']} errores, "
                      f"{doc['num_advertencias']} advertencias")

            if len(metricas['documentos_problematicos']) > 5:
                print(f"  ... y {len(metricas['documentos_problematicos']) - 5} más")

        # Veredicto final
        print("\n" + "="*80)
        if metricas['apto_entrenamiento']:
            print("✅ DATASET APTO PARA ENTRENAMIENTO")
            print("\n👍 El dataset cumple con los criterios de calidad.")
            print("   Puedes proceder con el entrenamiento de LayoutLMv3.")
        else:
            print("⛔ DATASET NO APTO PARA ENTRENAMIENTO")
            print("\n❌ El dataset tiene errores críticos que deben corregirse.")
            print("   Corrige los errores antes de entrenar el modelo.")

            if stats:
                tasa_error = stats.get('tasa_error_critico', 0)
                print(f"\n📊 Tasa de error: {tasa_error:.1%} (umbral: {self.umbral_error_critico:.1%})")

        print("="*80)


def validar_coordenadas_json(coordenadas_json: Dict) -> Dict[str, Any]:
    """
    Función de conveniencia para validar un JSON de coordenadas directamente.

    Args:
        coordenadas_json: Dict con coordenadas en formato estándar

    Returns:
        Dict con resultado de validación
    """
    validator = DatasetValidator()

    coordenadas = coordenadas_json.get('coordenadas', [])
    documento = coordenadas_json.get('documento_origen', 'unknown')

    resultado = {
        'documento': documento,
        'total_campos': len(coordenadas),
        'errores': [],
        'advertencias': [],
        'valido': True
    }

    for coord in coordenadas:
        errores, advertencias = validator._validar_campo(coord, documento)
        resultado['errores'].extend(errores)
        resultado['advertencias'].extend(advertencias)

    resultado['valido'] = len(resultado['errores']) == 0

    return resultado
