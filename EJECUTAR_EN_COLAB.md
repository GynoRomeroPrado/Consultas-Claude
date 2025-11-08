# 🚀 Ejecutar en Google Colab

## 📋 Funcionalidad del Proyecto

**Este sistema extrae coordenadas (bounding boxes) de campos específicos en archivos PDF.**

### ¿Qué hace?

**ENTRADA**:
- 📄 Archivo PDF con texto
- 📝 Archivo JSON con campos y valores a buscar en el PDF

**PROCESO**:
- 🔍 Busca cada valor del JSON en el PDF
- 📍 Extrae las coordenadas exactas donde está ese texto

**SALIDA**:
- 📊 JSON con las coordenadas (bounding boxes) de cada campo
- Formato: `{"campo": "valor", "bbox": [x0, y0, x1, y1], "page": 0}`

**PARA QUÉ**:
- Crear datasets de entrenamiento para modelos de LayoutLM, BERT para documentos, etc.
- Automatizar extracción de datos estructurados de PDFs
- Generar anotaciones para object detection en documentos

---

## ⚡ Ejecutar en Google Colab (Recomendado)

### Opción 1: Abrir Notebook Directamente

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GynoRomeroPrado/Consultas-Claude/blob/claude/pdf-json-coordinate-extraction-011CUuykxb37jUXNZgjAevQp/PDF_Coordinate_Extraction_Colab.ipynb)

**Haz clic en el botón arriba** y ejecuta las celdas en orden.

### Opción 2: Cargar Manualmente

1. Ve a https://colab.research.google.com
2. Menú: **Archivo > Abrir notebook**
3. Tab **GitHub**
4. Pega la URL del repositorio: `https://github.com/GynoRomeroPrado/Consultas-Claude`
5. Selecciona el notebook: `PDF_Coordinate_Extraction_Colab.ipynb`

---

## 📊 Tus Datos

Actualmente tienes en el repositorio:

- ✅ **15 facturas** (imágenes PNG)
- ✅ **15 archivos JSON** con los datos extraídos
- ✅ **29 campos por factura**

El notebook automáticamente:
1. Convierte los PNG a PDF
2. Extrae coordenadas de cada campo
3. Genera resultados en múltiples formatos

---

## 🎯 Pasos en el Notebook

El notebook de Colab hace TODO automáticamente:

1. **Clonar repositorio**
2. **Instalar dependencias** (PyMuPDF, RapidFuzz, etc.)
3. **Verificar archivos** disponibles
4. **Convertir PNG a PDF** (si es necesario)
5. **Probar con 1 factura** primero
6. **Procesar todas las 15 facturas**
7. **Mostrar estadísticas** y resultados
8. **Exportar** en diferentes formatos
9. **Descargar resultados**

---

## 📈 Resultados Esperados

Para cada factura obtendrás:

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
      "field_name": "emisor_ruc",
      "text": "20137291313",
      "bbox": {
        "x0": 150.2,
        "y0": 120.5,
        "x1": 250.7,
        "y1": 135.3
      },
      "page": 0,
      "confidence": 1.0,
      "match_type": "exact"
    }
    ... (27 campos más)
  ]
}
```

### Formatos de Exportación:

- ✅ **JSON personalizado** (con todos los detalles)
- ✅ **LayoutLM** (normalizado 0-1000 para entrenamiento)
- ✅ **COCO** (formato estándar de object detection)
- ✅ **CSV** (para análisis en Excel/Sheets)
- ✅ **Pascal VOC** (XML)
- ✅ **YOLO** (para YOLO models)

---

## 🔧 Personalización

### Si quieres procesar TUS propios PDFs:

1. Sube tus PDFs a Google Drive
2. Monta Drive en Colab:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```
3. Copia tus archivos:
   ```python
   !cp /content/drive/MyDrive/mis_pdfs/*.pdf "Datos extraidos de Originales/pdfs/"
   !cp /content/drive/MyDrive/mis_jsons/*.json "Datos extraidos de Originales/anotaciones/"
   ```
