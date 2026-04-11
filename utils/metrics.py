# ===== utils/metrics.py =====
"""
Metrics Utility: Computes precision, recall, F1-score for issue detection.
Used in the CodeXGLUE evaluation tab.
"""

from typing import Dict, List


def compute_precision_recall_f1(
    true_positives: int,
    false_positives: int,
    false_negatives: int,
) -> Dict[str, float]:
    """
    Compute standard IR metrics from confusion matrix counts.

    Args:
        true_positives: Correctly detected issues.
        false_positives: Issues flagged that shouldn't be.
        false_negatives: Issues missed by the scanner.

    Returns:
        Dict with precision, recall, f1 (all between 0.0 and 1.0).
    """
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate_scanner_against_labels(
    scan_results: List[Dict],
    ground_truth: List[Dict],
) -> Dict:
    """
    Compare scanner output against ground truth labels.

    Each ground_truth item: {"file": str, "line": int, "type": str}
    Each scan issue: {"file": str, "line": int, "type": str}

    Returns:
        Dict with per-type metrics and overall metrics.
    """
    # Build detected set
    detected = set()
    for result in scan_results:
        fp = result.get("relative_path", "")
        for issue in result.get("issues", []):
            detected.add((fp, issue.get("line", 0), issue.get("type", "")))

    # Build ground truth set
    truth = set()
    for gt in ground_truth:
        truth.add((gt.get("file", ""), gt.get("line", 0), gt.get("type", "")))

    tp = len(detected & truth)
    fp = len(detected - truth)
    fn = len(truth - detected)

    overall = compute_precision_recall_f1(tp, fp, fn)

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "overall": overall,
        "detected_count": len(detected),
        "ground_truth_count": len(truth),
    }


def build_confusion_summary(tp: int, fp: int, fn: int) -> str:
    """Format a simple confusion matrix summary string."""
    tn = 0  # Not applicable for issue detection (no "true negatives" in this context)
    return (
        f"True Positives:  {tp}\n"
        f"False Positives: {fp}\n"
        f"False Negatives: {fn}\n"
    )
