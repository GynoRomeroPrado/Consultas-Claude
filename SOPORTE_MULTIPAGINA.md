# 📄 Soporte para PDFs Multipágina

## ✅ Estado Actual

**Tu sistema YA soporta completamente PDFs con múltiples páginas.**

No necesitas hacer cambios - el sistema ya está diseñado para manejar documentos multipágina desde el inicio.

---

## 🔍 Cómo Funciona

### **Extracción de Coordenadas**

El sistema procesa **TODAS las páginas** automáticamente:

```python
# El extractor recorre todas las páginas
for page_num in range(len(doc)):  # ← Itera sobre TODAS las páginas
    page = doc[page_num]
    words = page.get_text("words")

    for word in words:
        word_data = {
            'text': word[4],
            'bbox': (word[0], word[1], word[2], word[3]),
            'page_num': page_num,  # ← Guarda número de página
            'page_width': page_width,
            'page_height': page_height
        }
        words_data.append(word_data)
```

### **Matching en Múltiples Páginas**

Cuando buscas un campo del JSON, el sistema:

1. ✅ Busca en **TODAS las páginas** del PDF
2. ✅ Encuentra el campo esté en la página que esté
3. ✅ Guarda el número de página en el resultado
4. ✅ Incluye las dimensiones de esa página específica

---

## 📊 Formato del Output JSON

### **Ejemplo: PDF de 3 páginas**

**Estructura del PDF:**
```
Página 0 (primera):
  - RUC: 20137291313
  - Razón Social: ACME Corporation SAC
  - Dirección: Av. Los Pinos 123

Página 1 (segunda):
  - Items de la factura
  - Subtotal: 1000.00
  - IGV: 180.00

Página 2 (tercera):
  - Total: 1180.00
  - Observaciones: Pago en efectivo
```

**Output JSON Generado:**

```json
{
  "documento_origen": "factura_001.pdf",
  "json_origen": "factura_001.json",
  "total_campos": 7,
  "campos_encontrados": 7,
  "match_rate": 100.0,
  "confianza_promedio": 0.9857,
  "paginas": [0, 1, 2],  ← Lista de páginas con matches
  "coordenadas": [
    {
      "campo": "emisor_ruc",
      "texto": "20137291313",
      "bbox": [100.0, 50.0, 200.0, 65.0],
      "pagina": 0,  ← PÁGINA 0 (primera)
      "confianza": 1.0,
      "tipo_matching": "exact",
      "dimensiones_pagina": {
        "ancho": 595.0,
        "alto": 842.0
      }
    },
    {
      "campo": "emisor_razon_social",
      "texto": "ACME Corporation SAC",
      "bbox": [100.0, 70.0, 300.0, 85.0],
      "pagina": 0,  ← PÁGINA 0 (primera)
      "confianza": 1.0,
      "tipo_matching": "exact",
      "dimensiones_pagina": {
        "ancho": 595.0,
        "alto": 842.0
      }
    },
    {
      "campo": "subtotal",
      "texto": "1000.00",
      "bbox": [450.0, 400.0, 520.0, 415.0],
      "pagina": 1,  ← PÁGINA 1 (segunda)
      "confianza": 1.0,
      "tipo_matching": "exact",
      "dimensiones_pagina": {
        "ancho": 595.0,
        "alto": 842.0
      }
    },
    {
      "campo": "igv",
      "texto": "180.00",
      "bbox": [450.0, 420.0, 520.0, 435.0],
      "pagina": 1,  ← PÁGINA 1 (segunda)
      "confianza": 1.0,
      "tipo_matching": "exact",
      "dimensiones_pagina": {
        "ancho": 595.0,
        "alto": 842.0
      }
    },
    {
      "campo": "total",
      "texto": "1180.00",
      "bbox": [450.0, 100.0, 520.0, 115.0],
      "pagina": 2,  ← PÁGINA 2 (tercera)
      "confianza": 1.0,
      "tipo_matching": "exact",
      "dimensiones_pagina": {
        "ancho": 595.0,
        "alto": 842.0
      }
    }
  ]
}
```

**Nota:** Cada coordenada incluye:
- ✅ `"pagina"`: Número de página (0-indexed: 0 = primera, 1 = segunda, etc.)
- ✅ `"bbox"`: Coordenadas en esa página específica
- ✅ `"dimensiones_pagina"`: Ancho y alto de esa página

---

## 📐 Sistema de Coordenadas

### **IMPORTANTE: Las coordenadas son relativas a cada página**

