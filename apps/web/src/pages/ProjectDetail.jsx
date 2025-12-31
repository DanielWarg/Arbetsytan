import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Input, Textarea } from '../ui/Input'
import './ProjectDetail.css'

function ProjectDetail() {
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showEventForm, setShowEventForm] = useState(false)
  const [newEventType, setNewEventType] = useState('')
  const [newEventMetadata, setNewEventMetadata] = useState('')

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

  const handleCreateEvent = async (e) => {
    e.preventDefault()
    
    try {
      const username = 'admin'
      const password = 'password'
      const auth = btoa(`${username}:${password}`)
      
      let metadata = null
      if (newEventMetadata.trim()) {
        try {
          metadata = JSON.parse(newEventMetadata)
        } catch {
          metadata = { note: newEventMetadata }
        }
      }
      
      const response = await fetch(`http://localhost:8000/api/projects/${id}/events`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          event_type: newEventType,
          metadata: metadata
        })
      })
      
      if (!response.ok) throw new Error('Failed to create event')
      
      setNewEventType('')
      setNewEventMetadata('')
      setShowEventForm(false)
      fetchProject()
    } catch (err) {
      alert('Fel vid skapande av event: ' + err.message)
    }
  }

  if (loading) return <div className="page">Laddar...</div>
  if (error) return <div className="page">Fel: {error}</div>
  if (!project) return <div className="page">Projekt hittades inte</div>

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <Link to="/projects" className="back-link">← Tillbaka till projekt</Link>
          <h1>{project.name}</h1>
        </div>
        <Button onClick={() => setShowEventForm(!showEventForm)}>
          {showEventForm ? 'Avbryt' : 'Nytt event'}
        </Button>
      </div>

      <Card className="project-info">
        <div className="info-section">
          <h2>Information</h2>
          {project.description && (
            <p className="project-description">{project.description}</p>
          )}
          <div className="info-grid">
            <div>
              <span className="info-label">Klassificering:</span>
              <Badge variant={project.classification === 'normal' ? 'normal' : project.classification === 'sensitive' ? 'sensitive' : 'source-sensitive'}>
                {project.classification}
              </Badge>
            </div>
            <div>
              <span className="info-label">Skapad:</span>
              <span>{new Date(project.created_at).toLocaleString('sv-SE')}</span>
            </div>
            <div>
              <span className="info-label">Uppdaterad:</span>
              <span>{new Date(project.updated_at).toLocaleString('sv-SE')}</span>
            </div>
          </div>
        </div>
      </Card>

      {showEventForm && (
        <Card className="create-form">
          <form onSubmit={handleCreateEvent}>
            <div className="form-group">
              <label htmlFor="event-type">Event-typ *</label>
              <Input
                id="event-type"
                type="text"
                value={newEventType}
                onChange={(e) => setNewEventType(e.target.value)}
                required
                placeholder="t.ex. note, meeting, document_added"
              />
            </div>
            <div className="form-group">
              <label htmlFor="event-metadata">Metadata (JSON eller text)</label>
              <Textarea
                id="event-metadata"
                value={newEventMetadata}
                onChange={(e) => setNewEventMetadata(e.target.value)}
                placeholder='{"key": "value"} eller vanlig text'
                rows="3"
              />
            </div>
            <div className="form-actions">
              <Button type="submit" variant="success">Skapa event</Button>
            </div>
          </form>
        </Card>
      )}

      <div className="events-section">
        <h2>Event Timeline</h2>
        {events.length === 0 ? (
          <p className="empty-state">Inga events ännu.</p>
        ) : (
          <div className="events-timeline">
            {events.map(event => (
              <Card key={event.id} className="event-item">
                <div className="event-time">
                  {new Date(event.timestamp).toLocaleString('sv-SE')}
                </div>
                <div className="event-content">
                  <div className="event-header">
                    <span className="event-type">{event.event_type}</span>
                    {event.actor && (
                      <span className="event-actor">av {event.actor}</span>
                    )}
                  </div>
                  {event.metadata && (
                    <div className="event-metadata">
                      <pre>{JSON.stringify(event.metadata, null, 2)}</pre>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ProjectDetail

