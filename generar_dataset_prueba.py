#!/usr/bin/env python3
"""
Script de PRUEBA: Procesa UNA factura y genera el archivo de coordenadas.
Este script se usa para validar que el formato de salida es correcto.
"""

import sys
import json
from pathlib import Path

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


def procesar_una_factura(pdf_path, json_path, output_dir="dataset_con_coordenadas"):
    """
    Procesa UNA factura y genera el archivo de coordenadas.

    Args:
        pdf_path: Ruta al PDF
        json_path: Ruta al JSON con anotaciones
        output_dir: Directorio de salida (default: dataset_con_coordenadas)

    Returns:
        Dict con el resultado
    """

    print("="*80)
    print("PROCESAMIENTO DE FACTURA - PRUEBA")
    print("="*80)
    print(f"PDF:  {pdf_path}")
    print(f"JSON: {json_path}")
    print()

    # Crear directorio de salida (separado de los originales)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Configuración del pipeline
    config = PipelineConfig(
        matcher=MatcherConfig(
            strategy=MatchStrategy.AUTO,  # Intenta exact, luego fuzzy
            fuzzy_threshold=80.0,
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
        # Procesar
        print("🔄 Procesando...\n")
        result = pipeline.process(
            pdf_path=pdf_path,
            json_path=json_path,
            output_path=None  # No guardar todavía, primero formatear
        )

        stats = result['statistics']

        # Mostrar resultados
        print("\n" + "="*80)
        print("📊 RESULTADOS")
        print("="*80)
        print(f"  Total de campos:       {stats['total_fields']}")
        print(f"  Campos encontrados:    {stats['matched_fields']}")
        print(f"  Campos NO encontrados: {stats['unmatched_fields']}")
        print(f"  Tasa de éxito:         {stats['match_rate']:.1f}%")
        print(f"  Confianza promedio:    {stats['average_confidence']:.4f}")

        if stats['match_types']:
            print(f"\n  Tipos de matching:")
            for match_type, count in stats['match_types'].items():
                print(f"    - {match_type}: {count}")

        # Formatear salida para el dataset
        pdf_name = Path(pdf_path).stem
        output_data = {
            "documento_origen": Path(pdf_path).name,
            "json_origen": Path(json_path).name,
            "fecha_procesamiento": None,  # Se puede agregar timestamp
            "total_campos": stats['total_fields'],
            "campos_encontrados": stats['matched_fields'],
            "campos_no_encontrados": stats['unmatched_fields'],
            "match_rate": stats['match_rate'],
            "confianza_promedio": stats['average_confidence'],
            "paginas": stats.get('pages', []),
            "coordenadas": []
        }

        # Convertir matches a formato de salida
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

        # Guardar en dataset_con_coordenadas/
        output_file = output_path / f"{pdf_name}_coordenadas.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Archivo generado: {output_file}")
        print(f"   Tamaño: {output_file.stat().st_size / 1024:.2f} KB")

        # Mostrar primeros 3 campos
        print("\n" + "="*80)
        print("📝 PRIMEROS 3 CAMPOS ENCONTRADOS")
        print("="*80)

        for i, coord in enumerate(output_data['coordenadas'][:3], 1):
            print(f"\n[{i}] {coord['campo']}")
            print(f"    Texto: '{coord['texto']}'")
            print(f"    Bbox:  {coord['bbox']}")
            print(f"    Página: {coord['pagina']}")
            print(f"    Confianza: {coord['confianza']:.2f}")

        # Mostrar campos NO encontrados
        if stats['unmatched_fields'] > 0:
            print("\n" + "="*80)
            print(f"⚠️  CAMPOS NO ENCONTRADOS ({stats['unmatched_fields']})")
            print("="*80)

            # Leer JSON original
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            matched_fields = set(result['field_names'])
            all_fields = set(json_data.keys())
            unmatched = all_fields - matched_fields

            for i, field in enumerate(list(unmatched)[:5], 1):
                value = json_data[field]
                if value is None:
                    print(f"  {i}. {field}: (null)")
                else:
                    print(f"  {i}. {field}: {str(value)[:60]}")

            if len(unmatched) > 5:
                print(f"  ... y {len(unmatched) - 5} más")

        print("\n" + "="*80)
        print("✅ PRUEBA COMPLETADA")
        print("="*80)
        print(f"\nArchivo de salida: {output_file}")
        print("\nSi el formato es correcto, ejecuta el script completo:")
        print("  python generar_dataset_completo.py")

        return output_data

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Función principal."""

    print("="*80)
    print("GENERACIÓN DE DATASET CON COORDENADAS - MODO PRUEBA")
    print("="*80)
    print("\nEste script procesa UNA factura para validar el formato.\n")

    # Buscar primer PDF y JSON disponible
    datos_dir = Path("Datos extraidos de Originales")

    # Buscar PDFs
    pdfs_dir = datos_dir / "pdfs"
    if not pdfs_dir.exists():
        # Intentar convertir PNGs
        print("⚠️  No hay PDFs. Intentando convertir PNGs...")
        facturas_dir = datos_dir / "facturas_procesadas"
        if facturas_dir.exists():
            import convertir_png_a_pdf_simple
            print("Ejecutando conversión...")
            # Esto debería crear la carpeta pdfs/

    if not pdfs_dir.exists():
        print("❌ No se encontró la carpeta de PDFs")
        print("   Esperado: Datos extraidos de Originales/pdfs/")
        sys.exit(1)

    pdfs = sorted(list(pdfs_dir.glob("*.pdf")))

    if not pdfs:
        print("❌ No hay PDFs en la carpeta")
        sys.exit(1)

    # Primer PDF
    pdf_path = pdfs[0]

    # Buscar JSON correspondiente
    json_dir = datos_dir / "anotaciones"
    json_path = json_dir / (pdf_path.stem + ".json")

    if not json_path.exists():
        print(f"❌ No se encontró el JSON: {json_path}")
        sys.exit(1)

    # Procesar
    resultado = procesar_una_factura(str(pdf_path), str(json_path))

    if resultado:
        print("\n🎯 SIGUIENTE PASO:")
        print("   1. Revisa el archivo generado en: dataset_con_coordenadas/")
        print("   2. Verifica que el formato sea correcto")
        print("   3. Si está bien, ejecuta: python generar_dataset_completo.py")


if __name__ == "__main__":
    main()
