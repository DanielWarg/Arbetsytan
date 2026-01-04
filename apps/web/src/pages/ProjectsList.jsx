import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Modal } from '../ui/Modal'
import CreateProject from './CreateProject'
import { getDueUrgency } from '../lib/urgency'
import { FolderPlus, Folder, Search, Calendar, Eye, Lock, FileText, ArrowRight } from 'lucide-react'
import './ProjectsList.css'

function ProjectsList() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [scoutItems, setScoutItems] = useState([])

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

  useEffect(() => {
    fetchProjects()
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
        
        if (!response.ok) throw new Error('Failed to fetch scout items')
        
        const data = await response.json()
        setScoutItems(data)
      } catch (err) {
        console.error('Error fetching scout items:', err)
        setScoutItems([])
      }
    }
    
    fetchScoutItems()
  }, [])

  const handleCreateSuccess = (project) => {
    setShowCreateModal(false)
    fetchProjects()
    navigate(`/projects/${project.id}`)
  }

  if (loading) return <div className="projects-list-page">Laddar...</div>
  if (error) return <div className="projects-list-page">Fel: {error}</div>

  const getClassificationLabel = (classification) => {
    if (classification === 'source-sensitive') {
      return 'Källkritisk'
    }
    if (classification === 'sensitive') {
      return 'Känslig'
    }
    return 'Offentlig'
  }

  const getClassificationClass = (classification) => {
    if (classification === 'sensitive' || classification === 'source-sensitive') {
      return 'badge-sensitive'
    }
    return 'badge-normal'
  }

  // Get projects with due dates for Due Dates widget
  // Prioritize urgent deadlines (warning/danger), then sort by date
  const projectsWithDueDates = projects
    .filter(p => p.due_date)
    .map(p => ({
      ...p,
      urgency: getDueUrgency(p.due_date)
    }))
    .sort((a, b) => {
      // First: prioritize urgent (warning/danger) over normal
      const aUrgent = a.urgency.variant === 'warning' || a.urgency.variant === 'danger'
      const bUrgent = b.urgency.variant === 'warning' || b.urgency.variant === 'danger'
      if (aUrgent && !bUrgent) return -1
      if (!aUrgent && bUrgent) return 1
      // Then: sort by date (earliest first)
      if (!a.urgency.normalizedDate) return 1
      if (!b.urgency.normalizedDate) return -1
      return a.urgency.normalizedDate.localeCompare(b.urgency.normalizedDate)
    })
    .slice(0, 4) // Limit to 4 most important

  // Filter projects by search query
  const filteredProjects = projects.filter(project => 
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (project.description && project.description.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  // Get last updated project
  const lastUpdatedProject = projects.length > 0 
    ? projects.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))[0]
    : null

  return (
    <div className="projects-list-page">
      <div className="projects-header">
        <h2 className="projects-title">Kontrollrum</h2>
      </div>

      {/* Scout - Full Width */}
      <Card className="overview-card overview-card-fullwidth scout-card-fullwidth">
        <div className="overview-card-header">
          <h3 className="overview-card-title">Scout – senaste 24h</h3>
        </div>
        <div className="overview-card-content">
            {scoutItems.length > 0 ? (
              <div className="scout-widget-list">
                {scoutItems.slice(0, 6).map(item => (
                <div key={item.id} className="scout-widget-item">
                  <Badge variant="normal" className="scout-widget-badge">{item.raw_source}</Badge>
                  <span className="scout-widget-title">{item.title}</span>
                  <span className="scout-widget-time">
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
            <div className="overview-empty-state">
              <p className="overview-empty-text">Inga leads</p>
            </div>
          )}
          <Link to="/scout" className="btn-overview">
            <Eye size={16} />
            <span>Visa alla</span>
          </Link>
        </div>
      </Card>

      {/* Dina Projekt - Full Width */}
      <Card className="overview-card overview-card-fullwidth projects-card-fullwidth">
        <div className="overview-card-header">
          <h3 className="overview-card-title">Dina Projekt</h3>
        </div>
        <div className="overview-card-content">
          {filteredProjects.length === 0 ? (
            <div className="overview-empty-state">
              <p className="overview-empty-text">
                {searchQuery ? 'Inga matchningar' : 'Inga projekt'}
              </p>
            </div>
          ) : (
            <div className="projects-list-compact">
              {filteredProjects.map(project => {
                const statusLabels = {
                  'research': 'Research',
                  'processing': 'Bearbetning',
                  'fact_check': 'Faktakoll',
                  'ready': 'Klar',
                  'archived': 'Arkiverad'
                }
                const urgency = getDueUrgency(project.due_date)
                
                return (
                  <Link 
                    key={project.id} 
                    to={`/projects/${project.id}`} 
                    className="project-item-compact"
                  >
                    <div className="project-item-compact-content">
                      <div className="project-item-main">
                        <Folder size={14} className="project-item-icon" />
                        <span className="project-item-name">{project.name}</span>
                      </div>
                      <div className="project-item-meta">
                        <span className="project-status-badge">
                          {statusLabels[project.status] || 'Research'}
                        </span>
                        {project.due_date && (
                          <span className={`project-due-date-badge ${urgency.variant}`}>
                            {urgency.normalizedDate}
                            {urgency.label && ` • ${urgency.label}`}
                          </span>
                        )}
                      </div>
                    </div>
                  </Link>
                )
              })}
            </div>
          )}
          <Link to="/projects" className="btn-overview">
            <Eye size={16} />
            <span>Visa alla</span>
          </Link>
        </div>
      </Card>

      {/* Overview Grid - Other Widgets */}
      <div className="overview-grid">
        {/* Projekt Widget */}
        <Card className="overview-card">
          <div className="overview-card-header">
            <h3 className="overview-card-title">Projekt</h3>
          </div>
          <div className="overview-card-content">
            <div className="project-widget-search">
              <Search size={16} className="search-icon" />
              <input
                type="text"
                placeholder="Sök projekt..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="project-search-input"
              />
            </div>
            <button 
              className="btn-create-project btn-create-project-inline"
              onClick={() => setShowCreateModal(true)}
            >
              <FolderPlus size={16} />
              <span>Nytt projekt</span>
            </button>
            {lastUpdatedProject && (
              <div className="project-widget-meta">
                <span className="project-widget-meta-label">Senast uppdaterade:</span>
                <span className="project-widget-meta-value">{lastUpdatedProject.name}</span>
              </div>
            )}
            <div className="project-widget-count">
              <span className="project-widget-count-label">Totalt:</span>
              <span className="project-widget-count-value">{projects.length} projekt</span>
            </div>
          </div>
        </Card>

        {/* Due Dates Widget */}
        <Card className="overview-card">
          <div className="overview-card-header">
            <h3 className="overview-card-title">Due Dates</h3>
          </div>
          <div className="overview-card-content">
            {projectsWithDueDates.length === 0 ? (
              <div className="overview-empty-state">
                <p className="overview-empty-text">Inga deadlines ännu</p>
              </div>
            ) : (
              <div className="due-dates-list">
                {projectsWithDueDates.map(project => (
                  <Link
                    key={project.id}
                    to={`/projects/${project.id}`}
                    className="due-date-item"
                  >
                    <div className="due-date-item-content">
                      <span className="due-date-item-name">{project.name}</span>
                      <div className="due-date-item-meta">
                        <span className="due-date-item-date">{project.urgency.normalizedDate}</span>
                        {project.urgency.label && (
                          <Badge 
                            variant="normal" 
                            className={`deadline-badge ${project.urgency.variant}`}
                          >
                            {project.urgency.label}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* Fort Knox Widget (Placeholder) */}
        <Card className="overview-card">
          <div className="overview-card-header">
            <h3 className="overview-card-title">Fort Knox</h3>
            <Badge variant="normal" className="coming-soon-badge">Kommer snart</Badge>
          </div>
          <div className="overview-card-content">
            <p className="overview-placeholder-text">
              Säkerhetshantering och åtkomstkontroll.
            </p>
            <button 
              className="btn-overview-disabled"
              disabled
            >
              <Lock size={16} />
              <span>Öppna Fort Knox</span>
            </button>
          </div>
        </Card>

        {/* Archive Widget (Placeholder) */}
        <Card className="overview-card">
          <div className="overview-card-header">
            <h3 className="overview-card-title">Arkiv</h3>
            <Badge variant="normal" className="coming-soon-badge">Kommer snart</Badge>
          </div>
          <div className="overview-card-content">
            <p className="overview-placeholder-text">
              Arkiverade projekt och dokument.
            </p>
            <button 
              className="btn-overview-disabled"
              disabled
            >
              <FileText size={16} />
              <span>Öppna Arkiv</span>
            </button>
          </div>
        </Card>

      </div>

      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Skapa nytt projekt"
      >
        <CreateProject
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleCreateSuccess}
        />
      </Modal>
    </div>
  )
}

export default ProjectsList

