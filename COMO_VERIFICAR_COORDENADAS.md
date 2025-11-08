# ✅ Cómo Verificar que las Coordenadas son Correctas

## 🎯 Importancia de la Verificación

Es **CRÍTICO** verificar visualmente que las coordenadas extraídas son correctas antes de usar el dataset para entrenar modelos.

---

## 📊 3 Métodos de Verificación

### **Método 1: Visualización Simple** ⭐ Recomendado

Genera una imagen del PDF con rectángulos dibujados sobre cada campo encontrado.

```bash
# Uso básico
python visualizar_coordenadas.py \
    "Datos extraidos de Originales/pdfs/factura_001.pdf" \
    "dataset_con_coordenadas/factura_001_coordenadas.json" \
    -o verificacion.png

# Con leyenda de colores
python visualizar_coordenadas.py \
    "Datos extraidos de Originales/pdfs/factura_001.pdf" \
    "dataset_con_coordenadas/factura_001_coordenadas.json" \
    -o verificacion_con_leyenda.png \
    --con-leyenda

# Sin etiquetas (más limpio)
python visualizar_coordenadas.py \
    "Datos extraidos de Originales/pdfs/factura_001.pdf" \
    "dataset_con_coordenadas/factura_001_coordenadas.json" \
    -o verificacion_limpia.png \
    --sin-etiquetas
```

**Resultado**: Genera una imagen PNG con:
- Rectángulos de colores sobre cada campo
- Etiquetas con nombre del campo y confianza
- Colores únicos para cada campo

**Cómo usar**:
1. Ejecuta el script
2. Abre `verificacion.png`
3. Verifica visualmente que cada rectángulo rodea correctamente el texto

---

### **Método 2: Verificación Interactiva en Colab** 🔍 Más Detallado

Muestra cada campo individualmente con zoom para verificación precisa.

```python
# En Google Colab
!python verificar_coordenadas_colab.py \
    "Datos extraidos de Originales/pdfs/factura_001.pdf" \
    "dataset_con_coordenadas/factura_001_coordenadas.json" \
    --modo todo
```

**Muestra:**
1. ✅ Vista individual de cada campo (con zoom)
2. ✅ Overview completo con todos los campos
3. ✅ Análisis estadístico de calidad
4. ✅ Gráfico de distribución de confianzas

**Salida esperada:**

```
================================================================================
VERIFICACIÓN INTERACTIVA DE COORDENADAS
================================================================================

📊 Documento: factura_001.pdf
📊 Total campos: 25
📊 Match rate: 86.2%
📊 Confianza promedio: 0.9534

Mostrando primeros 10 campos:

================================================================================
[1/10] Campo: emisor_ruc
================================================================================
  Texto encontrado: '20137291313'
  Coordenadas: (150.2, 120.5, 250.7, 135.3)
  Confianza: 1.00
  Tipo matching: exact

  ✅ ¿Es correcto? (Visualmente verifica que el rectángulo rojo rodee el texto)

[Muestra imagen con zoom del campo]

[2/10] Campo: importe_total
...
```

**Modos disponibles:**

```bash
# Solo vista interactiva (campo por campo)
--modo interactivo

# Solo overview (todos los campos juntos)
--modo overview

# Solo análisis de calidad
--modo calidad

# Todo (recomendado)
--modo todo
```

---

### **Método 3: Verificación Manual con Estadísticas**

Revisa las estadísticas del JSON sin visualización.

```python
import json

# Leer archivo
with open('dataset_con_coordenadas/factura_001_coordenadas.json') as f:
    data = json.load(f)

print(f"Match rate: {data['match_rate']:.1f}%")
print(f"Confianza promedio: {data['confianza_promedio']:.4f}")
print(f"Campos encontrados: {data['campos_encontrados']}/{data['total_campos']}")

# Ver campos con baja confianza
for coord in data['coordenadas']:
    if coord['confianza'] < 0.8:
        print(f"⚠️  {coord['campo']}: {coord['texto']} (conf: {coord['confianza']:.2f})")
```

