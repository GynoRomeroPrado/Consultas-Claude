#!/usr/bin/env python3
"""
Script avanzado para generar dataset con todas las mejoras implementadas.

MEJORAS FASE 1:
- Normalización de coordenadas 0-1000 para LayoutLMv3
- Validación exhaustiva de calidad
- Samples independientes por página
- Filtrado por confianza

MEJORAS FASE 2:
- Pipeline híbrido nativo/OCR con detección automática
- Preprocesamiento de imagen con OpenCV
- PaddleOCR para PDFs rasterizados
- Fuzzy matching avanzado con normalización específica por campo
- Estrategias de matching ponderadas
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


def procesar_documento_avanzado(
    pdf_path,
    json_path,
    output_dir="dataset_avanzado",
    confianza_minima=0.75,
    usar_ocr=True,
    usar_gpu=False,
    verbose=True
):
    """
    Procesa documento con pipeline avanzado completo.

    Args:
        pdf_path: Ruta al PDF
        json_path: Ruta al JSON con anotaciones
        output_dir: Directorio de salida
        confianza_minima: Umbral mínimo de confianza
        usar_ocr: Habilitar OCR para PDFs rasterizados
        usar_gpu: Usar GPU para OCR (requiere CUDA)
        verbose: Mostrar progreso detallado

    Returns:
        Dict con resultados
    """

    if not DEPS_OK:
        print("❌ Dependencias no disponibles")
        return None

    if verbose:
        print("="*80)
        print("GENERACIÓN DE DATASET AVANZADO (FASE 2)")
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
            print(f"   Total de campos: {len(fields)}")

        # 4. Abrir PDF y obtener número de páginas
        doc = fitz.open(pdf_path)
        num_paginas = len(doc)
        doc.close()

        if verbose:
            print(f"   Páginas del PDF: {num_paginas}\n")

        # 5. Procesar cada página
        coords_por_pagina = {}
        stats_por_pagina = {}

        for page_num in range(num_paginas):
            if verbose:
                print(f"📄 Procesando página {page_num + 1}/{num_paginas}...")

            # Extraer palabras con pipeline híbrido
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

            # Buscar cada campo en esta página
            coords_pagina = []
            matched_fields = 0
            filtered_fields = 0
            invalid_fields = 0

            for field_name, field_value in fields.items():
                if not field_value or not str(field_value).strip():
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
                        coords_pagina.append({
                            "campo": field_name,
                            "texto": str(field_value),
                            "bbox_original": list(match.bbox),
                            "bbox_normalizada": bbox_norm,
                            "pagina": page_num,
                            "confianza": match.confidence,
                            "tipo_matching": match.match_type,
                            "metodo_extraccion": metodo,
                            "dimensiones_pagina": {
                                "ancho": page_width,
                                "alto": page_height
                            },
                            "metadata": match.metadata
                        })
                        matched_fields += 1
                    else:
                        invalid_fields += 1
                        if verbose:
                            print(f"   ⚠️  Bbox inválida descartada: {field_name}")
                elif match:
                    filtered_fields += 1
                    if verbose:
                        print(f"   ⚠️  Filtrado por baja confianza: {field_name} ({match.confidence:.2f})")

            if coords_pagina:
                coords_por_pagina[page_num] = coords_pagina

            stats_por_pagina[page_num] = {
                'palabras_extraidas': len(words_data),
                'metodo': metodo,
                'campos_encontrados': matched_fields,
                'campos_filtrados': filtered_fields,
                'campos_invalidos': invalid_fields
            }

            if verbose:
                print(f"   Campos válidos: {matched_fields}")
                print(f"   Filtrados: {filtered_fields}, Inválidos: {invalid_fields}\n")

        # 6. Generar archivos de salida
        pdf_name = Path(pdf_path).stem
        archivos_generados = []
        total_campos_validos = 0

        for page_num in sorted(coords_por_pagina.keys()):
            coords = coords_por_pagina[page_num]

            if not coords:
                continue

            total_campos_validos += len(coords)

            # Sample para esta página
            sample = {
                "documento_id": f"{pdf_name}_page_{page_num}",
                "documento_origen": Path(pdf_path).name,
                "json_origen": Path(json_path).name,
                "pagina": page_num,
                "total_paginas": num_paginas,
                "fecha_generacion": datetime.now().isoformat(),
                "version_formato": "layoutlmv3_avanzado_v1",
                "total_campos": len(coords),
                "confianza_promedio": sum(c['confianza'] for c in coords) / len(coords),
                "metodo_extraccion": stats_por_pagina[page_num]['metodo'],
                "coordenadas": coords
            }

            # Guardar
            output_file = output_path / f"{pdf_name}_page_{page_num}_avanzado.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sample, f, indent=2, ensure_ascii=False)

            archivos_generados.append(str(output_file))

        # 7. Generar resumen
        resumen = {
            "documento_origen": Path(pdf_path).name,
            "json_origen": Path(json_path).name,
            "fecha_procesamiento": datetime.now().isoformat(),
            "configuracion": {
                "ocr_habilitado": usar_ocr,
                "gpu_habilitado": usar_gpu,
                "confianza_minima": confianza_minima,
                "preprocesamiento_imagen": True,
                "fuzzy_matching_avanzado": True
            },
            "estadisticas": {
                "total_paginas": num_paginas,
                "paginas_con_datos": len(coords_por_pagina),
                "total_campos_json": len(fields),
                "campos_finales": total_campos_validos,
                "metodos_usados": list(set(s['metodo'] for s in stats_por_pagina.values()))
            },
            "estadisticas_por_pagina": stats_por_pagina,
            "archivos_generados": archivos_generados
        }

        resumen_file = output_path / f"{pdf_name}_resumen_avanzado.json"
        with open(resumen_file, 'w', encoding='utf-8') as f:
            json.dump(resumen, f, indent=2, ensure_ascii=False)

        if verbose:
            print("="*80)
            print("📊 RESUMEN FINAL")
            print("="*80)
            print(f"  Páginas procesadas:        {len(coords_por_pagina)}/{num_paginas}")
            print(f"  Campos finales:            {total_campos_validos}")
            print(f"  Métodos usados:            {', '.join(resumen['estadisticas']['metodos_usados'])}")
            print(f"  Archivos generados:        {len(archivos_generados)}")
            print(f"\n💾 Resumen guardado en:     {resumen_file}")

        return resumen

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def procesar_dataset_completo_avanzado(
    input_dir="Datos extraidos de Originales",
    output_dir="dataset_avanzado",
    confianza_minima=0.75,
    usar_ocr=True,
    usar_gpu=False,
    validar_al_final=True
):
    """
    Procesa dataset completo con pipeline avanzado.

    Args:
        input_dir: Directorio con PDFs y JSONs
        output_dir: Directorio de salida
        confianza_minima: Umbral mínimo de confianza
        usar_ocr: Habilitar OCR
        usar_gpu: Usar GPU para OCR
        validar_al_final: Ejecutar validador al final

    Returns:
        Dict con estadísticas generales
    """

    print("="*80)
    print("GENERACIÓN DE DATASET COMPLETO - PIPELINE AVANZADO")
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
            resultado = procesar_documento_avanzado(
                str(pdf_file),
                str(json_file),
                output_dir=output_dir,
                confianza_minima=confianza_minima,
                usar_ocr=usar_ocr,
                usar_gpu=usar_gpu,
                verbose=False
            )

            if resultado:
                resultados.append(resultado)
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
    total_campos = sum(r['estadisticas']['campos_finales'] for r in resultados)
    total_paginas = sum(r['estadisticas']['paginas_con_datos'] for r in resultados)

    # Contar métodos usados
    metodos_count = {}
    for r in resultados:
        for metodo in r['estadisticas']['metodos_usados']:
            metodos_count[metodo] = metodos_count.get(metodo, 0) + 1

    print(f"  Documentos procesados:     {total_procesados}/{len(pdfs)}")
    print(f"  Errores:                   {total_errores}")
    print(f"  Total campos generados:    {total_campos}")
    print(f"  Total páginas con datos:   {total_paginas}")
    print(f"\n  Métodos de extracción usados:")
    for metodo, count in metodos_count.items():
        print(f"    - {metodo.upper()}: {count} páginas")

    # Guardar resumen global
    resumen_global = {
        "fecha_generacion": datetime.now().isoformat(),
        "version_formato": "layoutlmv3_avanzado_v1",
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
            "total_campos": total_campos,
            "total_paginas": total_paginas,
            "metodos_usados": metodos_count
        },
        "documentos": resultados,
        "errores": errores
    }

    output_path = Path(output_dir)
    resumen_file = output_path / "dataset_avanzado_resumen.json"

    with open(resumen_file, 'w', encoding='utf-8') as f:
        json.dump(resumen_global, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resumen global guardado en: {resumen_file}")

    # Validar calidad del dataset
    if validar_al_final and total_procesados > 0:
        print("\n" + "="*80)
        print("🔍 VALIDANDO CALIDAD DEL DATASET")
        print("="*80)

        validator = DatasetValidator(
            confianza_minima=confianza_minima,
            area_minima=10
        )

        try:
            metricas_validacion = validator.validar_dataset(
                output_dir,
                verbose=True
            )

            resumen_global['validacion'] = {
                'apto_entrenamiento': metricas_validacion['apto_entrenamiento'],
                'total_errores_criticos': len(metricas_validacion['errores_criticos']),
                'total_advertencias': len(metricas_validacion['advertencias'])
            }

            # Guardar resumen actualizado
            with open(resumen_file, 'w', encoding='utf-8') as f:
                json.dump(resumen_global, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️  Error en validación: {e}")

    print("\n" + "="*80)
    print("✅ GENERACIÓN DE DATASET COMPLETADA")
    print("="*80)
    print(f"\nDataset guardado en: {output_dir}/")
    print("\n🚀 SIGUIENTE PASO:")
    print("   El dataset está listo para entrenar LayoutLMv3")

    return resumen_global


def main():
    """Función principal."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Genera dataset con pipeline avanzado (Fase 1 + Fase 2)"
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
        default="dataset_avanzado",
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
        "--no-validar",
        action="store_true",
        help="No ejecutar validador al final"
    )

    args = parser.parse_args()

    if not DEPS_OK:
        print("\n❌ No se pueden cargar las dependencias necesarias")
        sys.exit(1)

    if args.modo == "prueba":
        # Modo prueba
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

        resultado = procesar_documento_avanzado(
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
        else:
            print("\n❌ Prueba fallida")
            sys.exit(1)

    else:
        # Modo completo
        resultado = procesar_dataset_completo_avanzado(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            confianza_minima=args.confianza_minima,
            usar_ocr=not args.sin_ocr,
            usar_gpu=args.gpu,
            validar_al_final=not args.no_validar
        )

        if resultado and resultado['estadisticas']['documentos_procesados'] > 0:
            print("\n✅ Dataset generado exitosamente")
        else:
            print("\n❌ No se pudo generar el dataset")
            sys.exit(1)


if __name__ == "__main__":
    main()
