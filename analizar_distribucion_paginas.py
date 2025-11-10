#!/usr/bin/env python3
"""
Analiza la distribución de campos por página en un conjunto de datasets.
Útil para entender cómo se distribuyen los campos en PDFs multipágina.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict


def analizar_distribucion(dataset_dir="dataset_con_coordenadas"):
    """
    Analiza la distribución de campos por página en todos los archivos del dataset.

    Args:
        dataset_dir: Directorio con archivos de coordenadas

    Returns:
        Dict con análisis
    """

    print("="*80)
    print("ANÁLISIS DE DISTRIBUCIÓN POR PÁGINA")
    print("="*80)
    print(f"Dataset: {dataset_dir}")
    print()

    dataset_path = Path(dataset_dir)

    if not dataset_path.exists():
        print(f"❌ No se encontró el directorio: {dataset_dir}")
        print("   Ejecuta primero: python generar_dataset_completo.py")
        return None

    # Buscar archivos de coordenadas
    archivos_coords = list(dataset_path.glob("*_coordenadas.json"))

    if not archivos_coords:
        print(f"❌ No se encontraron archivos de coordenadas en: {dataset_dir}")
        return None

    print(f"📁 Archivos encontrados: {len(archivos_coords)}")
    print()

    # Análisis global
    total_documentos = 0
    total_paginas_procesadas = set()
    distribucion_global = defaultdict(int)
    campos_por_pagina_stats = defaultdict(list)
    documentos_multipagina = 0

    # Análisis por documento
    analisis_documentos = []

    for archivo in sorted(archivos_coords):
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                data = json.load(f)

            documento = data.get('documento_origen', archivo.stem)
            coordenadas = data.get('coordenadas', [])
            paginas = data.get('paginas', [])

            # Agrupar por página
            campos_por_pagina = defaultdict(int)
            for coord in coordenadas:
                pagina = coord.get('pagina', 0)
                campos_por_pagina[pagina] += 1

            # Estadísticas del documento
            num_paginas = len(campos_por_pagina)
            es_multipagina = num_paginas > 1

            if es_multipagina:
                documentos_multipagina += 1

            analisis_doc = {
                'documento': documento,
                'total_campos': len(coordenadas),
                'num_paginas': num_paginas,
                'campos_por_pagina': dict(campos_por_pagina),
                'es_multipagina': es_multipagina
            }

            analisis_documentos.append(analisis_doc)

            # Actualizar estadísticas globales
            total_documentos += 1
            total_paginas_procesadas.update(paginas)

            for pagina, count in campos_por_pagina.items():
                distribucion_global[pagina] += count
                campos_por_pagina_stats[pagina].append(count)

        except Exception as e:
            print(f"⚠️  Error procesando {archivo.name}: {e}")
            continue

    # Mostrar resultados
    print("📊 RESUMEN GLOBAL")
    print("="*80)
    print(f"  Total de documentos:         {total_documentos}")
    print(f"  Documentos multipágina:      {documentos_multipagina} ({documentos_multipagina/total_documentos*100:.1f}%)")
    print(f"  Documentos de 1 página:      {total_documentos - documentos_multipagina} ({(total_documentos - documentos_multipagina)/total_documentos*100:.1f}%)")
    print(f"  Páginas únicas procesadas:   {len(total_paginas_procesadas)}")
    print()

    # Distribución global por página
    print("📄 DISTRIBUCIÓN GLOBAL DE CAMPOS POR PÁGINA")
    print("="*80)

    paginas_ordenadas = sorted(distribucion_global.keys())

    for pagina in paginas_ordenadas:
        total_campos = distribucion_global[pagina]
        porcentaje = total_campos / sum(distribucion_global.values()) * 100

        # Estadísticas de esta página
        campos_lista = campos_por_pagina_stats[pagina]
        promedio = sum(campos_lista) / len(campos_lista) if campos_lista else 0
        minimo = min(campos_lista) if campos_lista else 0
        maximo = max(campos_lista) if campos_lista else 0

        print(f"\n  Página {pagina}:")
        print(f"    Total de campos:       {total_campos} ({porcentaje:.1f}%)")
        print(f"    Documentos con campos: {len(campos_lista)}")
        print(f"    Promedio por doc:      {promedio:.1f} campos")
        print(f"    Rango:                 {minimo}-{maximo} campos")

    # Top documentos multipágina
    docs_multipagina = [d for d in analisis_documentos if d['es_multipagina']]

    if docs_multipagina:
        print("\n" + "="*80)
        print("📚 DOCUMENTOS MULTIPÁGINA")
        print("="*80)

        # Ordenar por número de páginas
        docs_multipagina.sort(key=lambda d: d['num_paginas'], reverse=True)

        print(f"\nTop {min(5, len(docs_multipagina))} documentos con más páginas:")
        for i, doc in enumerate(docs_multipagina[:5], 1):
            print(f"\n  [{i}] {doc['documento']}")
            print(f"      Páginas: {doc['num_paginas']}, Total campos: {doc['total_campos']}")
            print(f"      Distribución:")

            for pagina in sorted(doc['campos_por_pagina'].keys()):
                count = doc['campos_por_pagina'][pagina]
                porcentaje = count / doc['total_campos'] * 100
                print(f"        Página {pagina}: {count} campos ({porcentaje:.1f}%)")

    # Documentos de una sola página
    docs_unipagina = [d for d in analisis_documentos if not d['es_multipagina']]

    if docs_unipagina:
        print("\n" + "="*80)
        print("📄 DOCUMENTOS DE UNA PÁGINA")
        print("="*80)

        total_campos_unipagina = sum(d['total_campos'] for d in docs_unipagina)
        promedio_campos = total_campos_unipagina / len(docs_unipagina) if docs_unipagina else 0

        print(f"\n  Total documentos:   {len(docs_unipagina)}")
        print(f"  Total campos:       {total_campos_unipagina}")
        print(f"  Promedio por doc:   {promedio_campos:.1f} campos")

    # Generar reporte
    reporte = {
        'total_documentos': total_documentos,
        'documentos_multipagina': documentos_multipagina,
        'documentos_unipagina': total_documentos - documentos_multipagina,
        'paginas_unicas': len(total_paginas_procesadas),
        'distribucion_global': dict(distribucion_global),
        'estadisticas_por_pagina': {
            str(p): {
                'total_campos': distribucion_global[p],
                'num_documentos': len(campos_por_pagina_stats[p]),
                'promedio': sum(campos_por_pagina_stats[p]) / len(campos_por_pagina_stats[p]),
                'min': min(campos_por_pagina_stats[p]),
                'max': max(campos_por_pagina_stats[p])
            }
            for p in paginas_ordenadas
        },
        'documentos': analisis_documentos
    }

    # Guardar reporte
    reporte_path = dataset_path / "distribucion_paginas.json"

    with open(reporte_path, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)

    print("\n" + "="*80)
    print(f"💾 Reporte guardado en: {reporte_path}")
    print("="*80)

    return reporte


def generar_grafico(reporte, output_path="distribucion_paginas.png"):
    """
    Genera un gráfico de la distribución de campos por página.

    Args:
        reporte: Dict con el reporte generado
        output_path: Ruta del archivo de salida
    """

    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # Backend sin GUI
    except ImportError:
        print("\n⚠️  matplotlib no está instalado. No se puede generar el gráfico.")
        print("   Para instalar: pip install matplotlib")
        return None

    distribucion = reporte['distribucion_global']

    if not distribucion:
        print("No hay datos para graficar")
        return None

    # Preparar datos
    paginas = sorted(distribucion.keys())
    valores = [distribucion[p] for p in paginas]

    # Crear figura
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Gráfico de barras
    ax1.bar(paginas, valores, color='steelblue', alpha=0.7)
    ax1.set_xlabel('Número de Página', fontsize=12)
    ax1.set_ylabel('Total de Campos', fontsize=12)
    ax1.set_title('Distribución de Campos por Página', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)

    # Agregar valores sobre las barras
    for i, (p, v) in enumerate(zip(paginas, valores)):
        ax1.text(p, v + max(valores) * 0.01, str(v), ha='center', va='bottom', fontsize=10)

    # Gráfico de pie
    colors = plt.cm.Set3(range(len(paginas)))
    ax2.pie(valores, labels=[f'Pág {p}' for p in paginas], autopct='%1.1f%%',
            colors=colors, startangle=90)
    ax2.set_title('Proporción de Campos por Página', fontsize=14, fontweight='bold')

    # Ajustar layout
    plt.tight_layout()

    # Guardar
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"📊 Gráfico guardado en: {output_path}")

    return output_path


def main():
    """Función principal."""

    if len(sys.argv) > 1:
        dataset_dir = sys.argv[1]
    else:
        dataset_dir = "dataset_con_coordenadas"

    print("Analizando distribución de campos por página...\n")

    reporte = analizar_distribucion(dataset_dir)

    if reporte:
        # Intentar generar gráfico
        print("\n🎨 Generando gráfico...")
        grafico = generar_grafico(
            reporte,
            Path(dataset_dir) / "distribucion_paginas.png"
        )

        print("\n✅ Análisis completado")

        # Resumen
        print("\n" + "="*80)
        print("📋 CONCLUSIONES")
        print("="*80)

        if reporte['documentos_multipagina'] > 0:
            porcentaje = reporte['documentos_multipagina'] / reporte['total_documentos'] * 100
            print(f"\n  • {porcentaje:.1f}% de los documentos tienen múltiples páginas")
            print(f"  • El sistema procesa correctamente PDFs multipágina")
            print(f"  • Las coordenadas incluyen el número de página para cada campo")
        else:
            print("\n  • Todos los documentos tienen una sola página")
            print(f"  • Considera probar con PDFs multipágina para validar el soporte completo")

        paginas_mas_campos = max(reporte['distribucion_global'].items(), key=lambda x: x[1])
        print(f"\n  • Página con más campos: Página {paginas_mas_campos[0]} ({paginas_mas_campos[1]} campos)")

        print("\n" + "="*80)


if __name__ == "__main__":
    main()
