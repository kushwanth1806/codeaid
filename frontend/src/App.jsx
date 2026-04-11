import React, { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Dashboard from './components/Dashboard'
import Analysis from './components/Analysis'
import Overview from './components/Overview'
import Evaluation from './components/Evaluation'
import './styles/App.css'

function App() {
  const [currentView, setCurrentView] = useState('dashboard')
  const [results, setResults] = useState(null)
  const [evalResults, setEvalResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [config, setConfig] = useState({
    llmProvider: 'anthropic',
    llmAvailable: false,
    apiKeyConfigured: false
  })

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/status')
      const data = await response.json()
      setConfig({
        llmProvider: data.llm_provider,
        llmAvailable: data.llm_available,
        apiKeyConfigured: data.api_key_configured
      })
    } catch (err) {
      console.error('Failed to fetch config:', err)
    }
  }

  const handleAnalyze = async (source, isZip, useLlm) => {
    setLoading(true)
    setError(null)
    try {
      let response
      if (isZip) {
        const formData = new FormData()
        formData.append('files', source)
        formData.append('use_llm', useLlm)
        response = await fetch('/api/analyze/upload', {
          method: 'POST',
          body: formData
        })
      } else {
        response = await fetch('/api/analyze/github', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: source,
            use_llm: useLlm
          })
        })
      }
      const data = await response.json()
      setResults(data)
      setCurrentView('analysis')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleEvaluation = async (maxSamples) => {
    setLoading(true)
    setError(null)
    try {
      const requestBody = { max_samples: maxSamples }
      // Only include results if they exist (analysis was run)
      if (results) {
        requestBody.results = results
      }
      
      const response = await fetch('/api/eval/codexglue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      })
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`)
      }
      
      const data = await response.json()
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid response format from eval endpoint')
      }
      
      setEvalResults(data)
      setCurrentView('evaluation')
    } catch (err) {
      setError(`Evaluation failed: ${err.message}`)
      console.error('Eval error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleConfigLlm = async (provider, apiKey) => {
    try {
      const response = await fetch('/api/config/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: provider,
          api_key: apiKey
        })
      })
      const data = await response.json()
      setConfig({
        llmProvider: data.provider,
        llmAvailable: data.llm_available,
        apiKeyConfigured: data.api_key_set
      })
    } catch (err) {
      console.error('Failed to configure LLM:', err)
    }
  }

  return (
    <div className="app-wrapper">
      <Sidebar 
        onViewChange={setCurrentView}
        currentView={currentView}
        onAnalyze={handleAnalyze}
        onEvaluation={handleEvaluation}
        onConfigLlm={handleConfigLlm}
        config={config}
        loading={loading}
      />
      <main className="main-content">
        <Header />
        <div className="content-area">
          {error && (
            <div className="error-banner">
              <span>{error}</span>
              <button onClick={() => setError(null)}>✕</button>
            </div>
          )}
          {currentView === 'dashboard' && <Dashboard results={results} />}
          {currentView === 'analysis' && <Analysis results={results} onViewOverview={() => setCurrentView('overview')} />}
          {currentView === 'overview' && <Overview results={results} />}
          {currentView === 'evaluation' && <Evaluation results={evalResults} />}
        </div>
      </main>
    </div>
  )
}

export default App
