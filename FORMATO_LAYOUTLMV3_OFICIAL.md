# Formato LayoutLMv3 OFICIAL (FUNSD-Style)

## 📋 Descripción

Este documento describe el formato oficial de LayoutLMv3 implementado en `generar_layoutlmv3_oficial.py`, basado en el dataset FUNSD (Form Understanding in Noisy Scanned Documents).

---

## 🎯 Diferencias Clave vs Formato Anterior

| Aspecto | Formato Anterior | Formato OFICIAL |
|---------|------------------|-----------------|
| **Tokenización** | Todo el texto en un solo box | ✅ Palabras individuales con boxes |
| **Labels** | Nombres de campos personalizados | ✅ Solo: question/answer/header/other |
| **Linking** | Siempre vacío | ✅ Detecta y vincula etiquetas con valores |
| **Estructura** | Todo en un archivo | ✅ Dataset + Metadata separados |
| **Compatibilidad** | Formato custom | ✅ Compatible con FUNSD/LayoutLMv3 oficial |

---

## 📝 Formato de Salida

### Archivo Principal: `{nombre}_layoutlm_v3.json`

Contiene **solo** el array "form":

```json
{
  "form": [
    {
      "id": 0,
      "text": "RUC:",
      "box": [10, 20, 50, 35],
      "label": "question",
      "field_name": "RUC",
      "words": [
        {"text": "RUC:", "box": [10, 20, 50, 35]}
      ],
      "linking": [[0, 1]],
      "page": 0
    },
    {
      "id": 1,
      "text": "20 123 456 789",
      "box": [60, 20, 180, 35],
      "label": "answer",
      "field_name": "RUC",
      "words": [
        {"text": "20", "box": [60, 20, 80, 35]},
        {"text": "123", "box": [85, 20, 110, 35]},
        {"text": "456", "box": [115, 20, 140, 35]},
        {"text": "789", "box": [145, 20, 180, 35]}
      ],
      "linking": [[0, 1]],
      "page": 0
    }
  ]
}
```

### Archivo de Metadata: `{nombre}_metadata.json`

```json
{
  "documento": "factura_001.pdf",
  "num_paginas": 1,
  "fecha_generacion": "2024-01-15T10:30:00",
  "formato": "layoutlmv3_oficial_funsd_v1.0",
  "estadisticas": {
    "total_campos_json": 25,
    "campos_encontrados": 22,
    "campos_faltantes": 3,
    "match_rate": 88.0,
    "confianza_promedio": 0.945,
    "total_items_form": 44,
    "etiquetas_detectadas": 18,
    "palabras_tokenizadas": 156
  },
  "campos_faltantes": ["campo1", "campo2", "campo3"]
}
```

---

## 🔧 Funciones Implementadas

### 1. `tokenizar_texto_con_boxes(texto, bbox)`

**Propósito**: Divide texto en palabras individuales y estima bbox de cada palabra.

**¿Por qué es importante?**
- LayoutLMv3 necesita palabras individuales, NO texto agrupado
- Permite al modelo aprender la estructura espacial de cada palabra
- Mejora la precisión en campos con múltiples palabras

**Entrada**:
```python
texto = "EMPRESA SAC"
bbox = [100, 200, 300, 220]
```

**Salida**:
```python
[
  {"text": "EMPRESA", "box": [100, 200, 195, 220]},
  {"text": "SAC", "box": [205, 200, 300, 220]}
]
```

**Algoritmo**:
1. Divide el texto por espacios
2. Calcula la longitud total de caracteres
3. Asigna ancho proporcional a cada palabra
4. Considera espacios entre palabras (~2% del ancho total)

**Limitación**:
- Es una **estimación** porque no conocemos el ancho real de cada palabra
- Funciona bien para texto extraído de PDFs con coordenadas exactas
- Para mejor precisión, usa OCR que da coordenadas por palabra

---

### 2. `detectar_etiqueta_cercana(palabras_extraidas, campo_nombre, valor_bbox, umbral_distancia)`

**Propósito**: Busca etiquetas en el PDF que correspondan al campo.

