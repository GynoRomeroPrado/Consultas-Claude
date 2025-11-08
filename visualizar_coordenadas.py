#!/usr/bin/env python3
"""
Script de visualización: Dibuja los bounding boxes sobre el PDF para verificar
que las coordenadas extraídas son correctas.
"""

import sys
import json
from pathlib import Path

try:
    import fitz  # PyMuPDF
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    print(f"❌ Error: {e}")
    print("\nInstala las dependencias:")
    print("  pip install PyMuPDF Pillow")
    sys.exit(1)


def generar_colores_unicos(num_colores):
    """Genera colores únicos para cada campo."""
    colores = []
    for i in range(num_colores):
        # Generar colores con buena separación en el espectro HSV
        hue = (i * 137.5) % 360  # Golden angle
        # Convertir HSV a RGB
        import colorsys
        rgb = colorsys.hsv_to_rgb(hue / 360, 0.7, 0.9)
        colores.append(tuple(int(c * 255) for c in rgb))
    return colores


def visualizar_coordenadas(
    pdf_path,
    coordenadas_json_path,
    output_path="visualizacion.png",
    mostrar_etiquetas=True,
    grosor_linea=2,
    opacidad=0.3
):
    """
    Visualiza las coordenadas sobre el PDF.

    Args:
        pdf_path: Ruta al PDF original
        coordenadas_json_path: Ruta al JSON con coordenadas
        output_path: Ruta donde guardar la visualización
        mostrar_etiquetas: Si mostrar nombres de campos
        grosor_linea: Grosor de los rectángulos
        opacidad: Opacidad de los rectángulos (0-1)

    Returns:
        Path al archivo generado
    """

    print("="*80)
    print("VISUALIZACIÓN DE COORDENADAS")
    print("="*80)
    print(f"PDF:         {pdf_path}")
    print(f"Coordenadas: {coordenadas_json_path}")
    print(f"Salida:      {output_path}")
    print()

    # Leer coordenadas
    with open(coordenadas_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    coordenadas = data.get('coordenadas', [])

    if not coordenadas:
        print("❌ No hay coordenadas en el JSON")
        return None

    print(f"📊 Total de campos: {len(coordenadas)}")

    # Abrir PDF
    doc = fitz.open(pdf_path)

    # Generar colores únicos para cada campo
    colores = generar_colores_unicos(len(coordenadas))

    # Procesar cada página
    for page_num in range(len(doc)):
        page = doc[page_num]

        # Convertir página a imagen de alta resolución
        zoom = 2  # Factor de zoom para mejor calidad
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # Convertir a PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Crear capa para dibujar
        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Intentar cargar una fuente
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            font = ImageFont.load_default()
            font_small = font

        # Filtrar coordenadas de esta página
        coords_pagina = [c for c in coordenadas if c.get('pagina', 0) == page_num]

        print(f"\n📄 Página {page_num}: {len(coords_pagina)} campos")

        # Dibujar cada bounding box
        for i, coord in enumerate(coords_pagina):
            campo = coord['campo']
            bbox = coord['bbox']
            texto = coord['texto']
            confianza = coord.get('confianza', 1.0)

            # Escalar coordenadas por el zoom
            x0, y0, x1, y1 = [c * zoom for c in bbox]

            # Color basado en el índice
            color_idx = i % len(colores)
            color = colores[color_idx]

            # Dibujar rectángulo con relleno semi-transparente
            rect_fill = (*color, int(255 * opacidad))
            draw.rectangle([x0, y0, x1, y1], outline=color, width=grosor_linea, fill=rect_fill)

            # Dibujar etiqueta si está habilitado
            if mostrar_etiquetas:
                # Fondo para la etiqueta
                label = f"{campo} ({confianza:.2f})"
                bbox_text = draw.textbbox((x0, y0 - 20), label, font=font_small)
                draw.rectangle(bbox_text, fill=color)
                draw.text((x0, y0 - 20), label, fill=(255, 255, 255), font=font_small)

            print(f"  ✓ {campo:30} | Bbox: ({x0/zoom:.0f}, {y0/zoom:.0f}, {x1/zoom:.0f}, {y1/zoom:.0f}) | Conf: {confianza:.2f}")

        # Combinar imagen original con overlay
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)
        img = img.convert('RGB')

        # Guardar imagen
        if page_num == 0:
            output_file = output_path
        else:
            # Para múltiples páginas
            output_file = output_path.replace('.png', f'_page_{page_num}.png')

        img.save(output_file, 'PNG', quality=95)

        print(f"\n✅ Visualización guardada: {output_file}")
        print(f"   Dimensiones: {img.width}x{img.height} px")

    doc.close()

    print("\n" + "="*80)
    print("✅ VISUALIZACIÓN COMPLETADA")
    print("="*80)
    print(f"\nAbre el archivo para verificar visualmente las coordenadas:")
    print(f"  {output_path}")

    return output_path


