import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { FileText, StickyNote, Mic, Upload } from 'lucide-react'
import './ProjectDetail.css'

function ProjectDetail() {
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [ingestMode, setIngestMode] = useState('document') // document, note, audio
  const [contextCollapsed, setContextCollapsed] = useState(false)

  const fetchProject = async () => {
    try {
      const username = 'admin'
      const password = 'password'
      const auth = btoa(`${username}:${password}`)
      
      const [projectRes, eventsRes] = await Promise.all([
        fetch(`http://localhost:8000/api/projects/${id}`, {
          headers: { 'Authorization': `Basic ${auth}` }
        }),
        fetch(`http://localhost:8000/api/projects/${id}/events`, {
          headers: { 'Authorization': `Basic ${auth}` }
        })
      ])
      
      if (!projectRes.ok) throw new Error('Failed to fetch project')
      if (!eventsRes.ok) throw new Error('Failed to fetch events')
      
      const projectData = await projectRes.json()
      const eventsData = await eventsRes.json()
      
      setProject(projectData)
      setEvents(eventsData)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProject()
  }, [id])

  const handleDropzoneClick = () => {
    // Non-functional for now - will trigger file input
  }

  if (loading) return <div className="projects-page">Laddar...</div>
  if (error) return <div className="projects-page">Fel: {error}</div>
  if (!project) return <div className="projects-page">Projekt hittades inte</div>

  return (
    <div className="projects-page">
      <Link to="/projects" className="back-link">← Tillbaka till projekt</Link>
      <div className="projects-header">
        <h2 className="projects-title">{project.name}</h2>
      </div>

      <div className="project-workspace">
        {/* Left Column: Workspace / Material */}
        <div className={`workspace-main ${contextCollapsed ? 'workspace-main-expanded' : ''}`}>
          <div className="material-section">
            {/* Toolbar - Small, secondary */}
            <div className="ingest-toolbar">
              <div className="toolbar-left">
                <button 
                  className={`toolbar-btn ${ingestMode === 'document' ? 'active' : ''}`}
                  onClick={() => setIngestMode('document')}
                  disabled
                >
                  <FileText size={14} />
                  <span>Dokument</span>
                </button>
                <button 
                  className={`toolbar-btn ${ingestMode === 'note' ? 'active' : ''}`}
                  onClick={() => setIngestMode('note')}
                  disabled
                >
                  <StickyNote size={14} />
                  <span>Anteckning</span>
                </button>
                <button 
                  className={`toolbar-btn ${ingestMode === 'audio' ? 'active' : ''}`}
                  onClick={() => setIngestMode('audio')}
                  disabled
                >
                  <Mic size={14} />
                  <span>Röstmemo</span>
                </button>
              </div>
              <button 
                className="toolbar-toggle-btn"
                onClick={() => setContextCollapsed(!contextCollapsed)}
                aria-label={contextCollapsed ? 'Visa projektinfo' : 'Dölj projektinfo'}
                title={contextCollapsed ? 'Visa projektinfo' : 'Dölj projektinfo'}
              >
                <div className="panel-toggle-container">
                  <svg className="panel-toggle-arrow panel-toggle-arrow-left" width="8" height="8" viewBox="0 0 8 8" fill="none">
                    <path d="M5 1L2 4L5 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  <div className="panel-toggle-icon">
                    <div className="panel-toggle-box">
                      {!contextCollapsed && <div className="panel-toggle-sidebar"></div>}
                    </div>
                  </div>
                  <svg className="panel-toggle-arrow panel-toggle-arrow-right" width="8" height="8" viewBox="0 0 8 8" fill="none">
                    <path d="M3 1L6 4L3 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </button>
            </div>

            {/* Primary Dropzone - Full width, calm, editorial */}
            <div 
              className="ingest-dropzone"
              onClick={handleDropzoneClick}
            >
              <div className="dropzone-content">
                <Upload size={32} className="dropzone-icon" />
                <p className="dropzone-text">Dra hit en fil eller klicka för att välja</p>
                <p className="dropzone-hint">.TXT, .DOCX, .PDF • Max 25MB</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Context */}
        <div className={`workspace-context ${contextCollapsed ? 'workspace-context-collapsed' : ''}`}>
          {!contextCollapsed && (
            <>
              <Card className="context-card">
                <div className="context-section">
                  <h3 className="context-title">Projektinfo</h3>
                  <div className="context-info">
                    <div className="context-item">
                      <span className="context-label">Klassificering:</span>
                      <Badge variant={project.classification === 'normal' ? 'normal' : project.classification === 'sensitive' ? 'sensitive' : 'source-sensitive'}>
                        {project.classification}
                      </Badge>
                    </div>
                    <div className="context-item">
                      <span className="context-label">Skapad:</span>
                      <span className="context-value">{new Date(project.created_at).toLocaleDateString('sv-SE')}</span>
                    </div>
                    <div className="context-item">
                      <span className="context-label">Uppdaterad:</span>
                      <span className="context-value">{new Date(project.updated_at).toLocaleDateString('sv-SE')}</span>
                    </div>
                    {project.description && (
                      <div className="context-item context-description">
                        <span className="context-label">Beskrivning:</span>
                        <p className="context-value">{project.description}</p>
                      </div>
                    )}
                  </div>
                </div>
              </Card>

              <Card className="context-card context-timeline">
                <div className="context-section">
                  <h3 className="context-title context-title-muted">Händelser</h3>
                  {events.length === 0 ? (
                    <p className="timeline-empty">Inga händelser ännu.</p>
                  ) : (
                    <div className="timeline-list">
                      {events.map(event => (
                        <div key={event.id} className="timeline-item">
                          <div className="timeline-time">
                            {new Date(event.timestamp).toLocaleDateString('sv-SE', { 
                              month: 'short', 
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </div>
                          <div className="timeline-content">
                            <div className="timeline-header">
                              <span className="timeline-type">{event.event_type}</span>
                              {event.actor && (
                                <span className="timeline-actor">av {event.actor}</span>
                              )}
                            </div>
                            {event.metadata && (
                              <div className="timeline-metadata">
                                <pre>{JSON.stringify(event.metadata, null, 2)}</pre>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default ProjectDetail
