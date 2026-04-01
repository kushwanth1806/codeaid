"""
llm_agent.py
------------
Optional LLM-powered reasoning agent supporting multiple providers.

Supports: Anthropic Claude, OpenAI (GPT), and other compatible APIs.
If no API key is configured, the agent gracefully falls back to
rule-based summaries so the rest of the pipeline continues to work.

Environment Variables:
  LLM_PROVIDER: "anthropic", "openai", or others (default: "anthropic")
  ANTHROPIC_API_KEY: API key for Anthropic Claude
  OPENAI_API_KEY: API key for OpenAI
  LLM_MODEL: Override default model name (optional)

Public functions
----------------
  enrich_issues(issues, files)  → adds "llm_insight" to each issue dict
  analyze_project(summary)      → returns a string with high-level project advice
  is_llm_available()            → checks if LLM is configured and available
"""

import os
import json
import textwrap
from typing import List, Dict, Optional

# Try to import available LLM clients
try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

try:
    import openai
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

# Provider configurations
_PROVIDER_CONFIGS = {
    "anthropic": {
        "available": _HAS_ANTHROPIC,
        "default_model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "available": _HAS_OPENAI,
        "default_model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
}

def _get_provider() -> str:
    """Get the configured LLM provider."""
    return os.environ.get("LLM_PROVIDER", "anthropic").lower()

def _get_api_key() -> Optional[str]:
    """Get the API key for the current provider."""
    provider = _get_provider()
    config = _PROVIDER_CONFIGS.get(provider, {})
    api_key_env = config.get("api_key_env")
    return os.environ.get(api_key_env) if api_key_env else None

def _get_model() -> str:
    """Get the model name for the current provider."""
    custom = os.environ.get("LLM_MODEL")
    if custom:
        return custom
    provider = _get_provider()
    config = _PROVIDER_CONFIGS.get(provider, {})
    return config.get("default_model", "gpt-4o-mini")

_MAX_TOKENS = 512
_ISSUES_PER_BATCH = 5   # send at most this many issues per API call


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_issues(issues: List[Dict], files: List[Dict]) -> List[Dict]:
    """
    Add an "llm_insight" field to each issue with deeper reasoning.

    Falls back to a rule-based stub if no API key is available.
    """
    if not is_llm_available():
        for issue in issues:
            issue["llm_insight"] = _fallback_insight(issue)
        return issues

    file_map = {f["path"]: f["source"] for f in files}

    for i in range(0, len(issues), _ISSUES_PER_BATCH):
        batch = issues[i: i + _ISSUES_PER_BATCH]
        _enrich_batch(batch, file_map)

    return issues


def analyze_project(summary: Dict) -> str:
    """
    Ask the LLM for high-level architectural advice given the project summary.

    Falls back to a rule-based paragraph if no API key is available.
    """
    if not is_llm_available():
        return _fallback_project_analysis(summary)

    prompt = _build_project_prompt(summary)

    try:
        response = _call_llm(prompt)
        return response if response else _fallback_project_analysis(summary)
    except Exception as exc:
        return f"LLM analysis unavailable: {exc}\n\n" + _fallback_project_analysis(summary)


def is_llm_available() -> bool:
    """Check if LLM is available and configured."""
    provider = _get_provider()
    config = _PROVIDER_CONFIGS.get(provider, {})
    
    # Check if provider is installed
    if not config.get("available"):
        return False
    
    # Check if API key is set
    return bool(_get_api_key())


def llm_analyze_architecture(project_summary_text: str) -> str:
    """
    Ask the LLM for architectural analysis given project summary text.
    
    Falls back to a rule-based response if API is unavailable.
    """
    if not is_llm_available():
        return "LLM analysis not available. Configure LLM_PROVIDER and API key to enable."

    prompt = (
        f"Analyze the following project summary and provide high-level architectural advice:\n\n"
        f"{project_summary_text}"
    )

    try:
        return _call_llm(prompt)
    except Exception as exc:
        return f"LLM analysis failed: {exc}"


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _call_llm(prompt: str) -> str:
    """
    Call the configured LLM provider with the given prompt.
    
    Returns the text response from the LLM.
    """
    provider = _get_provider()
    api_key = _get_api_key()
    model = _get_model()
    
    if provider == "openai":
        return _call_openai(prompt, api_key, model)
    else:
        # Default to Anthropic
        return _call_anthropic(prompt, api_key, model)


def _call_anthropic(prompt: str, api_key: str, model: str) -> str:
    """Call Anthropic Claude API."""
    if not _HAS_ANTHROPIC:
        raise RuntimeError("anthropic library not installed. Install with: pip install anthropic")
    
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _call_openai(prompt: str, api_key: str, model: str) -> str:
    """Call OpenAI API."""
    if not _HAS_OPENAI:
        raise RuntimeError("openai library not installed. Install with: pip install openai")
    
    client = openai.OpenAI(api_key=api_key)
    message = client.chat.completions.create(
        model=model,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.choices[0].message.content.strip()


def _enrich_batch(batch: List[Dict], file_map: Dict[str, str]) -> None:
    """Send one batch of issues to the LLM and write insights back in place."""
    items = []
    for issue in batch:
        snippet = _get_snippet(file_map.get(issue["file"], ""), issue["line"])
        items.append({
            "issue_type": issue["issue_type"],
            "description": issue["description"],
            "file": issue["file"],
            "line": issue["line"],
            "snippet": snippet,
        })

    prompt = (
        "You are a senior Python code reviewer. "
        "For each issue below provide ONE concise sentence of actionable insight "
        "(max 40 words each). Respond ONLY with a JSON array of strings, one per issue.\n\n"
        + json.dumps(items, indent=2)
    )

    try:
        response = _call_llm(prompt)
        # Strip markdown fences if present
        raw = response.strip("```json").strip("```").strip()
        insights = json.loads(raw)
        for issue, insight in zip(batch, insights):
            issue["llm_insight"] = str(insight)
    except Exception as exc:
        for issue in batch:
            issue["llm_insight"] = _fallback_insight(issue)


def _get_snippet(source: str, lineno: int, context: int = 3) -> str:
    """Return up to *context* lines around *lineno* from *source*."""
    if not source or lineno < 1:
        return ""
    lines = source.splitlines()
    start = max(0, lineno - 1 - context)
    end = min(len(lines), lineno + context)
    return "\n".join(lines[start:end])


def _build_project_prompt(summary: Dict) -> str:
    return textwrap.dedent(f"""
        You are a senior software architect reviewing a Python project.
        Project summary:
        {json.dumps(summary, indent=2, default=str)}

        In 3-4 sentences, give concise, actionable architectural advice
        for the developers. Focus on the most impactful improvements.
    """).strip()


def _fallback_insight(issue: Dict) -> str:
    """Rule-based single-sentence insight (no LLM needed)."""
    tips = {
        "syntax_error":    "Fix the syntax error immediately; the file cannot be imported.",
        "unused_import":   "Remove this import to keep dependencies explicit and load time low.",
        "long_function":   "Break this function into smaller helpers to improve testability.",
        "too_many_params": "Group parameters into a dataclass or config object.",
        "todo_comment":    "Track this in your issue tracker instead of leaving it in source.",
    }
    return tips.get(issue["issue_type"], "Review and refactor this code section.")


def _fallback_project_analysis(summary: Dict) -> str:
    lines = ["Rule-based project analysis (LLM not configured):"]
    fc = summary.get("file_count", 0)
    tl = summary.get("total_lines", 0)
    if fc > 20:
        lines.append("• Large codebase — ensure you have a clear module boundary strategy.")
    if tl / max(fc, 1) > 200:
        lines.append("• Average file length is high — consider splitting large files.")
    lines.append("• Add type hints throughout for better IDE support and self-documentation.")
    lines.append("• Ensure every public function has a docstring.")
    return "\n".join(lines)
