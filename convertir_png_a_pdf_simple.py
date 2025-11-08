#!/usr/bin/env python3
"""
Convierte imágenes PNG a PDF usando solo PyMuPDF.
"""

import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF no está instalado")
    print("Intenta: pip install PyMuPDF")
    sys.exit(1)


def convertir_png_a_pdf(png_path, pdf_path):
    """
    Convierte una imagen PNG a PDF usando PyMuPDF.

    Args:
        png_path: Ruta a la imagen PNG
        pdf_path: Ruta donde guardar el PDF
    """
    try:
        # Crear un nuevo documento PDF
        doc = fitz.open()

        # Abrir la imagen
        img = fitz.open(png_path)

        # Obtener dimensiones de la imagen
        pdfbytes = img.convert_to_pdf()

        # Cerrar imagen
        img.close()

        # Crear PDF desde bytes
        imgpdf = fitz.open("pdf", pdfbytes)

        # Copiar la página al documento
        doc.insert_pdf(imgpdf)

        # Guardar
        doc.save(pdf_path)
        doc.close()
        imgpdf.close()

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


def convertir_directorio(input_dir, output_dir):
    """
    Convierte todas las PNGs de un directorio a PDF.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Crear directorio de salida
    output_path.mkdir(parents=True, exist_ok=True)

    # Buscar PNGs
    png_files = sorted(list(input_path.glob('*.png')))

    print(f"\nEncontradas {len(png_files)} imágenes PNG")
    print(f"Convirtiendo a PDF...\n")

    convertidas = 0
    errores = 0

    for i, png_file in enumerate(png_files, 1):
        pdf_file = output_path / (png_file.stem + '.pdf')

        print(f"[{i}/{len(png_files)}] {png_file.name[:50]:50}", end=' ')

        if convertir_png_a_pdf(str(png_file), str(pdf_file)):
            print("✓")
            convertidas += 1
        else:
            print("✗")
            errores += 1

    print(f"\n{'='*80}")
    print(f"RESULTADOS:")
    print(f"  Convertidas: {convertidas}/{len(png_files)}")
    print(f"  Errores: {errores}")
    print(f"  PDFs guardados en: {output_path}/")
    print(f"{'='*80}")

    return convertidas


def main():
    """Función principal."""

    print("=" * 80)
    print("CONVERSOR PNG → PDF (usando PyMuPDF)")
    print("=" * 80)

    # Directorios
    input_dir = "Datos extraidos de Originales/facturas_procesadas"
    output_dir = "Datos extraidos de Originales/pdfs"

    if not Path(input_dir).exists():
        print(f"\nError: Directorio no encontrado: {input_dir}")
        sys.exit(1)

    # Convertir
    convertidas = convertir_directorio(input_dir, output_dir)

    if convertidas > 0:
        print(f"\n✅ ¡Conversión completada!")
        print(f"\nAhora puedes ejecutar las pruebas:")
        print(f"  python test_facturas.py")


if __name__ == "__main__":
    main()
