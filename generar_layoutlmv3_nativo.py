#!/usr/bin/env python3
"""
Script para generar dataset en formato LayoutLMv3 NATIVO.

Genera el formato oficial de LayoutLMv3 con estructura:
- meta: información del documento
- form: array con campos detectados (id, text, label, words, box, linking, page, confidence)
- estadisticas: métricas de procesamiento
- campos_faltantes: campos del JSON que no se encontraron

Este formato es compatible con herramientas de anotación y entrenamiento de LayoutLMv3.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.extractors.hybrid_extractor import HybridPDFExtractor
    from src.matchers.advanced_fuzzy_matcher import AdvancedFuzzyMatcher
    from src.normalizers.layoutlm_normalizer import LayoutLMNormalizer
    from src.validation.dataset_validator import DatasetValidator
    from src.extractors.json_parser import JSONParser
    import fitz
    DEPS_OK = True
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("\nInstala las dependencias:")
    print("  pip install PyMuPDF rapidfuzz numpy pandas tqdm")
    print("  pip install opencv-python paddlepaddle paddleocr")
    DEPS_OK = False


def procesar_documento_layoutlmv3_nativo(
    pdf_path,
    json_path,
    output_dir="dataset_layoutlmv3_nativo",
    confianza_minima=0.75,
    usar_ocr=True,
    usar_gpu=False,
    verbose=True
):
    """
    Procesa documento y genera formato LayoutLMv3 NATIVO.

    Formato de salida:
    {
      "meta": {
        "version": "1.0",
        "documento": "archivo.pdf",
        "num_paginas": 2
      },
      "form": [
        {
          "id": 0,
          "text": "20123456789",
          "label": "RUC",
          "words": [{"text": "20123456789", "box": [120, 45, 250, 68]}],
          "box": [120, 45, 250, 68],
          "linking": [],
          "page": 0,
          "confidence": 0.98
        }
      ],
      "estadisticas": {
        "total_campos": 25,
        "campos_encontrados": 22,
        "match_rate": 88.0,
        "confianza_promedio": 0.945
      },
      "campos_faltantes": ["campo1", "campo2"]
    }

    Args:
        pdf_path: Ruta al PDF
        json_path: Ruta al JSON con anotaciones
        output_dir: Directorio de salida
        confianza_minima: Umbral mínimo de confianza
        usar_ocr: Habilitar OCR para PDFs rasterizados
        usar_gpu: Usar GPU para OCR
        verbose: Mostrar progreso detallado

    Returns:
        Dict con resultado en formato LayoutLMv3 nativo
    """

    if not DEPS_OK:
        print("❌ Dependencias no disponibles")
        return None

    if verbose:
        print("="*80)
        print("GENERACIÓN DE DATASET - FORMATO LAYOUTLMV3 NATIVO")
        print("="*80)
        print(f"PDF:  {pdf_path}")
        print(f"JSON: {json_path}")
        print(f"OCR:  {'Habilitado' if usar_ocr else 'Deshabilitado'}")
        print(f"GPU:  {'Sí' if usar_gpu else 'No'}")
        print()

    # Crear directorio de salida
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Inicializar extractor híbrido
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

        # 2. Inicializar fuzzy matcher avanzado
        matcher = AdvancedFuzzyMatcher(
            threshold=80.0,
            use_field_specific_normalization=True,
            use_weighted_strategies=True
        )

        # 3. Parsear JSON
        if verbose:
            print("📄 Parseando JSON...")

        json_parser = JSONParser()
        fields = json_parser.extract_fields(json_path)

        if verbose:
            print(f"   Total de campos en JSON: {len(fields)}")

        # 4. Abrir PDF y obtener número de páginas
        doc = fitz.open(pdf_path)
        num_paginas = len(doc)
        doc.close()

        pdf_name = Path(pdf_path).stem

        if verbose:
            print(f"   Páginas del PDF: {num_paginas}\n")

        # 5. Procesar cada página y recopilar matches
        form_items = []  # Array para "form"
        campos_encontrados = set()
        total_confianza = 0.0
        metodos_usados = []

        item_id = 0  # ID secuencial para cada item en "form"

        for page_num in range(num_paginas):
            if verbose:
                print(f"📄 Procesando página {page_num + 1}/{num_paginas}...")

            # Extraer palabras con pipeline híbrido
            words_data, metodo = extractor.extract_words_hybrid(
                pdf_path,
                page_num=page_num
            )

            metodos_usados.append(metodo)

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

            # Buscar cada campo en esta página
            for field_name, field_value in fields.items():
                if not field_value or not str(field_value).strip():
                    continue

                # Evitar duplicados (solo matchear cada campo una vez)
                if field_name in campos_encontrados:
                    continue

                # Buscar match usando fuzzy matcher avanzado
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

                    if es_valido:
                        # Crear item en formato LayoutLMv3 nativo
                        form_item = {
                            "id": item_id,
                            "text": match.text,  # Texto exacto encontrado en el PDF
                            "label": field_name,  # Nombre del campo del JSON
                            "words": [
                                {
                                    "text": match.text,
                                    "box": bbox_norm
                                }
                            ],
                            "box": bbox_norm,  # [x0, y0, x1, y1] en escala 0-1000
                            "linking": [],  # Array vacío para futuras relaciones entre campos
                            "page": page_num,  # Número de página (0-indexed)
                            "confidence": match.confidence  # Confianza del matching (0-1)
                        }

                        form_items.append(form_item)
                        campos_encontrados.add(field_name)
                        total_confianza += match.confidence
                        item_id += 1

                        if verbose:
                            print(f"   ✓ {field_name}: '{match.text}' (conf: {match.confidence:.3f})")

                    else:
                        if verbose:
                            print(f"   ⚠️  Bbox inválida descartada: {field_name}")
                elif match:
                    if verbose:
                        print(f"   ⚠️  Filtrado por baja confianza: {field_name} ({match.confidence:.2f})")

            if verbose:
                print()

        # 6. Calcular campos faltantes
        campos_faltantes = [
            field_name
            for field_name in fields.keys()
            if field_name not in campos_encontrados and fields[field_name]
        ]

        # 7. Calcular estadísticas
        total_campos_json = len([v for v in fields.values() if v and str(v).strip()])
        num_campos_encontrados = len(campos_encontrados)
        match_rate = (num_campos_encontrados / total_campos_json * 100) if total_campos_json > 0 else 0.0
        confianza_promedio = (total_confianza / num_campos_encontrados) if num_campos_encontrados > 0 else 0.0

        # 8. Construir salida en formato LayoutLMv3 nativo
        output_data = {
            "meta": {
                "version": "1.0",
                "documento": Path(pdf_path).name,
                "num_paginas": num_paginas,
                "fecha_generacion": datetime.now().isoformat(),
                "metodos_extraccion": list(set(metodos_usados))
            },
            "form": form_items,
            "estadisticas": {
                "total_campos": total_campos_json,
                "campos_encontrados": num_campos_encontrados,
                "match_rate": round(match_rate, 2),
                "confianza_promedio": round(confianza_promedio, 3)
            },
            "campos_faltantes": sorted(campos_faltantes)
        }

        # 9. Guardar archivo
        output_file = output_path / f"{pdf_name}_layoutlm.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

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
            print(f"  Campos faltantes:          {len(campos_faltantes)}")

            if campos_faltantes:
                print(f"\n  Campos no encontrados:")
                for campo in campos_faltantes[:10]:  # Mostrar máximo 10
                    print(f"    - {campo}")
                if len(campos_faltantes) > 10:
                    print(f"    ... y {len(campos_faltantes) - 10} más")

            print(f"\n💾 Guardado en:             {output_file}")
            print()

        return output_data

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def procesar_dataset_completo_layoutlmv3_nativo(
    input_dir="Datos extraidos de Originales",
    output_dir="dataset_layoutlmv3_nativo",
    confianza_minima=0.75,
    usar_ocr=True,
    usar_gpu=False
):
    """
    Procesa dataset completo en formato LayoutLMv3 nativo.

    Args:
        input_dir: Directorio con PDFs y JSONs
        output_dir: Directorio de salida
        confianza_minima: Umbral mínimo de confianza
        usar_ocr: Habilitar OCR
        usar_gpu: Usar GPU para OCR

    Returns:
        Dict con estadísticas generales
    """

    print("="*80)
    print("GENERACIÓN DE DATASET - FORMATO LAYOUTLMV3 NATIVO")
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
            resultado = procesar_documento_layoutlmv3_nativo(
                str(pdf_file),
                str(json_file),
                output_dir=output_dir,
                confianza_minima=confianza_minima,
                usar_ocr=usar_ocr,
                usar_gpu=usar_gpu,
                verbose=False
            )

            if resultado:
                resultados.append({
                    'documento': pdf_file.name,
                    'campos_encontrados': resultado['estadisticas']['campos_encontrados'],
                    'match_rate': resultado['estadisticas']['match_rate'],
                    'confianza_promedio': resultado['estadisticas']['confianza_promedio']
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
        match_rate_promedio = sum(r['match_rate'] for r in resultados) / len(resultados)
        confianza_global = sum(r['confianza_promedio'] for r in resultados) / len(resultados)

        print(f"  Documentos procesados:     {total_procesados}/{len(pdfs)}")
        print(f"  Errores:                   {total_errores}")
        print(f"  Total campos generados:    {total_campos}")
        print(f"  Match rate promedio:       {match_rate_promedio:.1f}%")
        print(f"  Confianza promedio:        {confianza_global:.3f}")
    else:
        print(f"  Documentos procesados:     0/{len(pdfs)}")
        print(f"  Errores:                   {total_errores}")

    # Guardar resumen global
    resumen_global = {
        "fecha_generacion": datetime.now().isoformat(),
        "formato": "layoutlmv3_nativo_v1.0",
        "configuracion": {
            "confianza_minima": confianza_minima,
            "ocr_habilitado": usar_ocr,
            "gpu_habilitado": usar_gpu,
            "input_dir": str(input_dir),
            "output_dir": str(output_dir)
        },
        "estadisticas": {
            "total_documentos": len(pdfs),
            "documentos_procesados": total_procesados,
            "documentos_con_errores": total_errores,
            "total_campos": total_campos if resultados else 0,
            "match_rate_promedio": match_rate_promedio if resultados else 0,
            "confianza_promedio": confianza_global if resultados else 0
        },
        "documentos": resultados,
        "errores": errores
    }

    output_path = Path(output_dir)
    resumen_file = output_path / "dataset_resumen.json"

    with open(resumen_file, 'w', encoding='utf-8') as f:
        json.dump(resumen_global, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resumen global guardado en: {resumen_file}")

    print("\n" + "="*80)
    print("✅ GENERACIÓN DE DATASET COMPLETADA")
    print("="*80)
    print(f"\nDataset guardado en: {output_dir}/")
    print("Formato: LayoutLMv3 NATIVO")
    print("\n📝 Cada archivo *_layoutlm.json contiene:")
    print("   - meta: información del documento")
    print("   - form: array con campos en formato LayoutLMv3")
    print("   - estadisticas: métricas de matching")
    print("   - campos_faltantes: campos no encontrados")
    print("\n🚀 SIGUIENTE PASO:")
    print("   Estos archivos son compatibles con herramientas de anotación")
    print("   y entrenamiento de LayoutLMv3")

    return resumen_global


def main():
    """Función principal."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Genera dataset en formato LayoutLMv3 NATIVO"
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
        default="dataset_layoutlmv3_nativo",
        help="Directorio de salida"
    )

    parser.add_argument(
        "--confianza-minima",
        type=float,
        default=0.75,
        help="Umbral mínimo de confianza (default: 0.75)"
    )

    parser.add_argument(
        "--sin-ocr",
        action="store_true",
        help="Deshabilitar OCR (solo extracción nativa)"
    )

    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Usar GPU para OCR (requiere CUDA)"
    )

    parser.add_argument(
        "--pdf",
        help="Procesar un PDF específico (modo prueba)"
    )

    parser.add_argument(
        "--json",
        help="JSON correspondiente al PDF (modo prueba)"
    )

    args = parser.parse_args()

    if not DEPS_OK:
        print("\n❌ No se pueden cargar las dependencias necesarias")
        sys.exit(1)

    if args.modo == "prueba":
        # Modo prueba
        if args.pdf and args.json:
            # PDF y JSON específicos
            pdf_path = args.pdf
            json_path = args.json
        else:
            # Tomar primer PDF del directorio
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

        resultado = procesar_documento_layoutlmv3_nativo(
            str(pdf_path),
            str(json_path),
            output_dir=args.output_dir,
            confianza_minima=args.confianza_minima,
            usar_ocr=not args.sin_ocr,
            usar_gpu=args.gpu,
            verbose=True
        )

        if resultado:
            print("\n✅ Prueba completada exitosamente")
            print(f"\n📄 Formato generado:")
            print(f"   Campos en 'form': {len(resultado['form'])}")
            print(f"   Match rate: {resultado['estadisticas']['match_rate']}%")
            print(f"   Campos faltantes: {len(resultado['campos_faltantes'])}")
        else:
            print("\n❌ Prueba fallida")
            sys.exit(1)

    else:
        # Modo completo
        resultado = procesar_dataset_completo_layoutlmv3_nativo(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            confianza_minima=args.confianza_minima,
            usar_ocr=not args.sin_ocr,
            usar_gpu=args.gpu
        )

        if resultado and resultado['estadisticas']['documentos_procesados'] > 0:
            print("\n✅ Dataset generado exitosamente")
        else:
            print("\n❌ No se pudo generar el dataset")
            sys.exit(1)


if __name__ == "__main__":
    main()
