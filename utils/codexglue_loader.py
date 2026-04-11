# ===== utils/codexglue_loader.py =====
"""
CodeXGLUE Evaluation Loader: Loads samples from the CodeXGLUE dataset
(code_x_glue_cc_code_refinement) and evaluates scanner performance.
Falls back to synthetic examples if the dataset is unavailable.
"""

from typing import Dict, List, Tuple

from utils.metrics import compute_precision_recall_f1
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
    {
        "id": "syn_009",
        "buggy": "import json\nimport time\nimport requests\n\ndef fetch_data():\n    # Getting API response\n    return None\n",
        "fixed": "import requests\n\ndef fetch_data():\n    # Getting API response\n    return None\n",
        "label": [{"line": 1, "type": "unused_import"}, {"line": 2, "type": "unused_import"}],
        "description": "Multiple unused imports in API handler",
    },
    {
        "id": "syn_010",
        "buggy": "def calculate(x, y, op='add'):    \n    if op == 'add':\n        return x + y\n    return x - y\n",
        "fixed": "def calculate(x, y, op='add'):\n    if op == 'add':\n        return x + y\n    return x - y\n",
        "label": [{"line": 1, "type": "trailing_whitespace"}],
        "description": "Trailing whitespace on function definition",
    },
    {
        "id": "syn_011",
        "buggy": "from typing import Dict, List, Optional, Set\n\ndata = [1, 2, 3]\nresult = [x for x in data]\nprint(result)\n",
        "fixed": "data = [1, 2, 3]\nresult = [x for x in data]\nprint(result)\n",
        "label": [{"line": 1, "type": "unused_import"}],
        "description": "Unused typing imports",
    },
    {
        "id": "syn_012",
        "buggy": "def helper():\n    pass\n\nclass Handler:\n    def __init__(self):\n        pass\n    # TODO: Implement error handling\n    def process(self, data):\n        return data\n",
        "fixed": "class Handler:\n    def __init__(self):\n        pass\n    def process(self, data):\n        return data\n",
        "label": [{"line": 1, "type": "unused_import"}, {"line": 7, "type": "todo_comment"}],
        "description": "Unused function and TODO comment",
    },
]


def load_codexglue_samples(max_samples: int = 20) -> Tuple[List[Dict], str]:
    """
    Load CodeXGLUE samples for evaluation.
    Prioritizes synthetic samples with proper issue labels for reliable metrics.
    The real CodeXGLUE dataset lacks labeled issues, so we primarily use synthetic.

    Args:
        max_samples: Maximum number of samples to load.

    Returns:
        (samples_list, source_description)
        Each sample: {id, buggy, fixed, label, description}
    """
    # For now, prefer synthetic samples as they have proper labeled issues
    # The real CodeXGLUE dataset is Java code without issue labels
    synthetic_samples = _SYNTHETIC_SAMPLES[:max_samples]
    
    # Try to augment with real CodeXGLUE if available and has labeled data
    try:
        from datasets import load_dataset

        ds = load_dataset(
            "code_x_glue_cc_code_refinement",
            "small",
            split="test",
            trust_remote_code=False,
        )
        
        real_samples = []
        for i, row in enumerate(ds):
            if i >= max_samples:
                break
            # Only include if there's meaningful labeled data or code differences
            label = row.get("label", [])
            buggy = row.get("buggy", "")
            fixed = row.get("fixed", "")
            
            # Skip if completely identical (no issue)
            if buggy.strip() == fixed.strip():
                continue
                
            real_samples.append(
                {
                    "id": f"cxg_{i:04d}",
                    "buggy": buggy,
                    "fixed": fixed,
                    "label": label if isinstance(label, list) else [],
                    "description": f"CodeXGLUE sample #{i}",
                }
            )
        
        # If we got real samples with actual code differences, use a mix
        if len(real_samples) >= 3:
            # Use 70% synthetic (with labels) + 30% real samples (code inference)
            mixed = synthetic_samples[:int(max_samples * 0.7)] + real_samples[:int(max_samples * 0.3)]
            return mixed[:max_samples], "Mixed: Synthetic (labeled) + CodeXGLUE (code-based)"
    
    except Exception:
        pass  # Fall back to synthetic if real failed
    
    # Return synthetic samples (they have proper issue labels)
    return (
        synthetic_samples,
        "Synthetic samples (Python code with labeled issues)",
    )


