import React, { useState } from 'react'
import '../styles/Analysis.css'

function Analysis({ results, onViewOverview }) {
  const [expandedFiles, setExpandedFiles] = useState({})
  const [expandedRepairs, setExpandedRepairs] = useState({})
  const [copiedId, setCopiedId] = useState(null)

  const copyToClipboard = (text, elementId, event) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(elementId)
      if (event?.target) {
        const btn = event.target
        const originalText = btn.textContent
        btn.textContent = '✓ Copied!'
        setTimeout(() => {
          btn.textContent = originalText
          setCopiedId(null)
        }, 2000)
      }
    }).catch(err => {
      console.error('Failed to copy:', err)
    })
  }

  const toggleFile = (file) => {
    setExpandedFiles(prev => ({
      ...prev,
      [file]: !prev[file]
    }))
  }

  const toggleRepair = (idx) => {
    setExpandedRepairs(prev => ({
      ...prev,
      [idx]: !prev[idx]
    }))
  }

  const stages = results.stages || {}
  const scan = stages.scan || {}
  const repair = stages.repair || {}
  const issues = scan.results || []
  const repairs = repair.results || []
  const source = results.source || 'Unknown'

  // Group issues by file
  const issuesByFile = {}
  issues.forEach(issue => {
    const file = issue.relative_path || issue.file || 'unknown'
    if (!issuesByFile[file]) {
      issuesByFile[file] = []
    }
    issuesByFile[file].push(issue)
  })

  // Count severity
  const severityCounts = {
    error: issues.filter(i => i.severity === 'error').length,
    warning: issues.filter(i => i.severity === 'warning').length,
    info: issues.filter(i => i.severity === 'info').length,
  }

  const getSeverityClass = (severity) => {
    return `severity-${severity || 'info'}`
  }

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'error':
        return '🔴'
      case 'warning':
        return '🟡'
      case 'info':
        return '🔵'
      default:
        return '⚪'
    }
  }

  return (
    <div className="analysis-container">
      {/* Navigation and Summary */}
      <div className="analysis-top-bar">
        <h1>Analysis Results</h1>
        {onViewOverview && (
          <button className="overview-btn" onClick={onViewOverview}>
            📊 View Project Overview
          </button>
        )}
      </div>

      {/* Summary Cards */}
      <div className="summary-cards">
        <div className="summary-card">
          <div className="card-value">{results.stages?.load?.python_file_count || 0}</div>
          <div className="card-label">Python Files</div>
        </div>
        <div className="summary-card">
          <div className="card-value">{results.stages?.load?.all_source_file_count || 0}</div>
          <div className="card-label">Source Files</div>
        </div>
        <div className="summary-card">
          <div className="card-value">{issues.length}</div>
          <div className="card-label">Issues Found</div>
        </div>
        <div className="summary-card accent">
          <div className="card-value">{repairs.filter(r => r.status === 'fixed').length}</div>
          <div className="card-label">Issues Fixed</div>
        </div>
      </div>

      {/* Severity Summary */}
      {issues.length > 0 && (
        <div className="severity-summary">
          <div className="severity-item error">
            <span className="severity-icon">🔴</span>
            <span className="severity-count">{severityCounts.error}</span>
            <span className="severity-label">Errors</span>
          </div>
          <div className="severity-item warning">
            <span className="severity-icon">🟡</span>
            <span className="severity-count">{severityCounts.warning}</span>
            <span className="severity-label">Warnings</span>
          </div>
          <div className="severity-item info">
            <span className="severity-icon">🔵</span>
            <span className="severity-count">{severityCounts.info}</span>
            <span className="severity-label">Info</span>
          </div>
        </div>
      )}

      {/* Issues Section */}
      <div className="analysis-section">
        <h2>Detected Issues</h2>
        {Object.entries(issuesByFile).length === 0 ? (
          <div className="empty-message">
            <p>✓ No issues detected!</p>
          </div>
        ) : (
          Object.entries(issuesByFile).map(([file, fileIssues]) => (
            <div key={file} className="file-group">
              <button
                className="file-header"
                onClick={() => toggleFile(file)}
              >
                <span className="file-icon">📄</span>
                <span className="file-name">{file}</span>
                <span className="issue-count">{fileIssues.length} issue(s)</span>
                <span className="expand-icon">{expandedFiles[file] ? '▼' : '▶'}</span>
              </button>

              {expandedFiles[file] && (
                <div className="file-issues">
                  {fileIssues.map((issue, idx) => (
                    <div key={idx} className={`issue-card ${getSeverityClass(issue.severity)}`}>
                      <div className="issue-header">
                        <div className="issue-main">
                          <span className="severity-badge">{getSeverityIcon(issue.severity)} {issue.severity?.toUpperCase()}</span>
                          <span className="issue-type">{issue.issue_type || issue.type || 'Unknown'}</span>
                          <span className="issue-line">Line {issue.line || '?'}</span>
                        </div>
                        {issue.fixable && <span className="badge-success">Fixable</span>}
                      </div>
                      <p className="issue-message">{issue.message || issue.description || 'No description'}</p>
                      {issue.detail && <p className="issue-detail">{issue.detail}</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Repairs Section */}
      {repairs.length > 0 && (
        <div className="analysis-section">
          <h2>Repair Results</h2>
          <div className="repair-stats">
            <div className="stat">
              <span className="stat-label">Fixed</span>
              <span className="stat-value success">{repairs.filter(r => r.status === 'fixed').length}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Skipped</span>
              <span className="stat-value warning">{repairs.filter(r => r.status === 'skipped').length}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Failed</span>
              <span className="stat-value danger">{repairs.filter(r => r.status === 'failed').length}</span>
            </div>
          </div>

          {repairs.map((repair, idx) => (
            <div key={idx} className={`repair-card status-${repair.status}`}>
              <button
                className="repair-header"
                onClick={() => toggleRepair(idx)}
              >
                <div className="repair-main">
                  <span className={`repair-status status-${repair.status}`}>{repair.status.toUpperCase()}</span>
                  <span className="repair-file">{repair.relative_path || repair.file}</span>
                  <span className="repair-line">Line {repair.line}</span>
                </div>
                <span className="expand-icon">{expandedRepairs[idx] ? '▼' : '▶'}</span>
              </button>
              <p className="repair-message">{repair.detail || repair.message || 'No description'}</p>
              
              {expandedRepairs[idx] && repair.status === 'fixed' && (
                <div className="code-comparison">
                  {repair.original_snippet && (
                    <div className="code-block original">
                      <div className="code-header">
                        <div className="code-label">Original Code</div>
                        <button 
                          className="copy-btn" 
                          onClick={(e) => copyToClipboard(repair.original_snippet, `original-${idx}`, e)}
                          title="Copy original code"
                        >
                          📋 Copy
                        </button>
                      </div>
                      <pre><code id={`original-${idx}`}>{repair.original_snippet}</code></pre>
                    </div>
                  )}
                  {repair.fixed_snippet && (
                    <div className="code-block fixed">
                      <div className="code-header">
                        <div className="code-label">Fixed Code ✓</div>
                        <button 
                          className="copy-btn" 
                          onClick={(e) => copyToClipboard(repair.fixed_snippet, `fixed-${idx}`, e)}
                          title="Copy fixed code"
                        >
                          📋 Copy
                        </button>
                      </div>
                      <pre><code id={`fixed-${idx}`}>{repair.fixed_snippet}</code></pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Timings Section */}
      <div className="analysis-section">
        <h2>Performance Metrics</h2>
        <div className="timings-grid">
          {results.timings && Object.entries(results.timings).map(([stage, time]) => (
            <div key={stage} className="timing-card">
              <span className="timing-label">{stage}</span>
              <span className="timing-value">{time}s</span>
            </div>
          ))}
        </div>
      </div>

      {/* Error Messages */}
      {results.errors && results.errors.length > 0 && (
        <div className="analysis-section">
          <h2>Errors</h2>
          {results.errors.map((error, idx) => (
            <div key={idx} className="error-message">
              <span className="error-icon">⚠️</span>
              <span>{error}</span>
            </div>
          ))}
        </div>
      )}

      {/* Source Information */}
      <div className="source-info">
        <p><strong>Source:</strong> {source}</p>
        <p><strong>LLM Used:</strong> {results.llm_available ? 'Yes' : 'No'}</p>
      </div>
    </div>
  )
}

export default Analysis
