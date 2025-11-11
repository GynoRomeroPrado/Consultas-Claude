#!/usr/bin/env python3
"""
Script para generar dataset en formato LayoutLMv3 OFICIAL (FUNSD-style).

Implementa el formato exacto según documentación oficial:
- Tokenización por palabras individuales (NO agrupar)
- Labels estándar: "question", "answer", "header", "other"
- Sistema de linking entre etiquetas y valores
- Detección automática de etiquetas en el PDF

Basado en: https://guillaumejaume.github.io/FUNSD/
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from typing import List, Dict, Any, Optional, Tuple

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.extractors.hybrid_extractor import HybridPDFExtractor
    from src.matchers.advanced_fuzzy_matcher import AdvancedFuzzyMatcher
    from src.normalizers.layoutlm_normalizer import LayoutLMNormalizer
    from src.extractors.json_parser import JSONParser
    import fitz
    DEPS_OK = True
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("\nInstala las dependencias:")
    print("  pip install PyMuPDF rapidfuzz numpy pandas tqdm")
    print("  pip install opencv-python paddlepaddle paddleocr")
    DEPS_OK = False


def tokenizar_texto_con_boxes(texto: str, bbox: List[int]) -> List[Dict[str, Any]]:
    """
    Divide texto en palabras individuales y estima bbox de cada palabra.

    Esta función es CRÍTICA para el formato LayoutLMv3:
    - NO agrupa todo el texto en un solo box
    - Divide en palabras individuales
    - Estima posición de cada palabra proporcionalmente

    Args:
        texto: Texto completo (ej: "EMPRESA SAC")
        bbox: Bbox del texto completo [x0, y0, x1, y1] en escala 0-1000

    Returns:
        Lista de {"text": palabra, "box": [x0, y0, x1, y1]}

    Ejemplo:
        Input: "EMPRESA SAC", [100, 200, 300, 220]
        Output: [
            {"text": "EMPRESA", "box": [100, 200, 195, 220]},
            {"text": "SAC", "box": [205, 200, 300, 220]}
        ]
    """
    # Dividir en palabras (respetando espacios múltiples)
    palabras = texto.split()

    if not palabras:
        return [{"text": texto, "box": bbox}]

    if len(palabras) == 1:
        # Solo una palabra - usar bbox completo
        return [{"text": palabras[0], "box": bbox}]

    # Múltiples palabras - estimar posición de cada una
    x0, y0, x1, y1 = bbox
    ancho_total = x1 - x0

    # Calcular longitud total de caracteres (para estimación proporcional)
    longitud_total = sum(len(p) for p in palabras)

    # Estimar ancho de espacios entre palabras
    num_espacios = len(palabras) - 1
    ancho_espacio = max(5, ancho_total * 0.02)  # ~2% del ancho total o mínimo 5
    ancho_disponible = ancho_total - (num_espacios * ancho_espacio)

    words_with_boxes = []
    x_actual = x0

    for i, palabra in enumerate(palabras):
        # Calcular ancho proporcional de esta palabra
        proporcion = len(palabra) / longitud_total
        ancho_palabra = ancho_disponible * proporcion

        # Bbox de esta palabra
        palabra_bbox = [
            int(x_actual),
            y0,
            int(x_actual + ancho_palabra),
            y1
        ]

        words_with_boxes.append({
            "text": palabra,
            "box": palabra_bbox
        })

        # Avanzar x_actual
        x_actual += ancho_palabra
        if i < num_espacios:
            x_actual += ancho_espacio

    return words_with_boxes


def detectar_etiqueta_cercana(
    palabras_extraidas: List[Dict[str, Any]],
    campo_nombre: str,
    valor_bbox: List[int],
    umbral_distancia: int = 150
) -> Optional[Dict[str, Any]]:
    """
    Detecta etiqueta cercana al valor del campo.

    Busca patrones como:
    - "RUC:", "RUC", "R.U.C."
    - "Total:", "TOTAL", "Total $"
    - "Fecha:", "FECHA", "Date:"

    Args:
        palabras_extraidas: Palabras extraídas del PDF con sus bboxes
        campo_nombre: Nombre del campo (ej: "emisor_ruc")
        valor_bbox: Bbox del valor encontrado
        umbral_distancia: Distancia máxima en píxeles (escala 0-1000)

    Returns:
        Dict con info de la etiqueta o None si no se encuentra
    """
    # Generar patrones de búsqueda basados en el nombre del campo
    patrones = generar_patrones_etiqueta(campo_nombre)

    # Buscar palabras que coincidan con patrones
    etiquetas_candidatas = []

    for palabra_data in palabras_extraidas:
        texto_palabra = palabra_data['text'].strip()
        bbox_palabra = palabra_data['bbox']

        # Verificar si coincide con algún patrón
        for patron in patrones:
            if re.search(patron, texto_palabra, re.IGNORECASE):
                # Calcular distancia al valor
                distancia = calcular_distancia_boxes(bbox_palabra, valor_bbox)

                if distancia <= umbral_distancia:
                    etiquetas_candidatas.append({
                        'text': texto_palabra,
                        'bbox': bbox_palabra,
                        'distancia': distancia
                    })
                    break

    # Retornar la etiqueta más cercana
    if etiquetas_candidatas:
        etiquetas_candidatas.sort(key=lambda x: x['distancia'])
        return etiquetas_candidatas[0]

    return None


def generar_patrones_etiqueta(campo_nombre: str) -> List[str]:
    """
    Genera patrones regex para buscar etiquetas basadas en el nombre del campo.

    Args:
        campo_nombre: Nombre del campo (ej: "emisor_ruc", "total", "fecha_emision")

    Returns:
        Lista de patrones regex

    Ejemplos:
        "emisor_ruc" → ["ruc", "r\\.?u\\.?c\\.?", "registro"]
        "total" → ["total", "importe", "monto"]
        "fecha_emision" → ["fecha", "date", "emision"]
    """
    # Mapeo de campos comunes a sus posibles etiquetas
    mapeo_etiquetas = {
        'ruc': ['ruc', r'r\.?u\.?c\.?', 'registro', 'tax', 'id'],
        'nombre': ['nombre', 'razon', 'social', 'name', 'company'],
        'total': ['total', 'importe', 'monto', 'amount', 'sum'],
        'subtotal': ['subtotal', 'base', 'imponible'],
        'igv': ['igv', r'i\.?g\.?v\.?', 'iva', 'tax', 'impuesto'],
        'fecha': ['fecha', 'date', 'emision', 'emission'],
        'numero': ['numero', r'n°', 'num', 'number', 'factura', 'invoice'],
        'direccion': ['direccion', 'domicilio', 'address', 'ubicacion'],
        'telefono': ['telefono', 'tel', 'phone', 'celular'],
        'email': ['email', 'correo', 'mail'],
        'moneda': ['moneda', 'currency'],
    }

    # Extraer palabras clave del nombre del campo
    palabras_campo = re.split(r'[_\-\s]+', campo_nombre.lower())

    # Buscar patrones relacionados
    patrones = set()

    for palabra in palabras_campo:
        # Agregar la palabra misma
        patrones.add(rf'\b{re.escape(palabra)}\b')

        # Buscar en el mapeo
        for clave, etiquetas in mapeo_etiquetas.items():
            if clave in palabra or palabra in clave:
                patrones.update(etiquetas)

    # Agregar patrones con sufijos comunes
    patrones_con_sufijos = set()
    for patron in patrones:
        patrones_con_sufijos.add(patron)
        patrones_con_sufijos.add(patron + r'\s*:')  # Con ":"
        patrones_con_sufijos.add(patron + r'\s*\.')  # Con "."

    return list(patrones_con_sufijos)


def calcular_distancia_boxes(bbox1: List[int], bbox2: List[int]) -> float:
    """
    Calcula distancia entre dos bounding boxes.

    Usa distancia euclidiana entre centros de los boxes.

    Args:
        bbox1: [x0, y0, x1, y1]
        bbox2: [x0, y0, x1, y1]

    Returns:
        Distancia en píxeles (escala 0-1000)
    """
    # Calcular centros
    cx1 = (bbox1[0] + bbox1[2]) / 2
    cy1 = (bbox1[1] + bbox1[3]) / 2

    cx2 = (bbox2[0] + bbox2[2]) / 2
    cy2 = (bbox2[1] + bbox2[3]) / 2

    # Distancia euclidiana
    distancia = ((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2) ** 0.5

    return distancia


def generar_linking(etiqueta_id: Optional[int], valor_id: int) -> List[List[int]]:
    """
    Genera array de linking entre etiqueta y valor.

    Formato LayoutLMv3 oficial:
    - Si hay etiqueta: [[etiqueta_id, valor_id]]
    - Si NO hay etiqueta: []

    Args:
        etiqueta_id: ID de la etiqueta (None si no existe)
        valor_id: ID del valor

    Returns:
        Lista de links: [[id1, id2]] o []

    Ejemplos:
        generar_linking(0, 1) → [[0, 1]]
        generar_linking(None, 1) → []
    """
    if etiqueta_id is not None:
        return [[etiqueta_id, valor_id]]
    else:
        return []


def procesar_documento_layoutlmv3_oficial(
    pdf_path: str,
    json_path: str,
    output_dir: str = "dataset_layoutlmv3_oficial",
    confianza_minima: float = 0.75,
    usar_ocr: bool = True,
    usar_gpu: bool = False,
    detectar_etiquetas: bool = True,
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Procesa documento y genera formato LayoutLMv3 OFICIAL (FUNSD-style).

    Formato de salida según documentación oficial:
    {
      "form": [
        {
          "id": 0,
          "text": "RUC:",
          "box": [10, 20, 50, 35],
          "label": "question",
          "field_name": "RUC",
          "words": [{"text": "RUC:", "box": [10, 20, 50, 35]}],
          "linking": [[0, 1]]
        },
        {
          "id": 1,
          "text": "20123456789",
          "box": [60, 20, 150, 35],
          "label": "answer",
          "field_name": "RUC",
          "words": [{"text": "20123456789", "box": [60, 20, 150, 35]}],
          "linking": [[0, 1]]
        }
      ]
    }

    Args:
        pdf_path: Ruta al PDF
        json_path: Ruta al JSON con anotaciones
        output_dir: Directorio de salida
        confianza_minima: Umbral mínimo de confianza
        usar_ocr: Habilitar OCR para PDFs rasterizados
        usar_gpu: Usar GPU para OCR
        detectar_etiquetas: Buscar etiquetas en el PDF
        verbose: Mostrar progreso detallado

    Returns:
        Dict con resultado en formato LayoutLMv3 oficial
    """

    if not DEPS_OK:
        print("❌ Dependencias no disponibles")
        return None

    if verbose:
        print("="*80)
        print("GENERACIÓN DE DATASET - FORMATO LAYOUTLMV3 OFICIAL (FUNSD-STYLE)")
        print("="*80)
        print(f"PDF:  {pdf_path}")
        print(f"JSON: {json_path}")
        print(f"OCR:  {'Habilitado' if usar_ocr else 'Deshabilitado'}")
        print(f"GPU:  {'Sí' if usar_gpu else 'No'}")
        print(f"Detectar etiquetas: {'Sí' if detectar_etiquetas else 'No'}")
        print()

    # Crear directorio de salida
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Inicializar componentes
        if verbose:
            print("🔧 Inicializando extractor híbrido...")

        extractor = HybridPDFExtractor(
            use_ocr_fallback=usar_ocr,
            ocr_language='es',
            use_gpu=usar_gpu,
            detection_threshold=10,
            ocr_confidence_threshold=0.5,
            preprocess_images=True
        )

        matcher = AdvancedFuzzyMatcher(
            threshold=80.0,
            use_field_specific_normalization=True,
            use_weighted_strategies=True
        )

        # 2. Parsear JSON
        if verbose:
            print("📄 Parseando JSON...")

        json_parser = JSONParser()
        fields = json_parser.extract_fields(json_path)

        if verbose:
            print(f"   Total de campos en JSON: {len(fields)}")

        # 3. Abrir PDF y obtener info
        doc = fitz.open(pdf_path)
        num_paginas = len(doc)
        doc.close()

        pdf_name = Path(pdf_path).stem

        if verbose:
            print(f"   Páginas del PDF: {num_paginas}\n")

        # 4. Procesar cada página y extraer TODAS las palabras
        todas_palabras = []  # Para búsqueda de etiquetas
        form_items = []
        item_id = 0
        campos_encontrados = set()
        total_confianza = 0.0
        num_links = 0

        for page_num in range(num_paginas):
            if verbose:
                print(f"📄 Procesando página {page_num + 1}/{num_paginas}...")

            # Extraer palabras
            words_data, metodo = extractor.extract_words_hybrid(
                pdf_path,
                page_num=page_num
            )

            if verbose:
                print(f"   Método usado: {metodo.upper()}")
                print(f"   Palabras extraídas: {len(words_data)}")

            if not words_data:
                if verbose:
                    print("   ⚠️  No se extrajo texto de esta página\n")
                continue

            # Obtener dimensiones de página
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            page_width = page.rect.width
            page_height = page.rect.height
            doc.close()

            # Normalizar todas las palabras para búsqueda de etiquetas
            palabras_normalizadas = []
            for word_data in words_data:
                bbox_norm, es_valido = LayoutLMNormalizer.normalize_bbox_safe(
                    word_data['bbox'],
                    page_width,
                    page_height
                )
                if es_valido:
                    palabras_normalizadas.append({
                        'text': word_data['text'],
                        'bbox': bbox_norm,
                        'page': page_num
                    })

            todas_palabras.extend(palabras_normalizadas)

            # 5. Buscar cada campo en esta página
            for field_name, field_value in fields.items():
                if not field_value or not str(field_value).strip():
                    continue

                # Evitar duplicados
                if field_name in campos_encontrados:
                    continue

                # Buscar match del valor
                match = matcher.find_best_match(
                    str(field_value),
                    words_data,
                    field_name=field_name
                )

                if match and match.confidence >= confianza_minima:
                    # Normalizar coordenadas
                    bbox_norm, es_valido = LayoutLMNormalizer.normalize_bbox_safe(
                        match.bbox,
                        page_width,
                        page_height
                    )

                    if not es_valido:
                        if verbose:
                            print(f"   ⚠️  Bbox inválida: {field_name}")
                        continue

                    # 6. Buscar etiqueta cercana (si está habilitado)
                    etiqueta_data = None
                    etiqueta_id = None

                    if detectar_etiquetas:
                        etiqueta_data = detectar_etiqueta_cercana(
                            palabras_normalizadas,
                            field_name,
                            bbox_norm,
                            umbral_distancia=150
                        )

                    # 7. Crear item para la ETIQUETA (si existe)
                    if etiqueta_data:
                        etiqueta_id = item_id

                        # Tokenizar etiqueta
                        etiqueta_words = tokenizar_texto_con_boxes(
                            etiqueta_data['text'],
                            etiqueta_data['bbox']
                        )

                        form_items.append({
                            "id": etiqueta_id,
                            "text": etiqueta_data['text'],
                            "box": etiqueta_data['bbox'],
                            "label": "question",  # LABEL ESTÁNDAR
                            "field_name": field_name,  # Referencia
                            "words": etiqueta_words,
                            "linking": [[etiqueta_id, item_id + 1]],  # Link al valor
                            "page": page_num
                        })

                        item_id += 1
                        num_links += 1

                        if verbose:
                            print(f"   ✓ Etiqueta detectada: '{etiqueta_data['text']}' → '{match.text}'")

                    # 8. Crear item para el VALOR
                    valor_id = item_id

                    # Tokenizar valor en palabras individuales
                    valor_words = tokenizar_texto_con_boxes(
                        match.text,
                        bbox_norm
                    )

                    # Linking del valor
                    if etiqueta_id is not None:
                        valor_linking = [[etiqueta_id, valor_id]]
                    else:
                        valor_linking = []

                    form_items.append({
                        "id": valor_id,
                        "text": match.text,
                        "box": bbox_norm,
                        "label": "answer",  # LABEL ESTÁNDAR
                        "field_name": field_name,  # Referencia
                        "words": valor_words,  # TOKENIZADO
                        "linking": valor_linking,
                        "page": page_num
                    })

                    campos_encontrados.add(field_name)
                    total_confianza += match.confidence
                    item_id += 1

                    if verbose:
                        etiqueta_info = f" (con etiqueta)" if etiqueta_data else ""
                        print(f"   ✓ {field_name}: '{match.text}' (conf: {match.confidence:.3f}){etiqueta_info}")
                        print(f"     Palabras tokenizadas: {len(valor_words)}")

                elif match:
                    if verbose:
                        print(f"   ⚠️  Filtrado: {field_name} (conf: {match.confidence:.2f})")

            if verbose:
                print()

        # 9. Calcular métricas
        campos_faltantes = [
            field_name
            for field_name in fields.keys()
            if field_name not in campos_encontrados and fields[field_name]
        ]

        total_campos_json = len([v for v in fields.values() if v and str(v).strip()])
        num_campos_encontrados = len(campos_encontrados)
        match_rate = (num_campos_encontrados / total_campos_json * 100) if total_campos_json > 0 else 0.0
        confianza_promedio = (total_confianza / num_campos_encontrados) if num_campos_encontrados > 0 else 0.0

        # 10. Construir salida en formato oficial
        output_data = {
            "form": form_items
        }

        # Metadata separada (NO dentro de form)
        metadata = {
            "documento": Path(pdf_path).name,
            "num_paginas": num_paginas,
            "fecha_generacion": datetime.now().isoformat(),
            "formato": "layoutlmv3_oficial_funsd_v1.0"
        }

        estadisticas = {
            "total_campos_json": total_campos_json,
            "campos_encontrados": num_campos_encontrados,
            "campos_faltantes": len(campos_faltantes),
            "match_rate": round(match_rate, 2),
            "confianza_promedio": round(confianza_promedio, 3),
            "total_items_form": len(form_items),
            "etiquetas_detectadas": num_links,
            "palabras_tokenizadas": sum(len(item['words']) for item in form_items)
        }

        # 11. Guardar archivo PRINCIPAL (solo "form")
        output_file = output_path / f"{pdf_name}_layoutlm_v3.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # 12. Guardar metadata y estadísticas en archivo separado
        metadata_file = output_path / f"{pdf_name}_metadata.json"

        metadata_completa = {
            **metadata,
            "estadisticas": estadisticas,
            "campos_faltantes": sorted(campos_faltantes)
        }

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata_completa, f, indent=2, ensure_ascii=False)

        if verbose:
            print("="*80)
            print("📊 RESUMEN FINAL")
            print("="*80)
            print(f"  Documento:                 {Path(pdf_path).name}")
            print(f"  Páginas procesadas:        {num_paginas}")
            print(f"  Total campos en JSON:      {total_campos_json}")
            print(f"  Campos encontrados:        {num_campos_encontrados}")
            print(f"  Match rate:                {match_rate:.1f}%")
            print(f"  Confianza promedio:        {confianza_promedio:.3f}")
            print(f"\n  Total items en 'form':     {len(form_items)}")
            print(f"  Etiquetas detectadas:      {num_links}")
            print(f"  Palabras tokenizadas:      {estadisticas['palabras_tokenizadas']}")

            if campos_faltantes:
                print(f"\n  Campos no encontrados ({len(campos_faltantes)}):")
                for campo in campos_faltantes[:5]:
                    print(f"    - {campo}")
                if len(campos_faltantes) > 5:
                    print(f"    ... y {len(campos_faltantes) - 5} más")

            print(f"\n💾 Guardado:")
            print(f"   Dataset:  {output_file}")
            print(f"   Metadata: {metadata_file}")
            print()

        return {
            "output_data": output_data,
            "metadata": metadata_completa
        }

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def procesar_dataset_completo_layoutlmv3_oficial(
    input_dir: str = "Datos extraidos de Originales",
    output_dir: str = "dataset_layoutlmv3_oficial",
    confianza_minima: float = 0.75,
    usar_ocr: bool = True,
    usar_gpu: bool = False,
    detectar_etiquetas: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Procesa dataset completo en formato LayoutLMv3 oficial.
    """

    print("="*80)
    print("GENERACIÓN DE DATASET - FORMATO LAYOUTLMV3 OFICIAL (FUNSD-STYLE)")
    print("="*80)
    print()

    input_path = Path(input_dir)
    pdfs_dir = input_path / "pdfs"
    json_dir = input_path / "anotaciones"

    if not pdfs_dir.exists():
        print(f"❌ No se encontró directorio de PDFs: {pdfs_dir}")
        return None

    if not json_dir.exists():
        print(f"❌ No se encontró directorio de anotaciones: {json_dir}")
        return None

    pdfs = sorted(list(pdfs_dir.glob("*.pdf")))

    if not pdfs:
        print(f"❌ No hay PDFs en: {pdfs_dir}")
        return None

    print(f"📁 Encontrados {len(pdfs)} PDFs")
    print(f"🔧 OCR: {'Habilitado' if usar_ocr else 'Deshabilitado'}")
    print(f"⚙️  GPU: {'Sí' if usar_gpu else 'No'}")
    print(f"🏷️  Detectar etiquetas: {'Sí' if detectar_etiquetas else 'No'}")
    print(f"📊 Confianza mínima: {confianza_minima}")
    print()

    # Procesar cada documento
    resultados = []
    errores = []

    for pdf_file in tqdm(pdfs, desc="Procesando documentos"):
        json_file = json_dir / (pdf_file.stem + ".json")

        if not json_file.exists():
            print(f"⚠️  JSON no encontrado para: {pdf_file.name}")
            errores.append({
                'pdf': pdf_file.name,
                'error': 'json_no_encontrado'
            })
            continue

        try:
            resultado = procesar_documento_layoutlmv3_oficial(
                str(pdf_file),
                str(json_file),
                output_dir=output_dir,
                confianza_minima=confianza_minima,
                usar_ocr=usar_ocr,
                usar_gpu=usar_gpu,
                detectar_etiquetas=detectar_etiquetas,
                verbose=False
            )

            if resultado:
                metadata = resultado['metadata']
                resultados.append({
                    'documento': pdf_file.name,
                    'campos_encontrados': metadata['estadisticas']['campos_encontrados'],
                    'match_rate': metadata['estadisticas']['match_rate'],
                    'etiquetas_detectadas': metadata['estadisticas']['etiquetas_detectadas']
                })
            else:
                errores.append({
                    'pdf': pdf_file.name,
                    'error': 'procesamiento_fallido'
                })

        except Exception as e:
            print(f"\n❌ Error procesando {pdf_file.name}: {e}")
            errores.append({
                'pdf': pdf_file.name,
                'error': str(e)
            })

    # Estadísticas globales
    print("\n" + "="*80)
    print("📊 ESTADÍSTICAS GLOBALES")
    print("="*80)

    total_procesados = len(resultados)
    total_errores = len(errores)

    if resultados:
        total_campos = sum(r['campos_encontrados'] for r in resultados)
        total_etiquetas = sum(r['etiquetas_detectadas'] for r in resultados)
        match_rate_promedio = sum(r['match_rate'] for r in resultados) / len(resultados)

        print(f"  Documentos procesados:     {total_procesados}/{len(pdfs)}")
        print(f"  Errores:                   {total_errores}")
        print(f"  Total campos generados:    {total_campos}")
        print(f"  Etiquetas detectadas:      {total_etiquetas}")
        print(f"  Match rate promedio:       {match_rate_promedio:.1f}%")
    else:
        print(f"  Documentos procesados:     0/{len(pdfs)}")
        print(f"  Errores:                   {total_errores}")

    # Guardar resumen
    resumen_global = {
        "fecha_generacion": datetime.now().isoformat(),
        "formato": "layoutlmv3_oficial_funsd_v1.0",
        "configuracion": {
            "confianza_minima": confianza_minima,
            "ocr_habilitado": usar_ocr,
            "gpu_habilitado": usar_gpu,
            "detectar_etiquetas": detectar_etiquetas
        },
        "estadisticas": {
            "total_documentos": len(pdfs),
            "documentos_procesados": total_procesados,
            "documentos_con_errores": total_errores,
            "total_campos": total_campos if resultados else 0,
            "total_etiquetas": total_etiquetas if resultados else 0,
            "match_rate_promedio": match_rate_promedio if resultados else 0
        },
        "documentos": resultados,
        "errores": errores
    }

    output_path = Path(output_dir)
    resumen_file = output_path / "dataset_resumen.json"

    with open(resumen_file, 'w', encoding='utf-8') as f:
        json.dump(resumen_global, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resumen guardado: {resumen_file}")

    print("\n" + "="*80)
    print("✅ GENERACIÓN COMPLETADA")
    print("="*80)
    print(f"\nDataset guardado en: {output_dir}/")
    print("\n📝 Formato generado:")
    print("   - *_layoutlm_v3.json: Datos en formato LayoutLMv3 oficial")
    print("   - *_metadata.json: Metadata y estadísticas")
    print("\n✨ Características:")
    print("   ✓ Tokenización por palabras individuales")
    print("   ✓ Labels estándar (question/answer)")
    print("   ✓ Sistema de linking entre etiquetas y valores")
    print("\n🚀 Compatible con:")
    print("   - Herramientas de anotación FUNSD")
    print("   - LayoutLMv3 fine-tuning")
    print("   - Pipelines de evaluación estándar")

    return resumen_global


def main():
    """Función principal."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Genera dataset en formato LayoutLMv3 OFICIAL (FUNSD-style)"
    )

    parser.add_argument(
        "--modo",
        choices=["prueba", "completo"],
        default="completo",
        help="Modo de ejecución"
    )

    parser.add_argument(
        "--input-dir",
        default="Datos extraidos de Originales",
        help="Directorio con PDFs y JSONs"
    )

    parser.add_argument(
        "--output-dir",
        default="dataset_layoutlmv3_oficial",
        help="Directorio de salida"
    )

    parser.add_argument(
        "--confianza-minima",
        type=float,
        default=0.75,
        help="Umbral mínimo de confianza"
    )

    parser.add_argument(
        "--sin-ocr",
        action="store_true",
        help="Deshabilitar OCR"
    )

    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Usar GPU para OCR"
    )

    parser.add_argument(
        "--sin-etiquetas",
        action="store_true",
        help="No detectar etiquetas automáticamente"
    )

    parser.add_argument(
        "--pdf",
        help="Procesar un PDF específico (modo prueba)"
    )

    parser.add_argument(
        "--json",
        help="JSON correspondiente (modo prueba)"
    )

    args = parser.parse_args()

    if not DEPS_OK:
        print("\n❌ No se pueden cargar las dependencias")
        sys.exit(1)

    if args.modo == "prueba":
        if args.pdf and args.json:
            pdf_path = args.pdf
            json_path = args.json
        else:
            input_path = Path(args.input_dir)
            pdfs_dir = input_path / "pdfs"
            json_dir = input_path / "anotaciones"

            pdfs = sorted(list(pdfs_dir.glob("*.pdf")))
            if not pdfs:
                print("❌ No hay PDFs para procesar")
                sys.exit(1)

            pdf_path = pdfs[0]
            json_path = json_dir / (pdf_path.stem + ".json")

            if not json_path.exists():
                print(f"❌ JSON no encontrado: {json_path}")
                sys.exit(1)

        resultado = procesar_documento_layoutlmv3_oficial(
            str(pdf_path),
            str(json_path),
            output_dir=args.output_dir,
            confianza_minima=args.confianza_minima,
            usar_ocr=not args.sin_ocr,
            usar_gpu=args.gpu,
            detectar_etiquetas=not args.sin_etiquetas,
            verbose=True
        )

        if resultado:
            print("\n✅ Prueba completada exitosamente")
        else:
            print("\n❌ Prueba fallida")
            sys.exit(1)

    else:
        resultado = procesar_dataset_completo_layoutlmv3_oficial(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            confianza_minima=args.confianza_minima,
            usar_ocr=not args.sin_ocr,
            usar_gpu=args.gpu,
            detectar_etiquetas=not args.sin_etiquetas
        )

        if resultado and resultado['estadisticas']['documentos_procesados'] > 0:
            print("\n✅ Dataset generado exitosamente")
        else:
            print("\n❌ No se pudo generar el dataset")
            sys.exit(1)


if __name__ == "__main__":
    main()
