import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Modal } from '../ui/Modal'
import CreateProject from './CreateProject'
import CreateProjectFromFeed from './CreateProjectFromFeed'
import { getDueUrgency } from '../lib/urgency'
import { FolderPlus, Folder, Search, Calendar, Eye, Lock, FileText, ArrowRight, RefreshCw, Plus, Trash2, ExternalLink, Rss } from 'lucide-react'
import './ProjectsList.css'

function ProjectsList() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showCreateFromFeedModal, setShowCreateFromFeedModal] = useState(false)
  const [createFromFeedUrl, setCreateFromFeedUrl] = useState('')
  const [createFromFeedName, setCreateFromFeedName] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [scoutItems, setScoutItems] = useState([])
  const [scoutFetching, setScoutFetching] = useState(false)
  const [showScoutModal, setShowScoutModal] = useState(false)
  const [scoutModalActiveTab, setScoutModalActiveTab] = useState('items')
  const [scoutModalItems, setScoutModalItems] = useState([])
  const [scoutModalFeeds, setScoutModalFeeds] = useState([])
  const [scoutModalLoading, setScoutModalLoading] = useState(false)
  const [scoutModalFetching, setScoutModalFetching] = useState(false)
  const [newFeedName, setNewFeedName] = useState('')
  const [newFeedUrl, setNewFeedUrl] = useState('')

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

  useEffect(() => {
    const fetchScoutItems = async () => {
      try {
        const username = 'admin'
        const password = 'password'
        const auth = btoa(`${username}:${password}`)
        
        const response = await fetch('http://localhost:8000/api/scout/items?hours=168&limit=50', {
          headers: {
            'Authorization': `Basic ${auth}`
          },
          credentials: 'omit'
        })
        
        if (!response.ok) throw new Error('Failed to fetch scout items')
        
        const data = await response.json()
        setScoutItems(data)
      } catch (err) {
        console.error('Error fetching scout items:', err)
        setScoutItems([])
      }
    }
    
    // Fetch immediately
    fetchScoutItems()
    
    // Auto-update items every 5 minutes
    const itemsInterval = setInterval(fetchScoutItems, 5 * 60 * 1000)
    
    // Auto-fetch feeds every 30 minutes
    const fetchFeeds = async () => {
      try {
        const username = 'admin'
        const password = 'password'
        const auth = btoa(`${username}:${password}`)
        
        await fetch('http://localhost:8000/api/scout/fetch', {
          method: 'POST',
          headers: {
            'Authorization': `Basic ${auth}`
          }
        })
        // Refresh items after fetching feeds
        fetchScoutItems()
      } catch (err) {
        console.error('Error auto-fetching feeds:', err)
      }
    }
    
    // Fetch feeds every 30 minutes
    const feedsInterval = setInterval(fetchFeeds, 30 * 60 * 1000)
    
    return () => {
      clearInterval(itemsInterval)
      clearInterval(feedsInterval)
    }
  }, [])

  // Scout box fetch function
  const handleScoutBoxFetch = async () => {
    setScoutFetching(true)
    try {
      const username = 'admin'
      const password = 'password'
      const auth = btoa(`${username}:${password}`)
      
      await fetch('http://localhost:8000/api/scout/fetch', {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`
        }
      })
      
      // Refresh items after fetching feeds
      const response = await fetch('http://localhost:8000/api/scout/items?hours=168&limit=50', {
        headers: {
          'Authorization': `Basic ${auth}`
        },
        credentials: 'omit'
      })
      
      if (response.ok) {
        const data = await response.json()
        setScoutItems(data)
      }
    } catch (err) {
      console.error('Error fetching scout feeds:', err)
    } finally {
      setScoutFetching(false)
    }
  }

  // Scout modal functions
  const scoutAuth = btoa('admin:password')

  const fetchScoutModalItems = useCallback(async () => {
    setScoutModalLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/scout/items?hours=168&limit=50', {
        headers: {
          'Authorization': `Basic ${scoutAuth}`
        }
      })
      if (!response.ok) throw new Error('Failed to fetch items')
      const data = await response.json()
      setScoutModalItems(data)
    } catch (err) {
      console.error('Error fetching scout items:', err)
      setScoutModalItems([])
    } finally {
      setScoutModalLoading(false)
    }
  }, [scoutAuth])

  const fetchScoutModalFeeds = async () => {
    setScoutModalLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/scout/feeds', {
        headers: {
          'Authorization': `Basic ${scoutAuth}`
        }
      })
      if (!response.ok) throw new Error('Failed to fetch feeds')
      const data = await response.json()
      setScoutModalFeeds(data)
    } catch (err) {
      console.error('Error fetching feeds:', err)
      setScoutModalFeeds([])
    } finally {
      setScoutModalLoading(false)
    }
  }

  useEffect(() => {
    if (showScoutModal) {
      if (scoutModalActiveTab === 'items') {
        fetchScoutModalItems()
        
        // Auto-update items every 2 minutes when modal is open
        const itemsInterval = setInterval(fetchScoutModalItems, 2 * 60 * 1000)
        return () => clearInterval(itemsInterval)
      } else {
        fetchScoutModalFeeds()
      }
    }
  }, [showScoutModal, scoutModalActiveTab, fetchScoutModalItems])

  const handleScoutModalFetch = async () => {
    setScoutModalFetching(true)
    try {
      const response = await fetch('http://localhost:8000/api/scout/fetch', {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${scoutAuth}`
        }
      })
      if (!response.ok) throw new Error('Failed to fetch feeds')
      await fetchScoutModalItems()
    } catch (err) {
      console.error('Error fetching feeds:', err)
      alert('Kunde inte uppdatera feeds')
    } finally {
      setScoutModalFetching(false)
    }
  }

  const handleScoutModalAddFeed = async () => {
    if (!newFeedName || !newFeedUrl) {
      alert('Fyll i både namn och URL')
      return
    }
    try {
      const response = await fetch('http://localhost:8000/api/scout/feeds', {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${scoutAuth}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: newFeedName,
          url: newFeedUrl
        })
      })
      if (!response.ok) throw new Error('Failed to create feed')
      setNewFeedName('')
      setNewFeedUrl('')
      await fetchScoutModalFeeds()
    } catch (err) {
      console.error('Error creating feed:', err)
      alert('Kunde inte skapa feed')
    }
  }

  const handleScoutModalDisableFeed = async (feedId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/scout/feeds/${feedId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Basic ${scoutAuth}`
        }
      })
      if (!response.ok) throw new Error('Failed to disable feed')
      await fetchScoutModalFeeds()
    } catch (err) {
      console.error('Error disabling feed:', err)
      alert('Kunde inte inaktivera feed')
    }
  }

  const handleCreateSuccess = (project) => {
    setShowCreateModal(false)
    fetchProjects()
    navigate(`/projects/${project.id}`)
  }

  const handleCreateProjectFromFeed = (feedUrl, feedName) => {
    setCreateFromFeedUrl(feedUrl)
    setCreateFromFeedName(feedName)
    setShowScoutModal(false)
    setShowCreateFromFeedModal(true)
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
  const filteredProjects = projects
    .filter(project => 
      project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (project.description && project.description.toLowerCase().includes(searchQuery.toLowerCase()))
    )
    .sort((a, b) => {
      // Sort by due_date: projects with due_date first, then by date (earliest first)
      if (!a.due_date && !b.due_date) return 0
      if (!a.due_date) return 1 // a without due_date goes last
      if (!b.due_date) return -1 // b without due_date goes last
      
      // Both have due_date, sort by date (earliest first)
      const dateA = new Date(a.due_date).getTime()
      const dateB = new Date(b.due_date).getTime()
      return dateA - dateB
    })

  // Get last updated project
  const lastUpdatedProject = projects.length > 0 
    ? projects.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))[0]
    : null

  return (
    <div className="projects-list-page">
      <div className="projects-header">
        <h2 className="projects-title">Kontrollrum</h2>
      </div>

      {/* Scout - Full Width */}
      <Card className="overview-card overview-card-fullwidth scout-card-fullwidth">
        <div className="overview-card-header">
          <h3 className="overview-card-title">Scout – senaste 7 dagar</h3>
        </div>
        <div className="overview-card-content">
            {scoutItems.length > 0 ? (
              <div className="scout-widget-list">
                {scoutItems.map(item => (
                <a
                  key={item.id}
                  href={item.link || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="scout-widget-item scout-widget-item-link"
                  onClick={(e) => {
                    if (!item.link) {
                      e.preventDefault()
                    }
                  }}
                >
                  <Badge variant="normal" className="scout-widget-badge">{item.raw_source}</Badge>
                  <span className="scout-widget-title">{item.title}</span>
                  <span className="scout-widget-time">
                    {new Date(item.published_at || item.fetched_at).toLocaleString('sv-SE', { 
                      month: 'short', 
                      day: 'numeric', 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </span>
                </a>
              ))}
            </div>
          ) : (
            <div className="overview-empty-state">
              <p className="overview-empty-text">Inga leads</p>
            </div>
          )}
          <div className="scout-box-actions">
            <button 
              className="btn-scout-refresh"
              onClick={handleScoutBoxFetch}
              disabled={scoutFetching}
              title="Uppdatera feeds"
            >
              <RefreshCw size={14} className={scoutFetching ? 'spinning' : ''} />
              <span>{scoutFetching ? 'Uppdaterar...' : 'Uppdatera'}</span>
            </button>
            <button 
              className="btn-overview"
              onClick={() => setShowScoutModal(true)}
            >
              <Eye size={16} />
              <span>Visa alla</span>
            </button>
          </div>
        </div>
      </Card>

      {/* Dina Projekt - Full Width */}
      <Card className="overview-card overview-card-fullwidth projects-card-fullwidth">
        <div className="overview-card-header">
          <h3 className="overview-card-title">Dina Projekt</h3>
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
              {filteredProjects.map(project => {
                const statusLabels = {
                  'research': 'Research',
                  'processing': 'Bearbetning',
                  'fact_check': 'Faktakoll',
                  'ready': 'Klar',
                  'archived': 'Arkiverad'
                }
                const urgency = getDueUrgency(project.due_date)
                
                return (
                  <Link 
                    key={project.id} 
                    to={`/projects/${project.id}`} 
                    className="project-item-compact"
                  >
                    <div className="project-item-compact-content">
                      <div className="project-item-main">
                        <Folder size={14} className="project-item-icon" />
                        <span className="project-item-name">{project.name}</span>
                      </div>
                      <div className="project-item-meta">
                        <span className="project-status-badge">
                          {statusLabels[project.status] || 'Research'}
                        </span>
                        {project.due_date && (
                          <span className={`project-due-date-badge ${urgency.variant}`}>
                            {urgency.normalizedDate}
                            {urgency.label && ` • ${urgency.label}`}
                          </span>
                        )}
                      </div>
                    </div>
                  </Link>
                )
              })}
            </div>
          )}
          <Link to="/projects" className="btn-overview">
            <Eye size={16} />
            <span>Visa alla</span>
          </Link>
        </div>
      </Card>

      {/* Overview Grid - Other Widgets */}
      <div className="overview-grid">
        {/* Projekt Widget */}
        <Card className="overview-card">
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
            <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
              <button 
                className="btn-create-project btn-create-project-inline"
                onClick={() => setShowCreateModal(true)}
              >
                <FolderPlus size={16} />
                <span>Nytt projekt</span>
              </button>
              <button 
                className="btn-create-project btn-create-project-inline"
                onClick={() => setShowCreateFromFeedModal(true)}
              >
                <Plus size={16} />
                <span>Skapa projekt från feed</span>
              </button>
            </div>
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

      <Modal
        isOpen={showCreateFromFeedModal}
        onClose={() => setShowCreateFromFeedModal(false)}
        title="Skapa projekt från feed"
      >
        <CreateProjectFromFeed
          onClose={() => {
            setShowCreateFromFeedModal(false)
            setCreateFromFeedUrl('')
            setCreateFromFeedName('')
          }}
          initialFeedUrl={createFromFeedUrl}
          initialProjectName={createFromFeedName}
        />
      </Modal>

      <Modal
        isOpen={showScoutModal}
        onClose={() => setShowScoutModal(false)}
        title="Scout – Senaste 7 dagar"
      >
        <div className="scout-modal-content">
          <div className="scout-modal-tabs">
            <button
              className={`scout-modal-tab ${scoutModalActiveTab === 'items' ? 'active' : ''}`}
              onClick={() => setScoutModalActiveTab('items')}
            >
              Senaste 7 dagar
            </button>
            <button
              className={`scout-modal-tab ${scoutModalActiveTab === 'feeds' ? 'active' : ''}`}
              onClick={() => setScoutModalActiveTab('feeds')}
            >
              Källor
            </button>
          </div>

          {scoutModalActiveTab === 'items' && (
            <div className="scout-modal-tab-content">
              <div className="scout-modal-actions">
                <button
                  className="scout-modal-fetch-btn"
                  onClick={handleScoutModalFetch}
                  disabled={scoutModalFetching}
                >
                  <RefreshCw size={14} />
                  <span>{scoutModalFetching ? 'Uppdaterar...' : 'Uppdatera nu'}</span>
                </button>
              </div>

              {scoutModalLoading ? (
                <p className="scout-modal-loading">Laddar...</p>
              ) : scoutModalItems.length > 0 ? (
                <div className="scout-modal-items-list">
                  {scoutModalItems.map(item => (
                    <div key={item.id} className="scout-modal-item">
                      <div className="scout-modal-item-header">
                        <Badge variant="normal">{item.raw_source}</Badge>
                        <span className="scout-modal-item-time">
                          {new Date(item.published_at || item.fetched_at).toLocaleString('sv-SE', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </span>
                      </div>
                      <a
                        href={item.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="scout-modal-item-link"
                      >
                        <span className="scout-modal-item-title">{item.title}</span>
                        <ExternalLink size={14} />
                      </a>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="scout-modal-empty">Inga leads hittades för de senaste 7 dagarna.</p>
              )}
            </div>
          )}

          {scoutModalActiveTab === 'feeds' && (
            <div className="scout-modal-tab-content">
              <div className="scout-modal-feeds-form">
                <h3 className="scout-modal-feeds-form-title">Lägg till feed</h3>
                <div className="scout-modal-feeds-form-fields">
                  <input
                    type="text"
                    placeholder="Namn på källa (t.ex. Polisen Göteborg)"
                    value={newFeedName}
                    onChange={(e) => setNewFeedName(e.target.value)}
                    className="scout-modal-feeds-input"
                  />
                  <input
                    type="url"
                    placeholder="RSS-URL (t.ex. https://polisen.se/rss)"
                    value={newFeedUrl}
                    onChange={(e) => setNewFeedUrl(e.target.value)}
                    className="scout-modal-feeds-input"
                  />
                  <button
                    className="scout-modal-feeds-add-btn"
                    onClick={handleScoutModalAddFeed}
                  >
                    <Plus size={14} />
                    <span>Lägg till källa</span>
                  </button>
                </div>
              </div>

              {scoutModalLoading ? (
                <p className="scout-modal-loading">Laddar...</p>
              ) : scoutModalFeeds.length > 0 ? (
                <div className="scout-modal-feeds-list">
                  {scoutModalFeeds.map(feed => (
                    <div key={feed.id} className={`scout-modal-feed-item ${!feed.is_enabled ? 'disabled' : ''}`}>
                      <div className="scout-modal-feed-info">
                        <span className="scout-modal-feed-name">{feed.name}</span>
                        <span className="scout-modal-feed-url">{feed.url || 'Ingen URL angiven'}</span>
                      </div>
                      <div className="scout-modal-feed-actions">
                        {!feed.is_enabled && <Badge variant="danger">Inaktiverad</Badge>}
                        {feed.url && (
                          <button
                            className="scout-modal-feed-create-project-btn"
                            onClick={() => handleCreateProjectFromFeed(feed.url, feed.name)}
                            title="Skapa projekt från denna feed"
                          >
                            <Rss size={16} />
                            <span>Skapa projekt</span>
                          </button>
                        )}
                        <button
                          className="scout-modal-feed-disable-btn"
                          onClick={() => handleScoutModalDisableFeed(feed.id)}
                          title="Inaktivera feed"
                          disabled={!feed.is_enabled}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="scout-modal-empty">Inga källor tillagda.</p>
              )}
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}

export default ProjectsList

