#!/usr/bin/env python3
"""
Script para analizar y visualizar cómo se manejan los campos multilínea.
Muestra la diferencia entre bbox única vs múltiples bboxes.
"""

import sys
import json
import fitz
from pathlib import Path
from collections import defaultdict

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.extractors.pdf_extractor import PDFExtractor
    from src.extractors.json_parser import JSONParser
    from src.matchers.fuzzy_matcher import MultiStrategyMatcher
except ImportError as e:
    print(f"❌ Error: {e}")
    print("\nInstala las dependencias:")
    print("  pip install PyMuPDF rapidfuzz")
    sys.exit(1)


def detectar_campos_multilinea(pdf_path, coordenadas_json_path):
    """
    Analiza un archivo de coordenadas y detecta campos multilínea.

    Args:
        pdf_path: Ruta al PDF
        coordenadas_json_path: Ruta al JSON con coordenadas generado

    Returns:
        Dict con análisis
    """

    print("="*80)
    print("ANÁLISIS DE CAMPOS MULTILÍNEA")
    print("="*80)
    print(f"PDF: {pdf_path}")
    print(f"Coordenadas: {coordenadas_json_path}")
    print()

    # Leer coordenadas generadas
    with open(coordenadas_json_path, 'r', encoding='utf-8') as f:
        coords_data = json.load(f)

    # Extraer palabras del PDF con información de líneas
    extractor = PDFExtractor()
    words_data = extractor.extract_words(pdf_path)

    # Agrupar palabras por línea
    lines_by_page = defaultdict(lambda: defaultdict(list))
    for word in words_data:
        page = word['page_num']
        line = word['line_no']
        lines_by_page[page][line].append(word)

    # Analizar cada campo
    campos_multilinea = []
    campos_unilinea = []

    for coord in coords_data['coordenadas']:
        campo = coord['campo']
        bbox = coord['bbox']
        pagina = coord['pagina']
        texto = coord['texto']

        # Encontrar qué palabras están dentro de esta bbox
        palabras_dentro = []
        lineas_dentro = set()

        x0, y0, x1, y1 = bbox

        for word in words_data:
            if word['page_num'] != pagina:
                continue

            wx0, wy0, wx1, wy1 = word['bbox']

            # Verificar si la palabra está dentro o se solapa con la bbox
            # (con un pequeño margen de tolerancia)
            margin = 2
            if (wx0 >= x0 - margin and wx1 <= x1 + margin and
                wy0 >= y0 - margin and wy1 <= y1 + margin):
                palabras_dentro.append(word)
                lineas_dentro.add(word['line_no'])

        # Determinar si es multilínea
        num_lineas = len(lineas_dentro)
        es_multilinea = num_lineas > 1

        info = {
            'campo': campo,
            'texto': texto,
            'bbox': bbox,
            'pagina': pagina,
            'num_lineas': num_lineas,
            'lineas': sorted(lineas_dentro),
            'num_palabras': len(palabras_dentro),
            'confianza': coord.get('confianza', 1.0)
        }

        if es_multilinea:
            # Calcular bboxes individuales por línea
            bboxes_por_linea = []
            textos_por_linea = []

            for line_no in sorted(lineas_dentro):
                palabras_linea = [w for w in palabras_dentro if w['line_no'] == line_no]
                if palabras_linea:
                    # Bbox de la línea
                    lx0 = min(w['bbox'][0] for w in palabras_linea)
                    ly0 = min(w['bbox'][1] for w in palabras_linea)
                    lx1 = max(w['bbox'][2] for w in palabras_linea)
                    ly1 = max(w['bbox'][3] for w in palabras_linea)

                    texto_linea = ' '.join(w['text'] for w in palabras_linea)

                    bboxes_por_linea.append([lx0, ly0, lx1, ly1])
                    textos_por_linea.append(texto_linea)

            info['bboxes_por_linea'] = bboxes_por_linea
            info['textos_por_linea'] = textos_por_linea

            campos_multilinea.append(info)
        else:
            campos_unilinea.append(info)

    # Mostrar resultados
    total = len(coords_data['coordenadas'])
    num_multilinea = len(campos_multilinea)
    num_unilinea = len(campos_multilinea)

    print(f"📊 RESUMEN")
    print(f"{'='*80}")
    print(f"  Total de campos:       {total}")
    print(f"  Campos multilínea:     {num_multilinea} ({num_multilinea/total*100:.1f}%)")
    print(f"  Campos de una línea:   {num_unilinea} ({num_unilinea/total*100:.1f}%)")
    print()

    if campos_multilinea:
        print(f"🔍 CAMPOS MULTILÍNEA DETECTADOS ({num_multilinea})")
        print("="*80)

        for i, campo in enumerate(campos_multilinea, 1):
            print(f"\n[{i}] {campo['campo']}")
            print(f"    Texto completo: '{campo['texto']}'")
            print(f"    Número de líneas: {campo['num_lineas']}")
            print(f"    Confianza: {campo['confianza']:.2f}")
            print()

            # Bbox combinada (actual)
            print(f"    ✅ ENFOQUE 1 (ACTUAL): Una sola bbox")
            print(f"       bbox: {campo['bbox']}")
            x0, y0, x1, y1 = campo['bbox']
            ancho = x1 - x0
            alto = y1 - y0
            print(f"       dimensiones: {ancho:.1f} x {alto:.1f}")
            print()

            # Bboxes por línea (alternativa)
            print(f"    📋 ENFOQUE 2 (ALTERNATIVO): Múltiples bboxes")
            for j, (bbox_linea, texto_linea) in enumerate(
                zip(campo['bboxes_por_linea'], campo['textos_por_linea']), 1
            ):
                print(f"       Línea {j}: {bbox_linea}")
                print(f"       Texto:  '{texto_linea}'")
                lx0, ly0, lx1, ly1 = bbox_linea
                lancho = lx1 - lx0
                lalto = ly1 - ly0
                print(f"       Dim:    {lancho:.1f} x {lalto:.1f}")

            # Comparación
            area_combinada = (x1 - x0) * (y1 - y0)
            area_individual = sum(
                (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                for bbox in campo['bboxes_por_linea']
            )
            espacio_vacio = area_combinada - area_individual
            porcentaje_vacio = (espacio_vacio / area_combinada) * 100

            print()
            print(f"    📐 COMPARACIÓN:")
            print(f"       Área bbox combinada:  {area_combinada:.1f} px²")
            print(f"       Área bboxes individuales: {area_individual:.1f} px²")
            print(f"       Espacio vacío incluido: {espacio_vacio:.1f} px² ({porcentaje_vacio:.1f}%)")

            if porcentaje_vacio > 20:
                print(f"       ⚠️  Bbox combinada incluye {porcentaje_vacio:.1f}% de espacio vacío")
            else:
                print(f"       ✅ Bbox combinada es eficiente")

            print(f"    {'-'*76}")
    else:
        print("✅ No se detectaron campos multilínea en este documento")
        print("   Todos los campos están en una sola línea.")

    # Generar JSON con ambos enfoques para comparación
    output_comparacion = {
        "documento": coords_data['documento_origen'],
        "total_campos": total,
        "campos_multilinea": num_multilinea,
        "campos_unilinea": num_unilinea,
        "enfoque_1_actual": {
            "descripcion": "Una bbox por campo (abarca todas las líneas)",
            "campos": [
                {
                    "campo": c['campo'],
                    "texto": c['texto'],
                    "bbox": c['bbox'],
                    "num_lineas": c['num_lineas']
                }
                for c in campos_multilinea
            ]
        },
        "enfoque_2_alternativo": {
            "descripcion": "Múltiples bboxes (una por línea)",
            "campos": [
                {
                    "campo": c['campo'],
                    "texto_completo": c['texto'],
                    "bbox_combinada": c['bbox'],
                    "num_lineas": c['num_lineas'],
                    "lineas": [
                        {
                            "numero": j + 1,
                            "texto": texto,
                            "bbox": bbox
                        }
                        for j, (bbox, texto) in enumerate(
                            zip(c['bboxes_por_linea'], c['textos_por_linea'])
                        )
                    ]
                }
                for c in campos_multilinea
            ]
        }
    }

    # Guardar comparación
    output_path = Path("dataset_con_coordenadas") / "analisis_multilinea.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_comparacion, f, indent=2, ensure_ascii=False)

    print()
    print("="*80)
    print(f"✅ Análisis guardado en: {output_path}")
    print("="*80)

    return output_comparacion


def visualizar_comparacion(pdf_path, analisis_json_path, output_base="visualizacion"):
    """
    Genera visualizaciones comparativas de ambos enfoques.

    Args:
        pdf_path: Ruta al PDF
        analisis_json_path: Ruta al JSON de análisis
        output_base: Prefijo para archivos de salida
    """
    from PIL import Image, ImageDraw, ImageFont

    # Leer análisis
    with open(analisis_json_path, 'r', encoding='utf-8') as f:
        analisis = json.load(f)

    if not analisis['campos_multilinea']:
        print("No hay campos multilínea para visualizar")
        return

    # Abrir PDF
    doc = fitz.open(pdf_path)
    page = doc[0]

    # Convertir a imagen (alta resolución)
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")

    # Cargar con PIL
    from io import BytesIO
    img1 = Image.open(BytesIO(img_bytes))
    img2 = img1.copy()

    draw1 = ImageDraw.Draw(img1)
    draw2 = ImageDraw.Draw(img2)

    # Colores
    color_combinada = (255, 0, 0, 80)  # Rojo semitransparente
    color_lineas = [(0, 255, 0, 100), (0, 0, 255, 100), (255, 165, 0, 100)]  # Verde, azul, naranja

    # Dibujar enfoque 1 (bbox combinada)
    for campo in analisis['enfoque_1_actual']['campos']:
        x0, y0, x1, y1 = campo['bbox']
        # Escalar por matriz de zoom (2x)
        draw1.rectangle([x0*2, y0*2, x1*2, y1*2], outline='red', width=3)

    # Dibujar enfoque 2 (bboxes por línea)
    for campo in analisis['enfoque_2_alternativo']['campos']:
        for i, linea in enumerate(campo['lineas']):
            x0, y0, x1, y1 = linea['bbox']
            color = color_lineas[i % len(color_lineas)]
            color_outline = tuple(color[:3])  # Sin alpha para outline
            draw2.rectangle([x0*2, y0*2, x1*2, y1*2], outline=color_outline, width=3)

    # Guardar
    output_dir = Path("dataset_con_coordenadas")
    output_dir.mkdir(parents=True, exist_ok=True)

    output1 = output_dir / f"{output_base}_enfoque1.png"
    output2 = output_dir / f"{output_base}_enfoque2.png"

    img1.save(output1)
    img2.save(output2)

    print(f"\n✅ Visualizaciones generadas:")
    print(f"   Enfoque 1 (bbox única):     {output1}")
    print(f"   Enfoque 2 (bboxes múltiples): {output2}")

    doc.close()


def main():
    """Función principal."""

    print("="*80)
    print("ANÁLISIS DE CAMPOS MULTILÍNEA")
    print("="*80)
    print()

    # Buscar archivos
    coords_dir = Path("dataset_con_coordenadas")

    if not coords_dir.exists():
        print("❌ No se encontró la carpeta 'dataset_con_coordenadas/'")
        print("   Primero ejecuta: python generar_dataset_prueba.py")
        sys.exit(1)

    # Buscar primer archivo de coordenadas
    coord_files = list(coords_dir.glob("*_coordenadas.json"))

    if not coord_files:
        print("❌ No se encontraron archivos de coordenadas")
        print("   Primero ejecuta: python generar_dataset_prueba.py")
        sys.exit(1)

    coord_file = coord_files[0]

    # Buscar PDF correspondiente
    with open(coord_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        pdf_name = data['documento_origen']

    pdf_path = Path("Datos extraidos de Originales") / "pdfs" / pdf_name

    if not pdf_path.exists():
        print(f"❌ No se encontró el PDF: {pdf_path}")
        sys.exit(1)

    # Analizar
    analisis = detectar_campos_multilinea(str(pdf_path), str(coord_file))

    # Visualizar si hay campos multilínea
    if analisis['campos_multilinea'] > 0:
        print("\n🎨 Generando visualizaciones comparativas...")
        visualizar_comparacion(
            str(pdf_path),
            "dataset_con_coordenadas/analisis_multilinea.json"
        )

    print("\n" + "="*80)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*80)
    print("\nArchivos generados:")
    print("  - dataset_con_coordenadas/analisis_multilinea.json")
    if analisis['campos_multilinea'] > 0:
        print("  - dataset_con_coordenadas/visualizacion_enfoque1.png")
        print("  - dataset_con_coordenadas/visualizacion_enfoque2.png")

    print("\n📖 Para más información, lee: CAMPOS_MULTILINEA.md")


if __name__ == "__main__":
    main()
