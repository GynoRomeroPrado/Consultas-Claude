#!/usr/bin/env python3
"""
Script de prueba para procesar facturas electrónicas.
Trabaja con la estructura: Datos extraidos de Originales/
"""

import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.core.pipeline import CoordinateExtractionPipeline
    from src.core.config import (
        PipelineConfig,
        MatchStrategy,
        ExportFormat,
        MatcherConfig,
        ExporterConfig
    )
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("\nAsegúrate de haber instalado las dependencias:")
    print("  pip install -r requirements.txt")
    sys.exit(1)


def verificar_prerequisitos():
    """Verifica que todo esté instalado y listo."""
    print("Verificando prerequisitos...")

    # Verificar PyMuPDF
    try:
        import fitz
        print(f"  ✓ PyMuPDF version {fitz.version}")
    except ImportError:
        print("  ✗ PyMuPDF no está instalado")
        print("    Instala con: pip install PyMuPDF")
        return False

    # Verificar RapidFuzz
    try:
        import rapidfuzz
        print(f"  ✓ RapidFuzz version {rapidfuzz.__version__}")
    except ImportError:
        print("  ✗ RapidFuzz no está instalado")
        print("    Instala con: pip install rapidfuzz")
        return False

    # Verificar estructura de directorios
    pdfs_dir = Path("Datos extraidos de Originales/pdfs")
    if not pdfs_dir.exists():
        print(f"  ✗ Directorio de PDFs no existe: {pdfs_dir}")
        print("    Ejecuta primero: python convertir_png_a_pdf_simple.py")
        return False

    pdf_files = list(pdfs_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"  ✗ No hay PDFs en {pdfs_dir}")
        print("    Ejecuta primero: python convertir_png_a_pdf_simple.py")
        return False

    print(f"  ✓ {len(pdf_files)} PDFs encontrados")

    # Verificar JSONs
    json_dir = Path("Datos extraidos de Originales/anotaciones")
    json_files = list(json_dir.glob("*.json"))
    print(f"  ✓ {len(json_files)} JSONs encontrados")

    print("\n✅ Todos los prerequisitos cumplidos\n")
    return True