---

## 🎨 Interpretación de Resultados

### **Colores en la Visualización:**

- 🟢 **Verde**: Confianza ≥ 0.95 (Excelente)
- 🟡 **Amarillo**: Confianza 0.80-0.95 (Bueno - fuzzy match)
- 🔴 **Rojo**: Confianza < 0.80 (Revisar)

### **Match Rate:**

- ✅ **> 90%**: Excelente - PDFs de alta calidad
- ✅ **80-90%**: Bueno - Algunos campos con variaciones
- ⚠️  **70-80%**: Aceptable - Considerar ajustar threshold
- ❌ **< 70%**: Revisar - Posibles problemas de OCR o formato

### **Tipos de Matching:**

- **exact**: Coincidencia exacta (confianza = 1.0)
- **fuzzy**: Coincidencia aproximada (confianza < 1.0)
- **multiline**: Texto en múltiples líneas

---

## 📋 Checklist de Verificación

### ✅ Para CADA visualización verifica:

1. **Rectángulos bien posicionados**:
   - [ ] El rectángulo rodea completamente el texto
   - [ ] No hay espacios vacíos significativos
   - [ ] No corta palabras

2. **Texto correcto**:
   - [ ] El texto en la etiqueta coincide con el del PDF
   - [ ] No hay errores de OCR evidentes

3. **Campos numéricos**:
   - [ ] Los números están completos
   - [ ] Formato correcto (decimales, separadores)

4. **Campos de fecha**:
   - [ ] Formato de fecha correcto
   - [ ] Fecha completa capturada

5. **Campos largos** (direcciones, descripciones):
   - [ ] Todo el texto está incluido
   - [ ] No se corta en medio

---

## 🔧 Qué Hacer si Hay Errores

### **Error Tipo 1: Campo no encontrado**

**Síntoma**: Campo falta en `coordenadas`

**Soluciones**:

```bash
# 1. Probar con fuzzy matching más permisivo
python generar_dataset_prueba.py --threshold 70

# 2. Verificar que el texto existe en el PDF
python -c "
import fitz
doc = fitz.open('ruta_al_pdf.pdf')
print(doc[0].get_text())
" | grep "texto_buscado"

# 3. Revisar el JSON original
cat "Datos extraidos de Originales/anotaciones/factura_001.json" | grep "campo_problema"
```

### **Error Tipo 2: Bounding box incorrecto**

**Síntoma**: El rectángulo no rodea bien el texto

**Causas posibles**:
- Texto en múltiples líneas no manejado correctamente
- PDF con layout complejo
- Coordenadas de PyMuPDF imprecisas

**Soluciones**:

```bash
# 1. Usar estrategia multiline
python generar_dataset_prueba.py --strategy fuzzy --threshold 75

# 2. Verificar dimensiones de página
python -c "
import fitz, json
doc = fitz.open('ruta_al_pdf.pdf')
page = doc[0]
print(f'Dimensiones: {page.rect.width} x {page.rect.height}')

with open('dataset_con_coordenadas/factura_001_coordenadas.json') as f:
    data = json.load(f)
    coord = data['coordenadas'][0]
    print(f'Dimensiones en JSON: {coord[\"dimensiones_pagina\"]}')"
```

### **Error Tipo 3: Confianza baja (<0.8)**

**Síntoma**: Muchos campos con confianza < 0.8

**Soluciones**:

```bash
# 1. Bajar threshold
python generar_dataset_prueba.py --threshold 65

# 2. Revisar si el texto en el PDF es diferente al JSON
# (pueden haber variaciones de formato, OCR errors, etc.)
```

### **Error Tipo 4: Texto duplicado capturado**

**Síntoma**: Mismo texto capturado varias veces

**Causa**: El texto aparece múltiples veces en el PDF

**Solución**: El sistema ya maneja esto eligiendo la primera ocurrencia. Si quieres otra, ajusta `prefer_first_match`:

```python
# En el script, cambiar:
config = PipelineConfig(
    matcher=MatcherConfig(
        prefer_first_match=False  # Elegir por confianza en vez de posición
    )
)
```

