"""Shared metric helpers."""


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = min(int(len(sorted_vals) * p / 100), len(sorted_vals) - 1)
    return sorted_vals[idx]


def format_ms(ms: float) -> str:
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms / 1000:.2f}s"
