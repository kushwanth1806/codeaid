import React, { useState } from 'react'
import '../styles/Sidebar.css'

function Sidebar({ onViewChange, currentView, onAnalyze, onEvaluation, onConfigLlm, config, loading }) {
  const [inputMode, setInputMode] = useState('github')
  const [githubUrl, setGithubUrl] = useState('')
  const [selectedFiles, setSelectedFiles] = useState([])
  const [useLlm, setUseLlm] = useState(config.apiKeyConfigured)
  const [llmProvider, setLlmProvider] = useState(config.llmProvider)
  const [apiKey, setApiKey] = useState('')
  const [showLlmConfig, setShowLlmConfig] = useState(false)

  const handleAnalyzeClick = () => {
    if (inputMode === 'github') {
      if (!githubUrl.trim()) {
        alert('Please enter a GitHub URL')
        return
      }
      onAnalyze(githubUrl.trim(), false, useLlm)
    } else if (selectedFiles.length > 0) {
      onAnalyze(selectedFiles[0], true, useLlm)
    } else {
      alert('Please select files to upload')
    }
  }

  const handleFileSelect = (e) => {
    setSelectedFiles(Array.from(e.target.files))
  }

  const handleLlmConfigSubmit = () => {
    onConfigLlm(llmProvider, apiKey)
    setShowLlmConfig(false)
    setApiKey('')
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-section">
          <h1>codeAID</h1>
          <p>AI Repository Debugger</p>
        </div>
      </div>

      <div className="sidebar-content">
        {/* Configuration Section */}
        <div className="sidebar-section">
          <h3 className="section-title">Configuration</h3>
          
          <div className="input-group">
            <label className="radio-label">
              <input
                type="radio"
                name="input_mode"
                value="github"
                checked={inputMode === 'github'}
                onChange={(e) => setInputMode(e.target.value)}
              />
              GitHub URL
            </label>
            <label className="radio-label">
              <input
                type="radio"
                name="input_mode"
                value="upload"
                checked={inputMode === 'upload'}
                onChange={(e) => setInputMode(e.target.value)}
              />
              ZIP Upload
            </label>
          </div>

          {inputMode === 'github' ? (
            <input
              type="text"
              className="input-field"
              placeholder="https://github.com/username/repo"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              disabled={loading}
            />
          ) : (
            <div className="upload-area">
              <label htmlFor="file-input" className="upload-label">
                <span>📁 Click to select files</span>
                <p>ZIP or source code files</p>
              </label>
              <input
                id="file-input"
                type="file"
                multiple
                accept=".zip,.py,.js,.ts,.jsx,.tsx,.java,.go,.rs,.rb,.php,.cs"
                onChange={handleFileSelect}
                disabled={loading}
              />
              {selectedFiles.length > 0 && (
                <div className="selected-files">
                  <span>{selectedFiles.length} file(s) selected</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* LLM Settings */}
        <div className="sidebar-section llm-settings-section">
          <div className="section-header">
            <h3 className="section-title">LLM Settings</h3>
            <button className="icon-btn" onClick={() => setShowLlmConfig(!showLlmConfig)}>⚙️</button>
          </div>

          {showLlmConfig && (
            <div className="llm-config">
              <select
                value={llmProvider}
                onChange={(e) => setLlmProvider(e.target.value)}
                className="input-field"
              >
                <option value="anthropic">Anthropic Claude</option>
                <option value="openai">OpenAI</option>
              </select>
              <input
                type="password"
                className="input-field"
                placeholder="API Key (optional)"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <button
                className="btn btn-primary"
                onClick={handleLlmConfigSubmit}
              >
                Save Configuration
              </button>
            </div>
          )}

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
              disabled={!config.llmAvailable}
            />
            Enable LLM Reasoning
          </label>

          <div className="status-badge">
            <span className={`status-dot ${config.llmAvailable ? 'active' : 'inactive'}`}></span>
            <span>{config.llmAvailable ? 'Available' : 'Not configured'}</span>
            <span className="provider-badge">{config.llmProvider}</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="sidebar-section">
          <button
            className="btn btn-primary btn-large"
            onClick={handleAnalyzeClick}
            disabled={loading}
          >
            {loading ? '⏳ Analyzing...' : '🚀 Run Analysis'}
          </button>

          <button
            className="btn btn-secondary btn-large"
            onClick={() => onEvaluation(15)}
            disabled={loading}
          >
            {loading ? '⏳ Running...' : '📊 CodeXGLUE Eval'}
          </button>
        </div>

        {/* Pipeline Info */}
        <div className="sidebar-section pipeline-info">
          <h4>Pipeline Stages</h4>
          <ol>
            <li>Load Repository</li>
            <li>AST Scan</li>
            <li>Auto-Repair</li>
            <li>Verify</li>
            <li>Explain</li>
            <li>Understand Project</li>
          </ol>
        </div>

        {/* Multi-language support */}
        <div className="sidebar-section languages">
          <h4>🌍 Multi-Language Support</h4>
          <div className="language-grid">
            <span className="lang-badge">🐍 Python</span>
            <span className="lang-badge">📜 JS/TS</span>
            <span className="lang-badge">☕ Java</span>
            <span className="lang-badge">🐹 Go</span>
            <span className="lang-badge">🦀 Rust</span>
            <span className="lang-badge">💎 Ruby</span>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <button
          className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
          onClick={() => onViewChange('dashboard')}
        >
          📊 Dashboard
        </button>
        <button
          className={`nav-item ${currentView === 'analysis' ? 'active' : ''}`}
          onClick={() => onViewChange('analysis')}
        >
          🔍 Analysis
        </button>
        <button
          className={`nav-item ${currentView === 'overview' ? 'active' : ''}`}
          onClick={() => onViewChange('overview')}
        >
          🏗️ Overview
        </button>
        <button
          className={`nav-item ${currentView === 'evaluation' ? 'active' : ''}`}
          onClick={() => onViewChange('evaluation')}
        >
          📈 Evaluation
        </button>
      </nav>
    </aside>
  )
}

export default Sidebar
