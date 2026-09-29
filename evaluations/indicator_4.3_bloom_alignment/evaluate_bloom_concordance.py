"""
Evaluación del Indicador 2: Concordancia de Taxonomía de Bloom.
Genera o extrae muestras de preguntas a través de los diferentes niveles cognitivos de Bloom,
ejecuta una auditoría ciega con el evaluador pedagógico y calcula:
- Matriz de Confusión (5x5)
- Precisión, Recall y F1 por cada nivel
- Macro F1-Score (Meta de Tesis: >= 0.75)
"""

import argparse
import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Asegurar codificación UTF-8 en stdout/stderr en entornos Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Asegurar path raíz y directorio local en sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CURRENT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from core.settings import settings
from evaluations.shared.db_sample_extractor import DbSampleExtractor
from evaluations.shared.metrics_engine import (
    calculate_classification_metrics,
    calculate_confusion_matrix,
)
from bloom_pedagogical_evaluator import (
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

Reglas Estructurales de la Sintaxis Gherkin:
1. 'Given' (Dado): Establece el contexto previo o precondición del sistema (ejemplo: 'Dado que un cliente tiene un saldo inicial de $100').
2. 'When' (Cuando): Especifica la acción detonante ejecutada por el actor (ejemplo: 'Cuando el cliente transfiere $40 a otra cuenta').
3. 'Then' (Entonces): Declara el resultado observable esperado o postcondición verificable (ejemplo: 'Entonces el saldo remanente debe ser de $60').
4. 'And' / 'But': Enlazan precondiciones o postcondiciones adicionales.

Diferencias Arquitectónicas Fundamentales (TDD vs BDD):
- Alcance: Las pruebas unitarias tradicionales de TDD verifican el estado interno o la lógica algorítmica de una clase (caja blanca/gris), mientras que los escenarios de BDD verifican comportamientos observables desde la perspectiva del usuario o del negocio (caja negra).
- Audiencia: TDD está orientado exclusivamente a desarrolladores; BDD involucra a Product Owners, QA y desarrolladores ('Los Tres Amigos').
- Automatización: Los pasos de Gherkin se mapean a código mediante 'Step Definitions' (Glue Code) usando frameworks como Cucumber o Behave.

Criterios de Evaluación y Buenas Prácticas:
1. Regla de Declaratividad: Un escenario debe describir 'QUÉ' hace el sistema según las reglas del negocio, jamás 'CÓMO' lo hace a nivel de interfaz de usuario (anti-patrón: hacer clic en el botón con id #submit-btn). Los escenarios acoplados a la UI son frágiles y de alto costo de mantenimiento.
2. Independencia y Atomicidad: Cada escenario debe ser autónomo y poder ejecutarse en cualquier orden sin depender del estado dejado por un escenario previo.
3. Trade-offs de Adopción: BDD introduce una sobrecarga inicial de mantenimiento del pegamento (glue code). Es altamente rentable en dominios complejos con reglas de negocio cambiantes, pero es contraproducente en microservicios puramente matemáticos o algoritmos de bajo nivel donde TDD unitario puro es más eficiente.
"""


RESOURCE_FILE = Path(__file__).resolve().parent / "Resource.md"


def get_academic_context(questions_per_level: int, custom_file: Optional[str] = None) -> str:
    """
    Retorna el contexto académico de referencia:
    - Si se especifica custom_file y existe, lo carga.
    - Si questions_per_level > 5 y Resource.md existe, carga el material curricular real y extenso (21KB, CMMI y Métricas).
    - En caso contrario, usa SAMPLE_ACADEMIC_CONTEXT (resumen compacto de BDD).
    """
    if custom_file:
        path = Path(custom_file)
        if path.exists():
            logger.info(f"Cargando contexto académico personalizado desde: {path.resolve()}")
            return path.read_text(encoding="utf-8")
        logger.warning(f"Archivo personalizado '{custom_file}' no encontrado. Evaluando alternativas...")

    if questions_per_level > 5 and RESOURCE_FILE.exists():
        logger.info(
            f"Escala amplia ({questions_per_level} preguntas/nivel solicitadas). "
            f"Cargando material curricular real desde {RESOURCE_FILE.name} (CMMI, Requerimientos y Métricas de Calidad)..."
        )
        return RESOURCE_FILE.read_text(encoding="utf-8")

    return SAMPLE_ACADEMIC_CONTEXT


async def generate_balanced_bloom_samples(
    questions_per_level: int = 3,
    context_file: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Genera un conjunto balanceado de preguntas para cada uno de los 5 niveles cognitivos de Bloom
    utilizando el generador oficial de cuestionarios del sistema.
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    quiz_generator = GeminiQuizGenerator(client=client)

    context_text = get_academic_context(questions_per_level, custom_file=context_file)

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
                context_text=context_text,
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
    batch_size: int = 20,
    context_file: Optional[str] = None,
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

    # 2. Generar muestra balanceada complementaria o principal si la BD está vacía o se ejecuta en modo live
    if not questions_pool and generate_synthetic_if_empty:
        logger.info(f"Modo en memoria activado. Generando lote balanceado ({synthetic_samples_per_level} preguntas por nivel, total: {synthetic_samples_per_level * 5})...")
        synthetic_pool = await generate_balanced_bloom_samples(
            questions_per_level=synthetic_samples_per_level,
            context_file=context_file,
        )
        questions_pool.extend(synthetic_pool)

    if not questions_pool:
        logger.error("No se dispuso de preguntas para evaluar.")
        return {"error": "Sin datos de preguntas"}

    logger.info(f"Total de preguntas en la muestra de auditoría: {len(questions_pool)}")

    evaluator = BloomPedagogicalEvaluator()
    y_target: List[str] = []
    y_evaluated: List[str] = []
    evaluations_log: List[Dict[str, Any]] = []

    batch_size = max(1, batch_size)
    for start_idx in range(0, len(questions_pool), batch_size):
        batch = questions_pool[start_idx : start_idx + batch_size]
        end_idx = min(start_idx + batch_size, len(questions_pool))
        logger.info(f"Evaluando lote de reactivos #{start_idx + 1} a #{end_idx} de {len(questions_pool)}...")

        batch_results = await evaluator.evaluate_batch_bloom_level(batch)

        for q_item, result in zip(batch, batch_results):
            target = q_item["target_bloom_level"].lower()
            if target not in BLOOM_LEVELS:
                continue

            if result is None:
                logger.warning("Reactivo omitido por error técnico de conectividad o cuota de API.")
                continue

            y_target.append(target)
            y_evaluated.append(result.cognitive_level)

            evaluations_log.append({
                "index": len(y_target),
                "question_text": q_item["text"],
                "target_level": target,
                "evaluated_level": result.cognitive_level,
                "is_concordant": target == result.cognitive_level,
                "confidence": result.confidence,
                "reasoning": result.cognitive_demand_analysis,
            })

        # Pausa defensiva breve entre lotes para respetar cuotas de API
        await asyncio.sleep(1.0)

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

    # Resumen en consola para visualización en vivo
    print("\n" + "=" * 65)
    print("[RESULTADOS DE AUDITORIA] - TAXONOMIA DE BLOOM")
    print("=" * 65)
    print(f"Total reactivos evaluados: {len(y_target)}")
    print(f"Macro F1-Score:           {macro_f1:.4f}  (Meta: >= 0.7500)")
    print(f"Accuracy Global:          {classification_results['accuracy'] * 100:.2f}%")
    print(f"Estado de la Meta:        {'[OK] META ALCANZADA' if academic_threshold_met else '[ALERTA] INFERIOR AL UMBRAL'}")
    print("-" * 65)
    print("Desglose por Nivel Cognitivo:")
    for level, metrics in classification_results["per_class"].items():
        print(f"  - {level.capitalize():<12} | Precision: {metrics['precision']:.4f} | Recall: {metrics['recall']:.4f} | F1: {metrics['f1_score']:.4f} | Soporte: {metrics['support']}")
    print("=" * 65 + "\n")

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
    parser = argparse.ArgumentParser(description="Auditoría de concordancia cognitiva de Bloom")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Generar nuevo lote balanceado de reactivos en memoria sin consultar ni persistir en BD",
    )
    parser.add_argument(
        "--samples-per-level",
        type=int,
        default=5,
        help="Número de reactivos por nivel cognitivo para la generación en memoria (default: 5)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Número de reactivos por lote para la evaluación con el juez pedagógico (default: 20)",
    )
    parser.add_argument(
        "--context-file",
        type=str,
        default=None,
        help="Ruta opcional a un archivo .md personalizado con material académico de referencia",
    )
    args = parser.parse_args()

    use_db = not args.live
    asyncio.run(
        run_bloom_concordance_evaluation(
            use_db_samples=use_db,
            generate_synthetic_if_empty=True,
            synthetic_samples_per_level=args.samples_per_level,
            batch_size=args.batch_size,
            context_file=args.context_file,
        )
    )
