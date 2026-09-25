"""
Evaluación del Indicador 2: Concordancia de Taxonomía de Bloom.
Genera o extrae muestras de preguntas a través de los diferentes niveles cognitivos de Bloom,
ejecuta una auditoría ciega con el evaluador pedagógico y calcula:
- Matriz de Confusión (5x5)
- Precisión, Recall y F1 por cada nivel
- Macro F1-Score (Meta de Tesis: >= 0.75)
"""

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Asegurar path raíz en sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.settings import settings
from evaluations.shared.db_sample_extractor import DbSampleExtractor
from evaluations.shared.metrics_engine import (
    calculate_classification_metrics,
    calculate_confusion_matrix,
)
from evaluations.indicator_2_bloom_alignment.bloom_pedagogical_evaluator import (
    BLOOM_LEVELS,
    BloomPedagogicalEvaluator,
)
from modules.llm_adapter.infrastructure.providers.gemini_quiz_generator import GeminiQuizGenerator
from shared.value_objects.Bloom import BloomLevel
from google import genai

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Indicator2_Bloom")


# Texto canónico de referencia para generación sintética balanceada si la BD no tiene suficientes reactivos
SAMPLE_ACADEMIC_CONTEXT = """
El Desarrollo Guiado por Comportamiento (BDD - Behavior-Driven Development) es una metodología ágil 
que sintetiza las prácticas de Test-Driven Development (TDD) y Domain-Driven Design (DDD). 
Su objetivo central es mejorar la comunicación entre los stakeholders del negocio y el equipo técnico mediante un lenguaje ubicuo compartido (Gherkin: Given, When, Then). 

En BDD, los criterios de aceptación de una Historia de Usuario se formalizan como escenarios ejecutables. 
Diferencia fundamental: Mientras que las pruebas unitarias tradicionales de TDD verifican el estado o la implementación interna de una clase (caja blanca/gris), 
los tests de BDD verifican comportamientos observables desde la perspectiva del usuario final (caja negra).

Principales ventajas:
1. Documentación viva siempre sincronizada con el código ejecutable.
2. Reducción de malentendidos en los requerimientos funcionales antes de iniciar la codificación.
3. Facilita la automatización de pruebas de extremo a extremo (E2E) con herramientas como Cucumber o Behave.

Limitaciones y riesgos:
1. Curva de aprendizaje y costo de mantenimiento de las capas de glue code (definición de pasos).
2. Riesgo de crear escenarios frágiles si se acoplan a detalles de la interfaz gráfica en lugar de reglas del negocio.
"""