**Ejemplos de etiquetas**:
- Para campo "emisor_ruc": busca "RUC:", "R.U.C.", "RUC", "Registro"
- Para campo "total": busca "Total:", "TOTAL", "Importe", "Monto"
- Para campo "fecha_emision": busca "Fecha:", "Date:", "Emisión"

**Entrada**:
```python
campo_nombre = "emisor_ruc"
valor_bbox = [100, 200, 200, 220]  # Bbox del valor "20123456789"
palabras_extraidas = [
  {"text": "RUC:", "bbox": [10, 200, 50, 220]},  # ← Etiqueta cercana
  {"text": "20123456789", "bbox": [100, 200, 200, 220]},
  ...
]
```

**Salida**:
```python
{
  "text": "RUC:",
  "bbox": [10, 200, 50, 220],
  "distancia": 50  # píxeles desde etiqueta al valor
}
```

**Algoritmo**:
1. Genera patrones regex basados en el nombre del campo
2. Busca palabras que coincidan con los patrones
3. Calcula distancia euclidiana entre bbox de etiqueta y valor
4. Retorna la etiqueta más cercana (si está dentro del umbral)

**Umbral por defecto**: 150 píxeles (en escala 0-1000)

---

### 3. `generar_patrones_etiqueta(campo_nombre)`

**Propósito**: Genera patrones regex para buscar etiquetas basadas en el nombre del campo.

**Mapeo de campos comunes**:
```python
{
  'ruc': ['ruc', r'r\.?u\.?c\.?', 'registro', 'tax', 'id'],
  'total': ['total', 'importe', 'monto', 'amount'],
  'fecha': ['fecha', 'date', 'emision'],
  'nombre': ['nombre', 'razon', 'social', 'name', 'company'],
  'direccion': ['direccion', 'domicilio', 'address'],
  ...
}
```

**Ejemplos**:

| Campo | Patrones Generados |
|-------|-------------------|
| `emisor_ruc` | `ruc`, `r\.?u\.?c\.?`, `registro`, `ruc:`, `ruc.` |
| `total` | `total`, `importe`, `monto`, `total:`, `total.` |
| `fecha_emision` | `fecha`, `date`, `emision`, `fecha:`, `date:` |

**Sufijos automáticos**: Agrega `:` y `.` a cada patrón

---

### 4. `calcular_distancia_boxes(bbox1, bbox2)`

**Propósito**: Calcula distancia euclidiana entre centros de dos bounding boxes.

**Fórmula**:
```python
centro1 = ((x0 + x1) / 2, (y0 + y1) / 2)
centro2 = ((x0 + x1) / 2, (y0 + y1) / 2)
distancia = sqrt((cx2 - cx1)² + (cy2 - cy1)²)
```

**Ejemplo**:
```python
bbox1 = [10, 200, 50, 220]   # Etiqueta "RUC:"
bbox2 = [100, 200, 200, 220]  # Valor "20123456789"

# Centro1: (30, 210)
# Centro2: (150, 210)
# Distancia: sqrt((150-30)² + (210-210)²) = 120
```

---

### 5. `generar_linking(etiqueta_id, valor_id)`

**Propósito**: Genera array de linking en formato LayoutLMv3.

**Reglas**:
- Si hay etiqueta: `[[etiqueta_id, valor_id]]`
- Si NO hay etiqueta: `[]`

**Ejemplos**:
```python
generar_linking(0, 1)      # → [[0, 1]]
generar_linking(None, 1)   # → []
generar_linking(5, 6)      # → [[5, 6]]
```

**Linking bidireccional**: Tanto la etiqueta como el valor tienen el mismo linking para indicar la relación.

---

## 🎨 Labels Estándar

Según la documentación oficial de FUNSD/LayoutLMv3:

| Label | Uso | Ejemplo |
|-------|-----|---------|
| `question` | Etiquetas/preguntas | "RUC:", "Total:", "Fecha:" |
| `answer` | Valores/respuestas | "20123456789", "1500.00", "2024-01-15" |
| `header` | Encabezados/títulos | "FACTURA ELECTRÓNICA", "COMPROBANTE" |
| `other` | Otro texto | Texto decorativo, instrucciones |