```
PÁGINA 0 (Primera):
┌─────────────────────────────┐
│ (0,0)                       │
│                             │
│   RUC: 20137291313          │ ← bbox: [100, 50, 200, 65]
│   bbox relativa a página 0  │
│                             │
└─────────────────────────────┘

PÁGINA 1 (Segunda):
┌─────────────────────────────┐
│ (0,0)  ← Origen NUEVO       │
│                             │
│                  Subtotal:  │ ← bbox: [450, 400, 520, 415]
│                  1000.00    │    bbox relativa a página 1
│                             │
└─────────────────────────────┘

PÁGINA 2 (Tercera):
┌─────────────────────────────┐
│ (0,0)  ← Origen NUEVO       │
│                             │
│                  Total:     │ ← bbox: [450, 100, 520, 115]
│                  1180.00    │    bbox relativa a página 2
│                             │
└─────────────────────────────┘
```

**Cada página tiene su propio sistema de coordenadas:**
- (0, 0) está en la esquina superior izquierda de CADA página
- Las coordenadas `bbox` son relativas a la página donde se encuentra el campo
- Esto es el estándar de LayoutLM y otros modelos

---

## 🎯 Casos de Uso Soportados

### ✅ **Caso 1: Campo en una sola página**
```json
{
  "campo": "ruc",
  "texto": "20137291313",
  "bbox": [100, 50, 200, 65],
  "pagina": 0
}
```

### ✅ **Caso 2: Múltiples campos en diferentes páginas**
```json
{
  "coordenadas": [
    {"campo": "ruc", "pagina": 0, ...},
    {"campo": "total", "pagina": 2, ...},
    {"campo": "observaciones", "pagina": 3, ...}
  ]
}
```

### ✅ **Caso 3: Campo duplicado en varias páginas**
Si el mismo valor aparece en múltiples páginas, el sistema:
- Por defecto toma **la primera ocurrencia**
- Puedes configurar para tomar **todas las ocurrencias**

```python
# Configuración en pipeline
config = PipelineConfig(
    matcher=MatcherConfig(
        prefer_first_match=True  # ← Solo primera ocurrencia (default)
        # prefer_first_match=False  ← Todas las ocurrencias
    )
)
```

### ✅ **Caso 4: Páginas de diferentes tamaños**
El sistema maneja PDFs con páginas de diferentes dimensiones:

```json
{
  "coordenadas": [
    {
      "campo": "titulo",
      "pagina": 0,
      "dimensiones_pagina": {"ancho": 595.0, "alto": 842.0}  ← A4
    },
    {
      "campo": "anexo",
      "pagina": 1,
      "dimensiones_pagina": {"ancho": 841.0, "alto": 595.0}  ← A4 horizontal
    }
  ]
}
```

---

## 📊 Estadísticas de Múltiples Páginas

El sistema genera estadísticas automáticamente:

```json
{
  "documento_origen": "factura_multipagina.pdf",
  "total_campos": 29,
  "campos_encontrados": 27,
  "match_rate": 93.1,
  "confianza_promedio": 0.9534,
  "paginas": [0, 1, 2],  ← Páginas con matches encontrados
  "distribucion_por_pagina": {
    "0": 15,  ← 15 campos en página 0
    "1": 8,   ← 8 campos en página 1
    "2": 4    ← 4 campos en página 2
  }
}
```

---

## 🔧 Herramientas para Validación

### **1. Script de Validación Multipágina**

```bash
python validar_multipagina.py "ruta/al/pdf_multipagina.pdf"
```

Este script:
- ✅ Detecta el número de páginas del PDF
- ✅ Procesa todas las páginas
- ✅ Muestra distribución de campos por página
- ✅ Valida que todas las páginas sean procesadas

### **2. Visualización por Página**

```bash
# Visualizar página específica
python visualizar_coordenadas.py \
    "factura.pdf" \
    "factura_coordenadas.json" \
    --pagina 0 \
    -o verificacion_pagina0.png

# Visualizar todas las páginas
python visualizar_coordenadas.py \
    "factura.pdf" \
    "factura_coordenadas.json" \
    --todas-las-paginas \
    -o verificacion_
```

Genera:
- `verificacion_pagina0.png`
- `verificacion_pagina1.png`
- `verificacion_pagina2.png`

### **3. Análisis de Distribución**

```bash
python analizar_distribucion_paginas.py "dataset_con_coordenadas/"
```

Muestra:
- Número de campos por página
- Páginas con más/menos campos
- Campos que aparecen en múltiples páginas

