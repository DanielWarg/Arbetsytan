import { useState, useEffect } from 'react'
import { Badge } from '../ui/Badge'
import './Scout.css'

function Scout() {
  const [activeTab, setActiveTab] = useState('items')
  const [scoutItems, setScoutItems] = useState([])
  const [feeds, setFeeds] = useState([])
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [newFeedName, setNewFeedName] = useState('')
  const [newFeedUrl, setNewFeedUrl] = useState('')

  const username = 'admin'
  const password = 'password'
  const auth = btoa(`${username}:${password}`)

  useEffect(() => {
    if (activeTab === 'items') {
      fetchItems()
    } else {
      fetchFeeds()
    }
  }, [activeTab])

  const fetchItems = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/scout/items?hours=24&limit=50', {
        headers: {
          'Authorization': `Basic ${auth}`
        }
      })
      if (!response.ok) throw new Error('Failed to fetch items')
      const data = await response.json()
      setScoutItems(data)
    } catch (err) {
      console.error('Error fetching scout items:', err)
      setScoutItems([])
    } finally {
      setLoading(false)
    }
  }

  const fetchFeeds = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/scout/feeds', {
        headers: {
          'Authorization': `Basic ${auth}`
        }
      })
      if (!response.ok) throw new Error('Failed to fetch feeds')
      const data = await response.json()
      setFeeds(data)
    } catch (err) {
      console.error('Error fetching feeds:', err)
      setFeeds([])
    } finally {
      setLoading(false)
    }
  }

  const handleFetch = async () => {
    setFetching(true)
    try {
      const response = await fetch('http://localhost:8000/api/scout/fetch?mode=fixture', {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`
        }
      })
      if (!response.ok) throw new Error('Failed to fetch feeds')
      // Refresh items after fetch
      await fetchItems()
    } catch (err) {
      console.error('Error fetching feeds:', err)
      alert('Kunde inte uppdatera feeds')
    } finally {
      setFetching(false)
    }
  }

  const handleAddFeed = async () => {
    if (!newFeedName || !newFeedUrl) {
      alert('Fyll i både namn och URL')
      return
    }
    try {
      const response = await fetch('http://localhost:8000/api/scout/feeds', {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`,
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
      await fetchFeeds()
    } catch (err) {
      console.error('Error creating feed:', err)
      alert('Kunde inte skapa feed')
    }
  }

  const handleDisableFeed = async (feedId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/scout/feeds/${feedId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Basic ${auth}`
        }
      })
      if (!response.ok) throw new Error('Failed to disable feed')
      await fetchFeeds()
    } catch (err) {
      console.error('Error disabling feed:', err)
      alert('Kunde inte inaktivera feed')
    }
  }

  return (
    <div className="scout-page">
      <div className="scout-header">
        <h1 className="scout-title">Scout</h1>
      </div>

      <div className="scout-tabs">
        <button
          className={`scout-tab ${activeTab === 'items' ? 'active' : ''}`}
          onClick={() => setActiveTab('items')}
        >
          Senaste 24h
        </button>
        <button
          className={`scout-tab ${activeTab === 'feeds' ? 'active' : ''}`}
          onClick={() => setActiveTab('feeds')}
        >
          Källor
        </button>
      </div>

      {activeTab === 'items' && (
        <div className="scout-content">
          <div className="scout-actions">
            <button
              className="scout-fetch-btn"
              onClick={handleFetch}
              disabled={fetching}
            >
              {fetching ? 'Uppdaterar...' : 'Uppdatera nu'}
            </button>
          </div>

          {loading ? (
            <p className="scout-loading">Laddar...</p>
          ) : scoutItems.length > 0 ? (
            <div className="scout-items-list-full">
              {scoutItems.map(item => (
                <div key={item.id} className="scout-item-full">
                  <Badge variant="normal" className="scout-item-badge">
                    {item.raw_source}
                  </Badge>
                  <a
                    href={item.link}
                    target="_blank"
                    rel="noopener"
                    className="scout-item-link"
                  >
                    {item.title}
                  </a>
                  <span className="scout-item-time-full">
                    {new Date(item.published_at || item.fetched_at).toLocaleString('sv-SE', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="scout-empty-full">Inga leads</p>
          )}
        </div>
      )}

      {activeTab === 'feeds' && (
        <div className="scout-content">
          <div className="scout-feeds-form">
            <h3 className="scout-feeds-form-title">Lägg till feed</h3>
            <div className="scout-feeds-form-fields">
              <input
                type="text"
                placeholder="Namn"
                value={newFeedName}
                onChange={(e) => setNewFeedName(e.target.value)}
                className="scout-feeds-input"
              />
              <input
                type="text"
                placeholder="URL"
                value={newFeedUrl}
                onChange={(e) => setNewFeedUrl(e.target.value)}
                className="scout-feeds-input"
              />
              <button
                className="scout-feeds-add-btn"
                onClick={handleAddFeed}
              >
                Lägg till
              </button>
            </div>
          </div>

          {loading ? (
            <p className="scout-loading">Laddar...</p>
          ) : feeds.length > 0 ? (
            <div className="scout-feeds-list">
              {feeds.map(feed => (
                <div key={feed.id} className="scout-feed-item">
                  <div className="scout-feed-info">
                    <span className="scout-feed-name">{feed.name}</span>
                    <span className="scout-feed-url">{feed.url || '(ingen URL)'}</span>
                    {feed.is_enabled ? (
                      <Badge variant="normal" className="scout-feed-badge">Aktiverad</Badge>
                    ) : (
                      <Badge variant="normal" className="scout-feed-badge disabled">Inaktiverad</Badge>
                    )}
                  </div>
                  {feed.is_enabled && (
                    <button
                      className="scout-feed-disable-btn"
                      onClick={() => handleDisableFeed(feed.id)}
                    >
                      Inaktivera
                    </button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="scout-empty-full">Inga feeds</p>
          )}
        </div>
      )}
    </div>
  )
}

export default Scout