**En este script**:
- `question`: Etiquetas detectadas automáticamente
- `answer`: Valores de campos del JSON
- `header`: No se usa (podría agregarse manualmente)
- `other`: No se usa (podría agregarse manualmente)

**Campo adicional**: `field_name` se agrega para mantener referencia al nombre del campo original.

---

## 📊 Sistema de Linking

### ¿Qué es linking?

El linking establece relaciones entre elementos del formulario, típicamente entre etiquetas (questions) y valores (answers).

### Formato

```json
"linking": [[id_origen, id_destino]]
```

### Ejemplos

#### Caso 1: Etiqueta y Valor Vinculados

```json
{
  "form": [
    {
      "id": 0,
      "text": "RUC:",
      "label": "question",
      "linking": [[0, 1]]  // ← Link al valor
    },
    {
      "id": 1,
      "text": "20123456789",
      "label": "answer",
      "linking": [[0, 1]]  // ← Mismo link (bidireccional)
    }
  ]
}
```

#### Caso 2: Valor Sin Etiqueta

```json
{
  "form": [
    {
      "id": 0,
      "text": "1500.00",
      "label": "answer",
      "field_name": "total",
      "linking": []  // ← Sin link (no se detectó etiqueta)
    }
  ]
}
```

#### Caso 3: Múltiples Campos Vinculados

```json
{
  "form": [
    {
      "id": 0,
      "text": "Cliente:",
      "label": "question",
      "linking": [[0, 1]]
    },
    {
      "id": 1,
      "text": "EMPRESA XYZ SAC",
      "label": "answer",
      "linking": [[0, 1]]
    },
    {
      "id": 2,
      "text": "RUC:",
      "label": "question",
      "linking": [[2, 3]]
    },
    {
      "id": 3,
      "text": "20123456789",
      "label": "answer",
      "linking": [[2, 3]]
    }
  ]
}
```

---

## 🚀 Uso del Script

### Modo Prueba (Un Solo PDF)

```bash
# Procesar primer PDF del directorio
python generar_layoutlmv3_oficial.py --modo prueba

# Procesar PDF específico
python generar_layoutlmv3_oficial.py \
  --modo prueba \
  --pdf "mi_factura.pdf" \
  --json "mi_factura.json"

# Con opciones adicionales
python generar_layoutlmv3_oficial.py \
  --modo prueba \
  --pdf "factura.pdf" \
  --json "factura.json" \
  --confianza-minima 0.8 \
  --gpu
```

### Modo Completo (Todos los PDFs)

```bash
# Procesamiento básico
python generar_layoutlmv3_oficial.py --modo completo

# Con OCR y GPU
python generar_layoutlmv3_oficial.py \
  --modo completo \
  --input-dir "Datos extraidos de Originales" \
  --output-dir "dataset_layoutlmv3_oficial" \
  --gpu

# Sin detección de etiquetas (solo valores)
python generar_layoutlmv3_oficial.py \
  --modo completo \
  --sin-etiquetas

# Sin OCR (solo PDFs nativos)
python generar_layoutlmv3_oficial.py \
  --modo completo \
  --sin-ocr
```

