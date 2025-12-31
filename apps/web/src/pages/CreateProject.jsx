import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Input, Textarea } from '../ui/Input'
import { Select } from '../ui/Select'
import './CreateProject.css'

function CreateProject() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [classification, setClassification] = useState('normal')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setCreating(true)

    try {
      const username = 'admin'
      const password = 'password'
      const auth = btoa(`${username}:${password}`)
      
      const response = await fetch('http://localhost:8000/api/projects', {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          classification: classification
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to create project')
      }
      
      const project = await response.json()
      navigate(`/projects/${project.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <Link to="/projects" className="back-link">← Tillbaka till projekt</Link>
          <h1>Skapa nytt projekt</h1>
        </div>
      </div>

      <Card className="create-project-form">
        <form onSubmit={handleSubmit}>
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

          <div className="form-group">
            <label htmlFor="description">Beskrivning</label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Valfri beskrivning av projektet"
              rows="4"
            />
          </div>

          <div className="form-group">
            <label htmlFor="classification">Klassificering</label>
            <Select
              id="classification"
              value={classification}
              onChange={(e) => setClassification(e.target.value)}
            >
              <option value="normal">Normal</option>
              <option value="sensitive">Känslig</option>
              <option value="source-sensitive">Källkänslig</option>
            </Select>
            <p className="form-hint">
              Klassificerade projekt har striktare åtkomstkontroll och säkerhetsregler enligt SECURITY_MODEL.md.
            </p>
          </div>

          <div className="form-actions">
            <Link to="/projects">
              <Button type="button" variant="secondary">Avbryt</Button>
            </Link>
            <Button type="submit" variant="success" disabled={!name.trim() || creating}>
              {creating ? 'Skapar...' : 'Skapa projekt'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}

export default CreateProject

