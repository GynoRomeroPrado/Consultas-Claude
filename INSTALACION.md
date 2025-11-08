# 📦 Instrucciones de Instalación

## ⚠️ IMPORTANTE: Instalar Dependencias

El sistema requiere varias bibliotecas de Python que NO están instaladas actualmente.

---

## 🔧 Instalación Paso a Paso

### **Paso 1: Instalar Python (si no lo tienes)**

```bash
# Verificar versión de Python
python --version  # Debe ser Python 3.8 o superior
```

### **Paso 2: Crear entorno virtual (Recomendado)**

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Linux/Mac:
source venv/bin/activate

# En Windows:
venv\Scripts\activate
```

### **Paso 3: Instalar dependencias**

```bash
# Instalar todas las dependencias
pip install -r requirements.txt
```

O instalar manualmente:

```bash
pip install PyMuPDF>=1.23.0
pip install rapidfuzz>=3.5.0
pip install Pillow>=10.0.0
pip install numpy>=1.24.0
pip install pandas>=2.0.0
pip install tqdm>=4.65.0
```

### **Paso 4: Verificar instalación**

```bash
python -c "import fitz; print('PyMuPDF:', fitz.version)"
python -c "import rapidfuzz; print('RapidFuzz:', rapidfuzz.__version__)"
python -c "from PIL import Image; print('Pillow: OK')"
```

Deberías ver:
```
PyMuPDF: [version]
RapidFuzz: [version]
Pillow: OK
```

---

## 🚀 Ejecutar el Sistema

Una vez instaladas las dependencias:

### **1. Convertir PNG a PDF**

```bash
python convertir_png_a_pdf_simple.py
```

Esto convertirá todas las imágenes PNG de facturas a PDF.

### **2. Ejecutar pruebas**

```bash
python test_facturas.py
```

Este script probará diferentes estrategias de matching y te mostrará los resultados.

---

## 📊 Tu Caso Específico: Facturas Electrónicas

He analizado tus archivos y veo que tienes:

- ✅ **15 imágenes PNG** de facturas electrónicas
- ✅ **15 archivos JSON** con los datos extraídos

### Estructura de tus datos:

```
Datos extraidos de Originales/
├── facturas_procesadas/     # 15 archivos PNG
│   ├── IMG-20251026-WA0038.png
│   ├── IMG-20251026-WA0039.png
│   └── ...
└── anotaciones/              # 15 archivos JSON
    ├── IMG-20251026-WA0038.json
    ├── IMG-20251026-WA0039.json
    └── ...
```

### Campos en tus JSONs:

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
  ...
}
```

**Total: 29 campos por factura**

---

## 🔍 Qué Va a Hacer el Sistema

El sistema va a:

1. ✅ Convertir cada PNG a PDF
2. ✅ Leer cada campo del JSON
3. ✅ Buscar ese texto en el PDF
4. ✅ Extraer las coordenadas (bounding box) donde está ese texto
5. ✅ Exportar resultados en múltiples formatos

### Resultado esperado:

Para cada factura obtendrás:

```json
{
  "tipo_documento": {
    "text": "FACTURA ELECTRÓNICA",
    "bbox": [100.5, 50.3, 300.8, 70.1],
    "page": 0,
    "confidence": 1.0
  },
  "emisor_ruc": {
    "text": "20137291313",
    "bbox": [150.2, 120.5, 250.7, 135.3],
    "page": 0,
    "confidence": 1.0
  },
  ...
}
```

---

## 🐛 Problemas Comunes

### Error: "No module named 'fitz'"

**Solución**:
```bash
pip install PyMuPDF
```

### Error: "No module named 'rapidfuzz'"

**Solución**:
```bash
pip install rapidfuzz
```

### Error: "No se encontraron pares PDF-JSON"

**Causa**: Las PNGs no se han convertido a PDF todavía.

**Solución**:
```bash
python convertir_png_a_pdf_simple.py
```

### Match rate muy bajo (< 50%)

**Causas posibles**:
1. Las imágenes tienen mala calidad de OCR
2. El texto en la imagen es diferente al del JSON
3. Los valores numéricos tienen formato diferente

**Solución**: Ejecuta con fuzzy matching:
```bash
python test_facturas.py --fuzzy --threshold 70
```

---

## 📝 Siguiente Paso

**Una vez instaladas las dependencias, ejecuta:**

```bash
# 1. Convertir PNGs a PDF
python convertir_png_a_pdf_simple.py

# 2. Ejecutar pruebas
python test_facturas.py

# 3. Ver resultados
ls output/facturas/
```

---

## 💡 Notas Importantes

1. **Las imágenes PNG deben tener texto legible**, no pueden ser fotos borrosas
2. **Los valores en el JSON deben aparecer tal cual en la imagen**
3. **El sistema soporta fuzzy matching** para pequeñas diferencias
4. **Se pueden exportar resultados en 6 formatos diferentes**:
   - JSON personalizado
   - CSV
   - LayoutLM (para entrenamiento de modelos)
   - COCO (para object detection)
   - Pascal VOC (XML)
   - YOLO

---

## 📞 ¿Necesitas Ayuda?

Si tienes problemas:

1. Comparte el error completo
2. Indica qué comando ejecutaste
3. Envía un ejemplo de tu JSON (si es diferente al que vi)

¡Estoy listo para ajustar el sistema a tus necesidades específicas!
