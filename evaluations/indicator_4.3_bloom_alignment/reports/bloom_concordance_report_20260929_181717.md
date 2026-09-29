# Reporte de Validación - Indicador 2: Concordancia con la Taxonomía de Bloom

- **Fecha de Evaluación:** `2026-09-29T18:17:17.864050`
- **Muestra Total de Preguntas Auditadas:** `102`
- **Estado de Meta de Tesis (Macro F1 $\ge 0.75$):** **✅ CUMPLIDO**

---

## 1. Resumen de Métricas de Rendimiento Cognitivo

| Métrica | Valor Obtenido | Umbral Académico de Referencia | Veredicto |
| :--- | :---: | :---: | :---: |
| **Macro F1-Score** | **0.9018** | $\ge 0.75$ (75.0%) | ✅ Meta Alcanzada |
| **Weighted F1-Score** | **0.9015** | - | Ponderado por soporte |
| **Accuracy Global** | **90.20%** | - | Proporción global de aciertos |

---

## 2. Matriz de Confusión ($5 \times 5$)

| Objetivo \ Evaluado | **Remember** | **Understand** | **Apply** | **Analyze** | **Evaluate** | **Total Real** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Remember** | 20 | 0 | 0 | 0 | 0 | **20** |
| **Understand** | 1 | 20 | 0 | 0 | 0 | **21** |
| **Apply** | 2 | 0 | 19 | 0 | 0 | **21** |
| **Analyze** | 0 | 2 | 0 | 18 | 0 | **20** |
| **Evaluate** | 0 | 3 | 2 | 0 | 15 | **20** |
| **Total Asignado** | 23 | 25 | 21 | 18 | 15 | **102** |

---

## 3. Desglose de Rendimiento por Nivel Cognitivo

| Nivel de Bloom | Precision | Recall | F1-Score | Soporte (Muestras) |
| :--- | :---: | :---: | :---: | :---: |
| **Remember** | 0.8696 | 1.0000 | 0.9302 | 20 |
| **Understand** | 0.8000 | 0.9524 | 0.8696 | 21 |
| **Apply** | 0.9048 | 0.9048 | 0.9048 | 21 |
| **Analyze** | 1.0000 | 0.9000 | 0.9474 | 20 |
| **Evaluate** | 1.0000 | 0.7500 | 0.8571 | 20 |

---

## 4. Justificación Metodológica para la Tesis

1. **Evaluación Multiclase Balanceada (Macro F1):** Al promediar aritméticamente el F1-Score de los 5 niveles cognitivos con igual ponderación (20% cada uno), el **Macro F1-Score** de **0.9018** evita que un alto acierto en preguntas de orden inferior (*Remember* o *Understand*) oculte deficiencias en niveles superiores.
2. **Garantía contra la Degradación Memorística:** La meta alcanzada de $\ge 0.75$ certifica empíricamente que los reactivos dirigidos a niveles de orden superior (*Apply*, *Analyze*, *Evaluate*) no se degradan hacia preguntas superficiales o puramente memorísticas, asegurando el valor pedagógico del sistema evaluativo.