def _infer_ground_truth_from_code(code: str) -> List[Dict]:
    """
    Infer ground truth labels for repository code using pattern-based detection.
    
    This is used when evaluating actual repository files where explicit ground truth
    is not available. We detect common known issues using simple patterns.
    
    Args:
        code: Source code string
        
    Returns:
        List of inferred ground truth labels (similar to CodeXGLUE format)
    """
    import re
    
    labels = []
    lines = code.split('\n')
    
    # Pattern 1: Unused imports (basic detection)
    # Check for import statements that might not be used
    import_lines = {}
    for line_num, line in enumerate(lines, 1):
        if re.match(r'^\s*import\s+\w+', line) or re.match(r'^\s*from\s+\w+\s+import', line):
            # Extract imported names
            if 'import' in line:
                import_lines[line_num] = line.strip()
    
    # Simple heuristic: if import is far from any usage, it might be unused
    # For now, mark imports that appear in isolation as potentially unused
    for import_line_num, import_stmt in import_lines.items():
        # Extract imported module name
        match = re.search(r'(?:from\s+(\w+)|import\s+(\w+))', import_stmt)
        if match:
            module_name = match.group(1) or match.group(2)
            # Check if it's used in the rest of the code
            is_used = False
            for i, line in enumerate(lines):
                # Skip the import line itself
                if i + 1 == import_line_num:
                    continue
                if module_name in line and not line.strip().startswith('#'):
                    is_used = True
                    break
            
            if not is_used:
                labels.append({
                    "line": import_line_num,
                    "type": "unused_import"
                })
    
    # Pattern 2: Syntax errors (basic detection)
    # Check for unclosed brackets, etc.
    open_count = {'(': 0, '[': 0, '{': 0}
    close_count = {'(': 0, '[': 0, '{': 0}
    close_to_open = {')': '(', ']': '[', '}': '{'}
    
    for line_num, line in enumerate(lines, 1):
        # Remove strings and comments to avoid false positives
        line_no_str = re.sub(r'"[^"]*"', '', re.sub(r"'[^']*'", '', line))
        line_no_comment = re.sub(r'#.*', '', line_no_str)
        
        for char in line_no_comment:
            if char in open_count:
                open_count[char] += 1
            elif char in close_to_open:
                key = close_to_open[char]
                close_count[key] += 1
                if close_count[key] > open_count[key]:
                    # Too many closing brackets - potential syntax error
                    labels.append({
                        "line": line_num,
                        "type": "syntax_error"
                    })
                    break
    
    # Pattern 3: TODO/FIXME comments
    for line_num, line in enumerate(lines, 1):
        if re.search(r'#.*\b(TODO|FIXME|BUG|HACK|XXX)\b', line, re.IGNORECASE):
            labels.append({
                "line": line_num,
                "type": "todo_comment"
            })
    
    # Pattern 4: Trailing whitespace
    for line_num, line in enumerate(lines, 1):
        if line and line != line.rstrip():
            labels.append({
                "line": line_num,
                "type": "trailing_whitespace"
            })
    
    # Remove duplicates
    seen = set()
    unique_labels = []
    for label in labels:
        key = (label['line'], label['type'])
        if key not in seen:
            seen.add(key)
            unique_labels.append(label)
    
    return unique_labels


