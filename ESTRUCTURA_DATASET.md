# 📁 Estructura del Dataset - Guía Completa

## 🎯 Resumen

Este proyecto lee PDFs y JSONs de una carpeta, extrae coordenadas, y genera un **dataset SEPARADO** listo para entrenar modelos.

---

## 📂 Estructura de Carpetas

### **ENTRADA** (Tus archivos originales):

```
Datos extraidos de Originales/
├── pdfs/                    # ← PDFs originales (o se generan de PNGs)
│   ├── IMG-20251026-WA0038.pdf
│   ├── IMG-20251026-WA0039.pdf
│   └── ...
├── anotaciones/             # ← JSONs con los datos a buscar
│   ├── IMG-20251026-WA0038.json
│   ├── IMG-20251026-WA0039.json
│   └── ...
└── facturas_procesadas/     # ← PNGs originales (se convierten a PDF)
    ├── IMG-20251026-WA0038.png
    └── ...
```

### **SALIDA** (Dataset generado - SEPARADO):

```
dataset_con_coordenadas/     # ← NUEVA carpeta con el dataset final
├── IMG-20251026-WA0038_coordenadas.json
├── IMG-20251026-WA0039_coordenadas.json
├── IMG-20251026-WA0040_coordenadas.json
├── ...
└── resumen_dataset.json     # ← Estadísticas generales
```

**IMPORTANTE**: `dataset_con_coordenadas/` es **TOTALMENTE SEPARADA** de las carpetas de entrada.

---

## 📄 Formato de los Archivos

### **Entrada: JSON con anotaciones**

Ejemplo: `IMG-20251026-WA0038.json`

```json
{
  "tipo_documento": "FACTURA ELECTRÓNICA",
  "serie_completa": "F003-00015692",
  "fecha_emision": "2025-07-21",
  "emisor_ruc": "20137291313",
  "emisor_razon_social": "MINERA YANACOCHA S.R.L.",
  "receptor_numero_doc": "20530074901",
  "subtotal": 13350.64,
  "igv": 2403.12,
  "importe_total": 15753.76,
  ... (21 campos más)
}
```

### **Salida: JSON con coordenadas**

Ejemplo: `IMG-20251026-WA0038_coordenadas.json`

```json
{
  "documento_origen": "IMG-20251026-WA0038.pdf",
  "json_origen": "IMG-20251026-WA0038.json",
  "total_campos": 29,
  "campos_encontrados": 25,
  "campos_no_encontrados": 4,
  "match_rate": 86.2,
  "confianza_promedio": 0.9534,
  "paginas": [0],
  "tipos_matching": {
    "exact": 20,
    "fuzzy": 5
  },
  "coordenadas": [
    {
      "campo": "tipo_documento",
      "texto": "FACTURA ELECTRÓNICA",
      "bbox": [100.5, 50.3, 300.8, 70.1],
      "pagina": 0,
      "confianza": 1.0,
      "tipo_matching": "exact",
      "dimensiones_pagina": {
        "ancho": 595.0,
        "alto": 842.0
      }
    },
    {
      "campo": "emisor_ruc",
      "texto": "20137291313",
      "bbox": [150.2, 120.5, 250.7, 135.3],
      "pagina": 0,
      "confianza": 1.0,
      "tipo_matching": "exact",
      "dimensiones_pagina": {
        "ancho": 595.0,
        "alto": 842.0
      }
    },
    ... (23 coordenadas más)
  ]
}
```

### **Resumen del Dataset**

Archivo: `resumen_dataset.json`

```json
{
  "fecha_generacion": "2025-01-08T10:30:45.123456",
  "total_documentos": 15,
  "procesados_exitosamente": 15,
  "errores": 0,
  "match_rate_promedio": 87.5,
  "confianza_promedio": 0.9234,
  "total_campos": 435,
  "total_campos_encontrados": 381,
  "documentos": [
    {
      "nombre": "IMG-20251026-WA0038.pdf",
      "match_rate": 86.2,
      "campos_encontrados": 25,
      "total_campos": 29
    },
    ... (14 más)
  ]
}
```

---

## 🚀 Flujo de Trabajo

### **Fase 1: Prueba con 1 Archivo**

```bash
# 1. Convertir PNGs a PDFs (si es necesario)
python convertir_png_a_pdf_simple.py

# 2. Generar dataset de prueba (1 archivo)
python generar_dataset_prueba.py

# 3. Revisar resultado en:
#    dataset_con_coordenadas/IMG-20251026-WA0038_coordenadas.json

# 4. Verificar que el formato sea correcto
```

**Salida esperada:**

```
================================================================================
PROCESAMIENTO DE FACTURA - PRUEBA
================================================================================
PDF:  Datos extraidos de Originales/pdfs/IMG-20251026-WA0038.pdf
JSON: Datos extraidos de Originales/anotaciones/IMG-20251026-WA0038.json

🔄 Procesando...

================================================================================
📊 RESULTADOS
================================================================================
  Total de campos:       29
  Campos encontrados:    25
  Campos NO encontrados: 4
  Tasa de éxito:         86.2%
  Confianza promedio:    0.9534

  Tipos de matching:
    - exact: 20
    - fuzzy: 5

✅ Archivo generado: dataset_con_coordenadas/IMG-20251026-WA0038_coordenadas.json
   Tamaño: 8.45 KB

📝 PRIMEROS 3 CAMPOS ENCONTRADOS
================================================================================

[1] tipo_documento
    Texto: 'FACTURA ELECTRÓNICA'
    Bbox:  [100.5, 50.3, 300.8, 70.1]
    Página: 0
    Confianza: 1.00
...
```

### **Fase 2: Dataset Completo**

Si el formato de prueba es correcto:

