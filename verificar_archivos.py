#!/usr/bin/env python3
"""
Script simple para verificar qué archivos hay disponibles.
"""

import os
from pathlib import Path

def verificar_archivos():
    """Verifica archivos en el directorio de datos."""

    print("=" * 80)
    print("VERIFICACIÓN DE ARCHIVOS")
    print("=" * 80)

    data_dir = Path("datos_extraidos_de_Originales")

    if not data_dir.exists():
        print(f"\n❌ El directorio '{data_dir}' no existe.")
        print("\nPor favor, créalo y sube tus archivos ahí.")
        return

    print(f"\n✓ Directorio encontrado: {data_dir}")

    # Buscar PDFs
    pdfs = list(data_dir.rglob("*.pdf"))
    print(f"\n📄 PDFs encontrados: {len(pdfs)}")
    for pdf in pdfs:
        size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"  - {pdf.relative_to(data_dir)} ({size_mb:.2f} MB)")

    # Buscar JSONs
    jsons = list(data_dir.rglob("*.json"))
    print(f"\n📝 JSONs encontrados: {len(jsons)}")
    for j in jsons:
        size_kb = j.stat().st_size / 1024
        print(f"  - {j.relative_to(data_dir)} ({size_kb:.2f} KB)")

    # Verificar emparejamiento
    print(f"\n🔗 Verificando emparejamiento:")
    matched = 0
    unmatched_pdfs = []

    for pdf in pdfs:
        json_name = pdf.stem + ".json"
        # Buscar en el mismo directorio
        json_path = pdf.with_suffix('.json')
        # O en subdirectorio anotaciones
        json_alt = data_dir / 'anotaciones' / (pdf.stem + '.json')

        if json_path.exists():
            print(f"  ✓ {pdf.name} <-> {json_path.name}")
            matched += 1
        elif json_alt.exists():
            print(f"  ✓ {pdf.name} <-> anotaciones/{json_alt.name}")
            matched += 1
        else:
            print(f"  ✗ {pdf.name} (sin JSON correspondiente)")
            unmatched_pdfs.append(pdf.name)

    print(f"\n{'='*80}")
    print(f"RESUMEN:")
    print(f"  Total PDFs: {len(pdfs)}")
    print(f"  Total JSONs: {len(jsons)}")
    print(f"  Pares emparejados: {matched}")
    print(f"  PDFs sin JSON: {len(unmatched_pdfs)}")

    if matched > 0:
        print(f"\n✅ Listo para procesar! Ejecuta:")
        print(f"   python test_real_data.py")
    else:
        print(f"\n⚠️  No hay pares para procesar todavía.")
        print(f"\n💡 Instrucciones:")
        print(f"   1. Coloca tus PDFs en: {data_dir}/pdfs/")
        print(f"   2. Coloca tus JSONs en: {data_dir}/anotaciones/")
        print(f"   3. Asegúrate que los nombres coincidan (sin extensión)")
        print(f"   4. Ejecuta nuevamente: python verificar_archivos.py")

    print(f"{'='*80}")

if __name__ == "__main__":
    verificar_archivos()
