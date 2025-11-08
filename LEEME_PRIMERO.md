# 🎯 LÉEME PRIMERO - Procesamiento de Facturas Electrónicas

## ✅ ¡Sistema Listo!

He analizado tus archivos y preparado TODO el sistema para procesar tus **15 facturas electrónicas**.

---

## 📊 Tus Datos

He identificado:

- ✅ **15 imágenes PNG** de facturas en: `Datos extraidos de Originales/facturas_procesadas/`
- ✅ **15 archivos JSON** con anotaciones en: `Datos extraidos de Originales/anotaciones/`
- ✅ **29 campos por factura**:
  - `tipo_documento`, `serie_completa`, `fecha_emision`
  - `emisor_ruc`, `emisor_razon_social`, `emisor_direccion`
  - `receptor_numero_doc`, `receptor_razon_social`
  - `subtotal`, `igv`, `importe_total`
  - Y 18 campos más...

---

## 🚀 Pasos para Ejecutar (3 minutos)

### **Paso 1: Instalar Dependencias** ⏱️ 2 min

```bash
# Instalar bibliotecas necesarias
pip install PyMuPDF rapidfuzz numpy pandas tqdm

# O usar el archivo requirements.txt
pip install -r requirements.txt
```

### **Paso 2: Convertir PNG a PDF** ⏱️ 30 seg

```bash
python convertir_png_a_pdf_simple.py
```

Esto creará:
- 📁 `Datos extraidos de Originales/pdfs/` con 15 PDFs

### **Paso 3: Ejecutar Pruebas** ⏱️ 1-2 min

```bash
python test_facturas.py
```

Este script hará TODO automáticamente:
1. ✅ Verifica que todo esté instalado
2. ✅ Analiza la estructura de tus JSONs
3. ✅ Prueba 3 estrategias diferentes de matching
4. ✅ Compara resultados y recomienda la mejor
5. ✅ Procesa las 15 facturas
6. ✅ Guarda resultados en `output/facturas/`

---

## 📋 Qué Va a Pasar

### Salida Esperada:

```
================================================================================
SISTEMA DE EXTRACCIÓN DE COORDENADAS - FACTURAS ELECTRÓNICAS
================================================================================

Verificando prerequisitos...
  ✓ PyMuPDF version 1.23.0
  ✓ RapidFuzz version 3.5.0
  ✓ 15 PDFs encontrados
  ✓ 15 JSONs encontrados

✅ Todos los prerequisitos cumplidos

✓ Encontrados 15 pares PDF-JSON

################################################################################
# ANÁLISIS DE ESTRUCTURA
################################################################################

📄 Estructura del JSON: IMG-20251026-WA0038.json
================================================================================
Total de campos: 29

Campos de texto: 13
  - tipo_documento: FACTURA ELECTRÓNICA
  - serie_completa: F003-00015692
  - emisor_razon_social: MINERA YANACOCHA S.R.L.
  - receptor_razon_social: CONSULTORIA ENTRENAMIENTO Y...
  ... y 9 más

Campos numéricos: 9
  - subtotal: 13350.64
  - igv: 2403.12
  - importe_total: 15753.76
  ...

Campos de fecha: 2
  - fecha_emision: 2025-07-21
  - fecha_vencimiento: 2025-08-20

Campos nulos: 5

================================================================================

################################################################################
# COMPARACIÓN DE ESTRATEGIAS (Primera factura)
################################################################################

================================================================================
PROBANDO: EXACT (threshold=100.0)
================================================================================

📊 RESULTADOS - EXACT
================================================================================
  Total de campos:       29
  Campos encontrados:    XX  (depende de la factura)
  Campos NO encontrados: XX
  Tasa de éxito:         XX.X%
  Confianza promedio:    1.0000

  Tipos de matching:
    - exact: XX

📝 EJEMPLOS DE MATCHES (primeros 10)
================================================================================

[1] tipo_documento
    Texto: 'FACTURA ELECTRÓNICA'
    Bbox: (100.5, 50.3, 300.8, 70.1)
    Página: 0
    Confianza: 1.00
    Tipo: exact

[2] serie_completa
    Texto: 'F003-00015692'
    Bbox: (150.2, 120.5, 250.7, 135.3)
    Página: 0
    Confianza: 1.00
    Tipo: exact

... (8 más)

================================================================================
RESUMEN COMPARATIVO
================================================================================
Estrategia                Threshold    Match Rate      Confianza
--------------------------------------------------------------------------------
exact                     100.0        XX.X%           1.0000
auto                      80.0         XX.X%           0.XXXX
fuzzy                     70.0         XX.X%           0.XXXX

🏆 MEJOR ESTRATEGIA: auto (threshold=80.0)
   Match rate: XX.X%
   Confianza: 0.XXXX

################################################################################
# PROCESANDO RESTO DE FACTURAS (14)
################################################################################

[2/15] ============================================================
PDF:  IMG-20251026-WA0039.pdf
JSON: IMG-20251026-WA0039.json
...

[3/15] ============================================================
...

================================================================================
PROCESO COMPLETADO
================================================================================
Resultados guardados en: output/facturas/
Total de facturas procesadas: 15
```