```bash
# Generar dataset completo
python generar_dataset_completo.py

# Ver resultados
ls dataset_con_coordenadas/

# Ver resumen
cat dataset_con_coordenadas/resumen_dataset.json
```

**Salida esperada:**

```
================================================================================
GENERACIÓN DE DATASET COMPLETO CON COORDENADAS
================================================================================

Directorio PDFs:        Datos extraidos de Originales/pdfs
Directorio JSONs:       Datos extraidos de Originales/anotaciones
Directorio de salida:   dataset_con_coordenadas
Estrategia:             auto
Threshold:              80.0

📄 Encontrados 15 PDFs

✅ 15 pares PDF-JSON listos para procesar

================================================================================
PROCESANDO DATASET
================================================================================
Procesando: 100%|██████████████████████████| 15/15 [00:45<00:00,  3.02s/it]

================================================================================
📊 RESUMEN FINAL
================================================================================
  Total documentos:          15
  Procesados exitosamente:   15
  Errores:                   0
  Match rate promedio:       87.5%
  Confianza promedio:        0.9234
  Total campos en dataset:   435
  Total campos encontrados:  381

================================================================================
📁 ARCHIVOS GENERADOS
================================================================================
  Directorio: dataset_con_coordenadas/
  Archivos individuales: 15
  Resumen general: resumen_dataset.json

  Primeros archivos:
    - IMG-20251026-WA0038_coordenadas.json (8.45 KB)
    - IMG-20251026-WA0039_coordenadas.json (8.32 KB)
    - IMG-20251026-WA0040_coordenadas.json (8.51 KB)
    - IMG-20251026-WA0041_coordenadas.json (8.47 KB)
    - IMG-20251026-WA0042_coordenadas.json (8.39 KB)
    ... y 10 más

================================================================================
✅ DATASET GENERADO COMPLETAMENTE
================================================================================

📂 Dataset disponible en: dataset_con_coordenadas/
```

---

## 🎯 Usar el Dataset para Entrenamiento

### **Opción 1: LayoutLM**

```python
import json

# Cargar coordenadas
with open('dataset_con_coordenadas/factura_001_coordenadas.json') as f:
    data = json.load(f)

# Convertir a formato LayoutLM
for coord in data['coordenadas']:
    bbox = coord['bbox']
    text = coord['texto']
    label = coord['campo']

    # Normalizar coordenadas a 0-1000
    width = coord['dimensiones_pagina']['ancho']
    height = coord['dimensiones_pagina']['alto']

    normalized_bbox = [
        int(1000 * bbox[0] / width),
        int(1000 * bbox[1] / height),
        int(1000 * bbox[2] / width),
        int(1000 * bbox[3] / height)
    ]

    print(f"{label}: {normalized_bbox}")
```

### **Opción 2: Object Detection (COCO)**

```python
import json

# Leer dataset
with open('dataset_con_coordenadas/factura_001_coordenadas.json') as f:
    data = json.load(f)

# Convertir a COCO format
coco_annotations = []

for i, coord in enumerate(data['coordenadas']):
    bbox = coord['bbox']
    # COCO usa [x, y, width, height]
    coco_bbox = [
        bbox[0],
        bbox[1],
        bbox[2] - bbox[0],  # width
        bbox[3] - bbox[1]   # height
    ]

    annotation = {
        'id': i,
        'image_id': 1,
        'category_id': get_category_id(coord['campo']),
        'bbox': coco_bbox,
        'area': coco_bbox[2] * coco_bbox[3],
        'iscrowd': 0
    }
    coco_annotations.append(annotation)
```

---

## 🔧 Personalización

### **Cambiar estrategia de matching:**

```bash
# Más estricto (solo exact)
python generar_dataset_completo.py --strategy exact

# Más permisivo (fuzzy con threshold bajo)
python generar_dataset_completo.py --strategy fuzzy --threshold 70

# Automático (recomendado)
python generar_dataset_completo.py --strategy auto --threshold 80
```

### **Cambiar directorios:**

```bash
python generar_dataset_completo.py \
    --pdfs-dir "mi_carpeta/pdfs" \
    --json-dir "mi_carpeta/jsons" \
    --output-dir "mi_dataset_final"
```

---

## 📊 Métricas de Calidad

### **Match Rate**
- **> 90%**: Excelente - PDFs de alta calidad
- **80-90%**: Bueno - Algunos campos con variaciones
- **70-80%**: Aceptable - Considerar fuzzy matching más permisivo
- **< 70%**: Revisar - Puede haber problemas de OCR o formato

### **Confianza**
- **> 0.95**: Matches muy confiables
- **0.80-0.95**: Matches buenos (fuzzy matching)
- **< 0.80**: Revisar manualmente

---

## 💡 Consejos

1. **Siempre ejecuta primero el modo prueba** para validar el formato
2. **Revisa el resumen_dataset.json** para ver estadísticas generales
3. **Usa `--strategy auto`** para mejor balance exactitud/cobertura
4. **Si match rate < 70%**, prueba `--threshold 65` o `60`
5. **La carpeta `dataset_con_coordenadas/` es tu dataset final** - no modifiques las carpetas de entrada

---

## 📞 Workflow Recomendado

```bash
# 1. Convertir PNGs si es necesario
python convertir_png_a_pdf_simple.py

# 2. Prueba con 1 archivo
python generar_dataset_prueba.py

# 3. Revisar resultado
cat dataset_con_coordenadas/*_coordenadas.json | head -50

# 4. Si está bien, generar dataset completo
python generar_dataset_completo.py

# 5. Ver estadísticas
cat dataset_con_coordenadas/resumen_dataset.json

# 6. Usar dataset para entrenar
# (copiar dataset_con_coordenadas/ a tu proyecto de ML)
```

---

¡Tu dataset está listo para entrenar modelos de Document Understanding! 🎉
