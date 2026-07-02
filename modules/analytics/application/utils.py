def pct(correct: int, total: int) -> float:
    """
    Auxiliary method to calculate the percentage of correct answers over total questions attempted.
    """
    if total == 0:
        return 0.0
    return round((correct / total) * 100, 1)