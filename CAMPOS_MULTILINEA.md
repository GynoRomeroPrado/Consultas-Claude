# 📐 Manejo de Campos Multilínea (Direcciones, etc.)

## 🔍 Tu Pregunta

> "En el caso de las direcciones, las direcciones pueden salir en una fila y debajo otra fila. ¿Consideras la dirección del mismo campo doblemente las coordenadas o se separa las coordenadas?"

---

## ✅ Comportamiento ACTUAL del Sistema

### **Ejemplo: Dirección en 2 líneas**

**En el JSON:**
```json
{
  "direccion": "Av. Los Pinos 123 San Isidro, Lima"
}
```

**En el PDF:**
```
Av. Los Pinos 123
San Isidro, Lima
```

**Lo que hace el sistema actualmente:**

1. ✅ **Detecta ambas líneas** como parte del mismo campo
2. ✅ **Fusiona las coordenadas** en UN SOLO rectángulo grande
3. ✅ **Genera UNA sola bbox** que abarca todo el texto

**Resultado:**
```json
{
  "campo": "direccion",
  "texto": "Av. Los Pinos 123 San Isidro, Lima",
  "bbox": [100.0, 200.0, 300.0, 250.0],  ← UNA sola bbox grande
  "pagina": 0,
  "confianza": 0.95,
  "tipo_matching": "fuzzy"
}
```

**Visualización:**
```
┌─────────────────────────┐
│ Av. Los Pinos 123       │ ← Primera línea
│                         │ ← Espacio vacío (incluido en bbox)
│ San Isidro, Lima        │ ← Segunda línea
└─────────────────────────┘
      ↑
  Una sola bbox que abarca TODO
```

---

## 📊 Comparación: ENFOQUE 1 vs ENFOQUE 2

### **ENFOQUE 1: UNA SOLA BBOX** ⭐ (Lo que hacemos AHORA)

```json
{
  "campo": "direccion",
  "bbox": [100, 200, 300, 250],  ← Rectángulo grande
  "texto": "Av. Los Pinos 123 San Isidro, Lima"
}
```

**Ventajas:**
- ✅ **Simple**: Un campo = una bbox
- ✅ **Semánticamente correcto**: La dirección es una sola entidad
- ✅ **Compatible con LayoutLM**: Es el formato estándar esperado
- ✅ **Fácil de visualizar**: Un rectángulo por campo
- ✅ **Bueno para detección**: Object detection models funcionan mejor

**Desventajas:**
- ❌ **Incluye espacio vacío**: El rectángulo abarca el espacio entre líneas
- ❌ **Menos preciso**: Si hay otro texto entre medio, puede incluirse
- ❌ **Bbox más grande**: Ocupa más área

**Recomendado para:**
- ✅ Entrenamiento de modelos de Document Understanding (LayoutLM, DocFormer, etc.)
- ✅ Detección de campos (object detection)
- ✅ Clasificación de documentos

---

### **ENFOQUE 2: MÚLTIPLES BBOXES** (Alternativa)

```json
{
  "campo": "direccion",
  "texto": "Av. Los Pinos 123 San Isidro, Lima",
  "bbox": [100, 200, 300, 250],          ← Bbox combinada (opcional)
  "bboxes_por_linea": [                  ← Bboxes individuales
    [100, 200, 300, 215],                ← Línea 1
    [100, 230, 250, 245]                 ← Línea 2
  ],
  "lineas": [
    {"texto": "Av. Los Pinos 123", "bbox": [100, 200, 300, 215]},
    {"texto": "San Isidro, Lima", "bbox": [100, 230, 250, 245]}
  ]
}
```

**Ventajas:**
- ✅ **Más preciso**: No incluye espacio vacío
- ✅ **Información detallada**: Sabes exactamente dónde está cada línea
- ✅ **Flexible**: Puedes usar la bbox combinada O las individuales
- ✅ **Mejor para OCR**: Útil si necesitas reconocimiento línea por línea

**Desventajas:**
- ❌ **Más complejo**: Requiere más procesamiento
- ❌ **JSON más grande**: Más datos por campo
- ❌ **No estándar**: LayoutLM espera una sola bbox
- ❌ **Visualización compleja**: Múltiples rectángulos para un solo campo

**Recomendado para:**
- ✅ OCR de alta precisión
- ✅ Análisis de layout detallado
- ✅ Casos donde necesitas separar líneas

---

## 🎯 ¿Cuál es MEJOR para tu caso?

### **Para entrenar modelos de Document Understanding → ENFOQUE 1** ⭐

Si tu objetivo es entrenar **LayoutLM, DocFormer, Donut, etc.**, estos modelos esperan:
- Una bbox por campo
- Coordenadas normalizadas (0-1000)
- Formato estándar

✅ **El sistema actual es PERFECTO para esto**

### **Para análisis detallado de layout → ENFOQUE 2**

Si necesitas:
- Precisión máxima
- Separar texto línea por línea
- Análisis de estructura de documento

❌ **Necesitarías mejoras al sistema**

---

## 🔧 Cómo Funciona Actualmente (Detalles Técnicos)

### **Paso 1: Extracción de Palabras**

PyMuPDF extrae cada palabra con su bbox:
```python
[
  {"texto": "Av.", "bbox": [100, 200, 120, 215], "line_no": 5},
  {"texto": "Los", "bbox": [125, 200, 145, 215], "line_no": 5},
  {"texto": "Pinos", "bbox": [150, 200, 180, 215], "line_no": 5},
  {"texto": "123", "bbox": [185, 200, 210, 215], "line_no": 5},
  {"texto": "San", "bbox": [100, 230, 125, 245], "line_no": 6},  ← Línea diferente
  {"texto": "Isidro,", "bbox": [130, 230, 170, 245], "line_no": 6},
  {"texto": "Lima", "bbox": [175, 230, 210, 245], "line_no": 6}
]
```

