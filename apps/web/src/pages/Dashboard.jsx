import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import './Dashboard.css'

function Dashboard() {
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchLatestProject = async () => {
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
        // Backend sorterar redan på updated_at.desc(), ta det första (senaste arbetade/öppnade)
        if (data.length > 0) {
          setProject(data[0])
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    
    fetchLatestProject()
  }, [])

  const isDueSoon = (dueDate) => {
    if (!dueDate) return false
    const due = new Date(dueDate)
    const today = new Date()
    const daysUntilDue = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    return daysUntilDue >= 0 && daysUntilDue <= 7
  }

  if (loading) return <div className="dashboard-page">Laddar...</div>
  if (error) return <div className="dashboard-page">Fel: {error}</div>

  return (
    <div className="dashboard-page">
      <div className="projects-header">
        <h2 className="projects-title">Dashboard</h2>
        <Link to="/projects" className="btn-create-project">
          <span>Alla projekt</span>
        </Link>
      </div>
      
      <section className="dashboard-section">
        <h2 className="section-title">Senast arbetade projekt</h2>
        {!project ? (
          <div className="empty-state">
            <p className="empty-state-title">Inga projekt hittades</p>
            <p className="empty-state-text">Skapa ditt första projekt för att organisera ditt arbete.</p>
            <Link to="/projects" className="btn-create-project">
              <span>Nytt projekt</span>
            </Link>
          </div>
        ) : (
          <Link to={`/projects/${project.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
            <Card interactive className="project-card">
              <div className="project-card-header">
                <h3>{project.name}</h3>
                <Badge variant={project.classification === 'normal' ? 'normal' : project.classification === 'sensitive' ? 'sensitive' : 'source-sensitive'}>
                  {project.classification === 'normal' ? 'Offentlig' : project.classification === 'sensitive' ? 'Känslig' : 'Källkritisk'}
                </Badge>
              </div>
              {project.description && (
                <p className="project-description">{project.description}</p>
              )}
              <div className="project-meta">
                {project.start_date && (
                  <span>Start: {new Date(project.start_date).toLocaleDateString('sv-SE')}</span>
                )}
                {project.due_date && (
                  <span className={isDueSoon(project.due_date) ? 'project-due-soon' : ''}>
                    Deadline: {new Date(project.due_date).toLocaleDateString('sv-SE')}
                    {isDueSoon(project.due_date) && ' ⚠️'}
                  </span>
                )}
              </div>
            </Card>
          </Link>
        )}
      </section>
    </div>
  )
}

export default Dashboard