### Parámetros Disponibles

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--modo` | prueba o completo | completo |
| `--input-dir` | Directorio con PDFs y JSONs | Datos extraidos de Originales |
| `--output-dir` | Directorio de salida | dataset_layoutlmv3_oficial |
| `--confianza-minima` | Umbral mínimo (0-1) | 0.75 |
| `--sin-ocr` | Deshabilitar OCR | False |
| `--gpu` | Usar GPU para OCR | False |
| `--sin-etiquetas` | No detectar etiquetas | False |
| `--pdf` | PDF específico (modo prueba) | - |
| `--json` | JSON específico (modo prueba) | - |

---

## 📁 Estructura de Salida

```
dataset_layoutlmv3_oficial/
├── factura_001_layoutlm_v3.json    # Dataset (solo "form")
├── factura_001_metadata.json       # Metadata y estadísticas
├── factura_002_layoutlm_v3.json
├── factura_002_metadata.json
├── ...
└── dataset_resumen.json            # Resumen global
```

---

## 🔍 Ejemplo Completo

### Input: JSON de Anotaciones

```json
{
  "emisor_ruc": "20137291313",
  "emisor_nombre": "EMPRESA SAC",
  "total": "1500.00",
  "fecha_emision": "2024-01-15"
}
```

### Output: `factura_001_layoutlm_v3.json`

```json
{
  "form": [
    {
      "id": 0,
      "text": "RUC:",
      "box": [50, 100, 90, 118],
      "label": "question",
      "field_name": "emisor_ruc",
      "words": [
        {"text": "RUC:", "box": [50, 100, 90, 118]}
      ],
      "linking": [[0, 1]],
      "page": 0
    },
    {
      "id": 1,
      "text": "20137291313",
      "box": [100, 100, 220, 118],
      "label": "answer",
      "field_name": "emisor_ruc",
      "words": [
        {"text": "20137291313", "box": [100, 100, 220, 118]}
      ],
      "linking": [[0, 1]],
      "page": 0
    },
    {
      "id": 2,
      "text": "Razón Social:",
      "box": [50, 130, 150, 148],
      "label": "question",
      "field_name": "emisor_nombre",
      "words": [
        {"text": "Razón", "box": [50, 130, 95, 148]},
        {"text": "Social:", "box": [100, 130, 150, 148]}
      ],
      "linking": [[2, 3]],
      "page": 0
    },
    {
      "id": 3,
      "text": "EMPRESA SAC",
      "box": [160, 130, 280, 148],
      "label": "answer",
      "field_name": "emisor_nombre",
      "words": [
        {"text": "EMPRESA", "box": [160, 130, 220, 148]},
        {"text": "SAC", "box": [225, 130, 280, 148]}
      ],
      "linking": [[2, 3]],
      "page": 0
    },
    {
      "id": 4,
      "text": "Total:",
      "box": [450, 550, 500, 568],
      "label": "question",
      "field_name": "total",
      "words": [
        {"text": "Total:", "box": [450, 550, 500, 568]}
      ],
      "linking": [[4, 5]],
      "page": 0
    },
    {
      "id": 5,
      "text": "1500.00",
      "box": [510, 550, 580, 568],
      "label": "answer",
      "field_name": "total",
      "words": [
        {"text": "1500.00", "box": [510, 550, 580, 568]}
      ],
      "linking": [[4, 5]],
      "page": 0
    },
    {
      "id": 6,
      "text": "2024-01-15",
      "box": [300, 100, 400, 118],
      "label": "answer",
      "field_name": "fecha_emision",
      "words": [
        {"text": "2024-01-15", "box": [300, 100, 400, 118]}
      ],
      "linking": [],
      "page": 0
    }
  ]
}
```

**Observaciones**:
- Items 0-1: Etiqueta "RUC:" vinculada a valor "20137291313"
- Items 2-3: Etiqueta "Razón Social:" vinculada a "EMPRESA SAC" (tokenizada en 2 palabras)
- Items 4-5: Etiqueta "Total:" vinculada a "1500.00"
- Item 6: Fecha sin etiqueta detectada (linking vacío)

### Output: `factura_001_metadata.json`

```json
{
  "documento": "factura_001.pdf",
  "num_paginas": 1,
  "fecha_generacion": "2024-01-15T10:30:00",
  "formato": "layoutlmv3_oficial_funsd_v1.0",
  "estadisticas": {
    "total_campos_json": 4,
    "campos_encontrados": 4,
    "campos_faltantes": 0,
    "match_rate": 100.0,
    "confianza_promedio": 0.956,
    "total_items_form": 7,
    "etiquetas_detectadas": 3,
    "palabras_tokenizadas": 8
  },
  "campos_faltantes": []
}
```

---

## 🎯 Ventajas del Formato Oficial

### 1. Compatibilidad Estándar
- ✅ Compatible con herramientas de anotación FUNSD
- ✅ Compatible con pipelines de LayoutLMv3
- ✅ Compatible con evaluaciones estándar

### 2. Mejor Aprendizaje del Modelo
- ✅ Tokenización por palabras permite aprender relaciones espaciales
- ✅ Labels estándar facilitan transferencia de conocimiento
- ✅ Linking explícito mejora comprensión de estructura

### 3. Más Información Semántica
- ✅ Distingue entre preguntas (etiquetas) y respuestas (valores)
- ✅ Captura relaciones entre elementos del formulario
- ✅ Permite análisis de estructura del documento

### 4. Facilita Anotación Manual
- ✅ Formato claro y estándar
- ✅ Fácil de revisar y corregir
- ✅ Compatible con herramientas existentes

---

## ⚠️ Limitaciones y Consideraciones

### 1. Estimación de Boxes de Palabras

**Problema**: `tokenizar_texto_con_boxes()` ESTIMA la posición de cada palabra.

**Por qué**:
- No tenemos coordenadas exactas de cada palabra
- Solo tenemos el bbox del texto completo

**Impacto**:
- Los boxes de palabras individuales son aproximados
- Funcionan bien para entrenamiento pero no son 100% exactos

**Solución mejor**:
- Usar OCR que retorne coordenadas por palabra
- O extraer del PDF usando PyMuPDF word-level extraction

### 2. Detección de Etiquetas

**Problema**: La detección de etiquetas es heurística.

**Limitaciones**:
- Puede no detectar todas las etiquetas
- Puede detectar falsos positivos
- Depende del umbral de distancia

**Mejora**:
- Ajustar `umbral_distancia` (default: 150)
- Agregar más patrones en `generar_patrones_etiqueta()`
- Revisar manualmente y corregir

### 3. Labels Limitados

**Problema**: Solo usamos "question" y "answer".

**No usamos**:
- `header`: Para títulos/encabezados
- `other`: Para texto decorativo

**Mejora futura**: Detectar automáticamente headers basándose en:
- Tamaño de fuente
- Posición en la página
- Palabras clave ("FACTURA", "COMPROBANTE", etc.)

---

## 📈 Comparación de Rendimiento

### Formato Anterior vs Oficial

| Métrica | Formato Anterior | Formato Oficial |
|---------|------------------|-----------------|
| Items generados | ~22 por documento | ~44 por documento |
| Palabras tokenizadas | ~22 (1 por campo) | ~150+ (todas separadas) |
| Etiquetas detectadas | 0 | ~18 promedio |
| Links creados | 0 | ~18 promedio |
| Compatibilidad FUNSD | ❌ No | ✅ Sí |

---

## 🚀 Próximos Pasos

### 1. Entrenar Modelo

```python
from transformers import LayoutLMv3ForTokenClassification

