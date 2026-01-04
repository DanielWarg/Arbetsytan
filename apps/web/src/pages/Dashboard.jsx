import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { getDueUrgency } from '../lib/urgency'
import './Dashboard.css'

function Dashboard() {
  const [project, setProject] = useState(null)
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [scoutItems, setScoutItems] = useState([])

  useEffect(() => {
    const fetchData = async () => {
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
        
        // DEBUG: Log projects payload before filtering
        console.log('[DEBUG] Total projects from API:', data.length)
        const projectsWithDueDate = data.filter(p => p.due_date)
        console.log('[DEBUG] Projects with due_date:', projectsWithDueDate.length)
        if (projectsWithDueDate.length > 0) {
          console.log('[DEBUG] Sample project with due_date:', {
            id: projectsWithDueDate[0].id,
            name: projectsWithDueDate[0].name,
            due_date: projectsWithDueDate[0].due_date
          })
        }
        
        setProjects(data)
        
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
    
    fetchData()
  }, [])

  useEffect(() => {
    const fetchScoutItems = async () => {
      try {
        const username = 'admin'
        const password = 'password'
        const auth = btoa(`${username}:${password}`)
        
        const response = await fetch('http://localhost:8000/api/scout/items?hours=24&limit=5', {
          headers: {
            'Authorization': `Basic ${auth}`
          },
          credentials: 'omit'
        })
        
        if (!response.ok) {
          console.error('Scout fetch failed:', response.status, response.statusText)
          throw new Error(`Failed to fetch scout items: ${response.status}`)
        }
        
        const data = await response.json()
        console.log('Scout items fetched:', data.length, data)
        setScoutItems(data)
      } catch (err) {
        console.error('Error fetching scout items:', err)
        setScoutItems([])
      }
    }
    
    fetchScoutItems()
  }, [])

  // Get projects with near deadlines (using shared urgency helper)
  const nearDeadlineProjects = projects
    .filter(p => {
      const urgency = getDueUrgency(p.due_date)
      // DEBUG: Log each project's urgency
      if (p.due_date) {
        console.log(`[DEBUG] Project ${p.id} (${p.name}): due_date=${p.due_date}, urgency=`, urgency)
      }
      return urgency.label !== null // Only show projects with warning/danger/overdue
    })
    .sort((a, b) => {
      // Sort by normalizedDate ascending (earliest first)
      const urgencyA = getDueUrgency(a.due_date)
      const urgencyB = getDueUrgency(b.due_date)
      if (!urgencyA.normalizedDate) return 1
      if (!urgencyB.normalizedDate) return -1
      return urgencyA.normalizedDate.localeCompare(urgencyB.normalizedDate)
    })
    .slice(0, 5) // Limit to 5
  
  // DEBUG: Log after filtering
  console.log('[DEBUG] urgentProjects.length:', nearDeadlineProjects.length)
  if (nearDeadlineProjects.length > 0) {
    console.log('[DEBUG] urgentProjects:', nearDeadlineProjects.map(p => ({
      id: p.id,
      name: p.name,
      due_date: p.due_date,
      urgency: getDueUrgency(p.due_date)
    })))
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
      
      {/* Deadlines nära section */}
      {(() => {
        console.log('[DEBUG] Rendering Deadlines nära check: nearDeadlineProjects.length =', nearDeadlineProjects.length)
        return null
      })()}
      {nearDeadlineProjects.length > 0 && (
        <section className="dashboard-section">
          {console.log('[DEBUG] Rendering Deadlines nära section')}
          <h2 className="section-title">Deadlines nära</h2>
          <div className="deadlines-list">
            {nearDeadlineProjects.map(proj => {
              const urgency = getDueUrgency(proj.due_date)
              // Use normalizedDate from helper (single source of truth)
              const dueDateStr = urgency.normalizedDate || ''
              
              return (
                <Link 
                  key={proj.id} 
                  to={`/projects/${proj.id}`} 
                  className="deadline-item-link"
                >
                  <Card className="deadline-item">
                    <div className="deadline-item-content">
                      <span className="deadline-item-title">{proj.name}</span>
                      <div className="deadline-item-meta">
                        <span className="deadline-item-date">{dueDateStr}</span>
                        {urgency.variant === 'warning' && (
                          <Badge variant="normal" className="deadline-badge warning">
                            {urgency.label}
                          </Badge>
                        )}
                        {urgency.variant === 'danger' && (
                          <Badge variant="normal" className="deadline-badge danger">
                            {urgency.label}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </Card>
                </Link>
              )
            })}
          </div>
        </section>
      )}

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
                {project.due_date && (() => {
                  const urgency = getDueUrgency(project.due_date)
                  return (
                    <span className={`project-due-date project-due-date-${urgency.variant === 'warning' ? 'due-soon' : urgency.variant === 'danger' ? 'overdue' : 'normal'}`}>
                      Deadline: {new Date(project.due_date).toLocaleDateString('sv-SE')}
                      {urgency.label && ` • ${urgency.label}`}
                    </span>
                  )
                })()}
              </div>
            </Card>
          </Link>
        )}
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Scout – senaste 24h</h2>
        <p className="scout-subtitle">Leads från dina RSS-källor</p>
        {scoutItems.length > 0 ? (
          <div className="scout-items-list">
            {scoutItems.slice(0, 5).map(item => (
              <div key={item.id} className="scout-item">
                <Badge variant="normal">{item.raw_source}</Badge>
                <span className="scout-item-title">{item.title}</span>
                <span className="scout-item-time">
                  {new Date(item.published_at || item.fetched_at).toLocaleString('sv-SE', { 
                    month: 'short', 
                    day: 'numeric', 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="scout-empty">Inga leads</p>
        )}
        <Link to="/scout" className="btn-view-all">Visa alla</Link>
      </section>
    </div>
  )
}

export default Dashboard

