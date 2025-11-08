#!/usr/bin/env python3
"""
Script de prueba para procesar archivos de la carpeta datos_extraidos_de_Originales.
Este script busca automáticamente PDFs y JSONs emparejados y los procesa.
"""

import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.pipeline import CoordinateExtractionPipeline
from src.core.config import (
    PipelineConfig,
    MatchStrategy,
    ExportFormat,
    MatcherConfig,
    ExporterConfig
)


def find_pdf_json_pairs(data_dir):
    """
    Busca pares de PDF-JSON en el directorio de datos.

    Patrones soportados:
    - documento.pdf + documento.json (mismo nombre)
    - pdfs/documento.pdf + anotaciones/documento.json
    """
    data_path = Path(data_dir)
    pairs = []

    # Buscar PDFs
    pdf_files = list(data_path.rglob('*.pdf'))

    print(f"Encontrados {len(pdf_files)} archivos PDF")

    for pdf_file in pdf_files:
        # Buscar JSON con el mismo nombre
        json_candidates = [
            pdf_file.with_suffix('.json'),  # Mismo directorio
            data_path / 'anotaciones' / (pdf_file.stem + '.json'),  # Subdirectorio anotaciones
            data_path / (pdf_file.stem + '.json'),  # Raíz del directorio de datos
        ]

        for json_file in json_candidates:
            if json_file.exists():
                pairs.append((str(pdf_file), str(json_file)))
                print(f"  ✓ Emparejado: {pdf_file.name} <-> {json_file.name}")
                break
        else:
            print(f"  ✗ Sin JSON para: {pdf_file.name}")

    return pairs


