import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Modal } from '../ui/Modal'
import CreateProject from './CreateProject'
import { FolderPlus, Folder } from 'lucide-react'
import './ProjectsList.css'

function ProjectsList() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)

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

  const isDueSoon = (dueDate) => {
    if (!dueDate) return false
    const due = new Date(dueDate)
    const today = new Date()
    const daysUntilDue = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    return daysUntilDue >= 0 && daysUntilDue <= 7
  }

  return (
    <div className="projects-list-page">
      <div className="projects-header">
        <h2 className="projects-title">Dina Projekt</h2>
        <button 
          className="btn-create-project"
          onClick={() => setShowCreateModal(true)}
        >
          <FolderPlus size={16} />
          <span>Nytt projekt</span>
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="projects-empty">
          <Folder size={48} className="empty-icon" />
          <p className="empty-title">Inga projekt hittades</p>
          <p className="empty-text">Skapa ditt första projekt för att organisera transkriptioner.</p>
          <button 
            className="btn-create-project"
            onClick={() => setShowCreateModal(true)}
          >
            <FolderPlus size={16} />
            <span>Nytt projekt</span>
          </button>
        </div>
      ) : (
        <div className="projects-grid">
          {projects.map(project => (
            <Link 
              key={project.id} 
              to={`/projects/${project.id}`} 
              className="project-card-link"
            >
              <Card interactive className="project-card">
                <div className="project-card-top">
                  <Folder size={18} className="project-icon" />
                  <Badge variant={project.classification === 'normal' ? 'normal' : project.classification === 'sensitive' ? 'sensitive' : 'source-sensitive'}>
                    {getClassificationLabel(project.classification)}
                  </Badge>
                </div>
                <h3 className="project-card-title">{project.name}</h3>
                <div className="project-card-meta">
                  {project.start_date && (
                    <p>Start: {new Date(project.start_date).toLocaleDateString('sv-SE')}</p>
                  )}
                  {project.due_date && (
                    <p className={isDueSoon(project.due_date) ? 'project-due-soon' : ''}>
                      Deadline: {new Date(project.due_date).toLocaleDateString('sv-SE')}
                      {isDueSoon(project.due_date) && ' ⚠️'}
                    </p>
                  )}
                  {project.description && (
                    <p className="project-card-description">{project.description}</p>
                  )}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

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

