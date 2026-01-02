import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Modal } from '../ui/Modal'
import CreateProject from './CreateProject'
import { getDueUrgency } from '../lib/urgency'
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
  
  // Recording states
  const [recordingUploading, setRecordingUploading] = useState(false)
  const [recordingProcessing, setRecordingProcessing] = useState(false)
  const [recordingError, setRecordingError] = useState(null)
  const [recordingSuccess, setRecordingSuccess] = useState(null)
  const audioInputRef = useRef(null)
  
  // MediaRecorder states
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0) // seconds
  const [recordingMode, setRecordingMode] = useState('record') // 'upload' | 'record' - default 'record' to show recording button
  const [micPermissionError, setMicPermissionError] = useState(null)
  
  // Refs to avoid stale state in callbacks
  const recorderRef = useRef(null)
  const timerRef = useRef(null)
  const streamRef = useRef(null)
  const audioChunksRef = useRef([])

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
    if (ingestMode === 'audio') {
      audioInputRef.current?.click()
    } else {
      fileInputRef.current?.click()
    }
  }

  const handleAudioSelect = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file size (25MB)
    if (file.size > 25 * 1024 * 1024) {
      setRecordingError('Filen är för stor. Maximal storlek är 25MB')
      return
    }

    setRecordingUploading(true)
    setRecordingProcessing(false)
    setRecordingError(null)
    setRecordingSuccess(null)

    try {
      // Validate file exists and has content
      if (!file || file.size === 0) {
        throw new Error('Filen är tom eller ogiltig')
      }

      const formData = new FormData()
      formData.append('file', file)

      // Add auth header (same as other fetch calls)
      const username = 'admin'
      const password = 'password'
      const auth = btoa(username + ':' + password)

      // Upload audio
      // NOTE: Do NOT set Content-Type header - browser will set it automatically with boundary for FormData
      const response = await fetch(`http://localhost:8000/api/projects/${id}/recordings`, {
        method: 'POST',
        headers: {
          'Authorization': 'Basic ' + auth
          // Do NOT set Content-Type - let browser set it with boundary
        },
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Kunde inte ladda upp ljudfil')
      }

      const documentData = await response.json()

      // Simulate processing delay (800-1200ms)
      setRecordingUploading(false)
      setRecordingProcessing(true)
      
      const delay = 800 + Math.random() * 400 // 800-1200ms
      await new Promise(resolve => setTimeout(resolve, delay))
      
      setRecordingProcessing(false)
      setRecordingSuccess({ documentId: documentData.id })

      // Refresh documents list
      await fetchProject()
    } catch (err) {
      setRecordingUploading(false)
      setRecordingProcessing(false)
      setRecordingError(err.message)
    } finally {
      // Reset file input
      if (audioInputRef.current) {
        audioInputRef.current.value = ''
      }
    }
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // Simplified recording functions - avoid constructor issues
  const startRecording = async () => {
    try {
      setMicPermissionError(null)
      
      // Check browser support
      if (typeof window === 'undefined') return
      if (!window.MediaRecorder) {
        setMicPermissionError('MediaRecorder stöds inte i denna webbläsare')
        return
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setMicPermissionError('Mikrofon stöds inte i denna webbläsare')
        return
      }
      
      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      
      // Find supported MIME type - prefer ogg for better Whisper compatibility
      const mimeTypes = ['audio/ogg', 'audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
      let mimeType = ''
      for (const type of mimeTypes) {
        if (window.MediaRecorder.isTypeSupported(type)) {
          mimeType = type
          break
        }
      }
      console.log('Using MIME type:', mimeType)
      
      if (!mimeType) {
        stream.getTracks().forEach(t => t.stop())
        setMicPermissionError('Inget ljudformat stöds. Använd fil-uppladdning.')
        return
      }
      
      // Create recorder
      const recorder = new window.MediaRecorder(stream, { mimeType })
      recorderRef.current = recorder
      audioChunksRef.current = []
      
      recorder.ondataavailable = function(e) {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }
      
      recorder.onstop = function() {
        // Clear timer
        if (timerRef.current) {
          clearInterval(timerRef.current)
          timerRef.current = null
        }
        
        // Stop tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(t => t.stop())
          streamRef.current = null
        }
        
        // Create blob and upload - use all collected chunks
        if (audioChunksRef.current.length > 0) {
          const audioBlob = new window.Blob(audioChunksRef.current, { type: mimeType })
          console.log('Recording blob size:', audioBlob.size, 'chunks:', audioChunksRef.current.length)
          if (audioBlob.size > 0) {
            uploadRecordingBlob(audioBlob)
          } else {
            setRecordingError('Inspelningen är tom. Försök igen.')
          }
        } else {
          setRecordingError('Ingen ljuddata inspelad. Försök igen.')
        }
      }
      
      // Start with timeslice to get data every 250ms (ensures data is collected)
      recorder.start(250)
      setIsRecording(true)
      setRecordingTime(0)
      
      // Timer - auto stop at 30s
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => {
          if (prev >= 29) {
            stopRecording()
            return 30
          }
          return prev + 1
        })
      }, 1000)
      
    } catch (err) {
      // Cleanup
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
        streamRef.current = null
      }
      setMicPermissionError('Mikrofonåtkomst nekad: ' + (err.message || 'Okänt fel'))
    }
  }

  const stopRecording = () => {
    if (recorderRef.current && isRecording) {
      recorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const uploadRecordingBlob = async (audioBlob) => {
    setRecordingUploading(true)
    setRecordingProcessing(false)
    setRecordingError(null)
    setRecordingSuccess(null)
    
    try {
      const ext = audioBlob.type.includes('webm') ? 'webm' : audioBlob.type.includes('ogg') ? 'ogg' : 'mp4'
      const filename = 'recording_' + Date.now() + '.' + ext
      
      const formData = new window.FormData()
      formData.append('file', audioBlob, filename)
      
      // Add auth header (same as other fetch calls)
      const username = 'admin'
      const password = 'password'
      const auth = btoa(username + ':' + password)
      
      const response = await fetch('http://localhost:8000/api/projects/' + id + '/recordings', {
        method: 'POST',
        headers: {
          'Authorization': 'Basic ' + auth
        },
        body: formData
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Kunde inte ladda upp inspelning')
      }
      
      const documentData = await response.json()
      
      setRecordingUploading(false)
      setRecordingProcessing(true)
      
      // Brief delay for UX
      await new Promise(r => setTimeout(r, 800))
      
      setRecordingProcessing(false)
      setRecordingSuccess({ documentId: documentData.id })
      await fetchProject()
    } catch (err) {
      setRecordingUploading(false)
      setRecordingProcessing(false)
      setRecordingError(err.message || 'Uppladdning misslyckades')
    }
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

  const getDueDateStatus = (dueDate) => {
    if (!dueDate) return null
    const due = new Date(dueDate)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    due.setHours(0, 0, 0, 0)
    const daysUntilDue = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    if (daysUntilDue < 0) return 'overdue'
    if (daysUntilDue <= 7) return 'due-soon'
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
      
      // DELETE returns 204 No Content - do NOT call .json()
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
          <div className="project-title-section">
            <h2 className="projects-title">{project.name}</h2>
            {(() => {
              const u = getDueUrgency(project.due_date)
              if (!u.normalizedDate) return null
              return (
                <div className="project-header-due-date">
                  <span className="project-due-date-muted">{u.normalizedDate}</span>
                  {u.label && (
                    <Badge variant="normal" className={`deadline-badge ${u.variant}`}>
                      {u.label}
                    </Badge>
                  )}
                </div>
              )
            })()}
          </div>
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
                  disabled={false}
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
                  onClick={() => {
                    setIngestMode('audio')
                    // Reset to 'record' mode when switching to audio to show recording button by default
                    setRecordingMode('record')
                    setMicPermissionError(null)
                  }}
                  disabled={false}
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

            {/* Primary CTA for Audio Transcription - Only when audio mode is active - MUST be before Material List */}
            {ingestMode === 'audio' && (
              <div className="audio-primary-cta">
                <div className="audio-cta-buttons">
                  <button
                    className={`audio-cta-btn ${recordingMode === 'record' ? 'active' : ''}`}
                    onClick={() => {
                      setRecordingMode('record')
                      setMicPermissionError(null)
                    }}
                    disabled={isRecording || recordingUploading || recordingProcessing}
                  >
                    <Mic size={20} />
                    <span>Spela in</span>
                  </button>
                  <button
                    className={`audio-cta-btn ${recordingMode === 'upload' ? 'active' : ''}`}
                    onClick={() => {
                      setRecordingMode('upload')
                      setMicPermissionError(null)
                    }}
                    disabled={isRecording || recordingUploading || recordingProcessing}
                  >
                    <Upload size={20} />
                    <span>Ladda upp fil</span>
                  </button>
                </div>
                <p className="audio-cta-help">Spela in direkt eller ladda upp en ljudfil för automatisk transkribering.</p>
              </div>
            )}

            {/* Audio Recording Controls and Upload - MUST be before Material List */}
            {ingestMode === 'audio' && (
              <div className="audio-recording-container">
                {/* Recording mode */}
                {recordingMode === 'record' ? (
                  <div className="recording-controls">
                    {micPermissionError && (
                      <div className="recording-error">
                        <p>{micPermissionError}</p>
                        <button 
                          className="recording-fallback-btn"
                          onClick={() => {
                            setRecordingMode('upload')
                            setMicPermissionError(null)
                          }}
                        >
                          Byt till uppladdning
                        </button>
                      </div>
                    )}
                    {!isRecording && !recordingUploading && !recordingProcessing && !micPermissionError && (
                      <button
                        className="record-start-btn"
                        onClick={startRecording}
                        disabled={!navigator.mediaDevices || !window.MediaRecorder}
                      >
                        <Mic size={24} />
                        <span>Starta inspelning</span>
                      </button>
                    )}
                    {isRecording && (
                      <div className="recording-active">
                        <div className="recording-pipeline">
                          <div className="recording-pipeline-step active">
                            <div className="pipeline-step-circle">
                              <Mic size={16} />
                            </div>
                            <span className="pipeline-step-label">Inspelning</span>
                          </div>
                          <div className="recording-pipeline-connector"></div>
                          <div className="recording-pipeline-step pending">
                            <div className="pipeline-step-circle">
                              <Upload size={16} />
                            </div>
                            <span className="pipeline-step-label">Uppladdning</span>
                          </div>
                          <div className="recording-pipeline-connector"></div>
                          <div className="recording-pipeline-step pending">
                            <div className="pipeline-step-circle">
                              <FileText size={16} />
                            </div>
                            <span className="pipeline-step-label">Transkription</span>
                          </div>
                        </div>
                        <div className="recording-indicator">
                          <div className="recording-dot"></div>
                          <span>Inspelar: {formatTime(recordingTime)}</span>
                          {recordingTime >= 30 && <span className="recording-limit"> (Max 30 sek)</span>}
                        </div>
                        <button className="record-stop-btn" onClick={stopRecording}>
                          Stoppa
                        </button>
                      </div>
                    )}
                    {(recordingUploading || recordingProcessing) && (
                      <div className="recording-status">
                        <div className="recording-pipeline">
                          <div className="recording-pipeline-step completed">
                            <div className="pipeline-step-circle">
                              <Mic size={16} />
                            </div>
                            <span className="pipeline-step-label">Inspelning</span>
                          </div>
                          <div className="recording-pipeline-connector active"></div>
                          <div className={`recording-pipeline-step ${recordingUploading ? 'active' : 'completed'}`}>
                            <div className="pipeline-step-circle">
                              <Upload size={16} />
                            </div>
                            <span className="pipeline-step-label">Uppladdning</span>
                          </div>
                          <div className={`recording-pipeline-connector ${recordingUploading ? '' : 'active'}`}></div>
                          <div className={`recording-pipeline-step ${recordingProcessing ? 'active' : 'pending'}`}>
                            <div className="pipeline-step-circle">
                              <FileText size={16} />
                            </div>
                            <span className="pipeline-step-label">Transkription</span>
                          </div>
                        </div>
                        <div className="recording-status-text">
                          {recordingUploading ? 'Laddar upp...' : 'Bearbetar transkription...'}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  /* Upload mode - existing file input */
                  <div 
                    className={`ingest-dropzone ${recordingUploading || recordingProcessing ? 'uploading' : ''}`}
                    onClick={() => audioInputRef.current?.click()}
                  >
                    <input
                      ref={audioInputRef}
                      type="file"
                      accept="audio/*"
                      onChange={handleAudioSelect}
                      style={{ display: 'none' }}
                    />
                    <div className="dropzone-content">
                      {recordingUploading || recordingProcessing ? (
                        <>
                          <div className="dropzone-loading">
                            {recordingUploading ? 'Laddar upp ljudfil...' : 'Bearbetar ljudfil...'}
                          </div>
                        </>
                      ) : (
                        <>
                          <Upload size={32} className="dropzone-icon" />
                          <p className="dropzone-text">Dra hit en ljudfil eller klicka för att välja</p>
                          <p className="dropzone-hint">Ljudfiler • Max 25MB</p>
                        </>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Success message */}
                {recordingSuccess && (
                  <div className="recording-success">
                    <p>Inspelning sparad!</p>
                    <Link to={`/projects/${id}/documents/${recordingSuccess.documentId}`}>
                      Öppna dokument
                    </Link>
                  </div>
                )}
                
                {/* Error message */}
                {recordingError && (
                  <div className="recording-error">
                    <p>{recordingError}</p>
                  </div>
                )}
              </div>
            )}

            {/* Primary Document Upload - Only when document mode is active - MUST be before Material List */}
            {ingestMode === 'document' && (
              <div className="document-primary-upload">
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
                <p className="document-upload-help">Ladda upp dokument för automatisk bearbetning och sanering.</p>
              </div>
            )}

            {/* Material List - Always visible, regardless of ingest mode */}
            {documents.length > 0 && (
              <div className="material-list">
                <h3 className="material-list-title">Material</h3>
                <div className="material-list-items">
                  {documents.map(doc => (
                    <div
                      key={doc.id}
                      className="material-list-item"
                      onClick={() => navigate(`/projects/${id}/documents/${doc.id}`)}
                      style={{ cursor: 'pointer' }}
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
                    {project.due_date && (
                      <div className="context-item">
                        <span className="context-label">Deadline:</span>
                        <span className={`context-value context-due-date context-due-date-${getDueDateStatus(project.due_date)}`}>
                          {new Date(project.due_date).toLocaleDateString('sv-SE')}
                          {getDueDateStatus(project.due_date) === 'due-soon' && ' ⚠️'}
                          {getDueDateStatus(project.due_date) === 'overdue' && ' 🔴'}
                        </span>
                      </div>
                    )}
                    {project.description && (
                      <div className="context-item context-description">
                        <span className="context-label">Beskrivning:</span>
                        <p className="context-value">{project.description}</p>
                      </div>
                    )}
                    {project.tags && project.tags.length > 0 && (
                      <div className="context-item">
                        <span className="context-label">Taggar:</span>
                        <div className="context-tags">
                          {project.tags.map((tag, index) => (
                            <Badge key={index} variant="normal" className="tag-badge">
                              {tag}
                            </Badge>
                          ))}
                        </div>
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
      <Modal isOpen={showEditModal} onClose={() => setShowEditModal(false)}>
        <CreateProject
          project={project}
          onClose={() => setShowEditModal(false)}
          onSuccess={async (updatedProject) => {
            setProject(updatedProject)
            setShowEditModal(false)
            // Refresh project data to ensure UI is up to date
            await fetchProject()
          }}
        />
      </Modal>
      
      {/* Delete Confirmation Modal */}
      <Modal isOpen={showDeleteModal} onClose={() => setShowDeleteModal(false)}>
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
    </div>
  )
}

export default ProjectDetail
