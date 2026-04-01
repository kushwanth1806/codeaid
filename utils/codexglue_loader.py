# ===== utils/codexglue_loader.py =====
"""
CodeXGLUE Evaluation Loader: Loads samples from the CodeXGLUE dataset
(code_x_glue_cc_code_refinement) and evaluates scanner performance.
Falls back to synthetic examples if the dataset is unavailable.
"""

import random
from typing import Dict, List, Optional, Tuple

from utils.metrics import evaluate_scanner_against_labels, compute_precision_recall_f1
from core.agents.scanner import scan_file


# ── Synthetic Fallback Dataset ────────────────────────────────────────────────

_SYNTHETIC_SAMPLES = [
    {
        "id": "syn_001",
        "buggy": "import os\nimport sys\n\ndef add(a, b):\n    return a + b\n",
        "fixed": "def add(a, b):\n    return a + b\n",
        "label": [{"line": 1, "type": "unused_import"}, {"line": 2, "type": "unused_import"}],
        "description": "Unused imports: os and sys",
    },
    {
        "id": "syn_002",
        "buggy": "def f(a, b, c, d, e, f, g):\n    pass\n",
        "fixed": "def f(config):\n    pass\n",
        "label": [{"line": 1, "type": "too_many_params"}],
        "description": "Too many parameters",
    },
    {
        "id": "syn_003",
        "buggy": "x = 1\n# TODO: implement this properly\ny = 2\n",
        "fixed": "x = 1\ny = 2\n",
        "label": [{"line": 2, "type": "todo_comment"}],
        "description": "TODO comment",
    },
    {
        "id": "syn_004",
        "buggy": "def foo(:\n    pass\n",
        "fixed": "def foo():\n    pass\n",
        "label": [{"line": 1, "type": "syntax_error"}],
        "description": "Syntax error: missing closing paren",
    },
    {
        "id": "syn_005",
        "buggy": (
            "import json\nimport re\n\n"
            + "\n".join([f"    # line {i}" for i in range(60)])
            + "\ndef long_func():\n"
            + "\n".join([f"    x{i} = {i}" for i in range(55)])
            + "\n"
        ),
        "fixed": "# Refactored into smaller functions\n",
        "label": [{"line": 1, "type": "unused_import"}, {"line": 2, "type": "unused_import"}],
        "description": "Unused imports + long function",
    },
    {
        "id": "syn_006",
        "buggy": "from math import sqrt\n\nresult = sqrt(16)\nprint(result)\n",
        "fixed": "from math import sqrt\n\nresult = sqrt(16)\nprint(result)\n",
        "label": [],
        "description": "Clean file — no issues expected",
    },
    {
        "id": "syn_007",
        "buggy": "import os\n\n# FIXME: this is broken\ndef broken():\n    return None\n",
        "fixed": "def broken():\n    return None\n",
        "label": [{"line": 1, "type": "unused_import"}, {"line": 3, "type": "todo_comment"}],
        "description": "Unused import + FIXME comment",
    },
    {
        "id": "syn_008",
        "buggy": "x = [\n",
        "fixed": "x = []\n",
        "label": [{"line": 1, "type": "syntax_error"}],
        "description": "Unclosed bracket syntax error",
    },
]


def load_codexglue_samples(max_samples: int = 20) -> Tuple[List[Dict], str]:
    """
    Attempt to load CodeXGLUE dataset; fall back to synthetic samples.

    Args:
        max_samples: Maximum number of samples to load.

    Returns:
        (samples_list, source_description)
        Each sample: {id, buggy, fixed, label, description}
    """
    try:
        from datasets import load_dataset

        ds = load_dataset(
            "code_x_glue_cc_code_refinement",
            "small",
            split="test",
            trust_remote_code=True,
        )
        samples = []
        for i, row in enumerate(ds):
            if i >= max_samples:
                break
            samples.append(
                {
                    "id": f"cxg_{i:04d}",
                    "buggy": row.get("buggy", ""),
                    "fixed": row.get("fixed", ""),
                    "label": [],  # CodeXGLUE doesn't provide typed labels
                    "description": f"CodeXGLUE sample #{i}",
                }
            )
        return samples, "CodeXGLUE (code_x_glue_cc_code_refinement / small / test)"

    except Exception:
        # Dataset not available — use synthetic samples
        return (
            _SYNTHETIC_SAMPLES[:max_samples],
            "Synthetic fallback dataset (CodeXGLUE unavailable)",
        )


def run_evaluation(max_samples: int = 20) -> Dict:
    """
    Run scanner against loaded samples and compute metrics.

    Returns:
        Dict with samples, per_sample_results, aggregate_metrics, source.
    """
    samples, source = load_codexglue_samples(max_samples)
    per_sample_results = []

    all_tp, all_fp, all_fn = 0, 0, 0

    for sample in samples:
        buggy_code = sample["buggy"]
        ground_truth_labels = sample["label"]

        # Scan the buggy code
        file_info = {
            "content": buggy_code,
            "relative_path": f"{sample['id']}.py",
        }
        scan_result = scan_file(file_info)
        detected_issues = scan_result.get("issues", [])

        # Match detected vs ground truth
        detected_types = {issue["type"] for issue in detected_issues}
        gt_types = {gt["type"] for gt in ground_truth_labels}

        tp = len(detected_types & gt_types)
        fp = len(detected_types - gt_types)
        fn = len(gt_types - detected_types)

        all_tp += tp
        all_fp += fp
        all_fn += fn

        sample_metrics = compute_precision_recall_f1(tp, fp, fn)

        per_sample_results.append(
            {
                "id": sample["id"],
                "description": sample["description"],
                "buggy_snippet": buggy_code[:200],
                "ground_truth": ground_truth_labels,
                "detected": detected_issues,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "metrics": sample_metrics,
            }
        )

    aggregate = compute_precision_recall_f1(all_tp, all_fp, all_fn)

    return {
        "source": source,
        "samples_evaluated": len(samples),
        "aggregate_metrics": aggregate,
        "total_tp": all_tp,
        "total_fp": all_fp,
        "total_fn": all_fn,
        "per_sample_results": per_sample_results,
    }
