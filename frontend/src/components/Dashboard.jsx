import React from 'react'
import '../styles/Dashboard.css'

function Dashboard({ results }) {
  if (results) {
    return null // Show analysis instead
  }

  return (
    <div className="dashboard">
      <div className="welcome-section">
        <h2>Welcome to codeAID</h2>
        <p>Your AI-powered repository debugging and auto-repair assistant</p>
      </div>

      <div className="features-grid">
        <div className="feature-card">
          <div className="feature-icon">🔍</div>
          <h3>Smart Scanning</h3>
          <p>Detect code issues across multiple programming languages using advanced AST analysis</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🛠️</div>
          <h3>Auto-Repair</h3>
          <p>Automatically fix common issues like unused imports, syntax errors, and code style problems</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">✓</div>
          <h3>Verification</h3>
          <p>Verify that repairs compile correctly and don't introduce new issues</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">📊</div>
          <h3>Project Analysis</h3>
          <p>Understand your project architecture, dependencies, and design patterns</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🤖</div>
          <h3>AI-Enhanced</h3>
          <p>Get intelligent insights and detailed explanations powered by LLMs</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🌍</div>
          <h3>Multi-Language</h3>
          <p>Support for Python, JavaScript, Java, Go, Rust, Ruby, PHP, C#, and more</p>
        </div>
      </div>

      <div className="stats-section">
        <h3>Supported Languages</h3>
        <div className="language-list">
          <span className="lang-item">🐍 Python</span>
          <span className="lang-item">📜 JavaScript</span>
          <span className="lang-item">☕ Java</span>
          <span className="lang-item">🟦 C#</span>
          <span className="lang-item">🐹 Go</span>
          <span className="lang-item">🦀 Rust</span>
          <span className="lang-item">💎 Ruby</span>
          <span className="lang-item">🐘 PHP</span>
        </div>
      </div>

      <div className="quick-start">
        <h3>Quick Start</h3>
        <ol className="steps">
          <li><strong>Configure:</strong> Choose GitHub URL or upload files in the sidebar</li>
          <li><strong>Analyze:</strong> Click "Run Analysis" to scan your repository</li>
          <li><strong>Review:</strong> Check detected issues and suggested repairs</li>
          <li><strong>Export:</strong> Download the repaired project</li>
        </ol>
      </div>

      <div className="pipeline-section">
        <h3>Analysis Pipeline</h3>
        <div className="pipeline-steps">
          <div className="step">
            <div className="step-number">1</div>
            <div className="step-label">Load Repository</div>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">2</div>
            <div className="step-label">Scan & Detect</div>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">3</div>
            <div className="step-label">Auto-Repair</div>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">4</div>
            <div className="step-label">Verify</div>
          </div>
        </div>
        <div className="pipeline-steps" style={{ marginTop: '1rem' }}>
          <div className="step">
            <div className="step-number">5</div>
            <div className="step-label">Explain</div>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">6</div>
            <div className="step-label">Project Understanding</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
