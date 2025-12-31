import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import './Dashboard.css'

function Dashboard() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const username = 'admin'
        const password = 'password'
        const auth = btoa(`${username}:${password}`)
        
        const response = await fetch('http://localhost:8000/api/projects', {
          headers: {
            'Authorization': `Basic ${auth}`
          }
        })
        
        if (!response.ok) throw new Error('Failed to fetch projects')
        
        const data = await response.json()
        setProjects(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    
    fetchProjects()
  }, [])

  if (loading) return <div className="projects-page">Laddar...</div>
  if (error) return <div className="projects-page">Fel: {error}</div>

  return (
    <div className="projects-page">
      <div className="projects-header">
        <h2 className="projects-title">Dashboard</h2>
        <Link to="/projects" className="btn-create-project">
          <span>Alla projekt</span>
        </Link>
      </div>
      
      <section className="dashboard-section">
        <h2 className="section-title">Senast arbetade projekt</h2>
        {projects.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state-title">Inga projekt hittades</p>
            <p className="empty-state-text">Skapa ditt första projekt för att organisera ditt arbete.</p>
            <Link to="/projects" className="btn-create-project">
              <span>Nytt projekt</span>
            </Link>
          </div>
        ) : (
          <div className="project-grid">
            {projects.slice(0, 6).map(project => (
              <Link key={project.id} to={`/projects/${project.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <Card interactive className="project-card">
                  <div className="project-card-header">
                    <h3>{project.name}</h3>
                    <Badge variant={project.classification === 'normal' ? 'normal' : project.classification === 'sensitive' ? 'sensitive' : 'source-sensitive'}>
                      {project.classification}
                    </Badge>
                  </div>
                  {project.description && (
                    <p className="project-description">{project.description}</p>
                  )}
                  <div className="project-meta">
                    <span>Uppdaterad: {new Date(project.updated_at).toLocaleDateString('sv-SE')}</span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default Dashboard

