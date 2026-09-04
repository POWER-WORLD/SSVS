import math
from typing import List, Dict, Any

class Normalizer:
    """Methods for normalizing raw scores into standard 0-100 scales."""

    @staticmethod
    def min_max(value: float, min_val: float, max_val: float, target_min: float = 0.0, target_max: float = 100.0) -> float:
        """Min-Max normalization to [target_min, target_max]."""
        if max_val <= min_val:
            return target_max if value >= max_val else target_min
        scaled = (value - min_val) / (max_val - min_val)
        scaled = max(0.0, min(1.0, scaled))
        return target_min + (scaled * (target_max - target_min))

    @staticmethod
    def z_score(value: float, mean: float, std_dev: float) -> float:
        """Standardizes a value and projects roughly to a 0-100 scale."""
        if std_dev == 0:
            return 50.0
        z = (value - mean) / std_dev
        # Map z-score from [-3, 3] to [0, 100]
        mapped = (z + 3.0) / 6.0
        return max(0.0, min(100.0, mapped * 100.0))

    @staticmethod
    def calculate_percentiles(scores: List[float]) -> List[float]:
        """Calculate percentile ranks for a list of scores."""
        n = len(scores)
        if n == 0:
            return []
        if n == 1:
            return [100.0]
            
        percentiles = []
        for s in scores:
            count_lower = sum(1 for x in scores if x < s)
            count_equal = sum(1 for x in scores if x == s)
            # Standard percentile rank formula: (below + 0.5 * equal) / total * 100
            pct = ((count_lower + 0.5 * count_equal) / n) * 100.0
            percentiles.append(round(pct, 1))
        return percentiles
