import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Modal } from '../ui/Modal'
import CreateProject from './CreateProject'
import { getDueUrgency } from '../lib/urgency'
import { FolderPlus, Folder, Search, Calendar, Eye, Lock, FileText } from 'lucide-react'
import './ProjectsList.css'

function ProjectsList() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

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

  const handleCreateSuccess = (project) => {
    setShowCreateModal(false)
    fetchProjects()
    // Optionally navigate to project detail
    // navigate(`/projects/${project.id}`)
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

      {/* Overview Grid */}
      <div className="overview-grid">
        {/* Projekt Widget (Large) */}
        <Card className="overview-card overview-card-large">
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

        {/* Scout Widget (Placeholder) */}
        <Card className="overview-card">
          <div className="overview-card-header">
            <h3 className="overview-card-title">Scout</h3>
            <Badge variant="normal" className="coming-soon-badge">Kommer snart</Badge>
          </div>
          <div className="overview-card-content">
            <p className="overview-placeholder-text">
              Automatisk identifiering och kategorisering av innehåll.
            </p>
            <button 
              className="btn-overview-disabled"
              disabled
            >
              <Eye size={16} />
              <span>Öppna Scout</span>
            </button>
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

        {/* Dina Projekt Widget */}
        <Card className="overview-card">
          <div className="overview-card-header">
            <h3 className="overview-card-title">Dina Projekt</h3>
            <button 
              className="btn-create-project-small"
              onClick={() => setShowCreateModal(true)}
              title="Nytt projekt"
            >
              <FolderPlus size={14} />
            </button>
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
                {filteredProjects.map(project => (
                  <Link 
                    key={project.id} 
                    to={`/projects/${project.id}`} 
                    className="project-item-compact"
                  >
                    <div className="project-item-compact-content">
                      <Folder size={14} className="project-item-icon" />
                      <span className="project-item-name">{project.name}</span>
                      {(() => {
                        const u = getDueUrgency(project.due_date)
                        if (u.label) {
                          return (
                            <Badge variant="normal" className={`deadline-badge-small ${u.variant}`}>
                              {u.label}
                            </Badge>
                          )
                        }
                        return null
                      })()}
                    </div>
                  </Link>
                ))}
              </div>
            )}
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

