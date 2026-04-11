import React, { useState, useEffect } from 'react'
import '../styles/Overview.css'

function Overview({ results }) {
  const [overview, setOverview] = useState(null)
  const [issuesSummary, setIssuesSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedSections, setExpandedSections] = useState({
    architecture: true,
    dependencies: true,
    quality: true,
    insights: true,
  })

  useEffect(() => {
    if (results) {
      fetchOverviewData()
    }
  }, [results])

  const fetchOverviewData = async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch overview
      const overviewRes = await fetch('/api/overview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ results })
      })
      const overviewData = await overviewRes.json()
      setOverview(overviewData)

      // Fetch issues summary
      const issuesRes = await fetch('/api/issues/summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ results })
      })
      const issuesData = await issuesRes.json()
      setIssuesSummary(issuesData)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  const getHealthColor = (score) => {
    if (score >= 80) return '#48bb78'  // Green
    if (score >= 60) return '#ed8936'  // Orange
    return '#f56565'  // Red
  }

  if (loading) {
    return <div className="loading">Loading project overview...</div>
  }

  if (error) {
    return <div className="error-message">Error: {error}</div>
  }

  if (!overview) {
    return <div className="empty-state">No overview data available.</div>
  }

  return (
    <div className="overview-container">
      {/* Project Header */}
      <div className="overview-header">
        <h1>📊 Project Overview</h1>
        <p className="project-type">{overview.project_type || 'Unknown Project Type'}</p>
        {overview.summary && <p className="project-summary">{overview.summary}</p>}
        
        {/* Health Score */}
        {typeof overview.health_score === 'number' && (
          <div className="health-indicator">
            <div className="health-bar">
              <div 
                className="health-fill" 
                style={{ width: `${overview.health_score}%`, backgroundColor: getHealthColor(overview.health_score) }}
              ></div>
            </div>
            <span className="health-label">Health Score: {overview.health_score}/100</span>
          </div>
        )}
      </div>

      {/* Statistics Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">📁</div>
          <div className="stat-info">
            <div className="stat-value">{overview.statistics?.total_files || 0}</div>
            <div className="stat-label">Total Files</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🐍</div>
          <div className="stat-info">
            <div className="stat-value">{overview.statistics?.python_files || 0}</div>
            <div className="stat-label">Python Files</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💾</div>
          <div className="stat-info">
            <div className="stat-value">{overview.statistics?.source_files || 0}</div>
            <div className="stat-label">Source Files</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📦</div>
          <div className="stat-info">
            <div className="stat-value">{overview.statistics?.dependencies?.declared || 0}</div>
            <div className="stat-label">Dependencies</div>
          </div>
        </div>
      </div>

      {/* Repository Statistics Table */}
      {overview.statistics?.file_stats && (
        <div className="section">
          <h2>📈 Repository Statistics</h2>
          <table className="stats-table">
            <tbody>
              <tr>
                <td className="stat-key">Total Files</td>
                <td className="stat-value">{overview.statistics?.file_stats?.total_files || 0}</td>
              </tr>
              <tr>
                <td className="stat-key">Python Files</td>
                <td className="stat-value">{overview.statistics?.file_stats?.python_files || 0}</td>
              </tr>
              <tr>
                <td className="stat-key">Test Files</td>
                <td className="stat-value">{overview.statistics?.file_stats?.test_files || 0}</td>
              </tr>
              <tr>
                <td className="stat-key">Configuration Files</td>
                <td className="stat-value">{overview.statistics?.file_stats?.config_files || 0}</td>
              </tr>
              <tr>
                <td className="stat-key">Documentation Files</td>
                <td className="stat-value">{overview.statistics?.file_stats?.doc_files || 0}</td>
              </tr>
              <tr>
                <td className="stat-key">Total Lines of Code</td>
                <td className="stat-value">{overview.statistics?.file_stats?.total_lines || 0}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Issues Summary */}
      {issuesSummary && (
        <div className="section">
          <h2>🔍 Issues Overview</h2>
          <div className="severity-grid">
            <div className="severity-card error">
              <div className="severity-count">{issuesSummary.by_severity?.errors || 0}</div>
              <div className="severity-label">Errors</div>
            </div>
            <div className="severity-card warning">
              <div className="severity-count">{issuesSummary.by_severity?.warnings || 0}</div>
              <div className="severity-label">Warnings</div>
            </div>
            <div className="severity-card info">
              <div className="severity-count">{issuesSummary.by_severity?.info || 0}</div>
              <div className="severity-label">Info</div>
            </div>
            <div className="severity-card total">
              <div className="severity-count">{issuesSummary.total_issues || 0}</div>
              <div className="severity-label">Total</div>
            </div>
          </div>

          {/* Critical Files */}
          {issuesSummary.critical_files && issuesSummary.critical_files.length > 0 && (
            <div className="critical-files">
              <h3>Files with Most Issues</h3>
              <div className="files-list">
                {issuesSummary.critical_files.map(([file, issues], idx) => (
                  <div key={idx} className="file-item">
                    <span className="file-icon">📄</span>
                    <span className="file-name">{file}</span>
                    <span className="issue-badge">{issues.length} issue{issues.length !== 1 ? 's' : ''}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Architecture Assessment */}
      {overview.architecture && (
        <div className="section">
          <button
            className="section-header"
            onClick={() => toggleSection('architecture')}
          >
            <span>🏗️ Architecture Assessment</span>
            <span className="expand-icon">{expandedSections.architecture ? '▼' : '▶'}</span>
          </button>
          {expandedSections.architecture && (
            <div className="section-content">
              <div className="architecture-style">
                <h3>Architecture Style</h3>
                <p className="style-value">{overview.architecture.style || 'Unknown'}</p>
                {overview.architecture.description && (
                  <div className="architecture-description">
                    {overview.architecture.description.split('\n').map((line, idx) => (
                      <p key={idx}>{line}</p>
                    ))}
                  </div>
                )}
              </div>

              {overview.architecture.positives && overview.architecture.positives.length > 0 && (
                <div className="architecture-positives">
                  <h3>✓ Strengths</h3>
                  <ul>
                    {overview.architecture.positives.map((pos, idx) => (
                      <li key={idx}>{pos}</li>
                    ))}
                  </ul>
                </div>
              )}

              {overview.architecture.issues && overview.architecture.issues.length > 0 && (
                <div className="architecture-issues">
                  <h3>⚠️ Areas for Improvement</h3>
                  <ul>
                    {overview.architecture.issues.map((issue, idx) => (
                      <li key={idx}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Code Quality */}
      {overview.code_quality && Object.keys(overview.code_quality).length > 0 && (
        <div className="section">
          <button
            className="section-header"
            onClick={() => toggleSection('quality')}
          >
            <span>⚡ Code Quality Metrics</span>
            <span className="expand-icon">{expandedSections.quality ? '▼' : '▶'}</span>
          </button>
          {expandedSections.quality && (
            <div className="section-content">
              <div className="quality-grid">
                {Object.entries(overview.code_quality).map(([key, value]) => (
                  <div key={key} className="quality-item">
                    <span className="quality-label">{key.replace(/_/g, ' ')}</span>
                    <span className={`quality-value ${value === true ? 'yes' : 'no'}`}>
                      {value === true ? '✓ Yes' : value === false ? '✗ No' : value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Dependencies */}
      {overview.dependencies && overview.dependencies.length > 0 && (
        <div className="section">
          <button
            className="section-header"
            onClick={() => toggleSection('dependencies')}
          >
            <span>📦 Dependencies ({overview.dependencies.length})</span>
            <span className="expand-icon">{expandedSections.dependencies ? '▼' : '▶'}</span>
          </button>
          {expandedSections.dependencies && (
            <div className="section-content">
              <div className="dependencies-grid">
                {overview.dependencies.map((dep, idx) => (
                  <div key={idx} className="dependency-tag">{dep}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Patterns */}
      {overview.patterns && (Object.keys(overview.patterns).length > 0) && (
        <div className="section">
          <h2>🎯 Code Patterns</h2>
          {overview.patterns.good_patterns && overview.patterns.good_patterns.length > 0 && (
            <div className="patterns-section">
              <h3>✨ Good Patterns</h3>
              <ul className="patterns-list">
                {overview.patterns.good_patterns.map((pattern, idx) => (
                  <li key={idx} className="good-pattern">{pattern}</li>
                ))}
              </ul>
            </div>
          )}
          {overview.patterns.anti_patterns && overview.patterns.anti_patterns.length > 0 && (
            <div className="patterns-section">
              <h3>⚠️ Anti-patterns</h3>
              <ul className="patterns-list">
                {overview.patterns.anti_patterns.map((pattern, idx) => (
                  <li key={idx} className="anti-pattern">{pattern}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* AI Insights */}
      {overview.llm_advice && (
        <div className="section llm-advice">
          <button
            className="section-header"
            onClick={() => toggleSection('insights')}
          >
            <span>💡 AI Insights & Recommendations</span>
            <span className="expand-icon">{expandedSections.insights ? '▼' : '▶'}</span>
          </button>
          {expandedSections.insights && (
            <div className="section-content">
              <div className="advice-text">
                {overview.llm_advice.split('\n').map((line, idx) => (
                  line.trim() ? <p key={idx}>{line}</p> : <br key={idx} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Overview
