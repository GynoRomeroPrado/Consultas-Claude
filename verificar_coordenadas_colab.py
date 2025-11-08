#!/usr/bin/env python3
"""
Script para verificar coordenadas en Google Colab.
Muestra visualizaciones inline y estadísticas de calidad.
"""

import sys
import json
from pathlib import Path

try:
    import fitz  # PyMuPDF
    from PIL import Image, ImageDraw, ImageFont
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
except ImportError as e:
    print(f"❌ Error: {e}")
    print("\nInstala las dependencias:")
    print("  pip install PyMuPDF Pillow matplotlib")
    sys.exit(1)


def verificar_coordenadas_interactivo(pdf_path, coordenadas_json_path, max_campos=10):
    """
    Verifica coordenadas de forma interactiva mostrando cada campo.

    Args:
        pdf_path: Ruta al PDF
        coordenadas_json_path: Ruta al JSON con coordenadas
        max_campos: Máximo de campos a mostrar
    """

    print("="*80)
    print("VERIFICACIÓN INTERACTIVA DE COORDENADAS")
    print("="*80)
    print()

    # Leer coordenadas
    with open(coordenadas_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    coordenadas = data.get('coordenadas', [])

    if not coordenadas:
        print("❌ No hay coordenadas en el JSON")
        return

    print(f"📊 Documento: {data.get('documento_origen', 'N/A')}")
    print(f"📊 Total campos: {len(coordenadas)}")
    print(f"📊 Match rate: {data.get('match_rate', 0):.1f}%")
    print(f"📊 Confianza promedio: {data.get('confianza_promedio', 0):.4f}")
    print()

    # Abrir PDF
    doc = fitz.open(pdf_path)
    page = doc[0]  # Primera página

    # Convertir a imagen
    zoom = 2
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Mostrar primeros N campos
    print(f"Mostrando primeros {min(max_campos, len(coordenadas))} campos:\n")

    for i, coord in enumerate(coordenadas[:max_campos], 1):
        campo = coord['campo']
        texto = coord['texto']
        bbox = coord['bbox']
        confianza = coord.get('confianza', 1.0)
        tipo = coord.get('tipo_matching', 'unknown')

        print(f"\n{'='*80}")
        print(f"[{i}/{min(max_campos, len(coordenadas))}] Campo: {campo}")
        print(f"{'='*80}")
        print(f"  Texto encontrado: '{texto}'")
        print(f"  Coordenadas: ({bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f})")
        print(f"  Confianza: {confianza:.2f}")
        print(f"  Tipo matching: {tipo}")

        # Crear visualización individual
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))

        # Mostrar imagen completa
        ax.imshow(img)

        # Dibujar rectángulo del campo actual
        x0, y0, x1, y1 = [c * zoom for c in bbox]
        rect = patches.Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            linewidth=3,
            edgecolor='red',
            facecolor='none'
        )
        ax.add_patch(rect)

        # Etiqueta
        ax.text(
            x0, y0 - 10,
            f"{campo}\n{texto}\nConf: {confianza:.2f}",
            bbox=dict(boxstyle='round', facecolor='red', alpha=0.7),
            fontsize=10,
            color='white',
            weight='bold'
        )

        # Hacer zoom al área del campo
        margen = 50
        ax.set_xlim(max(0, x0 - margen), min(img.width, x1 + margen))
        ax.set_ylim(min(img.height, y1 + margen), max(0, y0 - margen))

        ax.axis('off')
        plt.title(f"Campo: {campo}", fontsize=14, weight='bold')
        plt.tight_layout()
        plt.show()

        # Verificación manual
        print(f"\n  ✅ ¿Es correcto? (Visualmente verifica que el rectángulo rojo rodee el texto)")

    doc.close()

    print("\n" + "="*80)
    print("✅ VERIFICACIÓN COMPLETADA")
    print("="*80)