---

## 📂 Resultados Generados

Después de ejecutar, tendrás:

```
output/facturas/
├── IMG-20251026-WA0038_auto.json       # Coordenadas extraídas
├── IMG-20251026-WA0038_exact.json
├── IMG-20251026-WA0038_fuzzy.json
├── IMG-20251026-WA0039_auto.json
├── IMG-20251026-WA0040_auto.json
└── ... (15 archivos x 3 estrategias = 45 archivos)
```

### Formato de cada archivo:

```json
{
  "format": "custom",
  "total_fields": 29,
  "annotations": [
    {
      "field_name": "tipo_documento",
      "text": "FACTURA ELECTRÓNICA",
      "bbox": {
        "x0": 100.5,
        "y0": 50.3,
        "x1": 300.8,
        "y1": 70.1
      },
      "page": 0,
      "confidence": 1.0,
      "match_type": "exact"
    },
    {
      "field_name": "serie_completa",
      "text": "F003-00015692",
      "bbox": {
        "x0": 150.2,
        "y0": 120.5,
        "x1": 250.7,
        "y1": 135.3
      },
      "page": 0,
      "confidence": 1.0,
      "match_type": "exact"
    },
    ... (27 campos más)
  ]
}
```

---

## 🎯 Usar los Resultados

### Para Entrenamiento de LayoutLM:

```bash
# Exportar en formato LayoutLM (0-1000 scale)
python extract_coordinates.py \
    "Datos extraidos de Originales/pdfs/IMG-20251026-WA0038.pdf" \
    -o output/layoutlm/factura1.json \
    --format layoutlm
```

### Para Object Detection (COCO):

```bash
# Exportar en formato COCO
python extract_coordinates.py \
    "Datos extraidos de Originales/pdfs/IMG-20251026-WA0038.pdf" \
    -o output/coco/annotations.json \
    --format coco
```

### Procesamiento por Lotes:

```bash
# Procesar todas las facturas a la vez
python extract_coordinates.py \
    --batch "Datos extraidos de Originales/pdfs/" \
    output/batch/
```

---

## 🔍 Posibles Problemas

### Si Match Rate < 50%

**Causas**:
1. Las imágenes PNG tienen mala calidad
2. El texto en la imagen es diferente al JSON
3. Hay errores de OCR en las imágenes

**Solución**: Usa fuzzy matching más permisivo
```bash
python extract_coordinates.py \
    "Datos extraidos de Originales/pdfs/IMG-20251026-WA0038.pdf" \
    -o output/test.json \
    --fuzzy --threshold 60 -v
```

### Si algunos campos no se encuentran

**Debug**: Ver qué texto hay realmente en el PDF
```bash
python -c "
import fitz
doc = fitz.open('Datos extraidos de Originales/pdfs/IMG-20251026-WA0038.pdf')
print(doc[0].get_text())
"
```

---

## 📝 Compartir Resultados

Una vez ejecutado, compárteme:

1. **La salida completa** del script `test_facturas.py`
2. **Match rate obtenido** (%)
3. **Campos que NO se encontraron** (si hay)
4. **Problemas específicos** que veas

Con eso podré:
- ✅ Optimizar los parámetros
- ✅ Ajustar el matching
- ✅ Corregir errores específicos

---

## ⚡ Resumen Ejecutivo

```bash
# 1️⃣ Instalar (una sola vez)
pip install PyMuPDF rapidfuzz numpy pandas tqdm

# 2️⃣ Convertir PNGs a PDFs
python convertir_png_a_pdf_simple.py

# 3️⃣ Ejecutar pruebas
python test_facturas.py

# 4️⃣ Ver resultados
ls output/facturas/
```

**Tiempo total estimado: 3-5 minutos** ⏱️

---

## 🎉 ¡Estás Listo!

El sistema está **100% preparado** para procesar tus facturas.

Ejecuta los 3 comandos y comparte los resultados.

**¡Adelante!** 🚀
