import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Badge } from '../ui/Badge'
import { ArrowLeft, Info } from 'lucide-react'
import './DocumentView.css'

function DocumentView() {
  const { projectId, documentId } = useParams()
  const [document, setDocument] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchDocument = async () => {
      try {
        const username = 'admin'
        const password = 'password'
        const auth = btoa(`${username}:${password}`)

        const response = await fetch(`http://localhost:8000/api/documents/${documentId}`, {
          headers: { 'Authorization': `Basic ${auth}` }
        })

        if (!response.ok) throw new Error('Failed to fetch document')

        const data = await response.json()
        setDocument(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchDocument()
  }, [documentId])

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
    if (classification === 'sensitive' || classification === 'source-sensitive') {
      return 'sensitive'
    }
    return 'normal'
  }

  if (loading) return <div className="document-page">Laddar...</div>
  if (error) return <div className="document-page">Fel: {error}</div>
  if (!document) return <div className="document-page">Dokument hittades inte</div>

  return (
    <div className="document-page">
      <div className="document-content">
        <div className="document-header-sticky">
          <Link to={`/projects/${projectId}`} className="document-back-link">
            <ArrowLeft size={16} />
            <span>Tillbaka till projekt</span>
          </Link>
          <div className="document-header-info">
            <div className="document-title-row">
              <h1 className="document-title">{document.filename}</h1>
              <Badge variant={getClassificationVariant(document.classification)}>
                {getClassificationLabel(document.classification)}
              </Badge>
            </div>
            <div className="document-meta">
              <div className="document-meta-masked">
                <span className="document-meta-label">Maskad vy</span>
                <div className="document-meta-tooltip-container">
                  <Info size={14} className="document-meta-info-icon" />
                  <div className="document-meta-tooltip">
                    Originalmaterial bevaras i säkert lager och exponeras aldrig i arbetsytan. All känslig information är automatiskt maskerad.
                  </div>
                </div>
              </div>
              <span className="document-meta-separator">•</span>
              <span className="document-meta-date">
                {new Date(document.created_at).toLocaleDateString('sv-SE')}
              </span>
            </div>
          </div>
        </div>
        <div className="document-text">
          {document.masked_text.split('\n').map((line, index) => {
            // Show enhancement notice after "Sammanfattning" or "Nyckelpunkter" headings
            const isSummaryHeading = line.trim() === '## Sammanfattning'
            const isKeyPointsHeading = line.trim() === '## Nyckelpunkter'
            const isFullTranscriptHeading = line.trim() === '## Fullständigt transkript'
            
            return (
              <React.Fragment key={index}>
                <p className="document-line">
                  {line || '\u00A0'}
                </p>
                {isSummaryHeading && (
                  <p className="document-enhancement-notice">
                    Sammanfattning och nyckelpunkter är språkligt förtydligade. Originaltranskript bevaras.
                  </p>
                )}
              </React.Fragment>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default DocumentView

