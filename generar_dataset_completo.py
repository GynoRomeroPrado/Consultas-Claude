#!/usr/bin/env python3
"""
Script COMPLETO: Procesa TODAS las facturas y genera el dataset con coordenadas.
Este script se ejecuta después de validar que el formato de prueba es correcto.
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
    import fitz
except ImportError as e:
    print(f"❌ Error: {e}")
    print("\nInstala las dependencias:")
    print("  pip install PyMuPDF rapidfuzz numpy pandas tqdm")
    sys.exit(1)


def procesar_dataset_completo(
    pdfs_dir="Datos extraidos de Originales/pdfs",
    json_dir="Datos extraidos de Originales/anotaciones",
    output_dir="dataset_con_coordenadas",
    strategy=MatchStrategy.AUTO,
    threshold=80.0
):
    """
    Procesa TODAS las facturas y genera el dataset completo.

    Args:
        pdfs_dir: Directorio con los PDFs
        json_dir: Directorio con los JSONs
        output_dir: Directorio de salida (SEPARADO)
        strategy: Estrategia de matching
        threshold: Umbral para fuzzy matching

    Returns:
        Dict con estadísticas generales
    """

    print("="*80)
    print("GENERACIÓN DE DATASET COMPLETO CON COORDENADAS")
    print("="*80)
    print(f"\nDirectorio PDFs:        {pdfs_dir}")
    print(f"Directorio JSONs:       {json_dir}")
    print(f"Directorio de salida:   {output_dir}")
    print(f"Estrategia:             {strategy.value}")
    print(f"Threshold:              {threshold}")
    print()

    # Crear directorio de salida
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Buscar todos los PDFs
    pdfs_path = Path(pdfs_dir)
    json_path_dir = Path(json_dir)

    if not pdfs_path.exists():
        print(f"❌ Error: No existe el directorio {pdfs_dir}")
        return None

    pdfs = sorted(list(pdfs_path.glob("*.pdf")))

    if not pdfs:
        print(f"❌ Error: No hay PDFs en {pdfs_dir}")
        return None

    print(f"📄 Encontrados {len(pdfs)} PDFs\n")

    # Encontrar pares PDF-JSON
    pares = []
    for pdf_file in pdfs:
        json_file = json_path_dir / (pdf_file.stem + ".json")
        if json_file.exists():
            pares.append((pdf_file, json_file))
        else:
            print(f"⚠️  Sin JSON: {pdf_file.name}")

    if not pares:
        print("❌ No se encontraron pares PDF-JSON")
        return None

    print(f"✅ {len(pares)} pares PDF-JSON listos para procesar\n")

    # Configurar pipeline
    config = PipelineConfig(
        matcher=MatcherConfig(
            strategy=strategy,
            fuzzy_threshold=threshold,
            prefer_first_match=True
        ),
        exporter=ExporterConfig(
            format=ExportFormat.JSON,
            include_confidence=True,
            include_metadata=True
        ),
        verbose=False  # Silencioso para procesamiento masivo
    )

    pipeline = CoordinateExtractionPipeline(config=config)

    # Estadísticas generales
    estadisticas_generales = {
        "fecha_generacion": datetime.now().isoformat(),
        "total_documentos": len(pares),
        "procesados_exitosamente": 0,
        "errores": 0,
        "match_rate_promedio": 0.0,
        "confianza_promedio": 0.0,
        "total_campos": 0,
        "total_campos_encontrados": 0,
        "documentos": []
    }

    # Procesar cada par
    print("="*80)
    print("PROCESANDO DATASET")
    print("="*80)

    match_rates = []
    confidences = []

    for i, (pdf_file, json_file) in enumerate(tqdm(pares, desc="Procesando"), 1):
        try:
            # Procesar
            result = pipeline.process(
                pdf_path=str(pdf_file),
                json_path=str(json_file),
                output_path=None
            )

            stats = result['statistics']

            # Formatear salida
            output_data = {
                "documento_origen": pdf_file.name,
                "json_origen": json_file.name,
                "total_campos": stats['total_fields'],
                "campos_encontrados": stats['matched_fields'],
                "campos_no_encontrados": stats['unmatched_fields'],
                "match_rate": stats['match_rate'],
                "confianza_promedio": stats['average_confidence'],
                "paginas": stats.get('pages', []),
                "tipos_matching": stats.get('match_types', {}),
                "coordenadas": []
            }

            # Convertir matches
            for match, field_name in zip(result['matches'], result['field_names']):
                coord_data = {
                    "campo": field_name,
                    "texto": match.text,
                    "bbox": [match.bbox[0], match.bbox[1], match.bbox[2], match.bbox[3]],
                    "pagina": match.page_num,
                    "confianza": match.confidence,
                    "tipo_matching": match.match_type,
                    "dimensiones_pagina": {
                        "ancho": match.metadata.get('page_width'),
                        "alto": match.metadata.get('page_height')
                    }
                }
                output_data['coordenadas'].append(coord_data)

            # Guardar archivo individual
            output_file = output_path / f"{pdf_file.stem}_coordenadas.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            # Actualizar estadísticas
            estadisticas_generales["procesados_exitosamente"] += 1
            estadisticas_generales["total_campos"] += stats['total_fields']
            estadisticas_generales["total_campos_encontrados"] += stats['matched_fields']

            match_rates.append(stats['match_rate'])
            confidences.append(stats['average_confidence'])

            estadisticas_generales["documentos"].append({
                "nombre": pdf_file.name,
                "match_rate": stats['match_rate'],
                "campos_encontrados": stats['matched_fields'],
                "total_campos": stats['total_fields']
            })

        except Exception as e:
            estadisticas_generales["errores"] += 1
            print(f"\n❌ Error en {pdf_file.name}: {e}")
            estadisticas_generales["documentos"].append({
                "nombre": pdf_file.name,
                "error": str(e)
            })

    # Calcular promedios
    if match_rates:
        estadisticas_generales["match_rate_promedio"] = sum(match_rates) / len(match_rates)
        estadisticas_generales["confianza_promedio"] = sum(confidences) / len(confidences)

    # Guardar resumen general
    resumen_file = output_path / "resumen_dataset.json"

    with open(resumen_file, 'w', encoding='utf-8') as f:
        json.dump(estadisticas_generales, f, indent=2, ensure_ascii=False)

    # Mostrar resultados
    print("\n" + "="*80)
    print("📊 RESUMEN FINAL")
    print("="*80)
    print(f"  Total documentos:          {estadisticas_generales['total_documentos']}")
    print(f"  Procesados exitosamente:   {estadisticas_generales['procesados_exitosamente']}")
    print(f"  Errores:                   {estadisticas_generales['errores']}")
    print(f"  Match rate promedio:       {estadisticas_generales['match_rate_promedio']:.1f}%")
    print(f"  Confianza promedio:        {estadisticas_generales['confianza_promedio']:.4f}")
    print(f"  Total campos en dataset:   {estadisticas_generales['total_campos']}")
    print(f"  Total campos encontrados:  {estadisticas_generales['total_campos_encontrados']}")

    print("\n" + "="*80)
    print("📁 ARCHIVOS GENERADOS")
    print("="*80)
    print(f"  Directorio: {output_path}/")
    print(f"  Archivos individuales: {estadisticas_generales['procesados_exitosamente']}")
    print(f"  Resumen general: resumen_dataset.json")

    # Listar archivos
    archivos = sorted(output_path.glob("*_coordenadas.json"))
    print(f"\n  Primeros archivos:")
    for archivo in archivos[:5]:
        size_kb = archivo.stat().st_size / 1024
        print(f"    - {archivo.name} ({size_kb:.2f} KB)")
    if len(archivos) > 5:
        print(f"    ... y {len(archivos) - 5} más")

    print("\n" + "="*80)
    print("✅ DATASET GENERADO COMPLETAMENTE")
    print("="*80)

    return estadisticas_generales


def main():
    """Función principal."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Genera dataset completo con coordenadas de bounding boxes"
    )

    parser.add_argument(
        "--pdfs-dir",
        default="Datos extraidos de Originales/pdfs",
        help="Directorio con los PDFs"
    )

    parser.add_argument(
        "--json-dir",
        default="Datos extraidos de Originales/anotaciones",
        help="Directorio con los JSONs"
    )

    parser.add_argument(
        "--output-dir",
        default="dataset_con_coordenadas",
        help="Directorio de salida (default: dataset_con_coordenadas)"
    )

    parser.add_argument(
        "--strategy",
        choices=["exact", "fuzzy", "auto"],
        default="auto",
        help="Estrategia de matching (default: auto)"
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=80.0,
        help="Threshold para fuzzy matching (default: 80.0)"
    )

    args = parser.parse_args()

    # Mapear estrategia
    strategy_map = {
        "exact": MatchStrategy.EXACT,
        "fuzzy": MatchStrategy.FUZZY,
        "auto": MatchStrategy.AUTO
    }

    strategy = strategy_map[args.strategy]

    # Procesar
    resultado = procesar_dataset_completo(
        pdfs_dir=args.pdfs_dir,
        json_dir=args.json_dir,
        output_dir=args.output_dir,
        strategy=strategy,
        threshold=args.threshold
    )

    if resultado:
        print("\n✅ Proceso completado exitosamente")
        print(f"\n📂 Dataset disponible en: {args.output_dir}/")
    else:
        print("\n❌ Hubo errores en el proceso")
        sys.exit(1)


if __name__ == "__main__":
    main()
