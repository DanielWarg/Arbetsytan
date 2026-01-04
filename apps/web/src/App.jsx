import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Settings } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import ProjectsList from './pages/ProjectsList'
import ProjectDetail from './pages/ProjectDetail'
import DocumentView from './pages/DocumentView'
import Scout from './pages/Scout'
import Sidebar from './components/Sidebar'
import './index.css'

function App() {
  const [demoMode, setDemoMode] = useState(false)
  const [darkMode, setDarkMode] = useState(true)

  useEffect(() => {
    // Set dark mode as default
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    
    const apiBase = import.meta.env.VITE_API_URL || 
      (import.meta.env.DEV ? 'http://localhost:8000' : '')
    
    fetch(`${apiBase}/health`)
      .then(res => res.json())
      .then(data => {
        setDemoMode(data.demo_mode || false)
      })
      .catch(() => {})
  }, [darkMode])

  const toggleTheme = () => {
    setDarkMode(!darkMode)
  }

  return (
    <Router>
      <AppContent demoMode={demoMode} darkMode={darkMode} toggleTheme={toggleTheme} />
    </Router>
  )
}

function AppContent({ demoMode, darkMode, toggleTheme }) {
  const currentDate = new Date().toLocaleDateString('sv-SE', { 
    weekday: 'long', 
    day: 'numeric', 
    month: 'long' 
  })

  return (
    <div className="app-layout">
      <Sidebar darkMode={darkMode} toggleTheme={toggleTheme} />
      
      <main className="main-content">
        <header className="top-header">
          <div className="header-left">
            <div className="header-date">{currentDate}</div>
          </div>
          
          <div className="header-right">
            {demoMode && (
              <div className="demo-badge">
                Demo Protected
              </div>
            )}
            <button 
              className="header-settings-btn"
              title="Inställningar"
              disabled
            >
              <Settings size={18} />
            </button>
          </div>
        </header>
        
        <div className="content-area">
          <Routes>
            <Route path="/" element={<ProjectsList />} />
            <Route path="/projects" element={<ProjectsList />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/projects/:projectId/documents/:documentId" element={<DocumentView />} />
            <Route path="/scout" element={<Scout />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default App