def analizar_json_factura(json_path):
    """Analiza un JSON de factura para entender su estructura."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\n📄 Estructura del JSON: {Path(json_path).name}")
        print("=" * 80)
        print(f"Total de campos: {len(data)}")

        # Clasificar campos
        campos_texto = []
        campos_numericos = []
        campos_fecha = []
        campos_nulos = []

        for key, value in data.items():
            if value is None:
                campos_nulos.append(key)
            elif isinstance(value, (int, float)):
                campos_numericos.append(key)
            elif 'fecha' in key.lower():
                campos_fecha.append(key)
            else:
                campos_texto.append(key)

        print(f"\nCampos de texto: {len(campos_texto)}")
        for campo in campos_texto[:5]:
            valor = data[campo]
            valor_str = str(valor)[:40] if valor else "null"
            print(f"  - {campo}: {valor_str}")
        if len(campos_texto) > 5:
            print(f"  ... y {len(campos_texto) - 5} más")

        print(f"\nCampos numéricos: {len(campos_numericos)}")
        for campo in campos_numericos[:5]:
            print(f"  - {campo}: {data[campo]}")

        print(f"\nCampos de fecha: {len(campos_fecha)}")
        for campo in campos_fecha:
            print(f"  - {campo}: {data[campo]}")

        if campos_nulos:
            print(f"\nCampos nulos: {len(campos_nulos)}")

        print("=" * 80)

        return data

    except Exception as e:
        print(f"Error analizando JSON: {e}")
        return None


def probar_factura(pdf_path, json_path, strategy=MatchStrategy.AUTO, threshold=80.0):
    """Prueba la extracción de coordenadas para una factura."""

    print(f"\n{'='*80}")
    print(f"PROCESANDO FACTURA")
    print(f"{'='*80}")
    print(f"PDF:  {Path(pdf_path).name}")
    print(f"JSON: {Path(json_path).name}")
    print(f"Estrategia: {strategy.value} (threshold={threshold})")

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
        verbose=True  # Modo verbose para ver detalles
    )

    pipeline = CoordinateExtractionPipeline(config=config)

    try:
        # Crear directorio de salida
        output_dir = Path("output/facturas")
        output_dir.mkdir(parents=True, exist_ok=True)

        pdf_name = Path(pdf_path).stem
        output_path = output_dir / f"{pdf_name}_{strategy.value}.json"

        # Procesar
        result = pipeline.process(
            pdf_path=pdf_path,
            json_path=json_path,
            output_path=str(output_path)
        )

        # Mostrar resultados
        stats = result['statistics']

        print(f"\n{'='*80}")
        print(f"RESULTADOS")
        print(f"{'='*80}")
        print(f"  Total de campos:       {stats['total_fields']}")
        print(f"  Campos encontrados:    {stats['matched_fields']}")
        print(f"  Campos NO encontrados: {stats['unmatched_fields']}")
        print(f"  Tasa de éxito:         {stats['match_rate']:.1f}%")
        print(f"  Confianza promedio:    {stats['average_confidence']:.4f}")

        if stats['match_types']:
            print(f"\n  Tipos de matching:")
            for match_type, count in stats['match_types'].items():
                print(f"    - {match_type}: {count}")

        print(f"\n  Páginas procesadas: {stats['pages_with_matches']}")
        print(f"  Guardado en: {output_path}")

        # Mostrar matches de ejemplo
        if result['matches']:
            print(f"\n{'='*80}")
            print(f"EJEMPLOS DE MATCHES (primeros 10)")
            print(f"{'='*80}")

            for i, (match, field_name) in enumerate(zip(result['matches'][:10], result['field_names'][:10])):
                print(f"\n[{i+1}] {field_name}")
                print(f"    Texto: '{match.text}'")
                print(f"    Bbox: ({match.bbox[0]:.1f}, {match.bbox[1]:.1f}, {match.bbox[2]:.1f}, {match.bbox[3]:.1f})")
                print(f"    Página: {match.page_num}")
                print(f"    Confianza: {match.confidence:.2f}")
                print(f"    Tipo: {match.match_type}")

        # Mostrar campos NO encontrados
        if stats['unmatched_fields'] > 0:
            print(f"\n{'='*80}")
            print(f"CAMPOS NO ENCONTRADOS ({stats['unmatched_fields']})")
            print(f"{'='*80}")

            # Leer JSON original para saber qué faltó
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            matched_fields = set(result['field_names'])
            all_fields = set(json_data.keys())
            unmatched = all_fields - matched_fields

            for field in list(unmatched)[:10]:
                value = json_data[field]
                if value is None:
                    print(f"  - {field}: (null)")
                else:
                    value_str = str(value)[:60]
                    print(f"  - {field}: {value_str}")

        return result

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Función principal."""

    print("=" * 80)
    print("SISTEMA DE EXTRACCIÓN DE COORDENADAS - FACTURAS ELECTRÓNICAS")
    print("=" * 80)

    # Verificar prerequisitos
    if not verificar_prerequisitos():
        print("\n❌ No se pueden ejecutar las pruebas")
        print("   Sigue las instrucciones en INSTALACION.md")
        sys.exit(1)

    # Buscar pares PDF-JSON
    pdfs_dir = Path("Datos extraidos de Originales/pdfs")
    json_dir = Path("Datos extraidos de Originales/anotaciones")

    pdf_files = sorted(list(pdfs_dir.glob("*.pdf")))
    pairs = []

    for pdf_file in pdf_files:
        json_file = json_dir / (pdf_file.stem + ".json")
        if json_file.exists():
            pairs.append((str(pdf_file), str(json_file)))

    print(f"\n✓ Encontrados {len(pairs)} pares PDF-JSON")

    if not pairs:
        print("\n❌ No hay pares para procesar")
        sys.exit(1)

    # Analizar primer JSON
    print(f"\n{'#'*80}")
    print(f"# ANÁLISIS DE ESTRUCTURA")
    print(f"{'#'*80}")

    primer_json = pairs[0][1]
    analizar_json_factura(primer_json)

    # Procesar primera factura con diferentes estrategias
    print(f"\n{'#'*80}")
    print(f"# COMPARACIÓN DE ESTRATEGIAS (Primera factura)")
    print(f"{'#'*80}")

    primera_pdf, primer_json = pairs[0]

    estrategias = [
        (MatchStrategy.EXACT, 100.0, "Matching exacto"),
        (MatchStrategy.AUTO, 80.0, "Auto (exact + fuzzy)"),
        (MatchStrategy.FUZZY, 70.0, "Fuzzy permisivo"),
    ]

    resultados = []

    for strategy, threshold, descripcion in estrategias:
        print(f"\n\n{'#'*80}")
        print(f"# ESTRATEGIA: {descripcion}")
        print(f"{'#'*80}")

        result = probar_factura(primera_pdf, primer_json, strategy, threshold)

        if result:
            resultados.append({
                'strategy': strategy.value,
                'threshold': threshold,
                'stats': result['statistics']
            })

    # Resumen comparativo
    if resultados:
        print(f"\n\n{'='*80}")
        print(f"RESUMEN COMPARATIVO")
        print(f"{'='*80}")
        print(f"{'Estrategia':<25} {'Threshold':<12} {'Match Rate':<15} {'Confianza':<15}")
        print(f"{'-'*80}")

        for res in resultados:
            strategy = res['strategy']
            threshold = res['threshold']
            match_rate = res['stats']['match_rate']
            avg_conf = res['stats']['average_confidence']

            print(f"{strategy:<25} {threshold:<12.1f} {match_rate:<14.1f}% {avg_conf:<15.4f}")

        # Mejor estrategia
        best = max(resultados, key=lambda x: (x['stats']['match_rate'], x['stats']['average_confidence']))
        print(f"\n🏆 MEJOR ESTRATEGIA: {best['strategy']} (threshold={best['threshold']})")
        print(f"   Match rate: {best['stats']['match_rate']:.1f}%")
        print(f"   Confianza: {best['stats']['average_confidence']:.4f}")

    # Procesar resto de facturas con mejor estrategia
    if len(pairs) > 1:
        print(f"\n\n{'#'*80}")
        print(f"# PROCESANDO RESTO DE FACTURAS ({len(pairs)-1})")
        print(f"{'#'*80}")

        mejor_strategy = MatchStrategy[best['strategy'].upper()]
        mejor_threshold = best['threshold']

        for i, (pdf_path, json_path) in enumerate(pairs[1:], 2):
            print(f"\n\n[{i}/{len(pairs)}] " + "="*60)
            probar_factura(pdf_path, json_path, mejor_strategy, mejor_threshold)

    print(f"\n\n{'='*80}")
    print(f"PROCESO COMPLETADO")
    print(f"{'='*80}")
    print(f"Resultados guardados en: output/facturas/")
    print(f"Total de facturas procesadas: {len(pairs)}")


if __name__ == "__main__":
    main()
