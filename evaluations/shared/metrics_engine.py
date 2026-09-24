"""
Motor matemático nativo para cálculo de métricas de validación de tesis.
Calcula Matriz de Confusión, Kappa de Cohen, Macro F1, Precision, Recall
y Métricas de Fidelidad RAG sin dependencias externas pesadas.
"""

from typing import Any, Dict, List, Tuple


def calculate_confusion_matrix(
    y_true: List[str],
    y_pred: List[str],
    labels: List[str],
) -> Dict[str, Any]:
    """
    Construye la matriz de confusión cuadrada K x K para las etiquetas dadas.
    Retorna la matriz como diccionario indexable y como lista de listas.
    """
    label_to_idx = {label: i for i, label in enumerate(labels)}
    k = len(labels)
    matrix = [[0 for _ in range(k)] for _ in range(k)]

    for true_val, pred_val in zip(y_true, y_pred):
        if true_val in label_to_idx and pred_val in label_to_idx:
            row = label_to_idx[true_val]
            col = label_to_idx[pred_val]
            matrix[row][col] += 1

    return {
        "labels": labels,
        "matrix": matrix,
        "total_samples": len(y_true),
    }


def calculate_cohen_kappa(
    y_true: List[str],
    y_pred: List[str],
    labels: List[str],
) -> Dict[str, Any]:
    """
    Calcula el coeficiente Kappa de Cohen (kappa) para evaluar concordancia
    inter-evaluador penalizando el acuerdo esperado por azar.

    Fórmula: kappa = (Po - Pe) / (1 - Pe)
    """
    n = len(y_true)
    if n == 0:
        return {"kappa": 0.0, "observed_agreement_po": 0.0, "expected_agreement_pe": 0.0, "interpretation": "Sin datos"}

    conf = calculate_confusion_matrix(y_true, y_pred, labels)
    matrix = conf["matrix"]
    k = len(labels)

    # 1. Acuerdo Observado (Po): diagonal principal / N
    diagonal_sum = sum(matrix[i][i] for i in range(k))
    po = diagonal_sum / n

    # 2. Acuerdo Esperado por Azar (Pe): sum(row_total * col_total) / N^2
    row_totals = [sum(matrix[i][j] for j in range(k)) for i in range(k)]
    col_totals = [sum(matrix[i][j] for i in range(k)) for j in range(k)]

    pe = sum((row_totals[i] * col_totals[i]) for i in range(k)) / (n * n)

    if pe >= 1.0:
        kappa = 1.0
    else:
        kappa = (po - pe) / (1.0 - pe)

    # Interpretación estándar según Landis & Koch (1977)
    if kappa < 0.20:
        interpretation = "Pobre / Insignificante"
    elif kappa <= 0.40:
        interpretation = "Aceptable bajo"
    elif kappa <= 0.60:
        interpretation = "Moderado"
    elif kappa <= 0.80:
        interpretation = "Sustancial (Meta Académica Cumplida)"
    else:
        interpretation = "Casi perfecto / Excelente"

    return {
        "kappa": round(kappa, 4),
        "observed_agreement_po": round(po, 4),
        "expected_agreement_pe": round(pe, 4),
        "total_samples": n,
        "interpretation": interpretation,
    }


def calculate_classification_metrics(
    y_true: List[str],
    y_pred: List[str],
    labels: List[str],
) -> Dict[str, Any]:
    """
    Calcula Métricas Multiclase: Precision, Recall, F1-Score por clase,
    Macro F1-Score, Weighted F1-Score y Accuracy global.
    """
    n = len(y_true)
    if n == 0:
        return {"accuracy": 0.0, "macro_f1": 0.0, "per_class": {}}

    conf = calculate_confusion_matrix(y_true, y_pred, labels)
    matrix = conf["matrix"]
    k = len(labels)

    per_class: Dict[str, Dict[str, float]] = {}
    f1_list: List[float] = []
    support_list: List[int] = []

    correct_predictions = 0

    for i, label in enumerate(labels):
        tp = matrix[i][i]
        fp = sum(matrix[row][i] for row in range(k) if row != i)
        fn = sum(matrix[i][col] for col in range(k) if col != i)
        support = tp + fn

        correct_predictions += tp

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "support": support,
        }

        f1_list.append(f1)
        support_list.append(support)

    accuracy = correct_predictions / n if n > 0 else 0.0
    macro_f1 = sum(f1_list) / len(f1_list) if f1_list else 0.0
    
    total_support = sum(support_list)
    weighted_f1 = (
        sum(f1 * sup for f1, sup in zip(f1_list, support_list)) / total_support
        if total_support > 0
        else 0.0
    )

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "total_samples": n,
        "per_class": per_class,
        "confusion_matrix": matrix,
        "labels": labels,
    }


def calculate_faithfulness(verified_claims: int, total_claims: int) -> Dict[str, float]:
    """
    Calcula el índice de fidelidad semántica (Faithfulness) y tasa de alucinación.
    """
    if total_claims <= 0:
        return {"faithfulness": 1.0, "hallucination_rate": 0.0, "total_claims": 0}

    faithfulness = verified_claims / total_claims
    hallucination_rate = 1.0 - faithfulness

    return {
        "faithfulness": round(faithfulness, 4),
        "faithfulness_percentage": round(faithfulness * 100.0, 2),
        "hallucination_rate": round(hallucination_rate, 4),
        "hallucination_percentage": round(hallucination_rate * 100.0, 2),
        "verified_claims": verified_claims,
        "total_claims": total_claims,
    }
