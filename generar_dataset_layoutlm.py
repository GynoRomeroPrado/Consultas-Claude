#!/usr/bin/env python3
"""
Script para generar dataset optimizado para LayoutLMv3.

Mejoras implementadas:
- Normalización de coordenadas 0-1000 (estándar LayoutLMv3)
- Validación automática de calidad
- Formato por página (samples independientes)
- Filtrado por confianza
- Exportación en formato LayoutLMv3-ready
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.core.pipeline import CoordinateExtractionPipeline
    from src.core.config import PipelineConfig, MatchStrategy, ExportFormat, MatcherConfig, ExporterConfig
    from src.normalizers.layoutlm_normalizer import LayoutLMNormalizer
    from src.validation.dataset_validator import DatasetValidator
    import fitz
except ImportError as e:
    print(f"❌ Error: {e}")
    print("\nInstala las dependencias:")
    print("  pip install PyMuPDF rapidfuzz numpy pandas tqdm")
    sys.exit(1)


def procesar_documento_layoutlm(
    pdf_path,
    json_path,
    output_dir="dataset_layoutlm",
    confianza_minima=0.75,
    verbose=True
):
    """
    Procesa un documento y genera dataset en formato LayoutLMv3.

    Args:
        pdf_path: Ruta al PDF
        json_path: Ruta al JSON con anotaciones
        output_dir: Directorio de salida
        confianza_minima: Umbral mínimo de confianza para incluir campo
        verbose: Mostrar progreso

    Returns:
        Dict con resultados
    """

    if verbose:
        print("="*80)
        print("GENERACIÓN DE DATASET PARA LAYOUTLMV3")
        print("="*80)
        print(f"PDF:  {pdf_path}")
        print(f"JSON: {json_path}")
        print()

    # Crear directorio de salida
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Configuración del pipeline
    config = PipelineConfig(
        matcher=MatcherConfig(
            strategy=MatchStrategy.AUTO,
            fuzzy_threshold=80.0,
            prefer_first_match=True
        ),
        exporter=ExporterConfig(
            format=ExportFormat.JSON,
            include_confidence=True,
            include_metadata=True
        ),
        verbose=verbose
    )

    pipeline = CoordinateExtractionPipeline(config=config)

    try:
        # Procesar documento
        if verbose:
            print("🔄 Extrayendo coordenadas...\n")

        result = pipeline.process(
            pdf_path=pdf_path,
            json_path=json_path,
            output_path=None
        )

        stats = result['statistics']

        if verbose:
            print("\n" + "="*80)
            print("📊 RESULTADOS INICIALES")
            print("="*80)
            print(f"  Total de campos:       {stats['total_fields']}")
            print(f"  Campos encontrados:    {stats['matched_fields']}")
            print(f"  Tasa de éxito:         {stats['match_rate']:.1f}%")
            print(f"  Confianza promedio:    {stats['average_confidence']:.4f}")

        # Abrir PDF para obtener dimensiones por página
        doc = fitz.open(pdf_path)
        num_paginas = len(doc)

        # Agrupar coordenadas por página
        coords_por_pagina = {}
        coords_filtradas = 0
        coords_invalidas = 0

        for match, field_name in zip(result['matches'], result['field_names']):
            page_num = match.page_num

            if page_num not in coords_por_pagina:
                coords_por_pagina[page_num] = []

            # Filtrar por confianza
            if match.confidence < confianza_minima:
                coords_filtradas += 1
                if verbose:
                    print(f"⚠️  Filtrado por baja confianza: {field_name} "
                          f"({match.confidence:.2f})")
                continue

            # Obtener dimensiones de la página
            page = doc[page_num]
            page_width = page.rect.width
            page_height = page.rect.height

            # Normalizar coordenadas a escala 0-1000
            bbox_norm, es_valido = LayoutLMNormalizer.normalize_bbox_safe(
                match.bbox,
                page_width,
                page_height
            )

            if not es_valido:
                coords_invalidas += 1
                if verbose:
                    print(f"⚠️  Bbox inválida descartada: {field_name}")
                continue

            # Agregar coordenada normalizada
            coords_por_pagina[page_num].append({
                "campo": field_name,
                "texto": match.text,
                "bbox_original": list(match.bbox),
                "bbox_normalizada": bbox_norm,
                "pagina": page_num,
                "confianza": match.confidence,
                "tipo_matching": match.match_type,
                "dimensiones_pagina": {
                    "ancho": page_width,
                    "alto": page_height
                }
            })

        doc.close()

        if verbose:
            print(f"\n🔍 Filtrado de coordenadas:")
            print(f"  Filtradas por confianza:  {coords_filtradas}")
            print(f"  Descartadas (inválidas):  {coords_invalidas}")
            print(f"  Coordenadas válidas:      {sum(len(c) for c in coords_por_pagina.values())}")

        # Generar archivos de salida por página
        pdf_name = Path(pdf_path).stem
        archivos_generados = []

        for page_num in sorted(coords_por_pagina.keys()):
            coords = coords_por_pagina[page_num]

            if not coords:
                continue

            # Crear sample de entrenamiento para esta página
            sample = {
                "documento_id": f"{pdf_name}_page_{page_num}",
                "documento_origen": Path(pdf_path).name,
                "json_origen": Path(json_path).name,
                "pagina": page_num,
                "total_paginas": num_paginas,
                "fecha_generacion": datetime.now().isoformat(),
                "version_formato": "layoutlmv3_v1",
                "total_campos": len(coords),
                "confianza_promedio": sum(c['confianza'] for c in coords) / len(coords),
                "coordenadas": coords
            }

            # Guardar archivo individual
            output_file = output_path / f"{pdf_name}_page_{page_num}_layoutlm.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sample, f, indent=2, ensure_ascii=False)

            archivos_generados.append(str(output_file))

            if verbose:
                print(f"\n✅ Página {page_num}: {len(coords)} campos → {output_file.name}")

        # Generar resumen
        resumen = {
            "documento_origen": Path(pdf_path).name,
            "json_origen": Path(json_path).name,
            "fecha_procesamiento": datetime.now().isoformat(),
            "estadisticas": {
                "total_paginas": num_paginas,
                "paginas_con_datos": len(coords_por_pagina),
                "total_campos_originales": stats['total_fields'],
                "campos_extraidos": stats['matched_fields'],
                "campos_filtrados_confianza": coords_filtradas,
                "campos_invalidos": coords_invalidas,
                "campos_finales": sum(len(c) for c in coords_por_pagina.values()),
                "match_rate_original": stats['match_rate'],
                "confianza_promedio": stats['average_confidence'],
                "confianza_minima_aplicada": confianza_minima
            },
            "archivos_generados": archivos_generados,
            "distribucion_por_pagina": {
                str(p): len(c) for p, c in coords_por_pagina.items()
            }
        }

        resumen_file = output_path / f"{pdf_name}_resumen.json"
        with open(resumen_file, 'w', encoding='utf-8') as f:
            json.dump(resumen, f, indent=2, ensure_ascii=False)

        if verbose:
            print("\n" + "="*80)
            print("📊 RESUMEN FINAL")
            print("="*80)
            print(f"  Páginas procesadas:        {len(coords_por_pagina)}/{num_paginas}")
            print(f"  Campos finales:            {resumen['estadisticas']['campos_finales']}")
            print(f"  Archivos generados:        {len(archivos_generados)}")
            print(f"\n💾 Resumen guardado en:     {resumen_file}")

        return resumen

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def procesar_dataset_completo(
    input_dir="Datos extraidos de Originales",
    output_dir="dataset_layoutlm",
    confianza_minima=0.75,
    validar_al_final=True
):
    """
    Procesa dataset completo y genera formato LayoutLMv3.

    Args:
        input_dir: Directorio con PDFs y JSONs
        output_dir: Directorio de salida
        confianza_minima: Umbral mínimo de confianza
        validar_al_final: Si ejecutar validador de calidad al final

    Returns:
        Dict con estadísticas generales
    """

    print("="*80)
    print("GENERACIÓN DE DATASET COMPLETO PARA LAYOUTLMV3")
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

    # Buscar PDFs
    pdfs = sorted(list(pdfs_dir.glob("*.pdf")))

    if not pdfs:
        print(f"❌ No hay PDFs en: {pdfs_dir}")
        return None

    print(f"📁 Encontrados {len(pdfs)} PDFs")
    print(f"📊 Confianza mínima: {confianza_minima}")
    print()

    # Procesar cada documento
    resultados = []
    errores = []

    for pdf_file in tqdm(pdfs, desc="Procesando documentos"):
        # Buscar JSON correspondiente
        json_file = json_dir / (pdf_file.stem + ".json")

        if not json_file.exists():
            print(f"⚠️  JSON no encontrado para: {pdf_file.name}")
            errores.append({
                'pdf': pdf_file.name,
                'error': 'json_no_encontrado'
            })
            continue

        # Procesar
        try:
            resultado = procesar_documento_layoutlm(
                str(pdf_file),
                str(json_file),
                output_dir=output_dir,
                confianza_minima=confianza_minima,
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

    print(f"  Documentos procesados:     {total_procesados}/{len(pdfs)}")
    print(f"  Errores:                   {total_errores}")
    print(f"  Total campos generados:    {total_campos}")
    print(f"  Total páginas con datos:   {total_paginas}")

    if resultados:
        confianza_prom_global = sum(
            r['estadisticas']['confianza_promedio'] for r in resultados
        ) / len(resultados)
        print(f"  Confianza promedio global: {confianza_prom_global:.4f}")

    # Guardar resumen global
    resumen_global = {
        "fecha_generacion": datetime.now().isoformat(),
        "version_formato": "layoutlmv3_v1",
        "configuracion": {
            "confianza_minima": confianza_minima,
            "input_dir": str(input_dir),
            "output_dir": str(output_dir)
        },
        "estadisticas": {
            "total_documentos": len(pdfs),
            "documentos_procesados": total_procesados,
            "documentos_con_errores": total_errores,
            "total_campos": total_campos,
            "total_paginas": total_paginas,
            "confianza_promedio_global": confianza_prom_global if resultados else 0
        },
        "documentos": resultados,
        "errores": errores
    }

    output_path = Path(output_dir)
    resumen_file = output_path / "dataset_completo_resumen.json"

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

            # Agregar validación al resumen
            resumen_global['validacion'] = metricas_validacion

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
    print("   Usa los archivos *_layoutlm.json para el entrenamiento")

    return resumen_global


def main():
    """Función principal."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Genera dataset optimizado para LayoutLMv3"
    )

    parser.add_argument(
        "--modo",
        choices=["prueba", "completo"],
        default="completo",
        help="Modo de ejecución (default: completo)"
    )

    parser.add_argument(
        "--input-dir",
        default="Datos extraidos de Originales",
        help="Directorio con PDFs y JSONs"
    )

    parser.add_argument(
        "--output-dir",
        default="dataset_layoutlm",
        help="Directorio de salida (default: dataset_layoutlm)"
    )

    parser.add_argument(
        "--confianza-minima",
        type=float,
        default=0.75,
        help="Umbral mínimo de confianza (default: 0.75)"
    )

    parser.add_argument(
        "--no-validar",
        action="store_true",
        help="No ejecutar validador al final"
    )

    args = parser.parse_args()

    if args.modo == "prueba":
        # Modo prueba: procesar solo el primer PDF
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

        resultado = procesar_documento_layoutlm(
            str(pdf_path),
            str(json_path),
            output_dir=args.output_dir,
            confianza_minima=args.confianza_minima,
            verbose=True
        )

        if resultado:
            print("\n✅ Prueba completada exitosamente")
            print("\nSi el resultado es correcto, ejecuta en modo completo:")
            print(f"  python {sys.argv[0]} --modo completo")
        else:
            print("\n❌ Prueba fallida")
            sys.exit(1)

    else:
        # Modo completo
        resultado = procesar_dataset_completo(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            confianza_minima=args.confianza_minima,
            validar_al_final=not args.no_validar
        )

        if resultado and resultado['estadisticas']['documentos_procesados'] > 0:
            print("\n✅ Dataset generado exitosamente")
        else:
            print("\n❌ No se pudo generar el dataset")
            sys.exit(1)


if __name__ == "__main__":
    main()
