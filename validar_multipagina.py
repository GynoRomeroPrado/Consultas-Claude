#!/usr/bin/env python3
"""
Script para validar el procesamiento correcto de PDFs multipágina.
Muestra la distribución de campos por página y verifica que todo esté correcto.
"""

import sys
import json
import fitz
from pathlib import Path
from collections import defaultdict

def validar_pdf_multipagina(pdf_path, coordenadas_json_path=None):
    """
    Valida el procesamiento de un PDF multipágina.

    Args:
        pdf_path: Ruta al PDF
        coordenadas_json_path: Ruta al JSON con coordenadas (opcional)

    Returns:
        Dict con análisis
    """

    print("="*80)
    print("VALIDACIÓN DE PDF MULTIPÁGINA")
    print("="*80)
    print(f"PDF: {pdf_path}")
    print()

    # Abrir PDF
    try:
        doc = fitz.open(pdf_path)
        num_paginas = len(doc)
    except Exception as e:
        print(f"❌ Error al abrir PDF: {e}")
        return None

    print(f"📄 Número de páginas en PDF: {num_paginas}")
    print()

    # Mostrar dimensiones de cada página
    print("📐 DIMENSIONES POR PÁGINA:")
    print("-" * 80)
    for i in range(num_paginas):
        page = doc[i]
        rect = page.rect
        print(f"  Página {i}: {rect.width:.1f} x {rect.height:.1f} pts")

    doc.close()
    print()

    # Si no hay JSON de coordenadas, solo mostrar info del PDF
    if coordenadas_json_path is None:
        print("ℹ️  No se proporcionó archivo de coordenadas.")
        print("   Para validar el procesamiento, ejecuta primero:")
        print("   python generar_dataset_prueba.py")
        return {
            'pdf': pdf_path,
            'num_paginas': num_paginas,
            'coordenadas_validadas': False
        }

    # Verificar que exista el archivo de coordenadas
    if not Path(coordenadas_json_path).exists():
        print(f"❌ No se encontró el archivo de coordenadas: {coordenadas_json_path}")
        print("   Ejecuta primero: python generar_dataset_prueba.py")
        return None

    # Leer coordenadas
    print(f"📊 Archivo de coordenadas: {coordenadas_json_path}")
    print()

    with open(coordenadas_json_path, 'r', encoding='utf-8') as f:
        coords_data = json.load(f)

    total_campos = coords_data.get('total_campos', 0)
    campos_encontrados = coords_data.get('campos_encontrados', 0)
    match_rate = coords_data.get('match_rate', 0)
    paginas_con_matches = coords_data.get('paginas', [])

    print("📈 ESTADÍSTICAS GENERALES:")
    print("-" * 80)
    print(f"  Total de campos en JSON:     {total_campos}")
    print(f"  Campos encontrados en PDF:   {campos_encontrados}")
    print(f"  Tasa de éxito:              {match_rate:.1f}%")
    print(f"  Páginas con matches:        {paginas_con_matches}")
    print()

    # Agrupar coordenadas por página
    campos_por_pagina = defaultdict(list)

    for coord in coords_data.get('coordenadas', []):
        pagina = coord.get('pagina', -1)
        campos_por_pagina[pagina].append({
            'campo': coord.get('campo'),
            'texto': coord.get('texto'),
            'bbox': coord.get('bbox'),
            'confianza': coord.get('confianza', 1.0)
        })

    # Mostrar distribución por página
    print("📄 DISTRIBUCIÓN DE CAMPOS POR PÁGINA:")
    print("=" * 80)

    paginas_ordenadas = sorted(campos_por_pagina.keys())

    for pagina in paginas_ordenadas:
        campos = campos_por_pagina[pagina]
        porcentaje = (len(campos) / campos_encontrados * 100) if campos_encontrados > 0 else 0

        print(f"\n  📄 Página {pagina}: {len(campos)} campos ({porcentaje:.1f}%)")
        print("  " + "-" * 76)

        # Mostrar primeros 5 campos de la página
        for i, campo in enumerate(campos[:5], 1):
            print(f"    [{i}] {campo['campo']}")
            print(f"        Texto: '{campo['texto'][:60]}{'...' if len(campo['texto']) > 60 else ''}'")
            print(f"        Bbox: {campo['bbox']}")
            print(f"        Confianza: {campo['confianza']:.2f}")

        if len(campos) > 5:
            print(f"    ... y {len(campos) - 5} campos más")

    # Verificaciones
    print("\n" + "=" * 80)
    print("🔍 VERIFICACIONES:")
    print("=" * 80)

    verificaciones = []

    # 1. Todas las páginas tienen al menos un campo (opcional)
    paginas_sin_campos = set(range(num_paginas)) - set(paginas_ordenadas)
    if paginas_sin_campos:
        print(f"⚠️  Páginas sin campos detectados: {sorted(paginas_sin_campos)}")
        print("   Esto puede ser normal si esas páginas no contienen campos del JSON.")
        verificaciones.append({
            'tipo': 'warning',
            'mensaje': f'Páginas sin campos: {sorted(paginas_sin_campos)}'
        })
    else:
        print("✅ Todas las páginas tienen al menos un campo")
        verificaciones.append({
            'tipo': 'success',
            'mensaje': 'Todas las páginas procesadas'
        })

    # 2. Números de página válidos
    paginas_invalidas = [p for p in paginas_ordenadas if p < 0 or p >= num_paginas]
    if paginas_invalidas:
        print(f"❌ ERROR: Páginas inválidas detectadas: {paginas_invalidas}")
        print(f"   El PDF tiene {num_paginas} páginas (índices 0-{num_paginas-1})")
        verificaciones.append({
            'tipo': 'error',
            'mensaje': f'Páginas inválidas: {paginas_invalidas}'
        })
    else:
        print("✅ Todos los números de página son válidos")
        verificaciones.append({
            'tipo': 'success',
            'mensaje': 'Números de página correctos'
        })

    # 3. Coordenadas dentro de límites de página
    coordenadas_fuera_limites = []
    for pagina, campos in campos_por_pagina.items():
        if pagina < 0 or pagina >= num_paginas:
            continue

        # Obtener dimensiones de la página
        doc = fitz.open(pdf_path)
        page = doc[pagina]
        rect = page.rect
        page_width, page_height = rect.width, rect.height
        doc.close()

        for campo in campos:
            bbox = campo['bbox']
            x0, y0, x1, y1 = bbox

            # Verificar que bbox esté dentro de límites
            if x0 < 0 or y0 < 0 or x1 > page_width or y1 > page_height:
                coordenadas_fuera_limites.append({
                    'campo': campo['campo'],
                    'pagina': pagina,
                    'bbox': bbox,
                    'dimensiones_pagina': (page_width, page_height)
                })

    if coordenadas_fuera_limites:
        print(f"⚠️  {len(coordenadas_fuera_limites)} coordenadas fuera de límites de página:")
        for coord in coordenadas_fuera_limites[:3]:
            print(f"     - {coord['campo']} en página {coord['pagina']}")
            print(f"       bbox: {coord['bbox']}, límites: {coord['dimensiones_pagina']}")
        if len(coordenadas_fuera_limites) > 3:
            print(f"     ... y {len(coordenadas_fuera_limites) - 3} más")
        verificaciones.append({
            'tipo': 'warning',
            'mensaje': f'{len(coordenadas_fuera_limites)} coordenadas fuera de límites'
        })
    else:
        print("✅ Todas las coordenadas están dentro de los límites de página")
        verificaciones.append({
            'tipo': 'success',
            'mensaje': 'Coordenadas dentro de límites'
        })

    # 4. Match rate aceptable
    if match_rate >= 90:
        print(f"✅ Excelente match rate: {match_rate:.1f}%")
        verificaciones.append({'tipo': 'success', 'mensaje': f'Match rate: {match_rate:.1f}%'})
    elif match_rate >= 80:
        print(f"✅ Buen match rate: {match_rate:.1f}%")
        verificaciones.append({'tipo': 'success', 'mensaje': f'Match rate: {match_rate:.1f}%'})
    elif match_rate >= 70:
        print(f"⚠️  Match rate aceptable: {match_rate:.1f}%")
        verificaciones.append({'tipo': 'warning', 'mensaje': f'Match rate: {match_rate:.1f}%'})
    else:
        print(f"❌ Match rate bajo: {match_rate:.1f}%")
        print("   Considera ajustar el threshold de fuzzy matching")
        verificaciones.append({'tipo': 'error', 'mensaje': f'Match rate bajo: {match_rate:.1f}%'})

    # Resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN:")
    print("=" * 80)

    errores = [v for v in verificaciones if v['tipo'] == 'error']
    warnings = [v for v in verificaciones if v['tipo'] == 'warning']
    success = [v for v in verificaciones if v['tipo'] == 'success']

    print(f"  ✅ Verificaciones exitosas: {len(success)}")
    print(f"  ⚠️  Advertencias:          {len(warnings)}")
    print(f"  ❌ Errores:                {len(errores)}")
    print()

    if errores:
        print("❌ Hay errores que deben corregirse")
        estado = "ERROR"
    elif warnings:
        print("⚠️  Hay advertencias para revisar")
        estado = "WARNING"
    else:
        print("✅ Todas las verificaciones pasaron correctamente")
        estado = "SUCCESS"

    # Generar reporte
    reporte = {
        'pdf': pdf_path,
        'coordenadas_json': coordenadas_json_path,
        'num_paginas': num_paginas,
        'total_campos': total_campos,
        'campos_encontrados': campos_encontrados,
        'match_rate': match_rate,
        'paginas_con_matches': paginas_con_matches,
        'distribucion_por_pagina': {
            str(p): len(c) for p, c in campos_por_pagina.items()
        },
        'verificaciones': verificaciones,
        'estado': estado
    }

    # Guardar reporte
    reporte_path = Path("dataset_con_coordenadas") / "reporte_multipagina.json"
    reporte_path.parent.mkdir(parents=True, exist_ok=True)

    with open(reporte_path, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Reporte guardado en: {reporte_path}")

    return reporte


def main():
    """Función principal."""

    if len(sys.argv) < 2:
        print("Uso:")
        print("  python validar_multipagina.py <pdf_path> [coordenadas_json_path]")
        print()
        print("Ejemplos:")
        print("  # Solo analizar PDF")
        print("  python validar_multipagina.py 'Datos extraidos de Originales/pdfs/factura.pdf'")
        print()
        print("  # Validar con coordenadas")
        print("  python validar_multipagina.py \\")
        print("      'Datos extraidos de Originales/pdfs/factura.pdf' \\")
        print("      'dataset_con_coordenadas/factura_coordenadas.json'")
        sys.exit(1)

    pdf_path = sys.argv[1]
    coords_path = sys.argv[2] if len(sys.argv) > 2 else None

    # Si no se proporciona coords_path, intentar auto-detectar
    if coords_path is None:
        pdf_name = Path(pdf_path).stem
        auto_coords = Path("dataset_con_coordenadas") / f"{pdf_name}_coordenadas.json"
        if auto_coords.exists():
            coords_path = str(auto_coords)
            print(f"ℹ️  Auto-detectado archivo de coordenadas: {coords_path}\n")

    reporte = validar_pdf_multipagina(pdf_path, coords_path)

    if reporte and reporte['estado'] == 'SUCCESS':
        print("\n🎉 ¡Validación exitosa!")
        sys.exit(0)
    elif reporte and reporte['estado'] == 'WARNING':
        print("\n⚠️  Validación con advertencias")
        sys.exit(0)
    else:
        print("\n❌ Validación con errores")
        sys.exit(1)


if __name__ == "__main__":
    main()