4. Ejecuta el notebook

### Ajustar estrategia de matching:

En la celda de pruebas, cambia:

```python
# Más estricto (solo coincidencias exactas)
--strategy exact

# Más permisivo (permite errores de OCR)
--fuzzy --threshold 70

# Automático (recomendado)
--fuzzy --threshold 80
```

---

## 📝 Campos de las Facturas

Tus JSONs contienen estos campos:

```json
{
  "tipo_documento": "FACTURA ELECTRÓNICA",
  "serie_completa": "F003-00015692",
  "fecha_emision": "2025-07-21",
  "fecha_vencimiento": "2025-08-20",
  "moneda": "SOLES",
  "emisor_ruc": "20137291313",
  "emisor_razon_social": "MINERA YANACOCHA S.R.L.",
  "emisor_nombre_comercial": "Yanacocha",
  "emisor_direccion": "...",
  "emisor_telefono": "...",
  "receptor_numero_doc": "20530074901",
  "receptor_tipo_doc": "RUC",
  "receptor_razon_social": "...",
  "receptor_direccion": "...",
  "subtotal": 13350.64,
  "igv": 2403.12,
  "importe_total": 15753.76,
  "descuento": null,
  "otros_cargos": null,
  "numero_contrato": null,
  "orden_compra": null,
  "guia_remision": null,
  "condicion_pago": "Crédito",
  "observaciones": "...",
  "glosa": null,
  "detraccion_porcentaje": null,
  "detraccion_monto": null
}
```

---

## 💡 Consejos

### Para mejor tasa de éxito:

1. **PDFs nativos** (no escaneados) funcionan mejor
2. Si son imágenes escaneadas, usa **fuzzy matching**:
   ```bash
   --fuzzy --threshold 70
   ```
3. Para campos numéricos, el sistema detecta automáticamente formatos: `1,234.56`, `1234.56`, etc.
4. Campos con valores `null` en el JSON se ignoran automáticamente

### Si la tasa de match es baja:

1. **Revisar el PDF**: ¿El texto está bien? ¿Es imagen escaneada?
2. **Probar fuzzy matching** más permisivo:
   ```bash
   --fuzzy --threshold 60
   ```
3. **Ver qué hay en el PDF**:
   ```python
   import fitz
   doc = fitz.open('tu_pdf.pdf')
   print(doc[0].get_text())
   ```

---

## 📞 ¿Necesitas Ayuda?

Después de ejecutar el notebook en Colab:

1. **Copia la salida completa** de las celdas
2. **Comparte**:
   - Match rate obtenido (%)
   - Campos que NO se encontraron
   - Errores (si hay)
3. **Envíame** esa información para optimizar

---

## 🎯 Ventajas de Usar Colab

- ✅ **No instalas nada** en tu máquina
- ✅ **GPU gratis** (si la necesitas)
- ✅ **Ejecuta todo en la nube**
- ✅ **Descarga resultados** fácilmente
- ✅ **Comparte notebooks** con otros

---

## 🚀 ¡Empieza Ahora!

1. Abre el notebook en Colab
2. Ejecuta las celdas en orden (⇧Enter)
3. Espera los resultados
4. Descarga el ZIP con todo

**Tiempo estimado: 3-5 minutos** ⏱️

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GynoRomeroPrado/Consultas-Claude/blob/claude/pdf-json-coordinate-extraction-011CUuykxb37jUXNZgjAevQp/PDF_Coordinate_Extraction_Colab.ipynb)

---

## 📚 Documentación Adicional

- `README.md` - Documentación completa del sistema
- `INSTALACION.md` - Instalación local (si no usas Colab)
- `LEEME_PRIMERO.md` - Guía rápida
- `examples/basic_usage.py` - Ejemplos de código Python