---

## 📊 Ejemplo de Verificación Completa

### **Paso 1: Generar dataset de prueba**

```bash
python generar_dataset_prueba.py
```

### **Paso 2: Visualizar**

```bash
python visualizar_coordenadas.py \
    "Datos extraidos de Originales/pdfs/IMG-20251026-WA0038.pdf" \
    "dataset_con_coordenadas/IMG-20251026-WA0038_coordenadas.json" \
    -o verificacion_factura_001.png \
    --con-leyenda
```

### **Paso 3: Analizar estadísticas**

```python
import json

with open('dataset_con_coordenadas/IMG-20251026-WA0038_coordenadas.json') as f:
    data = json.load(f)

print(f"""
📊 RESUMEN:
  Match rate: {data['match_rate']:.1f}%
  Confianza: {data['confianza_promedio']:.4f}
  Encontrados: {data['campos_encontrados']}/{data['total_campos']}
""")

# Campos con problemas
problemas = [c for c in data['coordenadas'] if c['confianza'] < 0.9]
if problemas:
    print(f"\n⚠️  {len(problemas)} campos con confianza < 0.9:")
    for c in problemas:
        print(f"  - {c['campo']}: {c['confianza']:.2f}")
```

### **Paso 4: Verificación visual**

1. Abre `verificacion_factura_001.png`
2. Verifica que los rectángulos estén bien posicionados
3. Revisa la leyenda de colores

### **Paso 5: Decisión**

- ✅ **Si Match rate > 85% y visualización correcta**: Proceder con dataset completo
  ```bash
  python generar_dataset_completo.py
  ```

- ⚠️  **Si Match rate 70-85%**: Ajustar threshold y repetir
  ```bash
  python generar_dataset_prueba.py --threshold 70
  ```

- ❌ **Si Match rate < 70%**: Revisar PDFs y JSONs originales

---

## 🚀 Verificación en Google Colab

```python
# Notebook cell 1: Instalar dependencias
!pip install -q PyMuPDF Pillow matplotlib

# Cell 2: Clonar repo y preparar
!git clone https://github.com/GynoRomeroPrado/Consultas-Claude.git
%cd Consultas-Claude
!git checkout claude/pdf-json-coordinate-extraction-011CUuykxb37jUXNZgjAevQp

# Cell 3: Generar dataset de prueba
!python convertir_png_a_pdf_simple.py
!python generar_dataset_prueba.py

# Cell 4: Verificar interactivamente
!python verificar_coordenadas_colab.py \
    "Datos extraidos de Originales/pdfs/IMG-20251026-WA0038.pdf" \
    "dataset_con_coordenadas/IMG-20251026-WA0038_coordenadas.json" \
    --modo todo \
    --max-campos 5

# Cell 5: Si está bien, generar dataset completo
!python generar_dataset_completo.py

# Cell 6: Descargar resultados
!zip -r dataset_final.zip dataset_con_coordenadas/
from google.colab import files
files.download('dataset_final.zip')
```

---

## 💡 Tips Finales

1. **Siempre verifica al menos 3 documentos** antes de procesar todo el dataset
2. **Usa visualización con leyenda** para documentos con muchos campos
3. **Revisa especialmente campos numéricos** (montos, RUC, fechas)
4. **Si hay errores sistemáticos**, ajusta el threshold globalmente
5. **Guarda las visualizaciones** para documentación del dataset

---

## 📞 Qué Reportar

Cuando compartas resultados, incluye:

```
📊 REPORTE DE VERIFICACIÓN:

Match rate: XX.X%
Confianza promedio: 0.XXXX
Campos encontrados: XX/XX

Tipos de matching:
- exact: XX
- fuzzy: XX

Campos con problemas:
- campo_1: descripción del problema
- campo_2: descripción del problema

[Adjuntar imagen de verificacion.png]
```

---

¡Con estas herramientas puedes estar **100% seguro** de que las coordenadas son correctas! ✅