# Cargar dataset oficial
train_data = load_funsd_style_dataset("dataset_layoutlmv3_oficial")

# Entrenar
model = LayoutLMv3ForTokenClassification.from_pretrained(
    "microsoft/layoutlmv3-base",
    num_labels=4  # question, answer, header, other
)

trainer.train(train_data)
```

### 2. Evaluar con Métricas Estándar

```python
from seqeval.metrics import classification_report

predictions = model.predict(test_data)
print(classification_report(labels, predictions))
```

### 3. Visualizar Resultados

```python
# Dibujar boxes y links en imagen del PDF
visualize_form(
    image_path="factura_001.jpg",
    form_data=dataset["form"]
)
```

---

## 📚 Referencias

- **FUNSD Dataset**: https://guillaumejaume.github.io/FUNSD/
- **LayoutLMv3 Paper**: https://arxiv.org/abs/2204.08387
- **Hugging Face LayoutLMv3**: https://huggingface.co/microsoft/layoutlmv3-base
- **Seqeval (Evaluación)**: https://github.com/chakki-works/seqeval

---

## ✅ Checklist de Implementación

- [x] Tokenización por palabras individuales
- [x] Labels estándar (question/answer)
- [x] Detección automática de etiquetas
- [x] Sistema de linking bidireccional
- [x] Separación dataset/metadata
- [x] Formato compatible con FUNSD
- [x] Coordenadas normalizadas 0-1000
- [x] Soporte multi-página
- [ ] Detección de headers (futuro)
- [ ] Extracción word-level exacta (futuro)
- [ ] Visualización de links (futuro)

---

**Autor**: Sistema de Extracción de Coordenadas
**Versión**: 1.0
**Fecha**: 2024