def visualizar_con_leyenda(
    pdf_path,
    coordenadas_json_path,
    output_path="visualizacion_con_leyenda.png"
):
    """
    Crea visualización con leyenda de colores.
    """

    print("="*80)
    print("VISUALIZACIÓN CON LEYENDA")
    print("="*80)

    # Leer coordenadas
    with open(coordenadas_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    coordenadas = data.get('coordenadas', [])

    if not coordenadas:
        print("❌ No hay coordenadas en el JSON")
        return None

    # Generar visualización básica primero
    temp_output = output_path.replace('.png', '_temp.png')
    visualizar_coordenadas(
        pdf_path,
        coordenadas_json_path,
        temp_output,
        mostrar_etiquetas=False
    )

    # Abrir imagen generada
    img = Image.open(temp_output)

    # Crear imagen más grande para incluir leyenda
    leyenda_width = 400
    nueva_width = img.width + leyenda_width
    nueva_img = Image.new('RGB', (nueva_width, img.height), (255, 255, 255))

    # Pegar imagen original
    nueva_img.paste(img, (0, 0))

    # Dibujar leyenda
    draw = ImageDraw.Draw(nueva_img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except:
        font = ImageFont.load_default()
        font_title = font

    # Título de leyenda
    x_leyenda = img.width + 10
    y_leyenda = 20

    draw.text((x_leyenda, y_leyenda), "LEYENDA DE CAMPOS", fill=(0, 0, 0), font=font_title)
    y_leyenda += 40

    # Generar colores
    colores = generar_colores_unicos(len(coordenadas))

    # Dibujar cada campo en la leyenda
    for i, coord in enumerate(coordenadas[:30]):  # Máximo 30 campos en leyenda
        campo = coord['campo']
        confianza = coord.get('confianza', 1.0)

        color = colores[i % len(colores)]

        # Rectángulo de color
        draw.rectangle([x_leyenda, y_leyenda, x_leyenda + 20, y_leyenda + 15], fill=color, outline=(0, 0, 0))

        # Texto
        texto_leyenda = f"{campo[:25]} ({confianza:.2f})"
        draw.text((x_leyenda + 25, y_leyenda), texto_leyenda, fill=(0, 0, 0), font=font)

        y_leyenda += 20

    # Guardar
    nueva_img.save(output_path, 'PNG', quality=95)

    # Limpiar temporal
    import os
    os.remove(temp_output)

    print(f"\n✅ Visualización con leyenda guardada: {output_path}")

    return output_path


def main():
    """Función principal."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Visualiza coordenadas de bounding boxes sobre el PDF"
    )

    parser.add_argument(
        "pdf",
        help="Ruta al PDF original"
    )

    parser.add_argument(
        "coordenadas",
        help="Ruta al JSON con coordenadas"
    )

    parser.add_argument(
        "-o", "--output",
        default="visualizacion.png",
        help="Archivo de salida (default: visualizacion.png)"
    )

    parser.add_argument(
        "--con-leyenda",
        action="store_true",
        help="Incluir leyenda de colores"
    )

    parser.add_argument(
        "--sin-etiquetas",
        action="store_true",
        help="No mostrar etiquetas sobre los boxes"
    )

    args = parser.parse_args()

    # Verificar archivos
    if not Path(args.pdf).exists():
        print(f"❌ PDF no encontrado: {args.pdf}")
        sys.exit(1)

    if not Path(args.coordenadas).exists():
        print(f"❌ JSON no encontrado: {args.coordenadas}")
        sys.exit(1)

    # Generar visualización
    if args.con_leyenda:
        resultado = visualizar_con_leyenda(
            args.pdf,
            args.coordenadas,
            args.output
        )
    else:
        resultado = visualizar_coordenadas(
            args.pdf,
            args.coordenadas,
            args.output,
            mostrar_etiquetas=not args.sin_etiquetas
        )

    if resultado:
        print("\n🎯 CÓMO VERIFICAR:")
        print("  1. Abre la imagen generada")
        print("  2. Verifica que cada rectángulo rodee correctamente el texto")
        print("  3. Si hay errores, ajusta el threshold de fuzzy matching")


if __name__ == "__main__":
    main()
