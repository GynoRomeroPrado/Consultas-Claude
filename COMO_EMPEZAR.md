# 🚀 Cómo Empezar con las Pruebas

## ✅ Estado Actual

He creado un **sistema completo de pruebas** para validar la extracción de coordenadas con tus archivos reales. Todo está listo, solo faltan tus archivos PDF y JSON.

---

## 📋 Pasos a Seguir

### **Paso 1: Sube tus archivos**

Coloca los archivos en esta estructura:

```
datos_extraidos_de_Originales/
├── pdfs/
│   ├── documento1.pdf
│   ├── documento2.pdf
│   └── documento3.pdf
└── anotaciones/
    ├── documento1.json
    ├── documento2.json
    └── documento3.json
```

**IMPORTANTE**: Los nombres deben coincidir (sin extensión).

---

### **Paso 2: Verifica que se subieron correctamente**

Ejecuta:

```bash
python verificar_archivos.py
```

Deberías ver algo como:

```
📄 PDFs encontrados: 3
  - pdfs/documento1.pdf (2.5 MB)
  - pdfs/documento2.pdf (1.8 MB)
  - pdfs/documento3.pdf (3.1 MB)

📝 JSONs encontrados: 3
  - anotaciones/documento1.json (2.3 KB)
  - anotaciones/documento2.json (1.9 KB)
  - anotaciones/documento3.json (2.1 KB)

🔗 Verificando emparejamiento:
  ✓ documento1.pdf <-> anotaciones/documento1.json
  ✓ documento2.pdf <-> anotaciones/documento2.json
  ✓ documento3.pdf <-> anotaciones/documento3.json

RESUMEN:
  Pares emparejados: 3

✅ Listo para procesar!
```

---

### **Paso 3: Ejecuta las pruebas automáticas**

```bash
python test_real_data.py
```

Este script hará TODO automáticamente:

1. ✅ Busca todos los pares PDF-JSON
2. ✅ Inspecciona la estructura de los JSONs
3. ✅ Prueba 4 estrategias diferentes:
   - EXACT (solo coincidencias exactas)
   - AUTO (exact + fuzzy si es necesario)
   - FUZZY threshold 80%
   - FUZZY threshold 70%
4. ✅ Compara resultados
5. ✅ Recomienda la mejor estrategia
6. ✅ Guarda resultados en `output/pruebas/`

---

## 📊 Qué Verás en los Resultados

### Salida esperada:

```
################################################################################
# COMPARACIÓN DE ESTRATEGIAS
# PDF: documento1.pdf
# JSON: documento1.json
################################################################################

================================================================================
PROBANDO: EXACT (threshold=100.0)
================================================================================

📊 RESULTADOS - EXACT
================================================================================
  Total de campos:        25
  Campos encontrados:     18
  Campos no encontrados:  7
  Tasa de éxito:          72.0%
  Confianza promedio:     1.0000

  Tipos de matching:
    - exact: 18

  Páginas con matches: 2

📝 EJEMPLOS DE MATCHES:
  [1] nombre_completo
      Texto encontrado: 'Juan Pérez García'
      Página: 0, Bbox: (100.5, 200.3, 250.8, 220.1)
      Confianza: 1.00, Tipo: exact

  [2] documento_identidad
      Texto encontrado: '12345678-A'
      Página: 0, Bbox: (300.2, 200.5, 380.7, 220.3)
      Confianza: 1.00, Tipo: exact

...

================================================================================
RESUMEN COMPARATIVO
================================================================================
Estrategia           Threshold    Match Rate      Avg Confidence
--------------------------------------------------------------------------------
exact                100.0        72.0%           1.0000
auto                 80.0         88.0%           0.9234
fuzzy                80.0         88.0%           0.9120
fuzzy                70.0         92.0%           0.8845

🏆 MEJOR ESTRATEGIA: fuzzy (threshold=70.0)
   Match rate: 92.0%
   Avg confidence: 0.8845
```

---

## 🔍 Formato del JSON

### Formato Básico (Soportado):

```json
{
  "nombre": "Juan Pérez",
  "edad": "30",
  "ciudad": "Madrid",
  "telefono": "+34 600 123 456"
}
```

### Formato Anidado (También Soportado):

```json
{
  "datos_personales": {
    "nombre": "Juan Pérez",
    "edad": "30"
  },
  "direccion": {
    "calle": "Main St",
    "ciudad": "Madrid"
  }
}
```

Se aplana automáticamente a:
```json
{
  "datos_personales.nombre": "Juan Pérez",
  "datos_personales.edad": "30",
  "direccion.calle": "Main St",
  "direccion.ciudad": "Madrid"
}
```

---

## 🐛 Si Algo Sale Mal

### Error: "No se encontraron pares PDF-JSON"

**Solución**: Revisa que los nombres coincidan:
```bash
ls datos_extraidos_de_Originales/pdfs/
ls datos_extraidos_de_Originales/anotaciones/
```

### Match Rate muy bajo (< 50%)

**Causas**:
1. El PDF puede tener errores de OCR
2. El formato del JSON es diferente al esperado
3. Los valores en el JSON no existen tal cual en el PDF

**Solución**: Compárteme:
- Un ejemplo del JSON (pega el contenido)
- El resultado del script de pruebas
- Si puedes, una captura o descripción de cómo se ve el PDF

### Campos específicos no se encuentran

**Debugging**:
```bash
# Ver qué texto hay en el PDF
python -c "
import fitz
doc = fitz.open('datos_extraidos_de_Originales/pdfs/documento1.pdf')
print(doc[0].get_text())
"

# Ejecutar con verbose para ver detalles
python extract_coordinates.py \
    datos_extraidos_de_Originales/pdfs/documento1.pdf \
    -o output/debug.json \
    --fuzzy --threshold 70 -v
```

---

## 📦 Archivos Creados para Ti

He preparado estos scripts:

1. **`verificar_archivos.py`** - Verifica archivos subidos
2. **`test_real_data.py`** - Pruebas automáticas completas
3. **`extract_coordinates.py`** - CLI para uso manual
4. **`INSTRUCCIONES_PRUEBAS.md`** - Guía detallada
5. **`datos_extraidos_de_Originales/README.txt`** - Instrucciones en la carpeta de datos

---

## 🎯 Lo que Necesito de Ti

Después de ejecutar las pruebas, compárteme:

1. **La salida completa** de `python test_real_data.py`
2. **Un ejemplo de JSON** (pega el contenido de uno de tus archivos)
3. **Estadísticas obtenidas**:
   - Match rate
   - Campos que no se encontraron
   - Errores específicos

Con eso podré:
- ✅ Ajustar el sistema a tu formato específico
- ✅ Optimizar los parámetros
- ✅ Corregir errores
- ✅ Mejorar el matching

---

## ⚡ Uso Rápido (Una Vez Subidos los Archivos)

```bash
# Verificar archivos
python verificar_archivos.py

# Ejecutar pruebas completas
python test_real_data.py

# Ver resultados
ls output/pruebas/
```

---

## 📞 Estoy Listo

En cuanto subas los archivos y ejecutes las pruebas:

1. Comparte la salida del script
2. Dame un ejemplo de tu JSON
3. Cuéntame qué errores ves

Yo me encargo de:
- 🔧 Ajustar el código
- 🎯 Optimizar los parámetros
- ✅ Corregir bugs
- 📊 Mejorar el matching

**¡Adelante, sube los archivos y ejecuta las pruebas!** 🚀
