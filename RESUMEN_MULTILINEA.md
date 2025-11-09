# 📦 Campos Multilínea - Resumen Rápido

## ❓ Tu Pregunta

> "Las direcciones pueden salir en una fila y debajo otra fila. ¿Consideras la dirección del mismo campo doblemente las coordenadas o se separa las coordenadas?"

---

## ✅ Respuesta Corta

**El sistema ACTUALMENTE genera UNA sola bbox** que abarca todas las líneas del campo.

**Ejemplo:**

```
JSON: {"direccion": "Av. Los Pinos 123 San Isidro, Lima"}

PDF:
Av. Los Pinos 123    ← Línea 1
San Isidro, Lima     ← Línea 2

RESULTADO:
┌─────────────────────┐
│ Av. Los Pinos 123   │ ← Todo en UN solo rectángulo
│ San Isidro, Lima    │
└─────────────────────┘

{
  "campo": "direccion",
  "bbox": [100, 200, 300, 250],  ← UNA sola bbox
  "texto": "Av. Los Pinos 123 San Isidro, Lima"
}
```

---

## 🎯 ¿Es Correcto?

✅ **SÍ** - Este es el enfoque correcto para:
- Entrenar LayoutLM y modelos similares
- Document Understanding
- Detección de campos (object detection)

**Ventajas:**
- ✅ Formato estándar esperado por LayoutLM
- ✅ Un campo = una entidad semántica
- ✅ Simple y eficiente
- ✅ Fácil de visualizar

**Desventaja:**
- ❌ Incluye espacio vacío entre líneas (pero es aceptable)

---

## 🔄 Enfoque Alternativo (Si lo necesitas)

Puedo implementar que genere **múltiples bboxes** (una por línea):

```json
{
  "campo": "direccion",
  "texto_completo": "Av. Los Pinos 123 San Isidro, Lima",
  "bbox_combinada": [100, 200, 300, 250],
  "bboxes_por_linea": [
    [100, 200, 300, 215],  ← Línea 1
    [100, 230, 250, 245]   ← Línea 2
  ]
}
```

✅ Más preciso, pero más complejo y no estándar.

---

## 🧪 Verifica con tus Datos

```bash
# 1. Genera coordenadas de prueba
python generar_dataset_prueba.py

# 2. Analiza campos multilínea
python analizar_campos_multilinea.py
```

Este script te muestra:
- ✅ Cuántos campos son multilínea
- ✅ Comparación visual de ambos enfoques
- ✅ Porcentaje de espacio vacío incluido

---

## 💡 Recomendación

**Mantén el sistema actual** (enfoque 1) → Es perfecto para tu caso de uso.

Solo cambia a enfoque 2 si necesitas análisis de layout ultra-detallado.

---

## 📖 Más Info

Lee **CAMPOS_MULTILINEA.md** para detalles técnicos completos.