def run_evaluation(max_samples: int = 20, repo_files: List[Dict] = None) -> Dict:
    """
    Run scanner against ACTUAL REPOSITORY FILES if provided, with intelligent ground truth inference.
    Falls back to CodeXGLUE benchmarking samples if no repo files provided.

    Args:
        max_samples: Maximum number of samples to evaluate
        repo_files: List of repository files to evaluate.
                   If provided, evaluates ACTUAL repo files (not CodeXGLUE samples).
                   Metrics are based on detected issues vs known patterns.
                   If None, uses synthetic CodeXGLUE samples for benchmarking.

    Returns:
        Dict with samples, per_sample_results, aggregate_metrics, source.
    """
    # KEY FIX: If repo_files provided, evaluate THOSE, not CodeXGLUE samples
    if repo_files and len(repo_files) > 0:
        # REBUILD: Evaluate actual repository files
        samples = repo_files[:max_samples]
        source = f"Repository evaluation ({len(samples)} files)"
        evaluation_mode = "repository"
    else:
        # FALLBACK: Use CodeXGLUE benchmarking samples
        samples, base_source = load_codexglue_samples(max_samples)
        source = base_source
        evaluation_mode = "benchmarking"
    per_sample_results = []

    all_tp, all_fp, all_fn = 0, 0, 0
    issues_by_type = {}

    for idx, sample in enumerate(samples):
        # KEY FIX: Handle both CodeXGLUE samples and repository files
        if evaluation_mode == "benchmarking":
            # CodeXGLUE mode: samples have explicit ground truth labels
            buggy_code = sample["buggy"]
            ground_truth_labels = sample["label"]
            sample_id = sample.get("id", f"sample_{idx}")
            sample_desc = sample.get("description", f"CodeXGLUE sample {idx}")
        else:
            # Repository mode: use file content, infer ground truth from known patterns
            buggy_code = sample.get("content", "")
            sample_id = sample.get("relative_path", f"file_{idx}").split("/")[-1]
            sample_desc = f"Repository file: {sample.get('relative_path', 'unknown')}"
            
            # Infer ground truth from common known issues (pattern-based detection)
            ground_truth_labels = _infer_ground_truth_from_code(buggy_code)

        # Scan the buggy code
        file_info = {
            "content": buggy_code,
            "relative_path": sample_id if "." in sample_id else f"{sample_id}.py",
        }
        scan_result = scan_file(file_info)
        detected_issues = scan_result.get("issues", [])

        # Match detected vs ground truth (improved matching with type + line)
        detected_map = {}
        for issue in detected_issues:
            # Use the issue_type field from scanner
            issue_type = issue.get("issue_type") or issue.get("type", "unknown")
            issue_line = issue.get("line", -1)
            # Create key for matching (type + line)
            key = f"{issue_type}_{issue_line}"
            detected_map[key] = issue
        
        gt_map = {}
        for gt in ground_truth_labels:
            gt_type = gt.get("type", "unknown")
            gt_line = gt.get("line", -1)
            key = f"{gt_type}_{gt_line}"
            gt_map[key] = gt

        # Calculate TP, FP, FN with intersection-based matching
        detected_keys = set(detected_map.keys())
        gt_keys = set(gt_map.keys())
        
        tp = len(detected_keys & gt_keys)  # Both detected and in ground truth
        fp = len(detected_keys - gt_keys)  # Detected but not in ground truth (false positive)
        fn = len(gt_keys - detected_keys)  # In ground truth but not detected (false negative)

        all_tp += tp
        all_fp += fp
        all_fn += fn

        # Track issue types for per-type metrics
        for key in detected_keys:
            issue_type = key.split('_')[0]  # Extract type from composite key
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = {'detected': 0, 'correct': 0, 'missed': 0}
            issues_by_type[issue_type]['detected'] += 1
            if key in gt_keys:
                issues_by_type[issue_type]['correct'] += 1
        
        # Count missed detections
        for key in gt_keys:
            issue_type = key.split('_')[0]
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = {'detected': 0, 'correct': 0, 'missed': 0}
            if key not in detected_keys:
                issues_by_type[issue_type]['missed'] += 1

        sample_metrics = compute_precision_recall_f1(tp, fp, fn)

        per_sample_results.append(
            {
                "id": sample_id,
                "description": sample_desc,
                "buggy_snippet": buggy_code[:200],
                "ground_truth": ground_truth_labels,
                "detected": detected_issues,
                "matched_count": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "metrics": sample_metrics,
            }
        )

    aggregate = compute_precision_recall_f1(all_tp, all_fp, all_fn)

    # Compute per-type metrics
    per_type_metrics = {}
    for issue_type, stats in issues_by_type.items():
        detected = stats['detected']
        correct = stats['correct']
        missed = stats['missed']
        
        # Precision: correct / detected (0 if no detections)
        precision = (correct / detected * 100) if detected > 0 else 0.0
        # Recall: correct / (correct + missed) (0 if no ground truth)
        recall = (correct / (correct + missed) * 100) if (correct + missed) > 0 else 0.0
        # F1: harmonic mean of precision and recall
        f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        
        per_type_metrics[issue_type] = {
            'detected': detected,
            'correct': correct,
            'missed': missed,
            'precision': round(precision, 1),
            'recall': round(recall, 1),
            'f1': round(f1_score, 1),
        }

    return {
        "source": source,
        "samples_evaluated": len(samples),
        "aggregate_metrics": aggregate,
        "total_tp": all_tp,
        "total_fp": all_fp,
        "total_fn": all_fn,
        "per_sample_results": per_sample_results,
        "per_type_metrics": per_type_metrics,
        "evaluation_mode": evaluation_mode,  # "benchmarking" or "repository"
    }