def inspect_json_structure(json_path):
    """Inspecciona la estructura del JSON para entender el formato."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\nEstructura del JSON: {Path(json_path).name}")
        print("=" * 80)

        if isinstance(data, dict):
            print(f"Tipo: Diccionario con {len(data)} campos")
            print("\nCampos principales:")
            for key, value in list(data.items())[:10]:
                value_preview = str(value)[:50]
                print(f"  - {key}: {value_preview}{'...' if len(str(value)) > 50 else ''}")
        elif isinstance(data, list):
            print(f"Tipo: Lista con {len(data)} elementos")
            if data:
                print(f"Primer elemento: {data[0]}")

        print("=" * 80)

        return data

    except Exception as e:
        print(f"Error inspeccionando JSON: {e}")
        return None


def run_test_with_strategy(pdf_path, json_path, strategy, threshold=80.0):
    """Ejecuta una prueba con una estrategia específica."""

    strategy_name = strategy.value
    print(f"\n{'='*80}")
    print(f"PROBANDO: {strategy_name.upper()} (threshold={threshold})")
    print(f"{'='*80}")

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
        verbose=True
    )

    pipeline = CoordinateExtractionPipeline(config=config)

    try:
        # Generar output path
        output_dir = Path("output/pruebas")
        output_dir.mkdir(parents=True, exist_ok=True)

        pdf_name = Path(pdf_path).stem
        output_path = output_dir / f"{pdf_name}_{strategy_name}.json"

        # Procesar
        result = pipeline.process(
            pdf_path=pdf_path,
            json_path=json_path,
            output_path=str(output_path)
        )

        # Mostrar resultados
        stats = result['statistics']

        print(f"\n📊 RESULTADOS - {strategy_name.upper()}")
        print(f"{'='*80}")
        print(f"  Total de campos:     {stats['total_fields']}")
        print(f"  Campos encontrados:  {stats['matched_fields']}")
        print(f"  Campos no encontrados: {stats['unmatched_fields']}")
        print(f"  Tasa de éxito:       {stats['match_rate']:.1f}%")
        print(f"  Confianza promedio:  {stats['average_confidence']:.4f}")

        if stats['match_types']:
            print(f"\n  Tipos de matching:")
            for match_type, count in stats['match_types'].items():
                print(f"    - {match_type}: {count}")

        print(f"\n  Páginas con matches: {stats['pages_with_matches']}")
        print(f"  Páginas: {stats['pages']}")
        print(f"\n  💾 Guardado en: {output_path}")

        # Mostrar algunos matches
        if result['matches']:
            print(f"\n📝 EJEMPLOS DE MATCHES:")
            print(f"{'='*80}")
            for i, (match, field_name) in enumerate(zip(result['matches'][:5], result['field_names'][:5])):
                print(f"  [{i+1}] {field_name}")
                print(f"      Texto encontrado: '{match.text}'")
                print(f"      Página: {match.page_num}, Bbox: {match.bbox}")
                print(f"      Confianza: {match.confidence:.2f}, Tipo: {match.match_type}")
                print()

        return result

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_strategies(pdf_path, json_path):
    """Compara diferentes estrategias de matching."""

    print(f"\n{'#'*80}")
    print(f"# COMPARACIÓN DE ESTRATEGIAS")
    print(f"# PDF: {Path(pdf_path).name}")
    print(f"# JSON: {Path(json_path).name}")
    print(f"{'#'*80}")

    strategies = [
        (MatchStrategy.EXACT, 100.0),
        (MatchStrategy.AUTO, 80.0),
        (MatchStrategy.FUZZY, 80.0),
        (MatchStrategy.FUZZY, 70.0),
    ]

    results = []

    for strategy, threshold in strategies:
        result = run_test_with_strategy(pdf_path, json_path, strategy, threshold)
        if result:
            results.append({
                'strategy': strategy.value,
                'threshold': threshold,
                'stats': result['statistics']
            })

    # Resumen comparativo
    print(f"\n{'='*80}")
    print(f"RESUMEN COMPARATIVO")
    print(f"{'='*80}")
    print(f"{'Estrategia':<20} {'Threshold':<12} {'Match Rate':<15} {'Avg Confidence':<15}")
    print(f"{'-'*80}")

    for res in results:
        strategy = res['strategy']
        threshold = res['threshold']
        match_rate = res['stats']['match_rate']
        avg_conf = res['stats']['average_confidence']

        print(f"{strategy:<20} {threshold:<12.1f} {match_rate:<15.1f}% {avg_conf:<15.4f}")

    print(f"{'='*80}")

    # Recomendar mejor estrategia
    if results:
        best = max(results, key=lambda x: (x['stats']['match_rate'], x['stats']['average_confidence']))
        print(f"\n🏆 MEJOR ESTRATEGIA: {best['strategy']} (threshold={best['threshold']})")
        print(f"   Match rate: {best['stats']['match_rate']:.1f}%")
        print(f"   Avg confidence: {best['stats']['average_confidence']:.4f}")


def main():
    """Función principal."""

    print("=" * 80)
    print("SISTEMA DE PRUEBAS - EXTRACCIÓN DE COORDENADAS PDF-JSON")
    print("=" * 80)

    # Buscar datos
    data_dir = "datos_extraidos_de_Originales"

    if not Path(data_dir).exists():
        print(f"\n❌ Directorio no encontrado: {data_dir}")
        print(f"\nPor favor, sube los archivos en la siguiente estructura:")
        print(f"  {data_dir}/")
        print(f"    ├── pdfs/")
        print(f"    │   ├── documento1.pdf")
        print(f"    │   └── documento2.pdf")
        print(f"    └── anotaciones/")
        print(f"        ├── documento1.json")
        print(f"        └── documento2.json")
        print(f"\nO bien:")
        print(f"  {data_dir}/")
        print(f"    ├── documento1.pdf")
        print(f"    ├── documento1.json")
        print(f"    ├── documento2.pdf")
        print(f"    └── documento2.json")
        return

    # Buscar pares
    print(f"\n🔍 Buscando archivos en: {data_dir}/")
    print("=" * 80)

    pairs = find_pdf_json_pairs(data_dir)

    if not pairs:
        print(f"\n❌ No se encontraron pares PDF-JSON en {data_dir}")
        return

    print(f"\n✓ Encontrados {len(pairs)} pares PDF-JSON")

    # Inspeccionar primer JSON para entender la estructura
    if pairs:
        first_json = pairs[0][1]
        inspect_json_structure(first_json)

    # Procesar cada par
    for i, (pdf_path, json_path) in enumerate(pairs, 1):
        print(f"\n\n")
        print(f"{'#'*80}")
        print(f"# DOCUMENTO {i}/{len(pairs)}")
        print(f"{'#'*80}")

        # Comparar estrategias para el primer documento
        if i == 1:
            compare_strategies(pdf_path, json_path)
        else:
            # Para los demás, usar la mejor estrategia (AUTO)
            run_test_with_strategy(pdf_path, json_path, MatchStrategy.AUTO, 80.0)

    print(f"\n\n{'='*80}")
    print(f"PRUEBAS COMPLETADAS")
    print(f"{'='*80}")
    print(f"Resultados guardados en: output/pruebas/")


if __name__ == "__main__":
    main()