### **Paso 2: Fuzzy Matching**

El sistema busca el texto del JSON en el PDF:
```python
search_text = "Av. Los Pinos 123 San Isidro, Lima"

# Crea ventanas deslizantes combinando palabras
segment = {
  "texto": "Av. Los Pinos 123 San Isidro, Lima",
  "palabras": [word1, word2, word3, word4, word5, word6, word7],
  "bboxes": [bbox1, bbox2, bbox3, bbox4, bbox5, bbox6, bbox7]
}

# Calcula similitud
similarity = fuzzy_match("Av. Los Pinos 123 San Isidro, Lima", segment_texto)
# → 95% match
```

### **Paso 3: Fusión de Bboxes**

```python
def merge_bboxes(bboxes):
    x0 = min(bbox[0] for bbox in bboxes)  # Mínimo X
    y0 = min(bbox[1] for bbox in bboxes)  # Mínimo Y
    x1 = max(bbox[2] for bbox in bboxes)  # Máximo X
    y1 = max(bbox[3] for bbox in bboxes)  # Máximo Y
    return (x0, y0, x1, y1)

# Entrada:
bboxes = [
    [100, 200, 210, 215],  # Línea 1: "Av. Los Pinos 123"
    [100, 230, 210, 245]   # Línea 2: "San Isidro, Lima"
]

# Salida:
merged_bbox = [100, 200, 210, 245]  ← Abarca ambas líneas
```

**Resultado visual:**
```
    x0=100                x1=210
y0=200  ┌──────────────────┐
        │ Av. Los Pinos 123│ ← Línea 1
        │                  │ ← Espacio incluido
        │ San Isidro, Lima │ ← Línea 2
y1=245  └──────────────────┘
```

---

## 🧪 Prueba con tus Datos

He creado un script de prueba para que veas exactamente cómo se comporta:

```bash
python analizar_campos_multilinea.py
```

Este script:
1. ✅ Procesa una factura
2. ✅ Detecta campos multilínea automáticamente
3. ✅ Muestra AMBOS enfoques (bbox única vs múltiples)
4. ✅ Genera visualización comparativa

---

## 💡 Recomendación

### **Para tu caso (entrenamiento de modelos):**

✅ **Mantén el ENFOQUE 1 (sistema actual)**

**Razones:**
1. Es el formato estándar de LayoutLM y modelos similares
2. Mantiene la semántica del campo (una dirección = una entidad)
3. Más simple y eficiente
4. Funciona bien para detección y clasificación

### **Cuándo cambiar al ENFOQUE 2:**

Solo si necesitas:
- Análisis de layout muy detallado
- OCR línea por línea
- Separación de componentes de campos

---

## 🚀 ¿Quieres el ENFOQUE 2?

Si después de ver los resultados prefieres tener múltiples bboxes, puedo implementarte:

1. **Modo híbrido**: Generar AMBAS versiones
   - `bbox`: Bbox combinada (para LayoutLM)
   - `bboxes_lineas`: Array de bboxes individuales (para análisis detallado)

2. **Detección inteligente**: Identificar automáticamente campos multilínea

3. **Opción configurable**: Elegir enfoque por tipo de campo

---

## 📝 Ejemplo Completo

### **JSON de entrada:**
```json
{
  "emisor_nombre": "ACME Corporation SAC",
  "emisor_direccion": "Av. Los Pinos 123 San Isidro, Lima",
  "emisor_ruc": "20137291313"
}
```

### **PDF:**
```
ACME Corporation SAC          ← Línea 1 (nombre)
Av. Los Pinos 123             ← Línea 2 (dirección parte 1)
San Isidro, Lima              ← Línea 3 (dirección parte 2)
RUC: 20137291313              ← Línea 4 (RUC)
```

### **Salida ACTUAL (Enfoque 1):**
```json
{
  "coordenadas": [
    {
      "campo": "emisor_nombre",
      "texto": "ACME Corporation SAC",
      "bbox": [50, 100, 250, 115],      ← Una línea
      "confianza": 1.0
    },
    {
      "campo": "emisor_direccion",
      "texto": "Av. Los Pinos 123 San Isidro, Lima",
      "bbox": [50, 120, 250, 150],      ← DOS líneas fusionadas
      "confianza": 0.95
    },
    {
      "campo": "emisor_ruc",
      "texto": "20137291313",
      "bbox": [85, 155, 180, 170],      ← Una línea
      "confianza": 1.0
    }
  ]
}
```

---

## ✅ Conclusión

**Tu sistema ACTUALMENTE:**
- ✅ **SÍ detecta campos multilínea**
- ✅ **SÍ los maneja correctamente**
- ✅ **Genera UNA bbox combinada** (óptimo para Document Understanding)

**NO necesitas cambios** a menos que quieras análisis más detallado.

**Para verificar con tus datos:**
```bash
# Procesa una factura de prueba
python generar_dataset_prueba.py

# Visualiza las coordenadas
python visualizar_coordenadas.py \
    "Datos extraidos de Originales/pdfs/factura.pdf" \
    "dataset_con_coordenadas/factura_coordenadas.json" \
    -o verificacion_multilinea.png \
    --con-leyenda

# Analiza campos multilínea específicamente
python analizar_campos_multilinea.py
```

¿Quieres que implemente el **Enfoque 2** (múltiples bboxes) o el actual te funciona bien?
