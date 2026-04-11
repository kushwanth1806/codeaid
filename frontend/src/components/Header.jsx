import React from 'react'
import '../styles/Header.css'

function Header() {
  return (
    <header className="header">
      <div className="header-container">
        <div className="header-content">
          <h1>codeAID</h1>
          <p>AI-Powered Repository Debugger & Auto-Repair Assistant</p>
          <p className="subtitle">Scan • Analyze • Fix • Verify</p>
        </div>
        <div className="header-accent"></div>
      </div>
    </header>
  )
}

export default Header
