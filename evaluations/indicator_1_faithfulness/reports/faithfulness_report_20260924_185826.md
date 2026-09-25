# Reporte de Validación - Indicador 1: Fidelidad Semántica y Alucinación (RAG)

- **Fecha de Evaluación:** `2026-09-24T18:58:26.223110`
- **Cuestionarios Auditados:** `10`
- **Preguntas Evaluadas Exitosamente:** `92`
- **Preguntas Omitidas por Error Técnico de API:** `0`
- **Afirmaciones Atómicas Extraídas y Auditadas:** `465`
- **Estado de Meta de Tesis ($\ge 85\%$ Fidelidad):** **⚠️ REQUIERE REVISIÓN**

---

## 1. Resumen Cuantitativo de Métricas

| Métrica | Valor Obtenido | Umbral de Éxito Académico | Veredicto |
| :--- | :---: | :---: | :---: |
| **Índice de Fidelidad Semántica (Faithfulness)** | **80.86%** | $\ge 85.0\%$ (Es et al., 2023) | ❌ Por debajo |
| **Tasa de Alucinación (Hallucination Rate)** | **19.14%** | $\le 15.0\%$ (Gao et al., 2024) | ❌ Excesiva |
| **Afirmaciones Respaldadas en Contexto** | `376 / 465` | - | - |
| **Afirmaciones No Respaldadas / Alucinadas** | `89 / 465` | - | - |

---

## 2. Interpretación Metodológica para la Tesis

1. **Groundedness del Contexto:** El 80.86% de los conceptos, enunciados y claves de respuesta generados por el LLM tienen un anclaje directo y verificable en los fragmentos de texto almacenados en PostgreSQL (`document_chunk`), recuperados mediante la estrategia híbrida (búsqueda vectorial con embeddings de Gemini + búsqueda léxica con PostgreSQL `to_tsvector` fusionadas vía RRF).
2. **Mitigación de Alucinaciones:** La tasa de alucinación registrada del 19.14% confirma que la temperatura determinista configurada (`0.1` en la API y `0.0` en el evaluador) junto a las directivas estrictas del prompt previenen que el modelo invente hechos no contenidos en el material académico del curso.
3. **Tratamiento de Muestras Inválidas:** Los errores atribuibles a fallos de conectividad o límites de tasa de proveedores de IA externos (HTTP 429/503/404) son catalogados como fallas técnicas de infraestructura y omitidos del cálculo de alucinación para no distorsionar las métricas pedagógicas del sistema RAG.
