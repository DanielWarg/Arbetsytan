import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Modal } from '../ui/Modal'
import CreateProject from './CreateProject'
import { FileText, StickyNote, Mic, Upload, File, Info, Edit, Trash2 } from 'lucide-react'
import './ProjectDetail.css'

function ProjectDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [events, setEvents] = useState([])
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [ingestMode, setIngestMode] = useState('document') // document, note, audio
  const [contextCollapsed, setContextCollapsed] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const fileInputRef = useRef(null)

  const fetchProject = async () => {
    try {
      const username = 'admin'
      const password = 'password'
      const auth = btoa(`${username}:${password}`)
      
      const [projectRes, eventsRes, documentsRes] = await Promise.all([
        fetch(`http://localhost:8000/api/projects/${id}`, {
          headers: { 'Authorization': `Basic ${auth}` }
        }),
        fetch(`http://localhost:8000/api/projects/${id}/events`, {
          headers: { 'Authorization': `Basic ${auth}` }
        }),
        fetch(`http://localhost:8000/api/projects/${id}/documents`, {
          headers: { 'Authorization': `Basic ${auth}` }
        })
      ])
      
      if (!projectRes.ok) throw new Error('Failed to fetch project')
      if (!eventsRes.ok) throw new Error('Failed to fetch events')
      
      const projectData = await projectRes.json()
      const eventsData = await eventsRes.json()
      const documentsData = documentsRes.ok ? await documentsRes.json() : []
      
      setProject(projectData)
      setEvents(eventsData)
      setDocuments(documentsData)
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
    fileInputRef.current?.click()
  }

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file type
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (ext !== 'pdf' && ext !== 'txt') {
      setUploadError('Endast PDF och TXT-filer är tillåtna')
      return
    }

    // Validate file size (25MB)
    if (file.size > 25 * 1024 * 1024) {
      setUploadError('Filen är för stor. Maximal storlek är 25MB')
      return
    }

    setUploading(true)
    setUploadError(null)

    try {
      const username = 'admin'
      const password = 'password'
      const auth = btoa(`${username}:${password}`)

      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`http://localhost:8000/api/projects/${id}/documents`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`
        },
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Upload misslyckades')
      }

      // Refresh documents list
      await fetchProject()
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (err) {
      setUploadError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const getClassificationLabel = (classification) => {
    if (classification === 'source-sensitive') {
      return 'Källkritisk'
    }
    if (classification === 'sensitive') {
      return 'Känslig'
    }
    return 'Offentlig'
  }

  const getClassificationVariant = (classification) => {
    if (classification === 'source-sensitive') {
      return 'source-sensitive'
    }
    if (classification === 'sensitive') {
      return 'sensitive'
    }
    return 'normal'
  }

  const handleDeleteProject = async () => {
    setDeleting(true)
    try {
      const username = 'admin'
      const password = 'password'
      const auth = btoa(`${username}:${password}`)
      
      const response = await fetch(`http://localhost:8000/api/projects/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Basic ${auth}`
        }
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to delete project')
      }
      
      // Redirect to projects list
      navigate('/projects')
    } catch (err) {
      alert(`Fel vid radering: ${err.message}`)
      setDeleting(false)
    }
  }

  if (loading) return <div className="project-detail-page">Laddar...</div>
  if (error) return <div className="project-detail-page">Fel: {error}</div>
  if (!project) return <div className="project-detail-page">Projekt hittades inte</div>

  return (
    <div className="project-detail-page">
      <div className="workspace-container">
        <Link to="/projects" className="back-link">← Tillbaka till projekt</Link>
        <div className="projects-header">
          <h2 className="projects-title">{project.name}</h2>
          <div className="project-header-actions">
            <button 
              className="project-action-btn"
              onClick={() => setShowEditModal(true)}
              title="Redigera projekt"
            >
              <Edit size={18} />
            </button>
            <button 
              className="project-action-btn project-action-btn-delete"
              onClick={() => setShowDeleteModal(true)}
              title="Radera projekt"
            >
              <Trash2 size={18} />
            </button>
          </div>
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

            {/* Material List */}
            {documents.length > 0 ? (
              <div className="material-list">
                <h3 className="material-list-title">Material</h3>
                <div className="material-list-items">
                  {documents.map(doc => (
                    <div
                      key={doc.id}
                      className="material-list-item"
                      onClick={() => navigate(`/projects/${id}/documents/${doc.id}`)}
                    >
                      <div className="material-item-icon">
                        <File size={16} />
                      </div>
                      <div className="material-item-content">
                        <div className="material-item-header">
                          <span className="material-item-filename">{doc.filename}</span>
                          <div className="material-item-badges">
                            <Badge variant={getClassificationVariant(doc.classification)}>
                              {getClassificationLabel(doc.classification)}
                            </Badge>
                            {doc.sanitize_level && (
                              <div className="sanitize-badge-container">
                                <Badge variant={doc.sanitize_level === 'paranoid' ? 'sensitive' : 'normal'} className="sanitize-badge">
                                  {doc.sanitize_level === 'normal' ? 'Normal' : doc.sanitize_level === 'strict' ? 'Strikt' : 'Paranoid'}
                                </Badge>
                                <div className="material-item-tooltip-container">
                                  <Info size={12} className="material-item-info-icon" />
                                  <div className="material-item-tooltip">
                                    {doc.sanitize_level === 'normal' 
                                      ? 'Normal: Standard sanering. Email, telefonnummer och personnummer maskeras automatiskt.'
                                      : doc.sanitize_level === 'strict'
                                      ? 'Strikt: Ytterligare numeriska sekvenser maskeras för extra säkerhet.'
                                      : 'Paranoid: Alla siffror och känsliga mönster maskeras. AI och export avstängda för maximal säkerhet.'}
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="material-item-meta">
                          <span className="material-item-type">{doc.file_type.toUpperCase()}</span>
                          <span className="material-item-date">
                            {new Date(doc.created_at).toLocaleDateString('sv-SE')}
                          </span>
                          {doc.usage_restrictions && !doc.usage_restrictions.ai_allowed && (
                            <div className="material-item-restriction-container">
                              <span className="material-item-restriction">AI avstängt</span>
                              <div className="material-item-tooltip-container">
                                <Info size={12} className="material-item-info-icon" />
                                <div className="material-item-tooltip">
                                  Dokumentet krävde paranoid sanering. AI-funktioner är avstängda för säkerhet.
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {/* Primary Dropzone - Full width, calm, editorial */}
            <div 
              className={`ingest-dropzone ${uploading ? 'uploading' : ''}`}
              onClick={handleDropzoneClick}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
              <div className="dropzone-content">
                {uploading ? (
                  <>
                    <div className="dropzone-loading">Laddar upp...</div>
                  </>
                ) : (
                  <>
                    <Upload size={32} className="dropzone-icon" />
                    <p className="dropzone-text">Dra hit en fil eller klicka för att välja</p>
                    <p className="dropzone-hint">.TXT, .PDF • Max 25MB</p>
                  </>
                )}
              </div>
            </div>
            {uploadError && (
              <div className="upload-error">
                {uploadError}
              </div>
            )}
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
                        {getClassificationLabel(project.classification)}
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
      
      {/* Edit Project Modal */}
      {showEditModal && (
        <Modal onClose={() => setShowEditModal(false)}>
          <CreateProject
            project={project}
            onClose={() => setShowEditModal(false)}
            onSuccess={(updatedProject) => {
              setProject(updatedProject)
              setShowEditModal(false)
            }}
          />
        </Modal>
      )}
      
      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <Modal onClose={() => setShowDeleteModal(false)}>
          <div className="delete-confirmation">
            <h3 className="delete-confirmation-title">Radera projekt permanent</h3>
            <p className="delete-confirmation-text">
              Är du säker på att du vill radera detta projekt? Alla dokument och händelser kommer att raderas permanent från systemet. Denna åtgärd kan inte ångras.
            </p>
            <div className="delete-confirmation-actions">
              <Button 
                type="button" 
                variant="secondary" 
                onClick={() => setShowDeleteModal(false)}
                disabled={deleting}
              >
                Avbryt
              </Button>
              <Button 
                type="button" 
                variant="error" 
                onClick={handleDeleteProject}
                disabled={deleting}
              >
                {deleting ? 'Raderar...' : 'Radera permanent'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

export default ProjectDetail