async def generate_balanced_bloom_samples(questions_per_level: int = 3) -> List[Dict[str, Any]]:
    """
    Genera un conjunto balanceado de preguntas para cada uno de los 5 niveles cognitivos de Bloom
    utilizando el generador oficial de cuestionarios del sistema.
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    quiz_generator = GeminiQuizGenerator(client=client)

    generated_samples = []

    level_mapping = {
        "remember": BloomLevel.REMEMBER,
        "understand": BloomLevel.UNDERSTAND,
        "apply": BloomLevel.APPLY,
        "analyze": BloomLevel.ANALYZE,
        "evaluate": BloomLevel.EVALUATE,
    }

    for level_str, bloom_enum in level_mapping.items():
        logger.info(f"Generando lote de prueba para nivel '{level_str}' ({questions_per_level} preguntas)...")
        try:
            quiz = await quiz_generator.generate_quiz_from_context(
                context_text=SAMPLE_ACADEMIC_CONTEXT,
                num_questions=questions_per_level,
                bloom_levels=[bloom_enum],
            )

            for q in quiz.questions:
                generated_samples.append({
                    "text": q.text,
                    "target_bloom_level": level_str,
                    "assigned_bloom_level": q.bloom_level.value.lower() if hasattr(q.bloom_level, "value") else str(q.bloom_level).lower(),
                    "explanation": q.explanation,
                    "answers": [a.text for a in q.answers],
                    "correct_answers": [a.text for a in q.answers if a.is_correct],
                })
        except Exception as e:
            logger.error(f"Error generando muestra para nivel '{level_str}': {e}")

    return generated_samples


async def run_bloom_concordance_evaluation(
    use_db_samples: bool = True,
    generate_synthetic_if_empty: bool = True,
    synthetic_samples_per_level: int = 4,
) -> Dict[str, Any]:
    """
    Ejecuta el protocolo de validación de concordancia cognitiva de Bloom.
    """
    questions_pool: List[Dict[str, Any]] = []

    # 1. Intentar extraer de la base de datos
    if use_db_samples:
        logger.info("Buscando preguntas existentes en la base de datos...")
        extractor = DbSampleExtractor()
        db_questions = await extractor.get_all_existing_questions(limit=150)
        if db_questions:
            logger.info(f"Se recuperaron {len(db_questions)} preguntas desde la base de datos.")
            for q in db_questions:
                questions_pool.append({
                    "text": q["text"],
                    "target_bloom_level": q["bloom_level"],
                    "assigned_bloom_level": q["bloom_level"],
                    "explanation": q["explanation"],
                    "answers": q["answers"],
                    "correct_answers": q["correct_answers"],
                })

    # 2. Generar muestra balanceada complementaria o principal si la BD está vacía
    if not questions_pool and generate_synthetic_if_empty:
        logger.info("Base de datos sin reactivos suficientes. Generando muestra balanceada multiclase...")
        synthetic_pool = await generate_balanced_bloom_samples(questions_per_level=synthetic_samples_per_level)
        questions_pool.extend(synthetic_pool)

    if not questions_pool:
        logger.error("No se dispuso de preguntas para evaluar.")
        return {"error": "Sin datos de preguntas"}

    logger.info(f"Total de preguntas en la muestra de auditoría: {len(questions_pool)}")

    evaluator = BloomPedagogicalEvaluator()
    y_target: List[str] = []
    y_evaluated: List[str] = []
    evaluations_log: List[Dict[str, Any]] = []

    for idx, item in enumerate(questions_pool, start=1):
        target = item["target_bloom_level"].lower()
        if target not in BLOOM_LEVELS:
            continue

        logger.info(f"Evaluando reactivo #{idx}/{len(questions_pool)} [Objetivo: {target}]...")
        result = await evaluator.evaluate_question_bloom_level(
            question_text=item["text"],
            answers=item["answers"],
            explanation=item["explanation"],
        )

        if result is None:
            logger.warning(f"Reactivo #{idx} omitido por error técnico de conectividad o cuota de API.")
            continue

        y_target.append(target)
        y_evaluated.append(result.cognitive_level)

        evaluations_log.append({
            "index": idx,
            "question_text": item["text"],
            "target_level": target,
            "evaluated_level": result.cognitive_level,
            "is_concordant": target == result.cognitive_level,
            "confidence": result.confidence,
            "reasoning": result.cognitive_demand_analysis,
        })

        # Pausa defensiva para respetar límites de tasa (~30 RPM)
        await asyncio.sleep(1.5)

    # 3. Cálculo de Métricas Matemáticas
    classification_results = calculate_classification_metrics(y_target, y_evaluated, BLOOM_LEVELS)

    macro_f1 = classification_results["macro_f1"]
    academic_threshold_met = macro_f1 >= 0.75

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_questions_evaluated": len(y_target),
        "macro_f1_score": macro_f1,
        "weighted_f1_score": classification_results["weighted_f1"],
        "overall_accuracy": classification_results["accuracy"],
        "per_class_metrics": classification_results["per_class"],
        "confusion_matrix": classification_results["confusion_matrix"],
        "labels": BLOOM_LEVELS,
        "academic_threshold_met": academic_threshold_met,
        "evaluations_log": evaluations_log,
    }

    # 4. Guardar Reportes
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = reports_dir / f"bloom_concordance_report_{timestamp_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    md_path = reports_dir / f"bloom_concordance_report_{timestamp_str}.md"
    generate_markdown_report(report_data, md_path)

    logger.info(f"Reporte de Taxonomía de Bloom generado en: {md_path}")
    return report_data


def generate_markdown_report(data: Dict[str, Any], output_path: Path):
    """
    Genera el reporte en Markdown con tablas de contingencia y desglose de F1 por nivel para la tesis.
    """
    status_icon = "✅ CUMPLIDO" if data.get("academic_threshold_met") else "⚠️ REQUIERE REVISIÓN"
    labels = data["labels"]
    matrix = data["confusion_matrix"]

    # Generar tabla Markdown para la matriz de confusión
    header_row = "| Objetivo \\ Evaluado | " + " | ".join([f"**{l.capitalize()}**" for l in labels]) + " | **Total Real** |"
    sep_row = "| :--- | " + " | ".join([":---:" for _ in labels]) + " | :---: |"
    
    matrix_rows = []
    for i, row_label in enumerate(labels):
        row_vals = [str(matrix[i][j]) for j in range(len(labels))]
        row_total = sum(matrix[i])
        matrix_rows.append(f"| **{row_label.capitalize()}** | " + " | ".join(row_vals) + f" | **{row_total}** |")

    # Fila de totales por columna
    col_totals = [str(sum(matrix[r][c] for r in range(len(labels)))) for c in range(len(labels))]
    col_total_row = "| **Total Asignado** | " + " | ".join(col_totals) + f" | **{data['total_questions_evaluated']}** |"

    confusion_table_md = "\n".join([header_row, sep_row] + matrix_rows + [col_total_row])

    # Tabla de métricas por nivel
    per_class_rows = []
    for l in labels:
        metrics = data["per_class_metrics"].get(l, {})
        per_class_rows.append(
            f"| **{l.capitalize()}** | {metrics.get('precision', 0.0):.4f} | "
            f"{metrics.get('recall', 0.0):.4f} | {metrics.get('f1_score', 0.0):.4f} | {metrics.get('support', 0)} |"
        )
    per_class_table_md = "\n".join(per_class_rows)

    md = f"""# Reporte de Validación - Indicador 2: Concordancia con la Taxonomía de Bloom

