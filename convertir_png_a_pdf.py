#!/usr/bin/env python3
"""
Convierte imágenes PNG a PDF para procesamiento.
"""

import sys
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF

def convertir_png_a_pdf(png_path, pdf_path):
    """
    Convierte una imagen PNG a PDF.

    Args:
        png_path: Ruta a la imagen PNG
        pdf_path: Ruta donde guardar el PDF
    """
    try:
        # Abrir imagen
        img = Image.open(png_path)

        # Convertir a RGB si es necesario (PDFs no soportan RGBA)
        if img.mode == 'RGBA':
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3])  # 3 es el canal alpha
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Guardar como PDF
        img.save(pdf_path, 'PDF', resolution=100.0)

        return True

    except Exception as e:
        print(f"Error convirtiendo {png_path}: {e}")
        return False


def convertir_directorio(input_dir, output_dir):
    """
    Convierte todas las PNGs de un directorio a PDF.

    Args:
        input_dir: Directorio con PNGs
        output_dir: Directorio para guardar PDFs
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Crear directorio de salida
    output_path.mkdir(parents=True, exist_ok=True)

    # Buscar PNGs
    png_files = list(input_path.glob('*.png'))

    print(f"Encontradas {len(png_files)} imágenes PNG")
    print(f"Convirtiendo a PDF...")

    convertidas = 0
    errores = 0

    for png_file in png_files:
        pdf_file = output_path / (png_file.stem + '.pdf')

        print(f"  Convirtiendo: {png_file.name}...", end=' ')

        if convertir_png_a_pdf(str(png_file), str(pdf_file)):
            print("✓")
            convertidas += 1
        else:
            print("✗")
            errores += 1

    print(f"\nResultados:")
    print(f"  Convertidas: {convertidas}")
    print(f"  Errores: {errores}")
    print(f"  PDFs guardados en: {output_path}/")

    return convertidas


def main():
    """Función principal."""

    print("=" * 80)
    print("CONVERSOR PNG a PDF")
    print("=" * 80)

    # Directorios
    input_dir = "Datos extraidos de Originales/facturas_procesadas"
    output_dir = "Datos extraidos de Originales/pdfs"

    if not Path(input_dir).exists():
        print(f"\nError: Directorio no encontrado: {input_dir}")
        return

    # Convertir
    convertidas = convertir_directorio(input_dir, output_dir)

    if convertidas > 0:
        print(f"\n✅ Listo! Ahora puedes ejecutar:")
        print(f"   python test_real_data_facturas.py")


if __name__ == "__main__":
    main()