---

## 🧪 Ejemplo de Prueba

### **Paso 1: Crear JSON de prueba**

```json
{
  "emisor_ruc": "20137291313",
  "emisor_nombre": "ACME Corporation",
  "item_1_descripcion": "Producto A",
  "item_1_precio": "100.00",
  "subtotal": "1000.00",
  "igv": "180.00",
  "total": "1180.00",
  "observaciones": "Pago en efectivo"
}
```

### **Paso 2: Procesar PDF multipágina**

```bash
python generar_dataset_prueba.py
```

### **Paso 3: Verificar distribución**

```bash
python validar_multipagina.py \
    "Datos extraidos de Originales/pdfs/factura_multipagina.pdf" \
    "dataset_con_coordenadas/factura_multipagina_coordenadas.json"
```

**Output esperado:**
```
📊 ANÁLISIS DE PDF MULTIPÁGINA
==================================================
PDF: factura_multipagina.pdf
Número de páginas: 3
Total de campos: 8
Campos encontrados: 8

📄 DISTRIBUCIÓN POR PÁGINA:
==================================================
  Página 0: 2 campos (25.0%)
    - emisor_ruc
    - emisor_nombre

  Página 1: 4 campos (50.0%)
    - item_1_descripcion
    - item_1_precio
    - subtotal
    - igv

  Página 2: 2 campos (25.0%)
    - total
    - observaciones

✅ Todas las páginas fueron procesadas correctamente
```

---

## 🎨 Visualización Mejorada

He mejorado el visualizador para soportar múltiples páginas:

```python
# Opción 1: Visualizar una página específica
python visualizar_coordenadas.py \
    pdf.pdf coords.json \
    --pagina 1 \
    -o pagina1.png

# Opción 2: Visualizar todas las páginas (genera múltiples imágenes)
python visualizar_coordenadas.py \
    pdf.pdf coords.json \
    --todas-las-paginas \
    -o verificacion_

# Opción 3: Crear collage de todas las páginas
python visualizar_coordenadas.py \
    pdf.pdf coords.json \
    --modo collage \
    -o collage_completo.png
```

---

## ⚠️ Consideraciones Importantes

### **1. Páginas muy grandes**

Si tienes PDFs con muchas páginas (50+):
- El procesamiento puede tardar más
- El archivo JSON será más grande
- ✅ El sistema lo maneja sin problemas

### **2. Memoria**

Para PDFs de 100+ páginas:
- El sistema carga todas las palabras en memoria
- Recomendado: Procesar en batches si tienes muchos documentos grandes

### **3. Campos duplicados en varias páginas**

Si un valor aparece en múltiples páginas (ej: "RUC" en encabezado de cada página):
- Por defecto: Toma solo la primera ocurrencia
- Configurable: Puedes obtener todas las ocurrencias

---

## 🚀 Mejoras Implementadas

He agregado:

1. ✅ **`validar_multipagina.py`** - Script de validación
2. ✅ **`visualizar_coordenadas.py` mejorado** - Soporte para visualizar página específica
3. ✅ **`analizar_distribucion_paginas.py`** - Análisis de distribución
4. ✅ **Documentación completa** - Este archivo

---

## 📝 Resumen

### ✅ **Lo que YA funciona:**
- Procesamiento de todas las páginas automáticamente
- Extracción de coordenadas con número de página
- Estadísticas por página
- Formato JSON correcto con `"pagina"` para cada campo

### ✅ **Lo que he agregado:**
- Scripts de validación para PDFs multipágina
- Visualización mejorada por página
- Análisis de distribución
- Documentación completa

### ❌ **Lo que NO necesitas hacer:**
- Nada - el sistema ya está completo para multipágina

---

## 💡 Siguiente Paso

**Prueba con tus datos:**

```bash
# 1. Procesa un PDF multipágina
python generar_dataset_prueba.py

# 2. Valida el resultado
python validar_multipagina.py \
    "Datos extraidos de Originales/pdfs/tu_factura.pdf" \
    "dataset_con_coordenadas/tu_factura_coordenadas.json"

# 3. Visualiza cada página
python visualizar_coordenadas.py \
    "Datos extraidos de Originales/pdfs/tu_factura.pdf" \
    "dataset_con_coordenadas/tu_factura_coordenadas.json" \
    --todas-las-paginas \
    -o verificacion_pagina_
```

¡Listo! Tu sistema ya maneja PDFs multipágina perfectamente. 🎉
