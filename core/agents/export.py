"""
export.py
---------
Project export and download functionality.

Allows users to download repaired projects and artifacts.
"""

import os
import shutil
import zipfile
import io
from pathlib import Path
from typing import Dict, List, Tuple, BinaryIO
from datetime import datetime


def export_repaired_project(
    repo_path: str,
    files: List[Dict],
    issues: List[Dict],
    repairs_applied: List[Dict],
    export_format: str = "zip"
) -> Tuple[BinaryIO, str]:
    """
    Create an exportable package of the repaired project.
    
    Parameters
    ----------
    repo_path : str
        Path to original repository
    files : List[Dict]
        Current (repaired) files with {"path": str, "source": str}
    issues : List[Dict]
        Detected issues
    repairs_applied : List[Dict]
        Applied repairs
    export_format : str
        "zip" or "tar.gz"
    
    Returns
    -------
    Tuple of (file_buffer, filename)
        file_buffer: BytesIO object with compressed data
        filename: suggested filename for download
    """
    if export_format == "zip":
        return _create_zip_export(repo_path, files, issues, repairs_applied)
    else:
        raise ValueError(f"Unsupported export format: {export_format}")


def _create_zip_export(
    repo_path: str,
    files: List[Dict],
    issues: List[Dict],
    repairs_applied: List[Dict]
) -> Tuple[BinaryIO, str]:
    """
    Create a ZIP file with repaired project.
    
    Returns
    -------
    Tuple of (BytesIO buffer, filename)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"codeaid-repaired_{timestamp}.zip"
    
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add source files
        for file_dict in files:
            path = file_dict.get("path", "")
            source = file_dict.get("source", "")
            
            # Add to ZIP
            zf.writestr(path, source)
        
        # Add metadata JSON
        import json
        metadata = {
            "exported_at": datetime.now().isoformat(),
            "total_files": len(files),
            "total_issues": len(issues),
            "repairs_applied": len(repairs_applied),
            "issues_summary": _summarize_issues(issues),
            "repairs_summary": _summarize_repairs(repairs_applied),
        }
        zf.writestr("CODEAID_REPORT.json", json.dumps(metadata, indent=2))
        
        # Add readable report
        report_text = _generate_report(metadata, issues, repairs_applied)
        zf.writestr("CODEAID_REPORT.md", report_text)
    
    buffer.seek(0)
    return buffer, filename


def _summarize_issues(issues: List[Dict]) -> Dict:
    """Summarize issues by type and severity."""
    by_type = {}
    by_severity = {}
    
    for issue in issues:
        issue_type = issue.get("issue_type", "unknown")
        severity = issue.get("severity", "info")
        
        by_type[issue_type] = by_type.get(issue_type, 0) + 1
        by_severity[severity] = by_severity.get(severity, 0) + 1
    
    return {"by_type": by_type, "by_severity": by_severity, "total": len(issues)}


def _summarize_repairs(repairs: List[Dict]) -> Dict:
    """Summarize repair results."""
    fixed = len([r for r in repairs if r.get("status") == "fixed"])
    skipped = len([r for r in repairs if r.get("status") == "skipped"])
    failed = len([r for r in repairs if r.get("status") == "failed"])
    
    return {
        "fixed": fixed,
        "skipped": skipped,
        "failed": failed,
        "total": len(repairs)
    }


def _generate_report(metadata: Dict, issues: List[Dict], repairs: List[Dict]) -> str:
    """Generate a markdown report of analysis and repairs."""
    lines = [
        "# CodeAid Analysis Report",
        f"\n**Generated:** {metadata['exported_at']}\n",
        "## Summary",
        f"- **Total Files:** {metadata['total_files']}",
        f"- **Total Issues Found:** {metadata['total_issues']}",
        f"- **Repairs Applied:** {metadata['repairs_applied']}",
        "\n## Issues Detected",
        f"### By Type",
    ]
    
    for issue_type, count in metadata['issues_summary'].get('by_type', {}).items():
        lines.append(f"- `{issue_type}`: {count}")
    
    lines.extend(["\n### By Severity"])
    for severity, count in metadata['issues_summary'].get('by_severity', {}).items():
        lines.append(f"- **{severity}**: {count}")
    
    lines.extend(["\n## Repairs Applied"])
    repair_summary = metadata['repairs_summary']
    lines.append(f"- **Fixed:** {repair_summary['fixed']}")
    lines.append(f"- **Skipped:** {repair_summary['skipped']}")
    lines.append(f"- **Failed:** {repair_summary['failed']}")
    
    lines.extend([
        "\n## Details",
        "\n### Issue Details",
    ])
    
    # Group issues by file
    issues_by_file = {}
    for issue in issues:
        file_path = issue.get("file", "unknown")
        if file_path not in issues_by_file:
            issues_by_file[file_path] = []
        issues_by_file[file_path].append(issue)
    
    for file_path in sorted(issues_by_file.keys()):
        lines.append(f"\n#### `{file_path}`")
        for issue in issues_by_file[file_path]:
            severity = issue.get("severity", "info").upper()
            line_no = issue.get("line", -1)
            desc = issue.get("description", "No description")
            lines.append(f"- **Line {line_no}** [{severity}]: {desc}")
    
    lines.extend([
        "\n### Repairs Details",
    ])
    
    for repair in repairs:
        if repair.get("status") == "fixed":
            file_path = repair.get("file", "unknown")
            line_no = repair.get("line", -1)
            detail = repair.get("detail", "")
            lines.append(f"- ✅ `{file_path}:{line_no}` - {detail}")
        elif repair.get("status") == "skipped":
            file_path = repair.get("file", "unknown")
            detail = repair.get("detail", "")
            lines.append(f"- ⏭️  `{file_path}` - {detail}")
        elif repair.get("status") == "failed":
            file_path = repair.get("file", "unknown")
            detail = repair.get("detail", "")
            lines.append(f"- ❌ `{file_path}` - {detail}")
    
    lines.extend([
        "\n---",
        "*Report generated by CodeAid - AI Repository Debugger*"
    ])
    
    return "\n".join(lines)


def create_project_archive(
    files: List[Dict],
    project_name: str = "project",
    format: str = "zip"
) -> Tuple[BinaryIO, str]:
    """
    Create an archive of project files.
    
    Parameters
    ----------
    files : List[Dict]
        Files with {"path": str, "source": str}
    project_name : str
        Name for the project
    format : str
        "zip" or "tar"
    
    Returns
    -------
    Tuple of (buffer, filename)
    """
    if format != "zip":
        raise ValueError(f"Unsupported format: {format}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{project_name}_{timestamp}.zip"
    
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_dict in files:
            path = file_dict.get("path", "")
            source = file_dict.get("source", "")
            zf.writestr(path, source)
    
    buffer.seek(0)
    return buffer, filename