def mostrar_overview_completo(pdf_path, coordenadas_json_path):
    """
    Muestra un overview completo con todos los campos.
    """

    print("="*80)
    print("OVERVIEW COMPLETO - TODAS LAS COORDENADAS")
    print("="*80)

    # Leer coordenadas
    with open(coordenadas_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    coordenadas = data.get('coordenadas', [])

    # Abrir PDF
    doc = fitz.open(pdf_path)
    page = doc[0]

    # Convertir a imagen
    zoom = 2
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Crear figura
    fig, ax = plt.subplots(1, 1, figsize=(16, 20))

    ax.imshow(img)

    # Generar colores únicos
    import colorsys
    colores = []
    for i in range(len(coordenadas)):
        hue = (i * 137.5) % 360
        rgb = colorsys.hsv_to_rgb(hue / 360, 0.8, 0.9)
        colores.append(rgb)

    # Dibujar todos los campos
    for i, coord in enumerate(coordenadas):
        bbox = coord['bbox']
        campo = coord['campo']

        x0, y0, x1, y1 = [c * zoom for c in bbox]

        # Rectángulo
        rect = patches.Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            linewidth=2,
            edgecolor=colores[i],
            facecolor='none'
        )
        ax.add_patch(rect)

        # Número de campo
        ax.text(
            x0, y0 - 5,
            str(i + 1),
            bbox=dict(boxstyle='circle', facecolor=colores[i], alpha=0.7),
            fontsize=8,
            color='white',
            weight='bold'
        )

    ax.axis('off')
    plt.title(f"TODOS LOS CAMPOS ({len(coordenadas)})", fontsize=16, weight='bold')
    plt.tight_layout()
    plt.show()

    # Tabla de leyenda
    print("\n📋 LEYENDA DE CAMPOS:")
    print("="*80)
    for i, coord in enumerate(coordenadas, 1):
        conf_emoji = "🟢" if coord['confianza'] >= 0.95 else "🟡" if coord['confianza'] >= 0.8 else "🔴"
        print(f"  [{i:2}] {conf_emoji} {coord['campo']:30} | Texto: {coord['texto'][:40]:40} | Conf: {coord['confianza']:.2f}")

    doc.close()


def analizar_calidad(coordenadas_json_path):
    """
    Analiza la calidad de las coordenadas extraídas.
    """

    print("\n" + "="*80)
    print("ANÁLISIS DE CALIDAD")
    print("="*80)

    with open(coordenadas_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    coordenadas = data.get('coordenadas', [])

    # Estadísticas
    total = len(coordenadas)
    confianzas = [c['confianza'] for c in coordenadas]

    alta_confianza = sum(1 for c in confianzas if c >= 0.95)
    media_confianza = sum(1 for c in confianzas if 0.8 <= c < 0.95)
    baja_confianza = sum(1 for c in confianzas if c < 0.8)

    print(f"\n📊 Distribución de Confianza:")
    print(f"  🟢 Alta (≥0.95):   {alta_confianza:3} ({alta_confianza/total*100:.1f}%)")
    print(f"  🟡 Media (0.80-0.95): {media_confianza:3} ({media_confianza/total*100:.1f}%)")
    print(f"  🔴 Baja (<0.80):   {baja_confianza:3} ({baja_confianza/total*100:.1f}%)")

    # Tipos de matching
    tipos = {}
    for c in coordenadas:
        tipo = c.get('tipo_matching', 'unknown')
        tipos[tipo] = tipos.get(tipo, 0) + 1

    print(f"\n📊 Tipos de Matching:")
    for tipo, count in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f"  {tipo:15} {count:3} ({count/total*100:.1f}%)")

    # Campos con baja confianza
    if baja_confianza > 0:
        print(f"\n⚠️  Campos con Baja Confianza:")
        for c in coordenadas:
            if c['confianza'] < 0.8:
                print(f"  - {c['campo']:30} | Texto: {c['texto'][:40]:40} | Conf: {c['confianza']:.2f}")

    # Gráfico de confianzas
    plt.figure(figsize=(10, 5))
    plt.hist(confianzas, bins=20, color='skyblue', edgecolor='black')
    plt.xlabel('Confianza', fontsize=12)
    plt.ylabel('Frecuencia', fontsize=12)
    plt.title('Distribución de Confianza de las Coordenadas', fontsize=14, weight='bold')
    plt.axvline(x=0.95, color='green', linestyle='--', label='Alta confianza (≥0.95)')
    plt.axvline(x=0.8, color='orange', linestyle='--', label='Umbral aceptable (0.8)')
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.show()


def main():
    """Función principal para usar en Colab."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Verificación interactiva de coordenadas en Colab"
    )

    parser.add_argument("pdf", help="Ruta al PDF")
    parser.add_argument("coordenadas", help="Ruta al JSON con coordenadas")

    parser.add_argument(
        "--modo",
        choices=["interactivo", "overview", "calidad", "todo"],
        default="todo",
        help="Modo de verificación"
    )

    parser.add_argument(
        "--max-campos",
        type=int,
        default=10,
        help="Máximo de campos en modo interactivo"
    )

    args = parser.parse_args()

    if args.modo in ["interactivo", "todo"]:
        verificar_coordenadas_interactivo(args.pdf, args.coordenadas, args.max_campos)

    if args.modo in ["overview", "todo"]:
        mostrar_overview_completo(args.pdf, args.coordenadas)

    if args.modo in ["calidad", "todo"]:
        analizar_calidad(args.coordenadas)


if __name__ == "__main__":
    main()
