import React, { useState, useEffect } from 'react'
import '../styles/Evaluation.css'

function Evaluation({ results }) {
  const [expandedSample, setExpandedSample] = useState(null)

  // Debug: Log when component receives new results
  useEffect(() => {
    if (results) {
      console.log('Evaluation component received results:', {
        has_results: !!results,
        source: results.source,
        samples_evaluated: results.samples_evaluated,
        per_sample_results_count: Array.isArray(results.per_sample_results) ? results.per_sample_results.length : 0,
        has_aggregate_metrics: !!results.aggregate_metrics,
        aggregate_metrics_keys: results.aggregate_metrics ? Object.keys(results.aggregate_metrics) : [],
        total_tp: results.total_tp,
        total_fp: results.total_fp,
        total_fn: results.total_fn
      })
    }
  }, [results])

  if (!results) {
    return (
      <div className="empty-state">
        <p>No evaluation results yet. Run CodeXGLUE Eval from the sidebar to get started.</p>
      </div>
    )
  }

  const metrics = results.aggregate_metrics || {}
  const samples = Array.isArray(results.per_sample_results) ? results.per_sample_results : []
  const source = results.source || 'Unknown'

  const toggleSample = (id) => {
    setExpandedSample(expandedSample === id ? null : id)
  }

  return (
    <div className="evaluation-container">
      {/* Header */}
      <div className="eval-header">
        <h2>CodeXGLUE Evaluation Results</h2>
        <p className="eval-source">Dataset: {source}</p>
      </div>

      {/* Aggregate Metrics */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-icon">📊</div>
          <div className="metric-content">
            <div className="metric-value">
              {results.samples_evaluated || 0}
            </div>
            <div className="metric-label">Samples Evaluated</div>
          </div>
        </div>

        <div className="metric-card accent">
          <div className="metric-icon">🎯</div>
          <div className="metric-content">
            <div className="metric-value">
              {metrics.precision !== undefined ? (metrics.precision * 100).toFixed(1) : '0.0'}%
            </div>
            <div className="metric-label">Precision</div>
          </div>
        </div>

        <div className="metric-card accent">
          <div className="metric-icon">🔍</div>
          <div className="metric-content">
            <div className="metric-value">
              {metrics.recall !== undefined ? (metrics.recall * 100).toFixed(1) : '0.0'}%
            </div>
            <div className="metric-label">Recall</div>
          </div>
        </div>

        <div className="metric-card accent">
          <div className="metric-icon">⭐</div>
          <div className="metric-content">
            <div className="metric-value">
              {metrics.f1 !== undefined ? (metrics.f1 * 100).toFixed(1) : '0.0'}%
            </div>
            <div className="metric-label">F1 Score</div>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="summary-section">
        <h3>Detection Summary</h3>
        <div className="detection-stats">
          <div className="stat-box">
            <span className="stat-label">True Positives</span>
            <span className="stat-num success">{results.total_tp || 0}</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">False Positives</span>
            <span className="stat-num warning">{results.total_fp || 0}</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">False Negatives</span>
            <span className="stat-num danger">{results.total_fn || 0}</span>
          </div>
        </div>
      </div>

      {/* Performance Metrics Bars */}
      <div className="performance-section">
        <h3>Metric Breakdown</h3>
        <div className="metric-bars">
          <div className="metric-bar-item">
            <label>Precision</label>
            <div className="bar-container">
              <div
                className="bar-fill accent"
                style={{ width: `${(metrics.precision || 0) * 100}%` }}
              ></div>
            </div>
            <span className="bar-value">{((metrics.precision || 0) * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-bar-item">
            <label>Recall</label>
            <div className="bar-container">
              <div
                className="bar-fill info"
                style={{ width: `${(metrics.recall || 0) * 100}%` }}
              ></div>
            </div>
            <span className="bar-value">{((metrics.recall || 0) * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-bar-item">
            <label>F1 Score</label>
            <div className="bar-container">
              <div
                className="bar-fill success"
                style={{ width: `${(metrics.f1 || 0) * 100}%` }}
              ></div>
            </div>
            <span className="bar-value">{((metrics.f1 || 0) * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Per-Sample Results */}
      <div className="samples-section">
        <h3>Per-Sample Results ({samples.length} samples)</h3>
        <div className="samples-list">
          {samples && samples.length > 0 ? (
            samples.map((sample) => (
              <div
                key={sample.id}
                className={`sample-card ${expandedSample === sample.id ? 'expanded' : ''}`}
              >
                <button
                  className="sample-header"
                  onClick={() => toggleSample(sample.id)}
                >
                  <span className="sample-id">{sample.id}</span>
                  <span className="sample-description">{sample.description}</span>
                  <div className="sample-badges">
                    <span className={`badge tp`}>TP: {sample.tp || 0}</span>
                    <span className={`badge fp`}>FP: {sample.fp || 0}</span>
                    <span className={`badge fn`}>FN: {sample.fn || 0}</span>
                    <span className="sample-f1">F1: {sample.metrics && sample.metrics.f1 !== undefined ? (sample.metrics.f1 * 100).toFixed(0) : '0'}%</span>
                  </div>
                  <span className="expand-icon">{expandedSample === sample.id ? '▼' : '▶'}</span>
                </button>

                {expandedSample === sample.id && (
                  <div className="sample-details">
                    <div className="detail-section">
                      <h4>Buggy Code</h4>
                      <pre><code>{sample.buggy_snippet}...</code></pre>
                    </div>

                    <div className="detail-section">
                      <h4>Ground Truth ({sample.ground_truth ? sample.ground_truth.length : 0} issues)</h4>
                      {!sample.ground_truth || sample.ground_truth.length === 0 ? (
                        <p className="empty-detail">No issues expected</p>
                      ) : (
                        <ul className="issue-list">
                          {sample.ground_truth.map((issue, idx) => (
                            <li key={idx} className="issue-item">
                              Line {issue.line}: <strong>{issue.type}</strong>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div className="detail-section">
                      <h4>Detected Issues ({sample.detected ? sample.detected.length : 0} issues)</h4>
                      {!sample.detected || sample.detected.length === 0 ? (
                        <p className="empty-detail">No issues detected</p>
                      ) : (
                        <ul className="issue-list">
                          {sample.detected.map((issue, idx) => (
                            <li key={idx} className="issue-item detected">
                              Line {issue.line}: <strong>{issue.type || issue.issue_type}</strong>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div className="detail-section metrics-detail">
                      <h4>Metrics</h4>
                      <div className="metrics-grid-detail">
                        <div className="metric-detail-item">
                          <span className="label">Precision</span>
                          <span className="value">{sample.metrics ? (sample.metrics.precision * 100).toFixed(1) : '0.0'}%</span>
                        </div>
                        <div className="metric-detail-item">
                          <span className="label">Recall</span>
                          <span className="value">{sample.metrics ? (sample.metrics.recall * 100).toFixed(1) : '0.0'}%</span>
                        </div>
                        <div className="metric-detail-item">
                          <span className="label">F1 Score</span>
                          <span className="value">{sample.metrics ? (sample.metrics.f1 * 100).toFixed(1) : '0.0'}%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="empty-detail">
              <p>No samples to display</p>
            </div>
          )}
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="statistics-section">
        <h3>Evaluation Statistics</h3>
        <div className="stats-info">
          <p>
            The CodeXGLUE evaluation tests the scanner's ability to detect and classify code issues.
          </p>
          <ul className="stats-list">
            <li><strong>Precision:</strong> Of the issues detected, how many were correct?</li>
            <li><strong>Recall:</strong> Of the actual issues, how many did we detect?</li>
            <li><strong>F1 Score:</strong> Harmonic mean of precision and recall</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default Evaluation