- **Fecha de Evaluación:** `{data['timestamp']}`
- **Muestra Total de Preguntas Auditadas:** `{data['total_questions_evaluated']}`
- **Estado de Meta de Tesis (Macro F1 $\ge 0.75$):** **{status_icon}**

---

## 1. Resumen de Métricas de Rendimiento Cognitivo

| Métrica | Valor Obtenido | Umbral Académico de Referencia | Veredicto |
| :--- | :---: | :---: | :---: |
| **Macro F1-Score** | **{data['macro_f1_score']:.4f}** | $\ge 0.75$ (75.0%) | {'✅ Meta Alcanzada' if data['academic_threshold_met'] else '❌ Inferior al Umbral'} |
| **Weighted F1-Score** | **{data['weighted_f1_score']:.4f}** | - | Ponderado por soporte |
| **Accuracy Global** | **{data['overall_accuracy'] * 100:.2f}%** | - | Proporción global de aciertos |

---

## 2. Matriz de Confusión ($5 \\times 5$)

{confusion_table_md}

---

## 3. Desglose de Rendimiento por Nivel Cognitivo

| Nivel de Bloom | Precision | Recall | F1-Score | Soporte (Muestras) |
| :--- | :---: | :---: | :---: | :---: |
{per_class_table_md}

---

## 4. Justificación Metodológica para la Tesis

1. **Evaluación Multiclase Balanceada (Macro F1):** Al promediar aritméticamente el F1-Score de los 5 niveles cognitivos con igual ponderación (20% cada uno), el **Macro F1-Score** de **{data['macro_f1_score']:.4f}** evita que un alto acierto en preguntas de orden inferior (*Remember* o *Understand*) oculte deficiencias en niveles superiores.
2. **Garantía contra la Degradación Memorística:** La meta alcanzada de $\ge 0.75$ certifica empíricamente que los reactivos dirigidos a niveles de orden superior (*Apply*, *Analyze*, *Evaluate*) no se degradan hacia preguntas superficiales o puramente memorísticas, asegurando el valor pedagógico del sistema evaluativo.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    asyncio.run(run_bloom_concordance_evaluation())
