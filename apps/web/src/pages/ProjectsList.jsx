import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../ui/Button'
import { FolderPlus, Folder } from 'lucide-react'
import './ProjectsList.css'

function ProjectsList() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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

  if (loading) return <div className="projects-page">Laddar...</div>
  if (error) return <div className="projects-page">Fel: {error}</div>

  const getClassificationLabel = (classification) => {
    if (classification === 'sensitive' || classification === 'source-sensitive') {
      return 'Klassificerat'
    }
    return 'Offentligt'
  }

  const getClassificationClass = (classification) => {
    if (classification === 'sensitive' || classification === 'source-sensitive') {
      return 'badge-sensitive'
    }
    return 'badge-normal'
  }

  return (
    <div className="projects-page">
      <div className="projects-header">
        <h2 className="projects-title">Dina Projekt</h2>
        <Link to="/projects/new">
          <button className="btn-create-project">
            <FolderPlus size={16} />
            <span>Nytt projekt</span>
          </button>
        </Link>
      </div>

      {projects.length === 0 ? (
        <div className="projects-empty">
          <Folder size={48} className="empty-icon" />
          <p className="empty-title">Inga projekt hittades</p>
          <p className="empty-text">Skapa ditt första projekt för att organisera transkriptioner.</p>
          <Link to="/projects/new">
            <button className="btn-create-project">
              <FolderPlus size={16} />
              <span>Nytt projekt</span>
            </button>
          </Link>
        </div>
      ) : (
        <div className="projects-grid">
          {projects.map(project => (
            <Link 
              key={project.id} 
              to={`/projects/${project.id}`} 
              className="project-card-link"
            >
              <div className="project-card">
                <div className="project-card-top">
                  <Folder size={18} className="project-icon" />
                  <span className={`project-badge ${getClassificationClass(project.classification)}`}>
                    {getClassificationLabel(project.classification)}
                  </span>
                </div>
                <h3 className="project-card-title">{project.name}</h3>
                <div className="project-card-meta">
                  <p>Start: {project.created_at ? new Date(project.created_at).toLocaleDateString('sv-SE') : 'Ej startat'}</p>
                  {project.description && (
                    <p className="project-card-description">{project.description}</p>
                  )}
                  <p>Transkript: 0 | Filer: 0</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default ProjectsList

