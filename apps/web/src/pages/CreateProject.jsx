import { useState, useEffect } from 'react'
import { Button } from '../ui/Button'
import { Input, Textarea } from '../ui/Input'
import { Select } from '../ui/Select'
import { Badge } from '../ui/Badge'
import { Info } from 'lucide-react'
import './CreateProject.css'

function CreateProject({ onClose, onSuccess, project = null }) {
  const isEditMode = project !== null
  
  const [name, setName] = useState(project?.name || '')
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0])
  const [dueDate, setDueDate] = useState('')
  const [description, setDescription] = useState(project?.description || '')
  const [tags, setTags] = useState('')
  const [classification, setClassification] = useState(project?.classification || 'normal')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState(null)
  
  // Update state when project prop changes (for edit mode)
  useEffect(() => {
    if (project) {
      setName(project.name || '')
      setDescription(project.description || '')
      setClassification(project.classification || 'normal')
      if (project.due_date) {
        const dueDate = new Date(project.due_date)
        setDueDate(dueDate.toISOString().split('T')[0])
      } else {
        setDueDate('')
      }
      if (project.tags && Array.isArray(project.tags)) {
        setTags(project.tags.join(', '))
      } else {
        setTags('')
      }
    }
  }, [project])

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

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setCreating(true)

    try {
      const username = 'admin'
      const password = 'password'
      const auth = btoa(`${username}:${password}`)
      
      const url = isEditMode 
        ? `http://localhost:8000/api/projects/${project.id}`
        : 'http://localhost:8000/api/projects'
      
      const method = isEditMode ? 'PUT' : 'POST'
      
      // Parse tags from comma-separated string
      // Normalize: trim, remove empty, limit to 10 tags
      const tagsArray = tags.trim() 
        ? tags.split(',').map(t => t.trim()).filter(t => t.length > 0).slice(0, 10)
        : []
      
      const response = await fetch(url, {
        method: method,
        headers: {
          'Authorization': `Basic ${auth}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          classification: classification,
          due_date: dueDate ? new Date(dueDate).toISOString() : null,
          tags: tagsArray
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to ${isEditMode ? 'update' : 'create'} project`)
      }
      
      const updatedProject = await response.json()
      if (onSuccess) {
        onSuccess(updatedProject)
      }
      if (onClose) {
        onClose()
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="create-project-form">
      {error && (
        <div className="form-error">
          {error}
        </div>
      )}

      <div className="form-group">
        <label htmlFor="name">Projektnamn *</label>
        <Input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          placeholder="T.ex. Intervju med Anna Svensson"
          autoFocus
        />
      </div>

      <div className="form-group form-group-inline">
        <div className="form-group-half">
          <label htmlFor="startDate">Startdatum</label>
          <Input
            id="startDate"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div className="form-group-half">
          <label htmlFor="dueDate">Deadline (valfritt)</label>
          <Input
            id="dueDate"
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="classification">Klassificering</label>
        <Select
          id="classification"
          value={classification}
          onChange={(e) => setClassification(e.target.value)}
        >
          <option value="normal">Offentlig</option>
          <option value="sensitive">Känslig</option>
          <option value="source-sensitive">Källkritisk</option>
        </Select>
        <div className="classification-badge-container">
          <Badge variant={getClassificationVariant(classification)}>
            {getClassificationLabel(classification)}
          </Badge>
          <Info size={14} className="classification-info-icon" />
        </div>
        <p className="form-hint">
          Klassificering påverkar åtkomst, loggning och export enligt säkerhetsmodellen.
        </p>
      </div>

      <div className="form-group">
        <label htmlFor="description">Beskrivning (valfritt)</label>
        <Textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Valfri beskrivning av projektet"
          rows="3"
        />
      </div>

      <div className="form-group">
        <label htmlFor="tags">Taggar (valfritt, separera med komma)</label>
        <Input
          id="tags"
          type="text"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="T.ex. intervju, kommun, skola"
        />
      </div>

      <div className="form-actions">
        <Button type="button" variant="secondary" onClick={onClose}>
          Avbryt
        </Button>
        <Button type="submit" variant="success" disabled={!name.trim() || creating}>
          {creating ? (isEditMode ? 'Uppdaterar...' : 'Skapar...') : (isEditMode ? 'Spara ändringar' : 'Skapa projekt')}
        </Button>
      </div>
    </form>
  )
}

export default CreateProject
